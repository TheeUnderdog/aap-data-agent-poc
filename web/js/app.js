/**
 * Advance Insights — Main Application Logic
 * Handles tab switching, chat UI, message rendering, and user interaction.
 */
(function () {
    'use strict';

    const config = window.APP_CONFIG;
    let activeAgent = config.agentOrder[0]; // Default to The Boss
    let chatHistories = {};   // agentKey → [{role, content, timestamp}]
    let unreadAgents = {};    // agentKey → boolean
    let isWaiting = false;

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
            tab.onclick = () => switchToAgent(key);

            tab.innerHTML = `
                <img class="tab-icon" src="${agent.icon}" alt="">
                <div class="tab-label">
                    <span class="tab-name">${agent.name}</span>
                    <span class="tab-desc">${agent.shortDesc || ''}</span>
                </div>
                <div class="tab-unread" id="unread-${key}"></div>
            `;
            strip.appendChild(tab);
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

        // Clear unread
        unreadAgents[agentKey] = false;
        const dot = document.getElementById(`unread-${agentKey}`);
        if (dot) dot.classList.remove('visible');

        // Render chat
        renderChat(agentKey);

        // Focus input
        document.getElementById('message-input').focus();
    }

    // ── Chat Rendering ──────────────────────────────────────────

    function renderChat(agentKey) {
        const area = document.getElementById('chat-area');
        const agent = config.agents[agentKey];
        const history = chatHistories[agentKey];

        area.innerHTML = '';

        if (!history || history.length === 0) {
            // Show welcome message + sample questions
            const isLightAccent = agent.accent && ['#FFCF06'].includes(agent.accent.toUpperCase());
            const samplesHtml = (agent.sampleQuestions || [])
                .map(q => `<button class="sample-question"${isLightAccent ? ' data-accent-light' : ''} onclick="handleSampleQuestion(this)">${escapeHtml(q)}</button>`)
                .join('');

            area.innerHTML = `
                <div class="welcome-message">
                    <img class="welcome-icon" src="${agent.icon}" alt="${agent.name}">
                    <h2>${agent.name}</h2>
                    <p>${agent.welcome}</p>
                    ${samplesHtml ? `<div class="sample-questions">${samplesHtml}</div>` : ''}
                </div>
            `;
            return;
        }

        for (const msg of history) {
            area.appendChild(createMessageEl(msg, agent));
        }

        scrollToBottom();
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
                    <img src="${agent.icon}" alt="${agent.name}">
                </div>
                <div class="message-bubble">
                    <button class="copy-btn" onclick="copyMessage(this)" title="Copy">📋</button>
                    ${renderMarkdown(msg.content)}
                    <div class="message-meta">${agent.name} · ${timeStr}</div>
                </div>
            `;
        }

        return div;
    }

    function addMessageToUI(msg, agent) {
        const area = document.getElementById('chat-area');

        // Remove welcome message if present
        const welcome = area.querySelector('.welcome-message');
        if (welcome) welcome.remove();

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
                <img src="${agent.icon}" alt="${agent.name}">
            </div>
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        area.appendChild(div);
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

        try {
            let response;
            if (agentKey === 'the-boss') {
                response = await window.Executive.askTheBoss(text);
            } else {
                response = await window.AgentClient.sendMessage(agentKey, text);
            }

            removeTypingIndicator();

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

    // ── Auto-init on page load ──────────────────────────────────

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
