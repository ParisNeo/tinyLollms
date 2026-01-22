import { mdToHtml } from "./utils.js";

class LollmsChat extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
        this._appKey = "";
        this._model = "default";
        this._conversation = [];

        this.shadowRoot.innerHTML = `
            <style>
                .bubble { position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: #0066cc; border-radius: 50%; color: white; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3); z-index: 9999; font-size: 24px; transition: transform 0.2s; }
                .bubble:hover { transform: scale(1.1); }
                .window { position: fixed; bottom: 90px; right: 20px; width: 400px; height: 550px; background: white; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); display: none; flex-direction: column; z-index: 9999; overflow: hidden; font-family: system-ui, sans-serif; }
                .header { background: #0066cc; color: white; padding: 15px; font-weight: bold; display: flex; justify-content: space-between; }
                .messages { flex: 1; padding: 15px; overflow-y: auto; background: #f9f9f9; display: flex; flex-direction: column; gap: 10px; }
                .msg { padding: 10px 14px; border-radius: 10px; max-width: 85%; font-size: 14px; line-height: 1.4; }
                .msg.user { align-self: flex-end; background: #0066cc; color: white; }
                .msg.bot { align-self: flex-start; background: #e9e9eb; color: #333; }
                .input-box { border-top: 1px solid #eee; padding: 10px; display: flex; gap: 5px; }
                textarea { flex: 1; border: 1px solid #ddd; border-radius: 6px; padding: 8px; resize: none; outline: none; height: 40px; }
                button { background: #0066cc; color: white; border: none; padding: 0 15px; border-radius: 6px; cursor: pointer; }
            </style>
            <div class="bubble" id="toggle">💬</div>
            <div class="window" id="win">
                <div class="header">Chat Assistant <span style="cursor:pointer" id="close">✕</span></div>
                <div class="messages" id="msgs"></div>
                <div class="input-box">
                    <textarea id="txt" placeholder="Ask something..."></textarea>
                    <button id="send">Send</button>
                </div>
            </div>
        `;
    }

    connectedCallback() {
        this._appKey = this.getAttribute("app-key") || "";
        this._model = this.getAttribute("model") || "default";

        const win = this.shadowRoot.getElementById('win');
        const toggle = this.shadowRoot.getElementById('toggle');
        const txt = this.shadowRoot.getElementById('txt');
        
        toggle.onclick = () => win.style.display = win.style.display === 'flex' ? 'none' : 'flex';
        this.shadowRoot.getElementById('close').onclick = () => win.style.display = 'none';
        this.shadowRoot.getElementById('send').onclick = () => this.send();
        txt.onkeydown = (e) => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); } };
    }

    async send() {
        const input = this.shadowRoot.getElementById('txt');
        const text = input.value.trim();
        if (!text) return;

        input.value = '';
        this.addMessage('user', text);
        this._conversation.push({role: 'user', content: text});

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    app_key: this._appKey,
                    model: this._model,
                    messages: this._conversation
                })
            });
            const data = await res.json();
            const reply = data.response || "Error: No response from server.";
            this.addMessage('bot', reply);
            this._conversation.push({role: 'assistant', content: reply});
        } catch (e) {
            this.addMessage('bot', "Connection failed.");
        }
    }

    addMessage(role, text) {
        const div = document.createElement('div');
        div.className = `msg ${role}`;
        div.innerHTML = role === 'bot' ? mdToHtml(text) : text;
        const box = this.shadowRoot.getElementById('msgs');
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
    }
}

customElements.define("lollms-chat", LollmsChat);
