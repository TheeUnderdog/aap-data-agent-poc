/**
 * Advance Insights — Main Application Logic
 * Handles tab switching, chat UI, message rendering, and user interaction.
 */
(function () {
    'use strict';

    let config = {};
    let activeAgent = null;
    let chatHistories = {};   // agentKey → [{role, content, timestamp}]
    let unreadAgents = {};    // agentKey → boolean
    let isWaiting = false;
    let reasoningGroups = []; // Array of { question, agentKey, steps[], tokens, collapsed }
    let reasoningPanelOpen = false;
    let tokenUsage = { prompt: 0, completion: 0, total: 0 }; // Session token accumulator

    // ── SVG Icon Injection ───────────────────────────────────────
    // Shared cache + helper to inline SVGs so they inherit CSS color via currentColor

    const svgCache = {};

    async function injectSvgIcon(container, agent) {
        if (!container || !agent || !agent.icon) return;

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

    function buildRuntimeConfig(appConfig, agentOrder, agentConfigs) {
        const agents = {};
        for (const agentConfig of agentConfigs) {
            const { slug, ...rest } = agentConfig;
            agents[slug] = rest;
        }

        return {
            ...appConfig,
            useProxy: appConfig.auth.useProxy,
            workspaceId: appConfig.workspace.id,
            fabricScopes: appConfig.workspace.fabricScopes,
            msalConfig: appConfig.auth.useProxy ? null : {
                auth: {
                    clientId: appConfig.auth.msalConfig.clientId,
                    authority: appConfig.auth.msalConfig.authority,
                    redirectUri: window.location.origin
                },
                cache: { cacheLocation: 'sessionStorage', storeAuthStateInCookie: false }
            },
            agents,
            agentOrder,
            routingMode: appConfig.routing.mode,
            executiveRouting: Object.fromEntries(
                agentOrder
                    .filter(slug => agents[slug].routingKeywords && agents[slug].routingKeywords.length > 0)
                    .map(slug => [slug, agents[slug].routingKeywords])
            )
        };
    }

    function normalizeLoadedConfig(loadedConfig) {
        if (!loadedConfig || !loadedConfig.agents || !loadedConfig.agentOrder) {
            return loadedConfig;
        }

        const agents = Object.fromEntries(
            loadedConfig.agentOrder.map((slug) => [
                slug,
                {
                    ...loadedConfig.agents[slug],
                    icon: `agents/${slug}/icon.svg`
                }
            ])
        );

        return {
            ...loadedConfig,
            agents,
            executiveRouting: Object.fromEntries(
                loadedConfig.agentOrder
                    .filter(slug => agents[slug] && agents[slug].routingKeywords && agents[slug].routingKeywords.length > 0)
                    .map(slug => [slug, agents[slug].routingKeywords])
            )
        };
    }

    async function loadConfig() {
        try {
            const res = await fetch('/api/agents');
            if (res.ok) {
                return normalizeLoadedConfig(await res.json());
            }
        } catch (e) {
            console.warn('[Config] /api/agents unavailable, falling back to static files');
        }

        const appRes = await fetch('app.json');
        const appConfig = await appRes.json();

        const orderRes = await fetch('agents/_order.json');
        const agentOrder = await orderRes.json();

        const agentConfigs = await Promise.all(
            agentOrder.map(async (slug) => {
                const res = await fetch(`agents/${slug}/agent.json`);
                const agentConfig = await res.json();
                return { slug, ...agentConfig, icon: `agents/${slug}/icon.svg` };
            })
        );

        return buildRuntimeConfig(appConfig, agentOrder, agentConfigs);
    }

    function getCoordinatorKey() {
        if (!config || !Array.isArray(config.agentOrder)) return null;

        return config.agentOrder.find((agentKey) => config.agents[agentKey]?.role === 'coordinator')
            || config.agentOrder[0]
            || null;
    }

    function isCoordinator(agentKey) {
        return config.agents[agentKey]?.role === 'coordinator';
    }

    function applyTheme(theme) {
        if (!theme) return;

        const root = document.documentElement;
        if (theme.primaryColor) root.style.setProperty('--aap-red', theme.primaryColor);
        if (theme.backgroundColor) root.style.setProperty('--bg-chat', theme.backgroundColor);
        if (theme.borderRadius) root.style.setProperty('--radius-md', theme.borderRadius);
        if (theme.fontFamily) document.body.style.fontFamily = theme.fontFamily;

        if (theme.headingFont) {
            document.querySelectorAll('.wordmark-primary, .wordmark-secondary').forEach((el) => {
                el.style.fontFamily = theme.headingFont;
            });
        }
    }

    function applyBranding() {
        if (!config || !config.name) return;

        document.title = config.name;

        const nameParts = config.name.split(' ');
        const primary = nameParts.shift() || config.name;
        const secondary = nameParts.join(' ');

        const primaryEl = document.querySelector('.wordmark-primary');
        const secondaryEl = document.querySelector('.wordmark-secondary');
        const taglineEl = document.querySelector('.wordmark-tagline');
        const loginTitleEl = document.querySelector('.login-card h1');
        const loginTaglineEl = document.querySelector('.login-card p');
        const loginLogoEl = document.querySelector('.login-logo');
        const topLogoEl = document.querySelector('.top-bar-logo');

        if (primaryEl) primaryEl.textContent = primary;
        if (secondaryEl) secondaryEl.textContent = secondary || '';
        if (taglineEl && config.tagline) taglineEl.textContent = config.tagline;
        if (loginTitleEl) loginTitleEl.textContent = config.name;
        if (loginTaglineEl && config.tagline) loginTaglineEl.textContent = config.tagline;
        if (loginLogoEl && config.logo) loginLogoEl.src = config.logo;
        if (topLogoEl && config.logo) topLogoEl.src = config.logo;
        if (loginLogoEl && config.name) loginLogoEl.alt = config.name;
        if (topLogoEl && config.name) topLogoEl.alt = config.name;

        if (config.favicon) {
            document.querySelectorAll('link[rel="icon"]').forEach((link) => {
                link.href = config.favicon;
            });
        }

        applyTheme(config.theme);
    }

    // ── Initialization ──────────────────────────────────────────

    function isConfigured() {
        // Proxy mode — always configured (server handles auth)
        if (config.useProxy) return true;

        var cfg = config.msalConfig && config.msalConfig.auth;
        if (!cfg) return false;
        if (!cfg.clientId || cfg.clientId === 'YOUR_CLIENT_ID' || cfg.clientId === 'TODO_CLIENT_ID') return false;
        if (!cfg.authority || cfg.authority.indexOf('YOUR_TENANT_ID') !== -1 || cfg.authority.indexOf('TODO_TENANT_ID') !== -1) return false;
        return true;
    }

    async function init() {
        config = await loadConfig();
        window.APP_CONFIG = config;
        activeAgent = getCoordinatorKey();
        applyBranding();

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

        if (card.querySelector('.setup-notice')) return;

        var notice = document.createElement('div');
        notice.className = 'setup-notice';
        notice.innerHTML =
            '<h3>⚙️ Setup Required</h3>' +
            '<p>Update <code>app.json</code> with your Entra ID and Fabric settings:</p>' +
            '<ol style="text-align:left;font-size:0.9rem;line-height:1.8">' +
            '<li><strong>auth.msalConfig.clientId</strong> — from your Entra ID app registration</li>' +
            '<li><strong>auth.msalConfig.authority</strong> — replace TODO_TENANT_ID with your tenant</li>' +
            '<li><strong>workspace.id</strong> — from the Fabric portal URL</li>' +
            '<li><strong>agents/*/agent.json</strong> — set each published Data Agent GUID</li>' +
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

            tab.title = agent.welcome || agent.shortDesc || '';
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
                    <div class="agent-tagline">${agent.description}</div>
                    ${agent.about ? `<div class="agent-about">${escapeHtml(agent.about)}</div>` : ''}
                    <p>${agent.welcome}</p>
                    ${samplesHtml ? `<div class="sample-questions">${samplesHtml}</div>` : ''}
                </div>
            `;
            injectSvgIcon(area.querySelector('.welcome-icon'), agent);
        } else {
            // Keep the full welcome — it scrolls up naturally as messages are added
            area.innerHTML = `
                <div class="welcome-message" id="welcome-section">
                    <div class="welcome-icon" data-agent-key="${agentKey}"></div>
                    <h2>${agent.name}</h2>
                    <div class="agent-tagline">${agent.description}</div>
                    ${agent.about ? `<div class="agent-about">${escapeHtml(agent.about)}</div>` : ''}
                    <p>${agent.welcome}</p>
                    ${samplesHtml ? `<div class="sample-questions">${samplesHtml}</div>` : ''}
                </div>
            `;
            injectSvgIcon(area.querySelector('.welcome-icon'), agent);

            for (const msg of history) {
                area.appendChild(createMessageEl(msg, agent));
            }
            scrollToBottom();
        }

        // Close the suggestions panel when switching agents
        const panel = document.getElementById('suggestions-panel');
        const sugBtn = document.getElementById('suggestions-btn');
        if (panel) panel.classList.remove('open');
        if (sugBtn) sugBtn.classList.remove('active');

        // Update panel content for current agent
        updateSuggestionsPanel(agent);
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
            // Link this message to its reasoning group index
            const groupIdx = msg.reasoningGroupIndex != null ? msg.reasoningGroupIndex : -1;
            div.innerHTML = `
                <div class="message-avatar" data-reasoning-group="${groupIdx}" title="Show reasoning">
                    <div class="avatar-icon"></div>
                </div>
                <div class="message-bubble">
                    <button class="copy-btn" onclick="copyMessage(this)" title="Copy">📋</button>
                    ${renderMarkdown(msg.content)}
                    <div class="message-meta">${agent.name} · ${timeStr}</div>
                </div>
            `;
            injectSvgIcon(div.querySelector('.avatar-icon'), agent);

            // Click avatar → open reasoning panel and scroll to this group
            const avatar = div.querySelector('.message-avatar');
            avatar.style.cursor = 'pointer';
            avatar.addEventListener('click', () => {
                openReasoningToGroup(groupIdx);
            });
        }

        return div;
    }

    function addMessageToUI(msg, agent) {
        const area = document.getElementById('chat-area');

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

    // ── Methodology Extraction ────────────────────────────────────

    function extractMethodology(responseText) {
        // Match **How I got these numbers**, ## How I got these numbers, ### How I got these numbers
        const regex = /\n?\s*(?:\*\*How I got these numbers\*\*|#{2,3}\s*How I got these numbers)\s*\n?/i;
        const match = responseText.match(regex);
        if (!match) {
            return { cleanContent: responseText, methodology: null };
        }
        const idx = match.index;
        const methodology = responseText.slice(idx + match[0].length).trim();
        const cleanContent = responseText.slice(0, idx).trimEnd();
        return { cleanContent, methodology: methodology || null };
    }

    // Expose for executive.js
    window.extractMethodology = extractMethodology;

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

        // Start a new reasoning group for this question — collapse previous groups
        for (const g of reasoningGroups) g.collapsed = true;
        const coordinatorKey = getCoordinatorKey();
        const agentLabel = isCoordinator(agentKey)
            ? config.agents[coordinatorKey]?.name || agent.name
            : agent.name;
        reasoningGroups.push({
            question: text,
            agentKey: agentKey,
            agentLabel: agentLabel,
            steps: [],
            tokens: { prompt: 0, completion: 0, total: 0 },
            collapsed: false
        });
        renderReasoningPanel();

        // Add initial reasoning step — no fake narration, just the facts
        addReasoningStep('thinking', agentKey,
            isCoordinator(agentKey)
                ? 'Classifying query for routing...'
                : `Sending to ${agent.name}...`);

        try {
            let response;
            if (isCoordinator(agentKey)) {
                response = await window.Executive.askCrewChief(text);
            } else {
                addReasoningStep('agent-call', agentKey, `Calling ${agent.name}...`);
                response = await window.AgentClient.sendMessage(agentKey, text);
                completeLastReasoningStep();
            }

            removeTypingIndicator();
            completeLastReasoningStep();

            const { cleanContent, methodology } = extractMethodology(response);
            const assistantMsg = {
                role: 'assistant',
                content: cleanContent,
                timestamp: Date.now(),
                reasoningGroupIndex: reasoningGroups.length - 1
            };
            chatHistories[agentKey].push(assistantMsg);

            if (methodology) {
                addReasoningStep('methodology', agentKey, methodology);
                completeLastReasoningStep();
            }

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

    // ── Info Popup ──────────────────────────────────────────────

    // (Info popup removed — about text is always shown inline)

    // ── Reasoning Panel ─────────────────────────────────────────

    function currentGroup() {
        return reasoningGroups.length > 0 ? reasoningGroups[reasoningGroups.length - 1] : null;
    }

    function addReasoningStep(type, agent, message) {
        const group = currentGroup();
        if (!group) return;

        const now = Date.now();
        // Auto-complete previous step so every bubble gets a duration
        if (group.steps.length > 0) {
            const prev = group.steps[group.steps.length - 1];
            if (prev.duration === null) {
                prev.duration = now - prev.timestamp;
            }
        }
        group.steps.push({
            type: type,
            agent: agent,
            message: message,
            timestamp: now,
            duration: null
        });
        renderReasoningPanel();

        // Auto-scroll reasoning panel to bottom
        const panel = document.getElementById('reasoning-steps');
        if (panel) {
            requestAnimationFrame(() => {
                panel.scrollTop = panel.scrollHeight;
            });
        }
    }

    function completeLastReasoningStep() {
        const group = currentGroup();
        if (group && group.steps.length > 0) {
            const lastStep = group.steps[group.steps.length - 1];
            lastStep.duration = Date.now() - lastStep.timestamp;
            renderReasoningPanel();
        }
    }

    function renderReasoningPanel() {
        const container = document.getElementById('reasoning-steps');
        if (!container) return;

        if (reasoningGroups.length === 0) {
            container.innerHTML = '<div class="reasoning-empty">Send a message to see agent reasoning</div>';
            return;
        }

        container.innerHTML = '';
        for (let gi = 0; gi < reasoningGroups.length; gi++) {
            const group = reasoningGroups[gi];

            // Question group header
            const header = document.createElement('div');
            header.className = 'reasoning-group-header' + (group.collapsed ? ' collapsed' : '');
            header.setAttribute('data-group-index', gi);
            header.innerHTML = `
                <span class="reasoning-group-chevron">${group.collapsed ? '▸' : '▾'}</span>
                <span class="reasoning-group-agent">${escapeHtml(group.agentLabel)}</span>
                <span class="reasoning-group-question">${escapeHtml(truncate(group.question, 60))}</span>
                ${group.tokens.total > 0 ? `<span class="reasoning-group-tokens">🪙 ${group.tokens.total.toLocaleString()}</span>` : ''}
            `;
            header.addEventListener('click', () => {
                group.collapsed = !group.collapsed;
                renderReasoningPanel();
            });
            container.appendChild(header);

            // Steps (hidden when collapsed)
            if (!group.collapsed) {
                const body = document.createElement('div');
                body.className = 'reasoning-group-body';

                for (let i = 0; i < group.steps.length; i++) {
                    const step = group.steps[i];

                    if (i > 0) {
                        const arrow = document.createElement('div');
                        arrow.className = 'reasoning-arrow';
                        arrow.innerHTML = '↓';
                        body.appendChild(arrow);
                    }

                    const div = document.createElement('div');
                    div.className = `reasoning-bubble ${step.type}`;

                    let durationHtml = '';
                    if (step.duration !== null) {
                        const ms = step.duration;
                        const str = ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`;
                        durationHtml = `<span class="reasoning-bubble-duration">⏱ ${str}</span>`;
                    }

                    let contentHtml;
                    if (step.type === 'methodology') {
                        // Render methodology with light formatting for readability
                        let formatted = escapeHtml(step.message)
                            .replace(/\n- /g, '<br>• ')
                            .replace(/\n\* /g, '<br>• ')
                            .replace(/\n/g, '<br>');
                        contentHtml = `<span class="methodology-label">📊 Methodology</span><br>${formatted}`;
                    } else {
                        contentHtml = escapeHtml(step.message);
                    }

                    div.innerHTML = `
                        <div class="reasoning-bubble-text">${contentHtml}${durationHtml}</div>
                    `;
                    body.appendChild(div);
                }

                // Per-question token counter
                if (group.tokens.total > 0) {
                    const tc = document.createElement('div');
                    tc.className = 'token-counter';
                    tc.innerHTML = `
                        <div class="token-counter-header">
                            <span class="token-counter-icon">🪙</span>
                            <span class="token-counter-title">Tokens</span>
                            <span class="token-value token-total">${group.tokens.total.toLocaleString()}</span>
                        </div>
                        <div class="token-counter-breakdown">
                            <div class="token-row"><span class="token-label">Prompt</span><span class="token-value">${group.tokens.prompt.toLocaleString()}</span></div>
                            <div class="token-row"><span class="token-label">Completion</span><span class="token-value">${group.tokens.completion.toLocaleString()}</span></div>
                        </div>
                    `;
                    body.appendChild(tc);
                }

                container.appendChild(body);
            }
        }

        // Session total token counter (if more than one group has tokens)
        const groupsWithTokens = reasoningGroups.filter(g => g.tokens.total > 0);
        if (groupsWithTokens.length > 1 || tokenUsage.total > 0) {
            renderSessionTokenCounter(container);
        }
    }

    function truncate(str, max) {
        return str.length > max ? str.slice(0, max - 1) + '…' : str;
    }

    function openReasoningToGroup(groupIndex) {
        if (groupIndex < 0 || groupIndex >= reasoningGroups.length) {
            // No matching group — just toggle the panel open
            if (!reasoningPanelOpen) window.toggleReasoning();
            return;
        }

        // Uncollapse the target group, collapse others
        for (let i = 0; i < reasoningGroups.length; i++) {
            reasoningGroups[i].collapsed = (i !== groupIndex);
        }
        renderReasoningPanel();

        // Open the panel if not already open
        if (!reasoningPanelOpen) {
            reasoningPanelOpen = true;
            const panel = document.getElementById('reasoning-panel');
            const btn = document.getElementById('reasoning-toggle');
            if (panel) panel.classList.add('open');
            if (btn) btn.classList.add('active');
        }

        // Scroll to the target group header
        requestAnimationFrame(() => {
            const header = document.querySelector(`.reasoning-group-header[data-group-index="${groupIndex}"]`);
            if (header) {
                header.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
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

    function addTokenUsage(usage, agentKey) {
        if (!usage) return;
        const p = usage.prompt_tokens || 0;
        const c = usage.completion_tokens || 0;
        const t = usage.total_tokens || 0;

        // Session totals
        tokenUsage.prompt += p;
        tokenUsage.completion += c;
        tokenUsage.total += t;

        // Per-question group
        const group = currentGroup();
        if (group) {
            group.tokens.prompt += p;
            group.tokens.completion += c;
            group.tokens.total += t;
        }
        renderReasoningPanel();
    }

    function renderSessionTokenCounter(container) {
        if (tokenUsage.total === 0) return;

        const counter = document.createElement('div');
        counter.className = 'token-counter session-token-counter';
        counter.innerHTML = `
            <div class="token-counter-header">
                <span class="token-counter-icon">🪙</span>
                <span class="token-counter-title">Session Total</span>
                <span class="token-value token-total">${tokenUsage.total.toLocaleString()}</span>
            </div>
            <div class="token-counter-breakdown">
                <div class="token-row"><span class="token-label">Prompt</span><span class="token-value">${tokenUsage.prompt.toLocaleString()}</span></div>
                <div class="token-row"><span class="token-label">Completion</span><span class="token-value">${tokenUsage.completion.toLocaleString()}</span></div>
            </div>
        `;
        container.appendChild(counter);
    }

    window.addTokenUsage = addTokenUsage;

    // ── Global Handlers ─────────────────────────────────────────

    window.handleLogin = function () {
        window.AuthManager.login();
    };

    window.handleLogout = function () {
        if (config.useProxy) {
            window.location.reload();
            return;
        }
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

        // Close suggestions panel if open
        const panel = document.getElementById('suggestions-panel');
        const sugBtn = document.getElementById('suggestions-btn');
        if (panel) panel.classList.remove('open');
        if (sugBtn) sugBtn.classList.remove('active');

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
            // Also close suggestions panel
            const panel = document.getElementById('suggestions-panel');
            const sugBtn = document.getElementById('suggestions-btn');
            if (panel) panel.classList.remove('open');
            if (sugBtn) sugBtn.classList.remove('active');
        }
    });

    // ── New Chat Button ─────────────────────────────────────────

    window.handleNewChat = function () {
        const agentKey = activeAgent;
        chatHistories[agentKey] = [];

        // Reset reasoning panel
        reasoningGroups = [];
        tokenUsage = { prompt: 0, completion: 0, total: 0 };
        renderReasoningPanel();

        renderChat(agentKey);
        document.getElementById('message-input').focus();
    };

    // ── Suggestions Slide-Out Panel ────────────────────────────

    function updateSuggestionsPanel(agent) {
        const grid = document.getElementById('suggestions-grid');
        const headerText = document.getElementById('suggestions-header-text');
        const headerIcon = document.getElementById('suggestions-header-icon');
        if (!grid) return;
        const isLightAccent = agent.accent && ['#FFCC00'].includes(agent.accent.toUpperCase());
        grid.innerHTML = (agent.sampleQuestions || [])
            .map(q => `<button class="sample-question"${isLightAccent ? ' data-accent-light' : ''} onclick="handleSampleQuestion(this)">${escapeHtml(q)}</button>`)
            .join('');
        if (headerText) headerText.textContent = `Try asking ${agent.name}`;
        if (headerIcon) injectSvgIcon(headerIcon, agent);
    }

    window.toggleSuggestions = function () {
        const panel = document.getElementById('suggestions-panel');
        const btn = document.getElementById('suggestions-btn');
        if (!panel) return;
        const opening = !panel.classList.contains('open');
        panel.classList.toggle('open');
        if (btn) btn.classList.toggle('active', opening);
    };

    // ── Mystery Dice — LLM-generated surprise question ──────────

    // Pip layouts for dice faces 1–6 (positions within a 28×28 die, origin at die top-left)
    const PIP_LAYOUTS = {
        1: [[14, 14]],
        2: [[8, 8], [20, 20]],
        3: [[8, 8], [14, 14], [20, 20]],
        4: [[8, 8], [20, 8], [8, 20], [20, 20]],
        5: [[8, 8], [20, 8], [14, 14], [8, 20], [20, 20]],
        6: [[8, 8], [20, 8], [8, 14], [20, 14], [8, 20], [20, 20]],
    };

    function randomizeDicePips() {
        const svg = document.querySelector('#mystery-btn svg');
        if (!svg) return;

        const leftVal = Math.floor(Math.random() * 6) + 1;
        const rightVal = Math.floor(Math.random() * 6) + 1;

        // Left die group (first <g>): origin offset x=8, y=24
        const groups = svg.querySelectorAll('g');
        if (groups.length < 2) return;

        for (const [gi, cfg] of [[0, { val: leftVal, ox: 8, oy: 24 }],
                                   [1, { val: rightVal, ox: 28, oy: 26 }]]) {
            const g = groups[gi];
            // Remove existing pip circles
            g.querySelectorAll('circle').forEach(c => c.remove());
            // Add new pips
            for (const [px, py] of PIP_LAYOUTS[cfg.val]) {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', cfg.ox + px);
                circle.setAttribute('cy', cfg.oy + py);
                circle.setAttribute('r', '2.8');
                circle.setAttribute('fill', 'currentColor');
                g.appendChild(circle);
            }
        }
    }

    window.generateMysteryQuestion = async function () {
        const btn = document.getElementById('mystery-btn');
        const input = document.getElementById('message-input');
        if (!btn || !input || btn.disabled) return;

        const agentKey = activeAgent;
        const agent = config.agents[agentKey];

        // Pick an agent with a Fabric ID (for crew-chief, use a random specialist)
        let targetKey = agentKey;
        let targetAgent = agent;
        if (!agent.id) {
            const specialists = Object.keys(config.agents).filter(k => config.agents[k].id);
            targetKey = specialists[Math.floor(Math.random() * specialists.length)];
            targetAgent = config.agents[targetKey];
        }

        // Start dice spinning (pips randomize when response arrives)
        btn.classList.remove('rolling');
        void btn.offsetWidth; // force reflow so animation restarts
        btn.classList.add('rolling');
        btn.disabled = true;

        const existing = (agent.sampleQuestions || []).join('; ');
        const basePrompt = agent.mysteryPrompt || targetAgent.mysteryPrompt
            || `Generate ONE creative analytics question about ${agent.description || targetAgent.description}.`;
        const prompt = `${basePrompt}\n\nDo NOT repeat or rephrase any of these existing questions: ${existing}\n\nReply with ONLY the question text — no numbering, no quotes, no explanation.`;

        try {
            let question = await window.AgentClient.sendOneOffMessage(targetKey, prompt);
            question = question.replace(/^["'\s]+|["'\s]+$/g, '').trim();
            if (!question) throw new Error('No question generated');

            input.value = question;
            input.style.height = 'auto';
            input.style.height = input.scrollHeight + 'px';
            input.focus();
        } catch (err) {
            console.error('[Mystery] Failed to generate question:', err);
            // Fallback: pick a random sample question the user hasn't seen
            const pool = agent.sampleQuestions || [];
            if (pool.length) {
                input.value = pool[Math.floor(Math.random() * pool.length)];
                input.focus();
            }
        } finally {
            randomizeDicePips();
            btn.classList.remove('rolling');
            btn.disabled = false;
        }
    };

    // ── Auto-init on page load ──────────────────────────────────

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
