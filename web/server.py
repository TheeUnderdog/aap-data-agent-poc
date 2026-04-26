"""
Advance Insights — Flask API + Static File Server

Serves the web app and proxies Fabric Data Agent API calls.
Runs both locally (python web/server.py) and in production (gunicorn).

Auth:
  - Production: MSAL Entra ID auth (login/callback/logout flow)
  - Local dev:  InteractiveBrowserCredential (browser popup)

Fabric API:
  - Production: Managed identity via DefaultAzureCredential
  - Local dev:  InteractiveBrowserCredential fallback

Usage:
    # Local dev (no env vars needed — uses defaults + browser login)
    python web/server.py

    # Production (Container Apps via gunicorn)
    gunicorn --bind 0.0.0.0:8000 server:app
"""

import json
import os
import sys
import webbrowser
import threading
import uuid
import secrets

from flask import Flask, request, jsonify, send_from_directory, Response, redirect, session, url_for
from flask_cors import CORS

import msal
import jwt
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential, ChainedTokenCredential

# ── Configuration (env vars with sensible defaults) ──────────────────

WORKSPACE_ID = os.environ.get("FABRIC_WORKSPACE_ID", "82f53636-206f-4825-821b-bdaa8e089893")
FABRIC_SCOPE = os.environ.get("FABRIC_SCOPE", "https://api.fabric.microsoft.com/.default")
FABRIC_API_BASE = os.environ.get("FABRIC_API_BASE", "https://msitapi.fabric.microsoft.com/v1")
TENANT_ID = os.environ.get("ENTRA_TENANT_ID", "72f988bf-86f1-41af-91ab-2d7cd011db47")

# MSAL / Entra ID config (only needed in production)
ENTRA_CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID", "")
ENTRA_CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET", "")
ENTRA_AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
ENTRA_SCOPES = ["User.Read"]

# Flask session secret (generate random if not set)
SESSION_SECRET = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

PORT = int(os.environ.get("PORT", "5000"))
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

# Detect production mode: MSAL auth enabled when client ID is configured
IS_PRODUCTION = bool(ENTRA_CLIENT_ID)

# ── Fabric API Credential ────────────────────────────────────────────

_fabric_credential = None
_assistant_cache = {}  # agentId → assistantId


def _get_fabric_credential():
    """Get credential for Fabric API calls. Managed identity in prod, browser in dev."""
    global _fabric_credential
    if _fabric_credential is None:
        if IS_PRODUCTION:
            _fabric_credential = DefaultAzureCredential()
        else:
            _fabric_credential = ChainedTokenCredential(
                DefaultAzureCredential(exclude_interactive_browser_credential=True),
                InteractiveBrowserCredential(
                    tenant_id=TENANT_ID,
                    redirect_uri="http://localhost:8400",
                ),
            )
            # Force initial login in dev mode
            print("\n🔐 Opening browser for Azure login...")
            _fabric_credential.get_token(FABRIC_SCOPE)
            print("✅ Authenticated successfully!\n")
    return _fabric_credential


def get_fabric_token():
    """Get a valid Fabric API access token."""
    cred = _get_fabric_credential()
    return cred.get_token(FABRIC_SCOPE).token


# ── MSAL Confidential Client (production auth) ──────────────────────

_msal_app = None


def _get_msal_app():
    """Lazy-init MSAL ConfidentialClientApplication."""
    global _msal_app
    if _msal_app is None and IS_PRODUCTION:
        _msal_app = msal.ConfidentialClientApplication(
            ENTRA_CLIENT_ID,
            authority=ENTRA_AUTHORITY,
            client_credential=ENTRA_CLIENT_SECRET,
        )
    return _msal_app


# ── Flask App ────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=WEB_DIR)
app.secret_key = SESSION_SECRET
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
CORS(app)


# ── Auth Middleware ──────────────────────────────────────────────────

@app.before_request
def auth_middleware():
    """Protect /api/* routes with MSAL in production."""
    if not IS_PRODUCTION:
        return  # Local dev — no auth required

    # Public routes (no auth needed)
    public_paths = ["/auth/", "/api/health", "/.auth/"]
    if any(request.path.startswith(p) for p in public_paths):
        return

    # Static files don't need auth middleware (handled by SPA)
    if not request.path.startswith("/api/"):
        # For non-API routes, check if user is logged in; redirect if not
        if "user" not in session:
            if request.path == "/" or request.path.endswith(".html"):
                return redirect("/auth/login")
        return

    # API routes require auth
    if "user" not in session:
        return jsonify({"error": "Unauthorized", "login_url": "/auth/login"}), 401


# ── Auth Endpoints ──────────────────────────────────────────────────

@app.route("/auth/login")
def auth_login():
    """Initiate MSAL login flow."""
    if not IS_PRODUCTION:
        return redirect("/")

    msal_app = _get_msal_app()
    # Build the redirect URI from the request
    redirect_uri = request.host_url.rstrip("/") + "/auth/callback"

    flow = msal_app.initiate_auth_code_flow(
        scopes=ENTRA_SCOPES,
        redirect_uri=redirect_uri,
    )
    session["auth_flow"] = flow
    return redirect(flow["auth_uri"])


@app.route("/auth/callback")
def auth_callback():
    """Handle MSAL login callback."""
    if not IS_PRODUCTION:
        return redirect("/")

    msal_app = _get_msal_app()
    flow = session.pop("auth_flow", None)
    if not flow:
        return redirect("/auth/login")

    try:
        result = msal_app.acquire_token_by_auth_code_flow(
            flow,
            dict(request.args),
        )
    except Exception as e:
        print(f"❌ Auth callback error: {e}")
        return redirect("/auth/login")

    if "error" in result:
        print(f"❌ Auth error: {result.get('error_description', result['error'])}")
        return redirect("/auth/login")

    # Store user info in session
    id_token_claims = result.get("id_token_claims", {})
    session["user"] = {
        "name": id_token_claims.get("name", "Unknown"),
        "email": id_token_claims.get("preferred_username", ""),
        "oid": id_token_claims.get("oid", ""),
        "tid": id_token_claims.get("tid", ""),
    }

    return redirect("/")


@app.route("/auth/logout")
def auth_logout():
    """Log out and clear session."""
    session.clear()
    if IS_PRODUCTION:
        # Redirect to Entra ID logout
        logout_url = (
            f"{ENTRA_AUTHORITY}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={request.host_url}"
        )
        return redirect(logout_url)
    return redirect("/")


# ── API: Chat Proxy (SSE streaming — UNCHANGED) ─────────────────────

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

    print(f"🔗 Agent: {agent_id}")
    print(f"💬 Message: {user_message[:80]}...")

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
        """SSE generator — streams status updates then the final response."""
        t0 = time.time()

        try:
            # 1. Get or create assistant (cached per agent)
            yield sse_event({"status": "connecting", "message": "Connecting to agent…"})

            if agent_id in _assistant_cache:
                asst_id = _assistant_cache[agent_id]
                print(f"♻️  Reusing cached assistant: {asst_id}")
            else:
                asst = fabric_api("POST", "assistants", {"model": "not used"})
                asst_id = asst["id"]
                _assistant_cache[agent_id] = asst_id
                print(f"🆕 Created assistant: {asst_id}")

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
            print(f"⏳ Run {run_id} started (status: {run['status']})")

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
            print(f"✅ Run completed in {round(time.time() - t0)}s (status: {run['status']}) usage={usage}")

            if run["status"] != "completed":
                yield sse_event({
                    "error": f"Agent run ended with status: {run['status']}",
                })
                return

            # 5. Retrieve run steps (real reasoning data)
            yield sse_event({"status": "reading", "message": "Reading response…"})

            try:
                steps = fabric_api("GET", f"threads/{thread_id}/runs/{run_id}/steps")
                print(f"📋 Raw run steps response: {json.dumps(steps, indent=2)[:2000]}")
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
                    print(f"📋 Sent {len(reasoning_steps)} run steps to client")
            except Exception as e:
                print(f"⚠️  Could not fetch run steps: {e}")
                # Non-fatal — continue to deliver the response

            # 6. Retrieve response

            msgs = fabric_api("GET", f"threads/{thread_id}/messages")
            print(f"📨 Raw messages response: {json.dumps(msgs, indent=2)[:2000]}")

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
            print(f"❌ Fabric API error {e.code}: {error_body[:500]}")
            yield sse_event({"error": f"Fabric API returned {e.code}", "details": error_body})
        except Exception as e:
            print(f"❌ Proxy error: {e}")
            yield sse_event({"error": str(e)})

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── API: User Info ──────────────────────────────────────────────────

@app.route("/api/user", methods=["GET"])
def get_user():
    """Return the authenticated user's info."""
    if IS_PRODUCTION:
        user = session.get("user")
        if user:
            return jsonify({"authenticated": True, **user})
        return jsonify({"authenticated": False}), 401

    # Local dev — always authenticated
    return jsonify({"authenticated": True, "name": "Local Dev User"})


# ── API: Health Check ───────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Health check — confirms the app is running."""
    return jsonify({
        "status": "ok",
        "mode": "production" if IS_PRODUCTION else "local-dev",
        "workspace": WORKSPACE_ID,
        "fabricApi": FABRIC_API_BASE,
    })


# ── Static File Serving ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEB_DIR, path)


# ── Entry Point (local dev only) ────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Advance Insights — Local Dev Server")
    print("=" * 50)
    print(f"  Workspace: {WORKSPACE_ID}")
    print(f"  Tenant:    {TENANT_ID}")
    print(f"  Mode:      {'production (MSAL)' if IS_PRODUCTION else 'local-dev (browser login)'}")
    print(f"  Web dir:   {WEB_DIR}")
    print("=" * 50)

    if not IS_PRODUCTION:
        # Authenticate before starting the server (dev mode)
        try:
            _get_fabric_credential()
        except Exception as e:
            print(f"\n❌ Authentication failed: {e}")
            print("Make sure you can log in with your Microsoft account.")
            sys.exit(1)

    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    print(f"\n🚀 Server running at http://localhost:{PORT}")
    print("   Press Ctrl+C to stop\n")

    app.run(host="0.0.0.0", port=PORT, debug=False)
