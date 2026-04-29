/*
 * Claude Connector for Obsidian
 * Optimizat pentru: ElectroGestion | BFC Marketplace | Amazon FBA
 * Features: token caching, project context, inline AI, conversation history
 */

'use strict';

const { Plugin, PluginSettingTab, Setting, Modal, Notice, MarkdownView, requestUrl } = require('obsidian');

// ─── Project System Prompts (cached server-side via cache_control) ─────────────
const PROJECT_PROMPTS = {
    "ElectroGestion": `Esti un asistent AI specializat pentru ElectroGestion - sistem de gestiune pentru echipamente electrice si electronice.
Contextul tau include: managementul stocurilor de componente electrice, urmarirea comenzilor furnizori/clienti, rapoarte de vanzari, gestiunea service-ului.
Raspunzi in romana, esti concis si orientat pe actiune. Folosesti terminologie specifica domeniului electro.`,

    "BFC-Marketplace": `Esti un asistent AI specializat pentru BFC Marketplace - platforma de comert electronic.
Contextul tau include: managementul listingurilor de produse, procesarea comenzilor, relatia cu clientii, optimizarea preturilor, analytics de vanzari, logistica si livrari.
Raspunzi in romana, esti concis si orientat pe cresterea vanzarilor si eficienta operationala.`,

    "Amazon-FBA": `Esti un asistent AI specializat pentru operatiunile Amazon FBA (Fulfillment by Amazon).
Contextul tau include: optimizarea listingurilor (SEO Amazon, A+ Content), managementul inventarului FBA, analiza competitiei, calculul profitabilitatii (fees, COGS, PPC), rapoarte de performanta.
Raspunzi in romana, cunosti specificul platformei Amazon si algoritmul A9/A10.`
};

const DEFAULT_SETTINGS = {
    apiKey: '',
    model: 'claude-sonnet-4-6',
    maxTokens: 4096,
    temperature: 0.7,
    enableCaching: true,
    activeProject: 'BFC-Marketplace',
    maxHistoryMessages: 10,
    autoInsertResponse: false,
    showTokenCount: true,
    projects: {
        "ElectroGestion":  { enabled: true, color: "#4CAF50" },
        "BFC-Marketplace": { enabled: true, color: "#2196F3" },
        "Amazon-FBA":      { enabled: true, color: "#FF9800" }
    }
};

// ─── API Client cu token optimization ─────────────────────────────────────────
class ClaudeClient {
    constructor(settings) {
        this.settings = settings;
        this.totalInputTokens = 0;
        this.totalOutputTokens = 0;
        this.cacheHits = 0;
    }

    async sendMessage(messages, project) {
        if (!this.settings.apiKey) throw new Error('API Key lipsa. Configureaza in Settings > Claude Connector.');

        const systemPrompt = PROJECT_PROMPTS[project] || PROJECT_PROMPTS["BFC-Marketplace"];

        const body = {
            model: this.settings.model,
            max_tokens: this.settings.maxTokens,
            temperature: this.settings.temperature,
            system: this.settings.enableCaching
                ? [{ type: "text", text: systemPrompt, cache_control: { type: "ephemeral" } }]
                : systemPrompt,
            messages: this._truncateHistory(messages)
        };

        const response = await requestUrl({
            url: 'https://api.anthropic.com/v1/messages',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': this.settings.apiKey,
                'anthropic-version': '2023-06-01',
                'anthropic-beta': 'prompt-caching-2024-07-31'
            },
            body: JSON.stringify(body),
            throw: true
        });

        const data = response.json;

        // Track token usage
        if (data.usage) {
            this.totalInputTokens += data.usage.input_tokens || 0;
            this.totalOutputTokens += data.usage.output_tokens || 0;
            if (data.usage.cache_read_input_tokens > 0) this.cacheHits++;
        }

        return {
            content: data.content[0]?.text || '',
            usage: data.usage || {},
            cached: (data.usage?.cache_read_input_tokens || 0) > 0
        };
    }

    _truncateHistory(messages) {
        // Keep system context + last N message pairs for token efficiency
        const maxPairs = this.settings.maxHistoryMessages;
        if (messages.length <= maxPairs * 2) return messages;
        return messages.slice(-(maxPairs * 2));
    }

    getStats() {
        const estimatedCost = (this.totalInputTokens / 1000 * 0.003) + (this.totalOutputTokens / 1000 * 0.015);
        return {
            inputTokens: this.totalInputTokens,
            outputTokens: this.totalOutputTokens,
            cacheHits: this.cacheHits,
            estimatedCostUSD: estimatedCost.toFixed(4)
        };
    }
}

// ─── Chat Modal ────────────────────────────────────────────────────────────────
class ClaudeChatModal extends Modal {
    constructor(app, client, settings, initialText) {
        super(app);
        this.client = client;
        this.settings = settings;
        this.initialText = initialText || '';
        this.messages = [];
        this.isLoading = false;
    }

    onOpen() {
        const { contentEl } = this;
        contentEl.empty();
        contentEl.addClass('claude-modal');

        // Header with project selector
        const header = contentEl.createDiv('claude-header');
        header.createEl('h2', { text: 'Claude AI' });

        const projectBar = header.createDiv('claude-project-bar');
        const projectLabel = projectBar.createEl('span', { text: 'Proiect: ' });
        const projectSel = projectBar.createEl('select', { cls: 'claude-project-select' });

        Object.keys(PROJECT_PROMPTS).forEach(p => {
            const opt = projectSel.createEl('option', { text: p, value: p });
            if (p === this.settings.activeProject) opt.selected = true;
        });
        projectSel.addEventListener('change', () => {
            this.settings.activeProject = projectSel.value;
            this.messages = [];
            chatContainer.empty();
            this.addSystemMessage(`Context schimbat la: **${projectSel.value}**. Conversatia a fost resetata.`);
        });

        // Token stats bar
        this.statsEl = header.createDiv('claude-stats');
        this.updateStats();

        // Chat container
        const chatContainer = contentEl.createDiv('claude-chat-container');
        this.chatContainer = chatContainer;

        this.addSystemMessage(`Buna! Sunt contextul **${this.settings.activeProject}**. Ce pot face pentru tine?`);

        // Input area
        const inputArea = contentEl.createDiv('claude-input-area');
        const textarea = inputArea.createEl('textarea', {
            cls: 'claude-input',
            placeholder: 'Scrie intrebarea ta... (Enter = trimite, Shift+Enter = linie noua)'
        });
        textarea.value = this.initialText;

        const btnRow = inputArea.createDiv('claude-btn-row');

        const clearBtn = btnRow.createEl('button', { text: 'Sterge conv.', cls: 'claude-btn-secondary' });
        clearBtn.addEventListener('click', () => {
            this.messages = [];
            chatContainer.empty();
            this.addSystemMessage('Conversatie stearsa.');
            this.updateStats();
        });

        const copyBtn = btnRow.createEl('button', { text: 'Copiaza ultimul', cls: 'claude-btn-secondary' });
        copyBtn.addEventListener('click', () => {
            const last = this.messages.filter(m => m.role === 'assistant').pop();
            if (last) {
                navigator.clipboard.writeText(last.content[0]?.text || '');
                new Notice('Copiat in clipboard!');
            }
        });

        const sendBtn = btnRow.createEl('button', { text: 'Trimite →', cls: 'claude-btn-primary' });

        const send = async () => {
            const text = textarea.value.trim();
            if (!text || this.isLoading) return;
            textarea.value = '';
            this.isLoading = true;
            sendBtn.disabled = true;
            sendBtn.textContent = '...';

            this.addUserMessage(text);
            this.messages.push({ role: 'user', content: text });

            const loadingEl = this.addAssistantMessage('_Se gandeste..._', true);

            try {
                const result = await this.client.sendMessage(this.messages, this.settings.activeProject);
                loadingEl.remove();
                this.addAssistantMessage(result.content);
                this.messages.push({ role: 'assistant', content: [{ type: 'text', text: result.content }] });

                if (result.cached && this.settings.showTokenCount) {
                    new Notice('Cache hit! Tokeni economisiti.', 2000);
                }
                this.updateStats();

                // Auto-insert to active editor
                if (this.settings.autoInsertResponse) {
                    const view = this.app.workspace.getActiveViewOfType(MarkdownView);
                    if (view) {
                        view.editor.replaceSelection('\n\n' + result.content + '\n\n');
                    }
                }
            } catch (err) {
                loadingEl.remove();
                this.addSystemMessage(`**Eroare:** ${err.message}`);
            } finally {
                this.isLoading = false;
                sendBtn.disabled = false;
                sendBtn.textContent = 'Trimite →';
            }
        };

        sendBtn.addEventListener('click', send);
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
        });

        // Focus input
        setTimeout(() => textarea.focus(), 50);
        if (this.initialText) send();
    }

    addUserMessage(text) {
        const el = this.chatContainer.createDiv('claude-msg claude-msg-user');
        el.createEl('strong', { text: 'Tu: ' });
        el.createSpan({ text });
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        return el;
    }

    addAssistantMessage(text, isLoading = false) {
        const el = this.chatContainer.createDiv('claude-msg claude-msg-assistant');
        el.createEl('strong', { text: 'Claude: ' });
        const content = el.createSpan();
        // Simple markdown-like rendering
        content.innerHTML = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        if (isLoading) el.addClass('claude-loading');
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        return el;
    }

    addSystemMessage(text) {
        const el = this.chatContainer.createDiv('claude-msg claude-msg-system');
        el.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        return el;
    }

    updateStats() {
        if (!this.statsEl || !this.settings.showTokenCount) return;
        const s = this.client.getStats();
        this.statsEl.textContent = `Tokeni: ${s.inputTokens}↑ ${s.outputTokens}↓ | Cache hits: ${s.cacheHits} | ~$${s.estimatedCostUSD}`;
    }

    onClose() {
        this.contentEl.empty();
    }
}

// ─── Settings Tab ──────────────────────────────────────────────────────────────
class ClaudeConnectorSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();
        containerEl.createEl('h2', { text: 'Claude Connector Settings' });

        new Setting(containerEl)
            .setName('Anthropic API Key')
            .setDesc('Cheia API de la console.anthropic.com (nu o distribui niciodata)')
            .addText(text => {
                text.inputEl.type = 'password';
                text.setPlaceholder('sk-ant-...')
                    .setValue(this.plugin.settings.apiKey)
                    .onChange(async v => { this.plugin.settings.apiKey = v.trim(); await this.plugin.saveSettings(); });
            });

        new Setting(containerEl)
            .setName('Model Claude')
            .setDesc('Modelul de utilizat. Sonnet 4.6 = echilibru cost/calitate.')
            .addDropdown(dd => dd
                .addOption('claude-haiku-4-5-20251001', 'Claude Haiku 4.5 (rapid, ieftin)')
                .addOption('claude-sonnet-4-6', 'Claude Sonnet 4.6 (recomandat)')
                .addOption('claude-opus-4-7', 'Claude Opus 4.7 (cel mai capabil)')
                .setValue(this.plugin.settings.model)
                .onChange(async v => { this.plugin.settings.model = v; await this.plugin.saveSettings(); }));

        new Setting(containerEl)
            .setName('Proiect activ implicit')
            .addDropdown(dd => dd
                .addOption('ElectroGestion', 'ElectroGestion')
                .addOption('BFC-Marketplace', 'BFC Marketplace')
                .addOption('Amazon-FBA', 'Amazon FBA')
                .setValue(this.plugin.settings.activeProject)
                .onChange(async v => { this.plugin.settings.activeProject = v; await this.plugin.saveSettings(); }));

        new Setting(containerEl)
            .setName('Token caching')
            .setDesc('Activeaza prompt caching (reduce costurile cu ~90% pentru system prompt).')
            .addToggle(t => t
                .setValue(this.plugin.settings.enableCaching)
                .onChange(async v => { this.plugin.settings.enableCaching = v; await this.plugin.saveSettings(); }));

        new Setting(containerEl)
            .setName('Afiseaza statistici tokeni')
            .addToggle(t => t
                .setValue(this.plugin.settings.showTokenCount)
                .onChange(async v => { this.plugin.settings.showTokenCount = v; await this.plugin.saveSettings(); }));

        new Setting(containerEl)
            .setName('Auto-insereaza raspuns in editor')
            .setDesc('Inserteaza automat raspunsul Claude in nota activa.')
            .addToggle(t => t
                .setValue(this.plugin.settings.autoInsertResponse)
                .onChange(async v => { this.plugin.settings.autoInsertResponse = v; await this.plugin.saveSettings(); }));

        new Setting(containerEl)
            .setName('Mesaje maxime in istoric')
            .setDesc('Limiteaza istoricul conversatiei pentru optimizare tokeni (5-20).')
            .addSlider(s => s
                .setLimits(4, 40, 2)
                .setValue(this.plugin.settings.maxHistoryMessages)
                .setDynamicTooltip()
                .onChange(async v => { this.plugin.settings.maxHistoryMessages = v; await this.plugin.saveSettings(); }));

        new Setting(containerEl)
            .setName('Max output tokens')
            .addDropdown(dd => dd
                .addOption('1024', '1024')
                .addOption('2048', '2048')
                .addOption('4096', '4096 (implicit)')
                .addOption('8192', '8192')
                .setValue(String(this.plugin.settings.maxTokens))
                .onChange(async v => { this.plugin.settings.maxTokens = parseInt(v); await this.plugin.saveSettings(); }));
    }
}

// ─── Main Plugin ───────────────────────────────────────────────────────────────
class ClaudeConnectorPlugin extends Plugin {
    async onload() {
        await this.loadSettings();
        this.client = new ClaudeClient(this.settings);

        // Command: Open chat modal
        this.addCommand({
            id: 'claude-open-chat',
            name: 'Claude: Deschide chat',
            hotkeys: [{ modifiers: ['Ctrl', 'Shift'], key: 'C' }],
            callback: () => new ClaudeChatModal(this.app, this.client, this.settings, '').open()
        });

        // Command: Ask about selection
        this.addCommand({
            id: 'claude-ask-selection',
            name: 'Claude: Intreaba despre selectie',
            hotkeys: [{ modifiers: ['Ctrl', 'Shift'], key: 'A' }],
            editorCallback: (editor) => {
                const sel = editor.getSelection();
                if (!sel) { new Notice('Selecteaza text mai intai.'); return; }
                new ClaudeChatModal(this.app, this.client, this.settings, sel).open();
            }
        });

        // Command: Summarize current note
        this.addCommand({
            id: 'claude-summarize-note',
            name: 'Claude: Rezuma nota curenta',
            editorCallback: (editor) => {
                const content = editor.getValue();
                if (!content) { new Notice('Nota este goala.'); return; }
                const prompt = `Rezuma aceasta nota in maximum 5 puncte cheie:\n\n${content.slice(0, 3000)}`;
                new ClaudeChatModal(this.app, this.client, this.settings, prompt).open();
            }
        });

        // Per-project quick commands
        Object.keys(PROJECT_PROMPTS).forEach(project => {
            this.addCommand({
                id: `claude-switch-${project.toLowerCase().replace(/[^a-z0-9]/g, '-')}`,
                name: `Claude: Comuta la ${project}`,
                callback: () => {
                    this.settings.activeProject = project;
                    this.saveSettings();
                    new Notice(`Proiect activ: ${project}`);
                    new ClaudeChatModal(this.app, this.client, this.settings, '').open();
                }
            });
        });

        // Status bar
        this.statusBar = this.addStatusBarItem();
        this.updateStatusBar();

        this.addSettingTab(new ClaudeConnectorSettingTab(this.app, this));
        console.log('Claude Connector loaded');
    }

    updateStatusBar() {
        const project = this.settings.activeProject;
        const colors = { "ElectroGestion": "🟢", "BFC-Marketplace": "🔵", "Amazon-FBA": "🟠" };
        const icon = colors[project] || "🤖";
        this.statusBar.setText(`${icon} Claude: ${project}`);
    }

    onunload() {
        console.log('Claude Connector unloaded');
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
        this.client.settings = this.settings;
        this.updateStatusBar();
    }
}

module.exports = ClaudeConnectorPlugin;
