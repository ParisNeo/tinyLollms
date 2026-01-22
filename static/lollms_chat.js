// Enhanced lollms-chat web component – floating bubble chat widget.
// Usage: <lollms-chat app_key="my_key" model="gpt-4"></lollms-chat>
import { mdToHtml } from "./utils.js";

class LollmsChat extends HTMLElement {
    static get observedAttributes() {
        return ["app_key", "app-key", "model"];
    }

    constructor() {
        super();
        this.attachShadow({ mode: "open" });

        // Initialize attributes (will be updated in attributeChangedCallback)
        this._appKey = "";
        this._model = "default";

        // Base UI – hidden initially, will be toggled by the bubble button
        this.shadowRoot.innerHTML = `
            <style>
                .bubble-btn {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    width: 60px;
                    height: 60px;
                    background: #0066cc;
                    border-radius: 50%;
                    color: #fff;
                    font-size: 30px;
                    line-height: 60px;
                    text-align: center;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                    z-index: 1000;
                }
                .chat-window {
                    position: fixed;
                    bottom: 90px;
                    right: 20px;
                    width: 480px;               /* larger width */
                    max-height: 600px;          /* larger height */
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 1000;
                    font-family: Arial, sans-serif;
                }
                .header {
                    background: #0066cc;
                    color: #fff;
                    padding: 8px;
                    text-align: center;
                    font-weight: bold;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
                .messages {
                    flex: 1;
                    padding: 8px;
                    overflow-y: auto;
                }
                .msg {
                    margin: 4px 0;
                }
                .msg.user { color: #0b79d0; }
                .msg.assistant { color: #333; }
                .input-area {
                    display: flex;
                    border-top: 1px solid #eee;
                }
                textarea {
                    flex: 1;
                    resize: none;
                    border: none;
                    padding: 8px;
                    font-size: 14px;
                    line-height: 1.4;
                }
                button.send {
                    background: #0066cc;
                    color: #fff;
                    border: none;
                    padding: 0 12px;
                    cursor: pointer;
                }
            </style>
            <div class="bubble-btn" title="Open chat">💬</div>
            <div class="chat-window" style="display:none;">
                <div class="header">LollMS Chat</div>
                <div class="messages" id="msgBox"></div>
                <div class="input-area">
                    <textarea id="inputBox" rows="2" placeholder="Type a message..."></textarea>
                    <button class="send" id="sendBtn">▶</button>
                </div>
            </div>
        `;

        this._bubbleBtn = this.shadowRoot.querySelector(".bubble-btn");
        this._chatWindow = this.shadowRoot.querySelector(".chat-window");
        this._msgBox = this.shadowRoot.getElementById("msgBox");
        this._inputBox = this.shadowRoot.getElementById("inputBox");
        this._sendBtn = this.shadowRoot.getElementById("sendBtn");

        this._conversation = [];

        this._bubbleBtn.addEventListener("click", () => {
            this._chatWindow.style.display = "flex";
            this._bubbleBtn.style.display = "none";
            this._inputBox.focus();
        });

        this._sendBtn.addEventListener("click", () => this._onSend());

        // Enter (without Shift) sends the message
        this._inputBox.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this._onSend();
            }
        });
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "app_key" || name === "app-key") {
            this._appKey = newValue || "";
        } else if (name === "model") {
            this._model = newValue || "default";
        }
    }

    connectedCallback() {
        // Ensure attributes are read on initial connection
        this._appKey = this.getAttribute("app_key") || this.getAttribute("app-key") || "";
        this._model = this.getAttribute("model") || "default";
    }

    _appendMessage(role, content) {
        const div = document.createElement("div");
        div.className = `msg ${role}`;
        // Render markdown for assistant messages; plain text for user
        if (role === "assistant") {
            div.innerHTML = mdToHtml(content);
        } else {
            div.textContent = `You: ${content}`;
        }
        this._msgBox.appendChild(div);
        this._msgBox.scrollTop = this._msgBox.scrollHeight;
    }

    async _onSend() {
        const userMsg = this._inputBox.value.trim();
        if (!userMsg) return;
        this._inputBox.value = "";
        this._appendMessage("user", userMsg);
        this._conversation.push({ role: "user", content: userMsg });

        const payload = {
            app_key: this._appKey,
            model: this._model,
            messages: this._conversation,
        };

        try {
            const resp = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!resp.ok) throw new Error(`Server error ${resp.status}`);
            const data = await resp.json();
            const assistantMsg = data.response || "[no reply]";
            this._appendMessage("assistant", assistantMsg);
            this._conversation.push({ role: "assistant", content: assistantMsg });
            // Emit custom event for external listeners (e.g., demo page)
            this.dispatchEvent(new CustomEvent("lollms-response", { detail: data }));
        } catch (e) {
            console.error(e);
            this._appendMessage("assistant", `Error: ${e.message}`);
        }
    }
}

// Register the custom element (must contain a hyphen)
customElements.define("lollms-chat", LollmsChat);
