import { mdToHtml } from "./utils.js";

class LollmsChat extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
        this._conversation = [];
        this._selectedModel = "";
        this.shadowRoot.innerHTML = `
            <style>
                :host { --lollms-primary: #0066cc; --lollms-bg: #f5f5f5; --lollms-width: 400px; }
                .bubble { position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: var(--lollms-primary); border-radius: 50%; color: white; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.2); font-size: 24px; z-index: 9999; }
                .window { position: fixed; bottom: 90px; right: 20px; width: var(--lollms-width); height: 550px; background: white; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); display: none; flex-direction: column; overflow: hidden; font-family: sans-serif; z-index: 9999; }
                .header { background: var(--lollms-primary); color: white; padding: 12px 15px; }
                .header-top { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
                .model-sel { background: rgba(255,255,255,0.2); color: white; border: none; font-size: 11px; margin-top: 5px; border-radius: 4px; padding: 2px; width: 100%; outline: none; }
                .messages { flex: 1; padding: 15px; overflow-y: auto; background: var(--lollms-bg); display: flex; flex-direction: column; gap: 10px; }
                .msg { padding: 10px; border-radius: 8px; font-size: 14px; line-height: 1.4; max-width: 85%; }
                .msg.user { align-self: flex-end; background: var(--lollms-primary); color: white; }
                .msg.bot { align-self: flex-start; background: white; border: 1px solid #ddd; }
                .name { font-size: 10px; font-weight: bold; color: #777; margin-bottom: 2px; }
                .input-area { padding: 10px; border-top: 1px solid #eee; display: flex; gap: 5px; }
                textarea { flex: 1; height: 40px; resize: none; border: 1px solid #ddd; border-radius: 6px; padding: 8px; font-family: inherit; }
                button { background: var(--lollms-primary); color: white; border: none; padding: 0 15px; border-radius: 6px; cursor: pointer; font-weight: bold; }
                .loader { display: none; padding: 10px; }
                .dot { width: 6px; height: 6px; background: #bbb; border-radius: 50%; display: inline-block; animation: w 1s infinite ease-in-out; margin: 0 2px; }
                @keyframes w { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
            </style>
            <div class="bubble" id="btn">💬</div>
            <div class="window" id="win">
                <div class="header">
                    <div class="header-top"><span id="title">Chat</span><span id="close" style="cursor:pointer">✕</span></div>
                    <select id="sel" class="model-sel" style="display:none"></select>
                </div>
                <div class="messages" id="msgs"></div>
                <div id="loading" class="loader"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
                <div class="input-area">
                    <textarea id="txt" placeholder="Type here..."></textarea>
                    <button id="send">Send</button>
                </div>
            </div>
        `;
    }

    async connectedCallback() {
        this._appKey = this.getAttribute("app-key") || "";
        this._botName = this.getAttribute("assistant-name") || "Assistant";
        this.shadowRoot.getElementById('title').textContent = this.getAttribute("title") || "LollMS Chat";

        const res = await fetch(`/api/app_info/${this._appKey}`);
        if(res.ok) {
            const info = await res.json();
            if(info.welcome_message) this.addMessage('bot', info.welcome_message);
            const sel = this.shadowRoot.getElementById('sel');
            if(info.allowed_models.length > 1) {
                sel.style.display = 'block';
                sel.innerHTML = info.allowed_models.map(m => `<option value="${m}">${m}</option>`).join('');
                this._selectedModel = info.allowed_models[0];
                sel.onchange = (e) => this._selectedModel = e.target.value;
            } else { this._selectedModel = info.allowed_models[0] || this.getAttribute("model"); }
        }

        const win = this.shadowRoot.getElementById('win');
        const txt = this.shadowRoot.getElementById('txt');
        this.shadowRoot.getElementById('btn').onclick = () => { win.style.display='flex'; txt.focus(); };
        this.shadowRoot.getElementById('close').onclick = () => win.style.display='none';
        this.shadowRoot.getElementById('send').onclick = () => this.send();
        
        // ENTER TO SEND FIX
        txt.onkeydown = (e) => {
            if(e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send();
            }
        };
    }

    async send() {
        const txt = this.shadowRoot.getElementById('txt');
        const text = txt.value.trim();
        if(!text) return;
        txt.value = ''; this.addMessage('user', text);
        this._conversation.push({role:'user', content: text});
        this.shadowRoot.getElementById('loading').style.display = 'block';
        try {
            const r = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({app_key:this._appKey, model:this._selectedModel, messages:this._conversation})});
            const data = await r.json();
            this.shadowRoot.getElementById('loading').style.display = 'none';
            if(r.ok) {
                this.addMessage('bot', data.response);
                this._conversation.push({role:'assistant', content:data.response});
            }
        } catch(e) { this.shadowRoot.getElementById('loading').style.display = 'none'; }
    }

    addMessage(role, text) {
        const div = document.createElement('div');
        div.className = `msg ${role}`;
        div.innerHTML = role === 'bot' ? `<div class="name">${this._botName}</div>` + mdToHtml(text) : text;
        const msgs = this.shadowRoot.getElementById('msgs');
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
    }
}
customElements.define("lollms-chat", LollmsChat);
