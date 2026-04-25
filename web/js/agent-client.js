/**
 * AgentClient — Fabric Data Agent API client for the AAP chatbot.
 *
 * Handles communication with the Fabric Data Agent REST API,
 * per-agent conversation history, and structured error handling.
 *
 * Depends on:
 *   - window.APP_CONFIG  (workspace & agent configuration)
 *   - window.AuthManager (provides Entra ID tokens via getToken())
 */
(function () {
    "use strict";

    const LOG_PREFIX = "[AgentClient]";
    const FABRIC_API = "https://api.fabric.microsoft.com/v1/workspaces";

    // When running behind the local proxy, use relative URL
    const USE_PROXY = window.APP_CONFIG && window.APP_CONFIG.useProxy;

    // ── Custom error for auth failures (401/403) ──

    class AuthError extends Error {
        constructor(message) {
            super(message);
            this.name = "AuthError";
        }
    }

    // ── AgentClient ──

    class AgentClient {
        constructor() {
            const cfg = window.APP_CONFIG;
            if (!cfg || !cfg.workspaceId || !cfg.agents) {
                throw new Error(`${LOG_PREFIX} window.APP_CONFIG is missing or incomplete.`);
            }

            this._workspaceId = cfg.workspaceId;
            this._agents = cfg.agents;

            // Per-agent message history: { "agent-key": [{role, content}, …] }
            this._history = {};
            Object.keys(this._agents).forEach((key) => {
                this._history[key] = [];
            });

            console.log(`${LOG_PREFIX} Initialized with ${Object.keys(this._agents).length} agent(s).`);
        }

        // ── Public API ──

        /**
         * Send a user message to a specific Fabric Data Agent and return the
         * assistant's response text. Full conversation history is sent so the
         * agent has context across turns.
         *
         * @param {string} agentKey  Key in APP_CONFIG.agents (e.g. "pit-crew")
         * @param {string} userMessage  Natural-language query
         * @returns {Promise<string>} The assistant's response content
         */
        async sendMessage(agentKey, userMessage) {
            const agent = this._requireAgent(agentKey);

            if (!agent.id) {
                throw new Error(`${LOG_PREFIX} Agent "${agentKey}" has no Fabric agent ID.`);
            }

            // Append the user turn before sending
            this._history[agentKey].push({ role: "user", content: userMessage });

            let url, headers, body;

            if (USE_PROXY) {
                // Local proxy handles auth — just send agentId + messages
                url = "/api/chat";
                headers = { "Content-Type": "application/json" };
                body = JSON.stringify({
                    agentId: agent.id,
                    messages: this._history[agentKey],
                });
            } else {
                // Direct Fabric API call (requires MSAL token)
                url = `${FABRIC_API}/${this._workspaceId}/items/${agent.id}/chat`;
                const token = await window.AuthManager.getToken();
                headers = {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                };
                body = JSON.stringify({ messages: this._history[agentKey] });
            }

            try {
                const res = await fetch(url, {
                    method: "POST",
                    headers: headers,
                    body: body,
                });

                if (!res.ok) {
                    this._handleHttpError(res.status, agentKey);
                }

                const data = await res.json();
                const reply =
                    data.content ??
                    data.choices?.[0]?.message?.content ??
                    data.result ??
                    JSON.stringify(data);

                // Append the assistant turn
                this._history[agentKey].push({ role: "assistant", content: reply });

                return reply;
            } catch (err) {
                // If we already threw a structured error, re-throw as-is
                if (err instanceof AuthError || err.message.startsWith(LOG_PREFIX)) {
                    throw err;
                }
                // Network / unexpected errors
                const msg = `${LOG_PREFIX} Request to "${agentKey}" failed: ${err.message}`;
                console.error(msg);
                throw new Error(msg);
            }
        }

        /** Returns the full message history array for an agent (by reference). */
        getHistory(agentKey) {
            this._requireAgent(agentKey);
            return this._history[agentKey];
        }

        /** Clears conversation history for an agent. */
        clearHistory(agentKey) {
            this._requireAgent(agentKey);
            this._history[agentKey] = [];
            console.log(`${LOG_PREFIX} History cleared for "${agentKey}".`);
        }

        /** Returns the config object (name, accent, id) for an agent. */
        getAgentConfig(agentKey) {
            return this._requireAgent(agentKey);
        }

        /** Returns an array of all agent keys (e.g. ["crew-chief", "pit-crew", …]). */
        getAgentKeys() {
            return Object.keys(this._agents);
        }

        // ── Private helpers ──

        /** Validate that agentKey exists in config; return its config object. */
        _requireAgent(agentKey) {
            const agent = this._agents[agentKey];
            if (!agent) {
                throw new Error(`${LOG_PREFIX} Unknown agent key: "${agentKey}".`);
            }
            return agent;
        }

        /** Map HTTP status codes to descriptive, actionable errors. */
        _handleHttpError(status, agentKey) {
            if (status === 401 || status === 403) {
                const msg = `${LOG_PREFIX} Authentication failed (${status}) for "${agentKey}".`;
                console.error(msg);
                throw new AuthError(msg);
            }
            if (status === 404) {
                const msg = `${LOG_PREFIX} Agent not found (404) — verify agent ID for "${agentKey}".`;
                console.error(msg);
                throw new Error(msg);
            }
            if (status === 429) {
                const msg = `${LOG_PREFIX} Rate limited (429) for "${agentKey}" — please wait.`;
                console.warn(msg);
                throw new Error(msg);
            }
            const msg = `${LOG_PREFIX} HTTP ${status} from "${agentKey}".`;
            console.error(msg);
            throw new Error(msg);
        }
    }

    // Expose on window
    window.AgentClient = AgentClient;
    window.AuthError = AuthError;
})();
