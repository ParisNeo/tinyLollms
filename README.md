# 🤖 tinyLollms

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)

**tinyLollms** is a secure, production-ready gateway and proxy server designed to bridge frontend applications with a multitude of LLM backends. It solves the critical security issue of exposing API keys and backend infrastructure URLs directly to the client-side code.

---

## 🏗️ Architecture & How It Works

1.  **Frontend**: The `<lollms-chat>` web component (Widget) lives on your website. It only knows your tinyLollms server URL and an **App Key**.
2.  **Proxy Server**: tinyLollms receives the request, validates the **App Key**, checks if the application is **Active**, and verifies that the requested **Model** is whitelisted.
3.  **LLM Backend**: tinyLollms uses the stored credentials (API keys/Service keys) to communicate with the actual AI provider (Ollama, OpenAI, etc.) and streams the response back to the widget.

---

## ✨ Features in Depth

-   **Multi-Binding Core**: Native support for `lollms`, `ollama`, `openai`, `open_router`, `claude`, `google`, `litellm`, `openwebui`, `vllm`, and `llama_cpp_server`.
-   **Model Discovery**: Use the "Fetch Models" feature in the Admin Panel to query the backend in real-time. Selectable chips allow you to build a strict model whitelist for each key.
-   **Dynamic Installation**: Leverages `lollms_client`'s ability to dynamically install required libraries for specific bindings on the fly.
-   **SSL Mastery**: 
    -   Serve tinyLollms over **HTTPS** via environment variables.
    -   Configure backend-specific SSL verification (Skip verification for local dev or provide a path to a custom CA bundle).
-   **Persistence**: Uses an optimized SQLite backend with automatic migrations to ensure your configuration is safe.
-   **Developer Experience**: Built-in `/demo` endpoint for immediate testing and verification.

---

## 🚀 Deployment

### Method 1: Docker Compose (Recommended)

1.  Clone the repository.
2.  Configure your variables in a `.env` file (see Configuration section).
3.  Launch the stack:
    ```bash
    docker-compose up -d
    ```
    *Note: The `./data` directory will be created to store your SQLite database.*

### Method 2: Manual Installation

1.  **Environment Setup**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```
2.  **Launch**:
    ```bash
    python main.py --host 0.0.0.0 --port 8002
    ```

---

## ⚙️ Advanced Configuration (.env)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `HOST` | `0.0.0.0` | Binding address for the proxy server. |
| `PORT` | `8002` | Binding port. |
| `ADMIN_USERNAME` | `admin` | Username for the dashboard. |
| `ADMIN_PASSWORD` | `admin123` | Password for the dashboard. |
| `JWT_SECRET` | `supersecret...` | Cryptographic secret for session tokens. |
| `SSL_KEYFILE` | `None` | Path to the private key (e.g., `/app/certs/key.pem`) for HTTPS. |
| `SSL_CERTFILE` | `None` | Path to the certificate (e.g., `/app/certs/cert.pem`) for HTTPS. |
| `SQLITE_DB` | `data/lollms.db` | Path to the SQLite database file. |

---

## 🛠️ Admin Panel Workflow

### 1. The Demo App
On first launch, tinyLollms creates a **Demo Application** with the key `demo-key`.
-   It is **Deactivated** by default.
-   Go to `/admin`, log in, and click **Edit** on the Demo Application.
-   Configure your local provider (e.g., Ollama at `http://localhost:11434`).
-   Click **Fetch Models**, select your model, and check the **Active** box.

### 2. Model Whitelisting
To prevent unauthorized use of expensive models, each App Key has a whitelist. If the whitelist is empty, **all** models from that backend are allowed. Once you select at least one model via the "Fetch" tool, only those specific models will be accessible via that key.

### 3. Binding Defaults
The UI automatically populates default URLs for popular bindings:
-   **Ollama**: `http://localhost:11434`
-   **OpenAI**: `https://api.openai.com/v1`
-   **OpenWebUI**: `http://localhost:8080`
-   **LiteLLM**: `http://localhost:4000`

---

## 💬 Chat Widget Integration

To add the chat to your own website, add the following tag and script:

```html
<!-- Integration Tag -->
<lollms-chat 
    app-key="your-application-uuid-key" 
    model="the-model-id-e.g-mistral">
</lollms-chat>

<!-- Loading Script -->
<script type="module" src="https://your-server.com:8002/static/lollms_chat.js"></script>
```

### Widget Attributes
-   `app-key`: The unique key generated in the Admin Panel.
-   `model`: The specific model ID (must match one in your whitelist).

---

## 🔒 Security Best Practices

1.  **HTTPS**: If you serve the widget script over HTTPS, your `tinyLollms` server **must** also use HTTPS to avoid Mixed Content errors.
2.  **CORS**: By default, tinyLollms allows all origins. For production, modify the `CORSMiddleware` in `main.py` to only allow your specific frontend domains.
3.  **CA Certificates**: If your LLM backend is internal and uses a self-signed certificate, use the `cert_file_path` field in the Admin UI to provide the `.pem` file for secure verification.
4.  **Secrets**: Never commit your `.env` file or your `data/lollms.db` to version control.

## 🎨 Theming & Customization

You can customize the look and persona of the chat widget directly via HTML attributes and CSS variables.

### HTML Attributes
- `assistant-name`: The name displayed above AI messages (Default: "Assistant").
- `welcome-message`: A greeting message shown when the chat starts.
- `title`: The text shown in the chat window header.
- `app-key`: Your application key from the admin panel.

## 💬 Welcome Message
You can set a welcome message in two ways:
1.  **Globally**: In the Admin Panel, edit your application and fill in the "Welcome Message" field.
2.  **Locally**: Add the `welcome-message` attribute to your `<lollms-chat>` tag. The local attribute takes priority over the database setting.

### CSS Variables (Theming)
Override these in your site's CSS to match your brand:
```css
lollms-chat {
    --lollms-primary: #8e44ad; /* Purple theme */
    --lollms-bg: #fff;
    --lollms-width: 450px;
}
```

### 🔄 Multi-Model Support
If you whitelist more than one model in the Admin Panel for a specific key, the widget will automatically render a dropdown selector in the header, allowing users to switch models during the conversation.
---

## 📄 License
This project is licensed under the **Apache License 2.0**.

Created by [ParisNeo](https://github.com/ParisNeo)