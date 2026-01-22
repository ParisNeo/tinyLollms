# 🤖 tinyLollms

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-05998b.svg)](https://fastapi.tiangolo.com/)
[![GitHub stars](https://img.shields.io/github/stars/ParisNeo/tinyLollms.svg)](https://github.com/ParisNeo/tinyLollms/stargazers)

**tinyLollms** is a lightweight, secure proxy server and chat widget designed to expose various AI backends to your websites and applications. Built on top of `lollms_client`, it allows you to manage multiple AI providers (Ollama, OpenAI, Claude, etc.) through a single interface without exposing your sensitive API keys to the frontend.

---

## ✨ Features

- 🛡️ **Secure Proxy**: Hide your API keys behind a backend proxy.
- 🔌 **Multi-Backend Support**: Connect to Ollama, OpenAI, Anthropic, Google Gemini, vLLM, LiteLLM, and more.
- 🔐 **Admin Dashboard**: Manage "Applications" and generate unique keys for each project.
- 💬 **Web Component Widget**: A ready-to-use, floating chat bubble that can be embedded in any HTML page with one tag.
- 📦 **Lightweight**: Powered by FastAPI, SQLite, and Vanilla JS.

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/ParisNeo/tinyLollms.git
cd tinyLollms
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file (or copy from `.env.example`):

```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
JWT_SECRET=your_random_secret_string
```

### 3. Run the Server

```bash
python main.py
```
The server will start at `http://localhost:8002`.

---

## 🛠️ Usage Flow

### Step 1: Configure your AI Backend
1. Open `http://localhost:8002/admin`.
2. Login with your admin credentials.
3. Create a new **Application**.
4. Choose a **Binding** (e.g., `ollama` for local models or `openai` for cloud).
5. Enter the **Host Address** (e.g., `http://localhost:11434` for Ollama).
6. Enter the **Service Key** (if required by the provider).
7. Save and copy the generated **App Key**.

### Step 2: Embed the Chat Widget
Add the following code to any HTML file:

```html
<!-- 1. The Widget Tag -->
<lollms-chat 
    app-key="YOUR_GENERATED_APP_KEY" 
    model="your-model-name">
</lollms-chat>

<!-- 2. The Script (pointing to your tinyLollms server) -->
<script type="module" src="http://localhost:8002/static/lollms_chat.js"></script>
```

---

## 🔗 Supported Bindings

Through the `lollms_client` library, tinyLollms supports:

| Binding | Target |
| :--- | :--- |
| `lollms` | Lollms Main Server |
| `ollama` | Local Ollama instances |
| `openai` | OpenAI (GPT-4, etc.) |
| `claude` | Anthropic Claude |
| `google` | Google Gemini |
| `open_router` | OpenRouter API |
| `vllm` / `litellm` | High-performance inference servers |
| `llama_cpp_server` | Local llama.cpp instances |

---

## 📂 Project Structure

```text
├── main.py              # FastAPI Backend & Proxy Logic
├── static/
│   ├── admin.html       # Admin Management UI
│   ├── lollms_chat.js   # Frontend Web Component
│   ├── utils.js         # Markdown/Sanitization helpers
│   └── design-tokens.css # UI Styling
├── data/                # SQLite database (auto-generated)
└── test.html            # Local demo page
```

---

## 🛡️ Security Note

- **Admin Credentials**: Change your `ADMIN_PASSWORD` in production.
- **CORS**: By default, the proxy allows all origins (`*`). For production, restrict this in `main.py` to your specific domains.
- **HTTPS**: Always run behind a reverse proxy (like Nginx) with SSL in production environments.

---

## 📄 License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests to improve the UI, add features, or fix bugs.

Created by [Saifeddine ALOUI](https://github.com/ParisNeo)