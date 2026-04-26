"""
Advance Insights — Azure Functions API for Static Web Apps

⚠️  SUPERSEDED: This Azure Functions backend is superseded by the Container Apps
deployment (web/server.py + gunicorn). The single-container approach handles both
static files and API proxy. This file is retained for reference and potential
local SWA emulator testing.

Python v2 programming model. Proxies chat requests to Fabric Data Agent API
with SSE streaming, user info, and health check endpoints.

SWA manages auth — the x-ms-client-principal header provides user identity.
Fabric API auth uses DefaultAzureCredential (managed identity in prod, CLI creds locally).
"""

import azure.functions as func
import json
import logging
import os

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ── Configuration ────────────────────────────────────────────────────────

WORKSPACE_ID = os.environ.get(
    "FABRIC_WORKSPACE_ID", "82f53636-206f-4825-821b-bdaa8e089893"
)
FABRIC_API_BASE = os.environ.get(
    "FABRIC_API_BASE", "https://msitapi.fabric.microsoft.com/v1"
)
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"

# Cache assistant IDs per agent (singletons — no need to recreate)
_assistant_cache: dict[str, str] = {}


# ── Helpers ──────────────────────────────────────────────────────────────

def _get_client_principal(req: func.HttpRequest) -> dict | None:
    """Decode the SWA x-ms-client-principal header."""
    import base64
    header = req.headers.get("x-ms-client-principal")
    if not header:
        return None
    try:
        decoded = base64.b64decode(header)
        return json.loads(decoded)
    except Exception:
        return None


def _get_fabric_token() -> str:
    """Get a Fabric API access token via DefaultAzureCredential."""
    from azure.identity import DefaultAzureCredential
    credential = DefaultAzureCredential()
    token = credential.get_token(FABRIC_SCOPE)
    return token.token


def _fabric_api(method: str, path: str, token: str, payload: dict = None) -> dict:
    """Call a sub-path on the Fabric Data Agent OpenAI endpoint."""
    import urllib.request
    import uuid

    url = f"{path}?api-version=2024-05-01-preview"
    data = json.dumps(payload).encode("utf-8") if payload else None

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "ActivityId": str(uuid.uuid4()),
        },
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── /api/chat — Fabric Data Agent proxy with SSE ────────────────────────

@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    """
    Proxy chat requests to the Fabric Data Agent API.

    Streams SSE status updates back to the client. Azure Functions HTTP
    responses support streaming when returned as a full body — we build
    the SSE event stream and return it in one shot (Azure Functions v2
    doesn't support true generator-based streaming, so we accumulate
    events and flush them).

    For SWA deployment, consider upgrading to Azure Functions Flex
    Consumption with HTTP Streams for true SSE support.
    """
    import time
    import urllib.error

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body required"}),
            status_code=400,
            mimetype="application/json",
        )

    agent_id = body.get("agentId")
    messages = body.get("messages")

    if not agent_id or not messages:
        return func.HttpResponse(
            json.dumps({"error": "agentId and messages are required"}),
            status_code=400,
            mimetype="application/json",
        )

    user_message = messages[-1].get("content", "") if messages else ""
    if not user_message:
        return func.HttpResponse(
            json.dumps({"error": "No user message content"}),
            status_code=400,
            mimetype="application/json",
        )

    base_url = (
        f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}"
        f"/dataagents/{agent_id}/aiassistant/openai"
    )

    logging.info(f"Agent: {agent_id} | Message: {user_message[:80]}...")

    # Get Fabric API token
    try:
        token = _get_fabric_token()
    except Exception as e:
        logging.error(f"Auth failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Authentication failed: {str(e)}"}),
            status_code=401,
            mimetype="application/json",
        )

    def api_call(method: str, subpath: str, payload: dict = None) -> dict:
        return _fabric_api(method, f"{base_url}/{subpath}", token, payload)

    def sse_event(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    # Build SSE event stream
    events = []
    t0 = time.time()

    try:
        # 1. Get or create assistant (cached per agent)
        events.append(sse_event({"status": "connecting", "message": "Connecting to agent…"}))

        if agent_id in _assistant_cache:
            asst_id = _assistant_cache[agent_id]
            logging.info(f"Reusing cached assistant: {asst_id}")
        else:
            asst = api_call("POST", "assistants", {"model": "not used"})
            asst_id = asst["id"]
            _assistant_cache[agent_id] = asst_id
            logging.info(f"Created assistant: {asst_id}")

        # 2. Create thread + add message
        events.append(sse_event({"status": "sending", "message": "Sending your question…"}))

        thread = api_call("POST", "threads", {})
        thread_id = thread["id"]

        api_call("POST", f"threads/{thread_id}/messages", {
            "role": "user",
            "content": user_message,
        })

        # 3. Start run
        run = api_call("POST", f"threads/{thread_id}/runs", {
            "assistant_id": asst_id,
        })
        run_id = run["id"]
        logging.info(f"Run {run_id} started (status: {run['status']})")

        events.append(sse_event({"status": "processing", "message": "Agent is thinking…"}))

        # 4. Poll for completion
        poll_delays = [1, 1, 2, 2] + [3] * 36  # max ~2 min total
        for delay in poll_delays:
            time.sleep(delay)
            run = api_call("GET", f"threads/{thread_id}/runs/{run_id}")
            elapsed = round(time.time() - t0)

            if run["status"] not in ("queued", "in_progress"):
                break

            if elapsed > 5:
                events.append(sse_event({
                    "status": "processing",
                    "message": f"Agent is working… ({elapsed}s)",
                }))

        logging.info(f"Run completed in {round(time.time() - t0)}s (status: {run['status']})")

        if run["status"] != "completed":
            events.append(sse_event({
                "error": f"Agent run ended with status: {run['status']}",
            }))
            return func.HttpResponse(
                "".join(events),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        # 5. Retrieve response
        events.append(sse_event({"status": "reading", "message": "Reading response…"}))

        msgs = api_call("GET", f"threads/{thread_id}/messages")

        reply = ""
        for m in msgs.get("data", []):
            if m.get("role") == "assistant":
                content = m.get("content", [])
                if content:
                    c = content[0]
                    if isinstance(c, dict) and "text" in c:
                        txt = c["text"]
                        reply = txt.get("value", str(txt)) if isinstance(txt, dict) else str(txt)
                    else:
                        reply = str(c)
                break

        if not reply:
            reply = "The agent completed but returned no response."

        events.append(sse_event({"content": reply, "elapsed": round(time.time() - t0)}))

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        logging.error(f"Fabric API error {e.code}: {error_body[:500]}")
        events.append(sse_event({"error": f"Fabric API returned {e.code}", "details": error_body}))
    except Exception as e:
        logging.error(f"Proxy error: {e}")
        events.append(sse_event({"error": str(e)}))

    return func.HttpResponse(
        "".join(events),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── /api/user — Authenticated user info ─────────────────────────────────

@app.route(route="user", methods=["GET"])
def user(req: func.HttpRequest) -> func.HttpResponse:
    """Return the authenticated user's info from SWA's client principal."""
    principal = _get_client_principal(req)

    if not principal:
        return func.HttpResponse(
            json.dumps({"authenticated": False}),
            status_code=401,
            mimetype="application/json",
        )

    # Extract claims
    claims = {c["typ"]: c["val"] for c in principal.get("claims", [])}

    return func.HttpResponse(
        json.dumps({
            "authenticated": True,
            "userId": principal.get("userId", ""),
            "userDetails": principal.get("userDetails", ""),
            "identityProvider": principal.get("identityProvider", ""),
            "name": claims.get("name", principal.get("userDetails", "")),
            "email": claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", ""),
        }),
        mimetype="application/json",
    )


# ── /api/health — Health check ──────────────────────────────────────────

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Basic health check — confirms the Functions API is running."""
    return func.HttpResponse(
        json.dumps({
            "status": "ok",
            "workspace": WORKSPACE_ID,
            "fabricApi": FABRIC_API_BASE,
        }),
        mimetype="application/json",
    )
