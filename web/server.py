"""
Advance Insights — Flask API + Static File Server

Serves the web app and proxies Fabric Data Agent API calls.
Runs both locally (python web/server.py) and in production (gunicorn).

Auth: ChainedTokenCredential (server-side, no user login flow)
  1. ManagedIdentityCredential — Azure Container Apps (automatic)
  2. AzureCliCredential — local dev after `az login`
  3. DeviceCodeCredential — Docker / headless (prints code to stdout)

Usage:
    # Local dev (az login first)
    az login
    python web/server.py

    # Docker / headless (follow device code prompt in terminal)
    docker-compose up
    gunicorn --bind 0.0.0.0:8000 server:app
"""

import json
import os
import sys
import io
import webbrowser
import threading

# Fix encoding on Windows consoles that use cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load .env file if python-dotenv is available (local dev convenience)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] Loaded .env file via python-dotenv")
except ImportError:
    pass  # dotenv not installed — env vars must be set externally

import uuid

from azure.identity import ChainedTokenCredential, ManagedIdentityCredential, AzureCliCredential, DeviceCodeCredential
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

# -- Configuration (env vars with sensible defaults) -------------------

WORKSPACE_ID = os.environ.get("FABRIC_WORKSPACE_ID", "82f53636-206f-4825-821b-bdaa8e089893")
FABRIC_API_BASE = os.environ.get("FABRIC_API_BASE", "https://api.fabric.microsoft.com/v1")
PORT = int(os.environ.get("PORT", "5000"))
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"

# -- Credential Chain (lazy init) --------------------------------------

_credential = None
_assistant_cache = {}  # agentId -> assistantId


def _get_credential():
    """Lazy-init ChainedTokenCredential: ManagedIdentity → AzureCli → DeviceCode."""
    global _credential
    if _credential is None:
        _credential = ChainedTokenCredential(
            ManagedIdentityCredential(),
            AzureCliCredential(),
            DeviceCodeCredential(),
        )
    return _credential


def get_fabric_token():
    """Get a Fabric API access token via the credential chain."""
    cred = _get_credential()
    return cred.get_token(FABRIC_SCOPE).token


COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
ROUTING_TENANT = os.environ.get("AZURE_OPENAI_TENANT_ID")  # Cross-tenant auth for LLM routing


def get_cognitive_token():
    """Get an Azure Cognitive Services access token.
    Uses az cli subprocess with explicit tenant when AZURE_OPENAI_TENANT_ID is set
    (needed when the OpenAI resource is in a different tenant than the default).
    Falls back to the credential chain otherwise.
    """
    if ROUTING_TENANT:
        import subprocess, shutil
        az_path = shutil.which("az") or "az"
        cmd = [az_path, "account", "get-access-token",
               "--resource", "https://cognitiveservices.azure.com",
               "--tenant", ROUTING_TENANT,
               "--query", "accessToken", "-o", "tsv"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
        if result.returncode == 0:
            return result.stdout.strip()
        raise RuntimeError(f"az cli token failed: {result.stderr.strip()}")
    cred = _get_credential()
    return cred.get_token(COGNITIVE_SCOPE).token


# -- Flask App ---------------------------------------------------------

app = Flask(__name__, static_folder=WEB_DIR)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
CORS(app)


# -- API: LLM Routing (GPT-4o-mini via Foundry) ---------------------------

ROUTING_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")  # Foundry deployment URL
ROUTING_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")    # Only if not using managed identity

ROUTING_SYSTEM_PROMPT = """You route user questions to specialist agents for Advance Auto Parts' rewards loyalty program analytics.

Available agents (use these exact keys):

- pit-crew: Customer Service & Support — Analyzes CSR agent activity, member service patterns, and support operations. Provides activity breakdowns, member lookups, service records, escalation trends, complaint correlations, and resolution time analysis.

- gearup: Loyalty Program Manager — Monitors member health, engagement, tier distribution, points liability, and churn risk. Delivers tier breakdowns, at-risk member identification, points balance analysis, enrollment cohort behavior, and reward redemption patterns.

- ignition: Marketing & Promotions — Evaluates coupon campaign performance, promotion ROI, and tier-targeted marketing effectiveness. Provides redemption funnels, campaign comparisons, coupon liability reports, A/B test results, and reactivation metrics.

- partspro: Merchandising & Categories — Analyzes product performance, brand rankings, category trends, and return rates across the auto parts catalog. Delivers category comparisons, SKU-level detail, revenue concentration, cross-sell affinity, and margin insights.

- diehard: Store Operations — Tracks retail location performance, regional comparisons, channel mix (online vs. in-store), and operational metrics across the 500-store network. Provides store rankings, regional benchmarks, and return rate analysis.

Return a JSON array of agent keys that should handle the question.
For broad questions (e.g. "Q4 performance", "how's the business"), include ALL relevant agents.
For specific questions, pick 1-2 focused agents.
Return ONLY the JSON array, no explanation. Example: ["gearup", "ignition", "diehard"]"""


@app.route("/api/route", methods=["POST"])
def route_question():
    """
    Classify a question using GPT-4o-mini via Azure AI Foundry.
    Returns {"agents": ["agent-key", ...], "mode": "llm"}.
    Falls back gracefully if endpoint isn't configured.
    """
    import urllib.request
    import urllib.error

    if not ROUTING_ENDPOINT:
        return jsonify({"error": "LLM routing endpoint not configured", "agents": []}), 503

    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided", "agents": []}), 400

    # Build the chat completion request
    payload = json.dumps({
        "messages": [
            {"role": "system", "content": ROUTING_SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        "temperature": 0,
        "max_tokens": 50
    }).encode("utf-8")

    # Auth: prefer managed identity, fall back to API key
    headers = {"Content-Type": "application/json"}
    if ROUTING_API_KEY:
        headers["api-key"] = ROUTING_API_KEY
    else:
        token = get_cognitive_token()
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(ROUTING_ENDPOINT, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            agents = json.loads(content)
            # Validate agent keys
            valid = ["pit-crew", "gearup", "ignition", "partspro", "diehard"]
            agents = [a for a in agents if a in valid]
            return jsonify({"agents": agents, "mode": "llm"})
    except Exception as e:
        print(f"[WARN] LLM routing failed: {e}")
        return jsonify({"error": str(e), "agents": []}), 502


# -- API: Chat Proxy (SSE streaming) -----------------------------------

@app.route("/api/agents", methods=["GET"])
def get_agents():
    """Return the combined runtime agent configuration for the frontend."""
    def load_json_file(path, label):
        if not os.path.exists(path):
            rel_path = os.path.relpath(path, WEB_DIR)
            raise FileNotFoundError(f"{label} not found: {rel_path}")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            rel_path = os.path.relpath(path, WEB_DIR)
            raise ValueError(f"{label} contains invalid JSON: {rel_path}") from exc

    try:
        app_config = load_json_file(os.path.join(WEB_DIR, "app.json"), "Global config")
        agent_order = load_json_file(os.path.join(WEB_DIR, "agents", "_order.json"), "Agent order config")

        if not isinstance(app_config, dict):
            return jsonify({"error": "Invalid app config: app.json must contain a JSON object"}), 500
        if not isinstance(agent_order, list):
            return jsonify({"error": "Invalid agent order config: agents/_order.json must contain a JSON array"}), 500

        agents = {}
        executive_routing = {}

        for slug in agent_order:
            if not isinstance(slug, str) or not slug:
                return jsonify({"error": "Invalid agent order config: agents/_order.json must contain non-empty agent slugs"}), 500

            agent_config = load_json_file(
                os.path.join(WEB_DIR, "agents", slug, "agent.json"),
                f"Agent config for '{slug}'",
            )
            if not isinstance(agent_config, dict):
                return jsonify({"error": f"Invalid agent config: agents/{slug}/agent.json must contain a JSON object"}), 500

            agent_response = dict(agent_config)
            agent_response["icon"] = f"agents/{slug}/icon.svg"
            agents[slug] = agent_response

            routing_keywords = agent_config.get("routingKeywords") or []
            if routing_keywords:
                executive_routing[slug] = routing_keywords

        workspace = app_config.get("workspace") or {}
        auth = app_config.get("auth") or {}
        routing = app_config.get("routing") or {}
        llm_routing = routing.get("llmRouting")
        if llm_routing is None:
            llm_routing = routing.get("llm")
        if llm_routing is None and any(key in routing for key in ("llmEndpoint", "endpoint", "useProxy", "apiKey")):
            llm_routing = {
                "endpoint": routing.get("llmEndpoint", routing.get("endpoint")),
                "useProxy": routing.get("useProxy"),
                "apiKey": routing.get("apiKey"),
            }
        if llm_routing is None:
            llm_routing = app_config.get("llmRouting") or {}

        response = dict(app_config)
        response["workspace"] = workspace
        response["auth"] = auth
        response["routing"] = routing
        response["agents"] = agents
        response["agentOrder"] = agent_order
        response["useProxy"] = auth.get("useProxy", app_config.get("useProxy"))
        response["workspaceId"] = workspace.get("id", app_config.get("workspaceId"))
        response["fabricScopes"] = workspace.get("fabricScopes", app_config.get("fabricScopes", []))
        response["routingMode"] = routing.get("mode", app_config.get("routingMode"))
        response["llmRouting"] = llm_routing
        response["executiveRouting"] = executive_routing
        return jsonify(response)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/chat", methods=["POST"])
def chat_proxy():
    """
    Proxy chat requests to the Fabric Data Agent API using SSE streaming.

    Streams status updates to the client as the Assistants API flow progresses,
    so users see live feedback instead of a dead spinner.
    """
    import time
    import urllib.request
    import urllib.error

    body = request.get_json()
    if not body:
        return jsonify({"error": "Request body required"}), 400

    agent_id = body.get("agentId")
    messages = body.get("messages")

    if not agent_id or not messages:
        return jsonify({"error": "agentId and messages are required"}), 400

    user_message = messages[-1].get("content", "") if messages else ""
    if not user_message:
        return jsonify({"error": "No user message content"}), 400

    base_url = (
        f"{FABRIC_API_BASE}/workspaces/{WORKSPACE_ID}"
        f"/dataagents/{agent_id}/aiassistant/openai"
    )
    api_version = "api-version=2024-05-01-preview"

    print(f"[INFO] Agent: {agent_id}")
    print(f"[INFO] Message: {user_message[:80]}...")

    try:
        token = get_fabric_token()
    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 401

    def fabric_api(method, path, payload=None):
        """Call a sub-path on the Fabric Data Agent OpenAI endpoint."""
        url = f"{base_url}/{path}?{api_version}"
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

    def sse_event(data):
        """Format a Server-Sent Event."""
        return f"data: {json.dumps(data)}\n\n"

    def generate():
        """SSE generator -- streams status updates then the final response."""
        t0 = time.time()

        try:
            # 1. Get or create assistant (cached per agent)
            yield sse_event({"status": "connecting", "message": "Connecting to agent…"})

            if agent_id in _assistant_cache:
                asst_id = _assistant_cache[agent_id]
                print(f"[OK] Reusing cached assistant: {asst_id}")
            else:
                asst = fabric_api("POST", "assistants", {"model": "not used"})
                asst_id = asst["id"]
                _assistant_cache[agent_id] = asst_id
                print(f"[OK] Created assistant: {asst_id}")

            # 2. Create thread + add message
            yield sse_event({"status": "sending", "message": "Sending your question…"})

            thread = fabric_api("POST", "threads", {})
            thread_id = thread["id"]

            fabric_api("POST", f"threads/{thread_id}/messages", {
                "role": "user",
                "content": user_message,
            })

            # 3. Start run
            run = fabric_api("POST", f"threads/{thread_id}/runs", {
                "assistant_id": asst_id,
            })
            run_id = run["id"]
            print(f"[INFO] Run {run_id} started (status: {run['status']})")

            yield sse_event({"status": "processing", "message": "Agent is thinking…"})

            # 4. Poll with aggressive timing: 1s, 1s, 2s, 2s, then 3s
            poll_delays = [1, 1, 2, 2] + [3] * 36  # max ~2 min total
            for i, delay in enumerate(poll_delays):
                time.sleep(delay)
                run = fabric_api("GET", f"threads/{thread_id}/runs/{run_id}")
                elapsed = round(time.time() - t0)

                if run["status"] not in ("queued", "in_progress"):
                    break

                # Update client with elapsed time
                if elapsed > 5:
                    yield sse_event({
                        "status": "processing",
                        "message": f"Agent is working… ({elapsed}s)",
                    })

            # Extract token usage from completed run
            usage = run.get("usage") or {}
            print(f"[OK] Run completed in {round(time.time() - t0)}s (status: {run['status']}) usage={usage}")

            if run["status"] != "completed":
                yield sse_event({
                    "error": f"Agent run ended with status: {run['status']}",
                })
                return

            # 5. Retrieve run steps (real reasoning data)
            yield sse_event({"status": "reading", "message": "Reading response…"})

            try:
                steps = fabric_api("GET", f"threads/{thread_id}/runs/{run_id}/steps")
                print(f"[INFO] Raw run steps response: {json.dumps(steps, indent=2)[:2000]}")
                step_list = steps.get("data", [])
                if step_list:
                    reasoning_steps = []
                    for s in step_list:
                        step_detail = s.get("step_details", {})
                        step_type = step_detail.get("type", "unknown")
                        step_info = {
                            "id": s.get("id"),
                            "type": step_type,
                            "status": s.get("status"),
                            "created_at": s.get("created_at"),
                            "completed_at": s.get("completed_at"),
                        }
                        # Extract tool call details
                        if step_type == "tool_calls":
                            tool_calls = step_detail.get("tool_calls", [])
                            step_info["tool_calls"] = []
                            for tc in tool_calls:
                                tc_info = {
                                    "id": tc.get("id"),
                                    "type": tc.get("type"),
                                }
                                if tc.get("type") == "code_interpreter":
                                    ci = tc.get("code_interpreter", {})
                                    tc_info["input"] = ci.get("input", "")
                                    outputs = ci.get("outputs", [])
                                    tc_info["outputs"] = [
                                        o.get("logs", o.get("text", str(o)))
                                        for o in outputs
                                    ]
                                elif tc.get("type") == "retrieval":
                                    tc_info["retrieval"] = tc.get("retrieval", {})
                                elif tc.get("type") == "function":
                                    fn = tc.get("function", {})
                                    tc_info["function_name"] = fn.get("name", "")
                                    tc_info["arguments"] = fn.get("arguments", "")
                                    tc_info["output"] = fn.get("output", "")
                                step_info["tool_calls"].append(tc_info)
                        elif step_type == "message_creation":
                            mc = step_detail.get("message_creation", {})
                            step_info["message_id"] = mc.get("message_id")
                        reasoning_steps.append(step_info)
                    yield sse_event({"reasoning": reasoning_steps})
                    print(f"[INFO] Sent {len(reasoning_steps)} run steps to client")
            except Exception as e:
                print(f"[WARN] Could not fetch run steps: {e}")
                # Non-fatal -- continue to deliver the response

            # 6. Retrieve response

            msgs = fabric_api("GET", f"threads/{thread_id}/messages")
            print(f"[INFO] Raw messages response: {json.dumps(msgs, indent=2)[:2000]}")

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

            yield sse_event({
                "content": reply,
                "elapsed": round(time.time() - t0),
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                } if usage else None,
            })

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            print(f"[ERROR] Fabric API error {e.code}: {error_body[:500]}")
            yield sse_event({"error": f"Fabric API returned {e.code}", "details": error_body})
        except Exception as e:
            print(f"[ERROR] Proxy error: {e}")
            yield sse_event({"error": str(e)})

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# -- API: Auth Status -------------------------------------------------

@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    """Auth status — always authenticated (credential chain is server-side)."""
    return jsonify({
        "authenticated": True,
        "auth_mode": "credential_chain",
        "user": {"name": "Advance Insights User"},
    })


# -- API: User Info ---------------------------------------------------

@app.route("/api/user", methods=["GET"])
def get_user():
    """Return user info — always authenticated."""
    return jsonify({"authenticated": True, "name": "Advance Insights User"})


# -- API: Health Check -------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    """Health check — confirms the app is running."""
    return jsonify({
        "status": "ok",
        "auth": "credential_chain",
        "workspace": WORKSPACE_ID,
        "fabricApi": FABRIC_API_BASE,
    })


# -- Static File Serving -----------------------------------------------

@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEB_DIR, path)


# -- Entry Point (local dev only) --------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  Advance Insights — Local Dev Server")
    print("=" * 50)
    print(f"  Workspace: {WORKSPACE_ID}")
    print(f"  Auth:      Credential chain (ManagedIdentity \u2192 AzureCli \u2192 DeviceCode)")
    print(f"  Web dir:   {WEB_DIR}")
    print("=" * 50)

    try:
        print("\n[AUTH] Verifying Azure credentials...")
        print("[AUTH] If prompted, follow the device code instructions below.")
        get_fabric_token()
        print("[OK] Authenticated successfully!\n")
    except Exception as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        print("Run `az login` first, or follow device code instructions above.")
        sys.exit(1)

    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    print(f"\n[OK] Server running at http://localhost:{PORT}")
    print("   Press Ctrl+C to stop\n")

    app.run(host="0.0.0.0", port=PORT, debug=False)
