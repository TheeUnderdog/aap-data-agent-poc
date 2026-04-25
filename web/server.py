"""
Advance Insights — Local Auth Proxy

Serves the web app and proxies Fabric Data Agent API calls using
Azure Identity (InteractiveBrowserCredential). No app registration needed —
uses the Azure SDK's built-in developer client.

Usage:
    python web/server.py
    → Opens browser for Azure login
    → Serves app at http://localhost:5000
"""

import json
import os
import sys
import webbrowser
import threading

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

from azure.identity import InteractiveBrowserCredential
from azure.core.credentials import TokenCredential

# ── Configuration ────────────────────────────────────────────────

WORKSPACE_ID = "82f53636-206f-4825-821b-bdaa8e089893"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
# Fabric Data Agent endpoint (msitapi for MSIT tenant; OpenAI-compatible chat API)
FABRIC_API_BASE = "https://msitapi.fabric.microsoft.com/v1"
TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"

PORT = 5000
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Azure Identity ───────────────────────────────────────────────

credential = None
cached_token = None

# Cache assistant IDs per agent (they're singletons — no need to recreate)
_assistant_cache = {}  # agentId → assistantId


def get_credential():
    """Initialize the interactive browser credential (one-time login)."""
    global credential
    if credential is None:
        print("\n🔐 Opening browser for Azure login...")
        credential = InteractiveBrowserCredential(
            tenant_id=TENANT_ID,
            redirect_uri="http://localhost:8400",
        )
        # Force an immediate login so the user authenticates up front
        credential.get_token(FABRIC_SCOPE)
        print("✅ Authenticated successfully!\n")
    return credential


def get_token():
    """Get a valid access token (auto-refreshes if expired)."""
    cred = get_credential()
    token = cred.get_token(FABRIC_SCOPE)
    return token.token


# ── Flask App ────────────────────────────────────────────────────

app = Flask(__name__, static_folder=WEB_DIR)
CORS(app)


@app.route("/api/chat", methods=["POST"])
def chat_proxy():
    """
    Proxy chat requests to the Fabric Data Agent API using SSE streaming.

    Streams status updates to the client as the Assistants API flow progresses,
    so users see live feedback instead of a dead spinner.
    """
    import time
    import uuid
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
        token = get_token()
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
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


@app.route("/api/user", methods=["GET"])
def get_user():
    """Return the authenticated user's info."""
    try:
        cred = get_credential()
        # The credential doesn't expose user info directly,
        # but we know they're authenticated if we get here
        return jsonify({"authenticated": True, "name": "Authenticated User"})
    except Exception:
        return jsonify({"authenticated": False}), 401


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "authenticated": credential is not None})


# ── Static file serving ──────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEB_DIR, path)


# ── Entry point ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Advance Insights — Local Auth Proxy")
    print("=" * 50)
    print(f"  Workspace: {WORKSPACE_ID}")
    print(f"  Tenant:    {TENANT_ID}")
    print(f"  Web dir:   {WEB_DIR}")
    print("=" * 50)

    # Authenticate before starting the server
    try:
        get_credential()
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
