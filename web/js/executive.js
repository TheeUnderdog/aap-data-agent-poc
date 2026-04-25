/**
 * Advance Insights — Crew Chief (Executive Orchestrator)
 * Client-side agent that routes questions to specialist agents,
 * fans out queries in parallel, and synthesizes a unified response.
 */
(function () {
    'use strict';

    const config = window.APP_CONFIG;
    const routing = config.executiveRouting;

    /**
     * Classify a user question into one or more specialist agent keys
     * based on keyword matching from the routing config.
     */
    function classifyQuestion(question) {
        const lower = question.toLowerCase();
        const scores = {};
        const matchedKeywords = {};

        for (const [agentKey, keywords] of Object.entries(routing)) {
            let score = 0;
            const hits = [];
            for (const kw of keywords) {
                if (lower.includes(kw)) { score++; hits.push(kw); }
            }
            if (score > 0) {
                scores[agentKey] = score;
                matchedKeywords[agentKey] = hits;
            }
        }

        // Sort by score descending
        const ranked = Object.entries(scores).sort((a, b) => b[1] - a[1]);

        if (ranked.length === 0) {
            // Can't classify — fan out to all specialists
            classifyQuestion._lastDetail = 'No keyword matches — broadcasting to all specialists.';
            return Object.keys(routing);
        }

        // Take top agents (up to 3), but include ties
        const topScore = ranked[0][1];
        const threshold = Math.max(1, topScore - 1);
        const selected = ranked
            .filter(([, s]) => s >= threshold)
            .slice(0, 3)
            .map(([key]) => key);

        // Build detail showing actual keyword match data
        const detailLines = [];
        for (const key of selected) {
            const name = agentDisplayName(key);
            const kws = matchedKeywords[key].map(k => `"${k}"`).join(', ');
            detailLines.push(`${name}: matched ${kws} (score ${scores[key]})`);
        }
        const unmatched = Object.keys(routing).filter(k => !scores[k]);
        if (unmatched.length > 0) {
            detailLines.push(`No hits: ${unmatched.map(agentDisplayName).join(', ')}`);
        }
        classifyQuestion._lastDetail = detailLines.join('\n');

        return selected;
    }

    /**
     * Get a friendly name for attribution in the response
     */
    function agentDisplayName(agentKey) {
        const agent = config.agents[agentKey];
        return agent ? agent.name : agentKey;
    }

    /**
     * Send a question to the Crew Chief. Classifies, fans out, synthesizes.
     * @param {string} question - The user's question
     * @returns {Promise<string>} - Synthesized executive response
     */
    async function askCrewChief(question) {
        const client = window.AgentClient;
        const targets = classifyQuestion(question);

        const targetNames = targets.map(agentDisplayName).join(', ');
        console.log(`[CrewChief] Routing to: ${targetNames}`);

        // Add reasoning step for routing decision with keyword match details
        if (window.addReasoningStep) {
            window.addReasoningStep('routing', 'crew-chief',
                `Routing to ${targetNames}`,
                classifyQuestion._lastDetail);
        }

        // Fan out to all target agents in parallel
        const queries = targets.map(async (agentKey) => {
            try {
                // Add reasoning step for each agent call
                if (window.addReasoningStep) {
                    window.addReasoningStep('agent-call', agentKey,
                        `Querying ${agentDisplayName(agentKey)}...`);
                }

                const response = await client.sendMessage(agentKey, question);

                // Complete the reasoning step
                if (window.completeLastReasoningStep) {
                    window.completeLastReasoningStep();
                }

                // Add response reasoning step with preview
                if (window.addReasoningStep) {
                    const preview = response.length > 300 ? response.substring(0, 300) + '…' : response;
                    window.addReasoningStep('agent-response', agentKey,
                        `${agentDisplayName(agentKey)} responded (${response.length} chars)`,
                        preview);
                }

                return { agentKey, response, error: null };
            } catch (err) {
                console.warn(`[CrewChief] ${agentDisplayName(agentKey)} failed:`, err.message);

                // Add error reasoning step
                if (window.addReasoningStep) {
                    window.addReasoningStep('error', agentKey, `${agentDisplayName(agentKey)} failed: ${err.message}`);
                }

                return { agentKey, response: null, error: err.message };
            }
        });

        const results = await Promise.all(queries);
        const successful = results.filter(r => r.response);
        const failed = results.filter(r => r.error);

        if (successful.length === 0) {
            return "I tried reaching my team but couldn't get a response. " +
                   "Please try again, or switch to a specialist tab for direct access.";
        }

        // Add synthesis reasoning step
        if (window.addReasoningStep) {
            const agentList = successful.map(r => agentDisplayName(r.agentKey)).join(', ');
            let detail = `Sources: ${agentList} (${successful.length} responded)`;
            if (failed.length > 0) {
                detail += `\nFailed: ${failed.map(r => agentDisplayName(r.agentKey) + ' (' + r.error + ')').join(', ')}`;
            }
            window.addReasoningStep('thinking', 'crew-chief',
                `Synthesizing ${successful.length} response(s)...`,
                detail);
        }

        return synthesize(question, successful, failed);
    }

    /**
     * Synthesize specialist responses into an executive summary
     */
    function synthesize(question, successful, failed) {
        const parts = [];

        // Opening
        if (successful.length === 1) {
            const agent = agentDisplayName(successful[0].agentKey);
            parts.push(`I checked with **${agent}** on this. Here's what they found:\n`);
        } else {
            const names = successful.map(r => `**${agentDisplayName(r.agentKey)}**`);
            parts.push(`I talked to my team — ${names.join(' and ')} — and here's what we found:\n`);
        }

        // Each agent's contribution
        for (const result of successful) {
            const name = agentDisplayName(result.agentKey);
            if (successful.length > 1) {
                parts.push(`**${name}** reports:\n${result.response}\n`);
            } else {
                parts.push(result.response);
            }
        }

        // Note any failures
        if (failed.length > 0) {
            const failedNames = failed.map(r => agentDisplayName(r.agentKey)).join(', ');
            parts.push(`\n_Note: I couldn't reach ${failedNames} this time. You can try asking them directly._`);
        }

        return parts.join('\n');
    }

    // Expose globally
    window.Executive = {
        askCrewChief,
        classifyQuestion,
    };
})();
