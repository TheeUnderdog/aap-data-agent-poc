/**
 * Advance Insights — Main Application Logic
 * Handles tab switching, chat UI, message rendering, and user interaction.
 */
(function () {
    'use strict';

    const config = window.APP_CONFIG;
    let activeAgent = config.agentOrder[0]; // Default to Crew Chief
    let chatHistories = {};   // agentKey → [{role, content, timestamp}]
    let unreadAgents = {};    // agentKey → boolean
    let isWaiting = false;
    let reasoningSteps = [];  // Array of reasoning steps for current query
    let reasoningPanelOpen = false;
    let tokenUsage = { prompt: 0, completion: 0, total: 0 }; // Session token accumulator

    // ── SVG Icon Injection ───────────────────────────────────────
    // Shared cache + helper to inline SVGs so they inherit CSS color via currentColor

    const svgCache = {};

    async function injectSvgIcon(container, agent, className) {
        const color = agent.textColor || agent.accent;
        container.style.color = color;

        if (svgCache[agent.icon]) {
            container.innerHTML = svgCache[agent.icon];
            return;
        }

        try {
            const resp = await fetch(agent.icon);
            const svgText = await resp.text();
            svgCache[agent.icon] = svgText;
            container.innerHTML = svgText;
        } catch (e) {
            container.innerHTML = `<img src="${agent.icon}" alt="${agent.name}">`;
        }
    }

    // ── Initialization ──────────────────────────────────────────

    function isConfigured() {
        // Proxy mode — always configured (server handles auth)
        if (config.useProxy) return true;

        var cfg = config.msalConfig && config.msalConfig.auth;
        if (!cfg) return false;
        if (!cfg.clientId || cfg.clientId === 'YOUR_CLIENT_ID') return false;
        if (!cfg.authority || cfg.authority.indexOf('YOUR_TENANT_ID') !== -1) return false;
        return true;
    }

    async function init() {
        if (!isConfigured()) {
            showSetupRequired();
            return;
        }

        if (config.useProxy) {
            // Proxy mode — server already authenticated, go straight to app
            var AgentClientClass = window.AgentClient;
            window.AgentClient = new AgentClientClass();
            showApp();
            return;
        }

        await window.AuthManager.initialize();

        if (window.AuthManager.isAuthenticated()) {
            // Instantiate the agent client (exposed as class, used as singleton)
            var AgentClientClass = window.AgentClient;
            window.AgentClient = new AgentClientClass();
            showApp();
        }
        // If not authenticated, login screen is shown by default
    }

    function showSetupRequired() {
        var card = document.querySelector('.login-card');
        if (!card) return;
        var btn = document.getElementById('login-btn');
        if (btn) btn.style.display = 'none';

        var notice = document.createElement('div');
        notice.className = 'setup-notice';
        notice.innerHTML =
            '<h3>⚙️ Setup Required</h3>' +
            '<p>Edit <code>config.js</code> with your Entra ID and Fabric settings:</p>' +
            '<ol style="text-align:left;font-size:0.9rem;line-height:1.8">' +
            '<li><strong>clientId</strong> — from your Entra ID app registration</li>' +
            '<li><strong>authority</strong> — replace YOUR_TENANT_ID with your tenant</li>' +
            '<li><strong>workspaceId</strong> — from the Fabric portal URL</li>' +
            '<li><strong>Agent GUIDs</strong> — from each published Data Agent</li>' +
            '</ol>' +
            '<p style="margin-top:1rem;font-size:0.85rem;color:#666">See <code>SETUP.md</code> for full instructions.</p>';
        card.appendChild(notice);
    }

    function showApp() {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('app').classList.remove('hidden');

        if (config.useProxy) {
            document.getElementById('user-name').textContent = 'Connected';
        } else {
            const user = window.AuthManager.getUser();
            if (user) {
                document.getElementById('user-name').textContent = user.name || user.username;
            }
        }

        buildTabs();
        switchToAgent(activeAgent);
    }

    // ── Tab Strip ────────────────────────────────────────────────

    function buildTabs() {
        const strip = document.getElementById('tab-strip');
        strip.innerHTML = '';

        for (const key of config.agentOrder) {
            const agent = config.agents[key];
            const tab = document.createElement('div');
            tab.className = 'tab';
            tab.dataset.agent = key;
            tab.style.color = agent.textColor || agent.accent;
            tab.onclick = () => switchToAgent(key);

            tab.innerHTML = `
                <div class="tab-icon"></div>
                <div class="tab-label">
                    <span class="tab-name">${agent.name}</span>
                    <span class="tab-desc">${agent.shortDesc || ''}</span>
                </div>
                <div class="tab-unread" id="unread-${key}"></div>
            `;
            strip.appendChild(tab);

            // Inline SVG so it inherits color via currentColor (uses shared cache)
            const iconContainer = tab.querySelector('.tab-icon');
            injectSvgIcon(iconContainer, agent);
        }
    }

    function switchToAgent(agentKey) {
        activeAgent = agentKey;
        const agent = config.agents[agentKey];

        // Update CSS accent
        document.documentElement.style.setProperty('--active-accent', agent.accent);

        // Update active tab
        document.querySelectorAll('.tab').forEach(t => {
            t.classList.toggle('active', t.dataset.agent === agentKey);
        });

        // Update active agent label (mobile)
        const label = document.getElementById('active-agent-label');
        if (label) label.textContent = agent.name;

        // Clear unread
        unreadAgents[agentKey] = false;
        const dot = document.getElementById(`unread-${agentKey}`);
        if (dot) dot.classList.remove('visible');

        // Render chat
        renderChat(agentKey);

        // Focus input
        document.getElementById('message-input').focus();

        // Close sidebar if open (mobile)
        closeSidebar();
    }

    // ── Chat Rendering ──────────────────────────────────────────

    function renderChat(agentKey) {
        const area = document.getElementById('chat-area');
        const agent = config.agents[agentKey];
        const history = chatHistories[agentKey];
        const hasMessages = history && history.length > 0;

        area.innerHTML = '';

        // Always render sample questions at the top (full welcome when empty, compact when chatting)
        const isLightAccent = agent.accent && ['#FFCC00'].includes(agent.accent.toUpperCase());
        const samplesHtml = (agent.sampleQuestions || [])
            .map(q => `<button class="sample-question"${isLightAccent ? ' data-accent-light' : ''} onclick="handleSampleQuestion(this)">${escapeHtml(q)}</button>`)
            .join('');

        if (!hasMessages) {
            area.innerHTML = `
                <div class="welcome-message" id="welcome-section">
                    <div class="welcome-icon" data-agent-key="${agentKey}"></div>
                    <h2>${agent.name}</h2>
                    <p>${agent.welcome}</p>
                    ${samplesHtml ? `<div class="sample-questions">${samplesHtml}</div>` : ''}
                </div>
            `;
            injectSvgIcon(area.querySelector('.welcome-icon'), agent);
        } else {
            // Compact suggestions pinned at top — scroll up to find them
            area.innerHTML = `
                <div class="welcome-compact" id="welcome-section">
                    <div class="welcome-compact-header">
                        <div class="welcome-compact-icon" data-agent-key="${agentKey}"></div>
                        <span class="welcome-compact-label">Try asking ${agent.name}</span>
                    </div>
                    ${samplesHtml ? `<div class="sample-questions compact">${samplesHtml}</div>` : ''}
                </div>
            `;
            injectSvgIcon(area.querySelector('.welcome-compact-icon'), agent);

            for (const msg of history) {
                area.appendChild(createMessageEl(msg, agent));
            }
            scrollToBottom();
        }

        // Show/hide the suggestions chip based on whether there are messages
        const chip = document.getElementById('suggestions-chip');
        if (chip) chip.classList.toggle('hidden', !hasMessages);
    }

    function createMessageEl(msg, agent) {
        const div = document.createElement('div');
        div.className = `message ${msg.role}`;

        const timeStr = msg.timestamp
            ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : '';

        if (msg.role === 'user') {
            div.innerHTML = `
                <div class="message-bubble">
                    ${escapeHtml(msg.content)}
                    <div class="message-meta">${timeStr}</div>
                </div>
            `;
        } else {
            div.innerHTML = `
                <div class="message-avatar">
                    <div class="avatar-icon"></div>
                </div>
                <div class="message-bubble">
                    <button class="copy-btn" onclick="copyMessage(this)" title="Copy">📋</button>
                    ${renderMarkdown(msg.content)}
                    <div class="message-meta">${agent.name} · ${timeStr}</div>
                </div>
            `;
            injectSvgIcon(div.querySelector('.avatar-icon'), agent);
        }

        return div;
    }

    function addMessageToUI(msg, agent) {
        const area = document.getElementById('chat-area');

        // On first message, swap full welcome for compact version
        const fullWelcome = area.querySelector('.welcome-message');
        if (fullWelcome) {
            const agentKey = activeAgent;
            const agentCfg = config.agents[agentKey];
            const isLightAccent = agentCfg.accent && ['#FFCC00'].includes(agentCfg.accent.toUpperCase());
            const samplesHtml = (agentCfg.sampleQuestions || [])
                .map(q => `<button class="sample-question"${isLightAccent ? ' data-accent-light' : ''} onclick="handleSampleQuestion(this)">${escapeHtml(q)}</button>`)
                .join('');

            const compact = document.createElement('div');
            compact.className = 'welcome-compact';
            compact.id = 'welcome-section';
            compact.innerHTML = `
                <div class="welcome-compact-header">
                    <div class="welcome-compact-icon" data-agent-key="${agentKey}"></div>
                    <span class="welcome-compact-label">Try asking ${agentCfg.name}</span>
                </div>
                ${samplesHtml ? `<div class="sample-questions compact">${samplesHtml}</div>` : ''}
            `;
            fullWelcome.replaceWith(compact);
            injectSvgIcon(compact.querySelector('.welcome-compact-icon'), agentCfg);

            // Show the suggestions chip
            const chip = document.getElementById('suggestions-chip');
            if (chip) chip.classList.remove('hidden');
        }

        area.appendChild(createMessageEl(msg, agent));
        scrollToBottom();
    }

    function showTypingIndicator(agent) {
        const area = document.getElementById('chat-area');
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.id = 'typing-indicator';
        div.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-icon"></div>
            </div>
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        area.appendChild(div);
        injectSvgIcon(div.querySelector('.avatar-icon'), agent);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    function scrollToBottom() {
        const area = document.getElementById('chat-area');
        requestAnimationFrame(() => {
            area.scrollTop = area.scrollHeight;
        });
    }

    // ── Message Sending ─────────────────────────────────────────

    async function sendMessage() {
        const input = document.getElementById('message-input');
        const text = input.value.trim();
        if (!text || isWaiting) return;

        const agentKey = activeAgent;
        const agent = config.agents[agentKey];

        // Init history if needed
        if (!chatHistories[agentKey]) chatHistories[agentKey] = [];

        // Add user message
        const userMsg = { role: 'user', content: text, timestamp: Date.now() };
        chatHistories[agentKey].push(userMsg);
        addMessageToUI(userMsg, agent);

        // Clear input and resize
        input.value = '';
        input.style.height = 'auto';

        // Disable input while waiting
        isWaiting = true;
        document.getElementById('send-btn').disabled = true;

        showTypingIndicator(agent);

        // Clear reasoning steps for new query
        reasoningSteps = [];
        renderReasoningSteps();

        // Add initial reasoning step — no fake narration, just the facts
        addReasoningStep('thinking', agentKey,
            agentKey === 'crew-chief'
                ? 'Classifying query for routing...'
                : `Sending to ${agent.name}...`);

        try {
            let response;
            if (agentKey === 'crew-chief') {
                response = await window.Executive.askCrewChief(text);
            } else {
                addReasoningStep('agent-call', agentKey, `Calling ${agent.name}...`);
                response = await window.AgentClient.sendMessage(agentKey, text);
                completeLastReasoningStep();
            }

            removeTypingIndicator();
            completeLastReasoningStep();

            const assistantMsg = { role: 'assistant', content: response, timestamp: Date.now() };
            chatHistories[agentKey].push(assistantMsg);

            // If user switched tabs while waiting, mark as unread
            if (activeAgent !== agentKey) {
                unreadAgents[agentKey] = true;
                const dot = document.getElementById(`unread-${agentKey}`);
                if (dot) dot.classList.add('visible');
            } else {
                addMessageToUI(assistantMsg, agent);
            }
        } catch (err) {
            removeTypingIndicator();
            console.error(`[App] Error from ${agent.name}:`, err);

            addReasoningStep('error', agentKey, `Error: ${err.message}`);

            if (err instanceof window.AuthError) {
                window.AuthManager.login();
                return;
            }

            const errorMsg = {
                role: 'assistant',
                content: `⚠️ ${err.message || 'Something went wrong. Please try again.'}`,
                timestamp: Date.now()
            };
            chatHistories[agentKey].push(errorMsg);

            if (activeAgent === agentKey) {
                addMessageToUI(errorMsg, agent);
            }
        } finally {
            isWaiting = false;
            document.getElementById('send-btn').disabled = false;
            document.getElementById('message-input').focus();
        }
    }

    // ── Markdown Rendering (lightweight) ────────────────────────

    function renderMarkdown(text) {
        if (!text) return '';

        // Split into lines for block-level processing
        const lines = text.split('\n');
        const blocks = [];
        let i = 0;

        while (i < lines.length) {
            const line = lines[i];

            // Detect markdown table: line with pipes, followed by separator row
            if (line.trim().startsWith('|') && i + 1 < lines.length && /^\|[\s:?-]+\|/.test(lines[i + 1].trim())) {
                const tableLines = [];
                while (i < lines.length && lines[i].trim().startsWith('|')) {
                    tableLines.push(lines[i]);
                    i++;
                }
                blocks.push(renderTable(tableLines));
                continue;
            }

            // Code block: ```
            if (line.trim().startsWith('```')) {
                const codeLines = [];
                i++; // skip opening ```
                while (i < lines.length && !lines[i].trim().startsWith('```')) {
                    codeLines.push(lines[i]);
                    i++;
                }
                i++; // skip closing ```
                blocks.push('<pre><code>' + escapeHtml(codeLines.join('\n')) + '</code></pre>');
                continue;
            }

            // List items (- or *)
            if (/^[\s]*[-*] /.test(line)) {
                const listItems = [];
                while (i < lines.length && /^[\s]*[-*] /.test(lines[i])) {
                    listItems.push('<li>' + inlineMarkdown(escapeHtml(lines[i].replace(/^[\s]*[-*] /, ''))) + '</li>');
                    i++;
                }
                blocks.push('<ul>' + listItems.join('') + '</ul>');
                continue;
            }

            // Numbered lists
            if (/^[\s]*\d+\.\s/.test(line)) {
                const listItems = [];
                while (i < lines.length && /^[\s]*\d+\.\s/.test(lines[i])) {
                    listItems.push('<li>' + inlineMarkdown(escapeHtml(lines[i].replace(/^[\s]*\d+\.\s/, ''))) + '</li>');
                    i++;
                }
                blocks.push('<ol>' + listItems.join('') + '</ol>');
                continue;
            }

            // Headers: # ## ###
            const headerMatch = line.match(/^(#{1,3})\s+(.+)$/);
            if (headerMatch) {
                const level = headerMatch[1].length;
                // Render as h4/h5/h6 inside chat bubbles to keep sizing reasonable
                const tag = 'h' + Math.min(level + 3, 6);
                blocks.push('<' + tag + '>' + inlineMarkdown(escapeHtml(headerMatch[2])) + '</' + tag + '>');
                i++;
                continue;
            }

            // Blank line → paragraph break
            if (line.trim() === '') {
                blocks.push('');
                i++;
                continue;
            }

            // Regular paragraph text
            blocks.push('<p>' + inlineMarkdown(escapeHtml(line)) + '</p>');
            i++;
        }

        return blocks.join('\n');
    }

    /** Render a markdown table (array of pipe-delimited lines) to an HTML table. */
    function renderTable(lines) {
        if (lines.length < 2) return escapeHtml(lines.join('\n'));

        function parseCells(line) {
            return line.split('|').slice(1, -1).map(function (c) { return c.trim(); });
        }

        // Header row
        const headers = parseCells(lines[0]);
        // Skip separator row (lines[1])
        // Data rows
        const rows = lines.slice(2).map(parseCells);

        let html = '<div class="table-wrapper"><table><thead><tr>';
        for (const h of headers) {
            html += '<th>' + inlineMarkdown(escapeHtml(h)) + '</th>';
        }
        html += '</tr></thead><tbody>';
        for (const row of rows) {
            html += '<tr>';
            for (let j = 0; j < headers.length; j++) {
                html += '<td>' + inlineMarkdown(escapeHtml(row[j] || '')) + '</td>';
            }
            html += '</tr>';
        }
        html += '</tbody></table></div>';
        return html;
    }

    /** Apply inline markdown formatting (bold, italic, code). */
    function inlineMarkdown(html) {
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/(?<!\w)_(.+?)_(?!\w)/g, '<em>$1</em>');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        return html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ── Reasoning Panel ─────────────────────────────────────────

    function addReasoningStep(type, agent, message) {
        const now = Date.now();
        // Auto-complete previous step so every bubble gets a duration
        if (reasoningSteps.length > 0) {
            const prev = reasoningSteps[reasoningSteps.length - 1];
            if (prev.duration === null) {
                prev.duration = now - prev.timestamp;
            }
        }
        const step = {
            type: type,
            agent: agent,
            message: message,
            timestamp: now,
            duration: null
        };
        reasoningSteps.push(step);
        renderReasoningSteps();
        
        // Auto-scroll reasoning panel to bottom
        const panel = document.getElementById('reasoning-steps');
        if (panel) {
            requestAnimationFrame(() => {
                panel.scrollTop = panel.scrollHeight;
            });
        }
    }

    function completeLastReasoningStep() {
        if (reasoningSteps.length > 0) {
            const lastStep = reasoningSteps[reasoningSteps.length - 1];
            lastStep.duration = Date.now() - lastStep.timestamp;
            renderReasoningSteps();
        }
    }

    function renderReasoningSteps() {
        const container = document.getElementById('reasoning-steps');
        if (!container) return;

        if (reasoningSteps.length === 0) {
            container.innerHTML = '<div class="reasoning-empty">Send a message to see agent reasoning</div>';
            return;
        }

        container.innerHTML = '';
        for (let i = 0; i < reasoningSteps.length; i++) {
            const step = reasoningSteps[i];

            // Arrow connector between steps
            if (i > 0) {
                const arrow = document.createElement('div');
                arrow.className = 'reasoning-arrow';
                arrow.innerHTML = '↓';
                container.appendChild(arrow);
            }

            const div = document.createElement('div');
            div.className = `reasoning-bubble ${step.type}`;

            let durationHtml = '';
            if (step.duration !== null) {
                const ms = step.duration;
                const str = ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`;
                durationHtml = `<span class="reasoning-bubble-duration">⏱ ${str}</span>`;
            }

            div.innerHTML = `
                <div class="reasoning-bubble-text">${escapeHtml(step.message)}${durationHtml}</div>
            `;

            container.appendChild(div);
        }

        // Re-render token counter at the bottom
        renderTokenCounter();
    }

    window.toggleReasoning = function () {
        reasoningPanelOpen = !reasoningPanelOpen;
        const panel = document.getElementById('reasoning-panel');
        const btn = document.getElementById('reasoning-toggle');
        
        if (reasoningPanelOpen) {
            panel.classList.add('open');
            btn.classList.add('active');
        } else {
            panel.classList.remove('open');
            btn.classList.remove('active');
        }
    };

    // Expose reasoning functions for executive.js to use
    window.addReasoningStep = addReasoningStep;
    window.completeLastReasoningStep = completeLastReasoningStep;

    function addTokenUsage(usage) {
        if (!usage) return;
        tokenUsage.prompt += (usage.prompt_tokens || 0);
        tokenUsage.completion += (usage.completion_tokens || 0);
        tokenUsage.total += (usage.total_tokens || 0);
        renderTokenCounter();
    }

    function renderTokenCounter() {
        const container = document.getElementById('reasoning-steps');
        if (!container) return;
        let counter = container.querySelector('.token-counter');
        if (tokenUsage.total === 0) {
            if (counter) counter.remove();
            return;
        }
        if (!counter) {
            counter = document.createElement('div');
            counter.className = 'token-counter';
            container.appendChild(counter);
        }
        counter.innerHTML = `
            <div class="token-counter-icon">🎟</div>
            <div class="token-counter-values">
                <span class="token-label">Prompt</span> <span class="token-value">${tokenUsage.prompt.toLocaleString()}</span>
                <span class="token-sep">·</span>
                <span class="token-label">Completion</span> <span class="token-value">${tokenUsage.completion.toLocaleString()}</span>
                <span class="token-sep">·</span>
                <span class="token-label">Total</span> <span class="token-value token-total">${tokenUsage.total.toLocaleString()}</span>
            </div>
        `;
        // Ensure counter is always at the bottom
        if (counter !== container.lastElementChild) {
            container.appendChild(counter);
        }
    }

    window.addTokenUsage = addTokenUsage;

    // ── Global Handlers ─────────────────────────────────────────

    window.handleLogin = function () {
        window.AuthManager.login();
    };

    window.handleLogout = function () {
        window.AuthManager.logout();
    };

    window.handleSend = function () {
        sendMessage();
    };

    window.handleInputKeydown = function (e) {
        // Enter sends, Shift+Enter adds newline
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }

        // Auto-resize textarea
        const input = e.target;
        requestAnimationFrame(() => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });
    };

    window.handleSampleQuestion = function (btn) {
        const text = btn.textContent;
        const input = document.getElementById('message-input');
        input.value = text;
        sendMessage();
    };

    window.copyMessage = function (btn) {
        const bubble = btn.closest('.message-bubble');
        const text = bubble.textContent.replace('📋', '').trim();
        navigator.clipboard.writeText(text).then(() => {
            btn.textContent = '✓';
            setTimeout(() => { btn.textContent = '📋'; }, 1500);
        });
    };

    // ── Hamburger Menu (Mobile) ─────────────────────────────────

    window.toggleSidebar = function () {
        const sidebar = document.getElementById('tab-strip');
        const overlay = document.getElementById('sidebar-overlay');
        const isOpen = sidebar.classList.contains('open');

        if (isOpen) {
            closeSidebar();
        } else {
            sidebar.classList.add('open');
            overlay.classList.add('open');
        }
    };

    function closeSidebar() {
        const sidebar = document.getElementById('tab-strip');
        const overlay = document.getElementById('sidebar-overlay');
        sidebar.classList.remove('open');
        overlay.classList.remove('open');
    }

    // Close sidebar on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeSidebar();
        }
    });

    // ── New Chat Button ─────────────────────────────────────────

    window.handleNewChat = function () {
        const agentKey = activeAgent;
        chatHistories[agentKey] = [];
        renderChat(agentKey);
        document.getElementById('message-input').focus();
    };

    // ── Suggestions Chip (scroll to top) ────────────────────────

    window.scrollToSuggestions = function () {
        const section = document.getElementById('welcome-section');
        if (section) {
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    // ── Auto-init on page load ──────────────────────────────────

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
