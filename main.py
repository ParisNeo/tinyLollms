import os
import json
import datetime
import uuid
from typing import List, Dict, Any, Optional

import uvicorn
import jwt  # PyJWT
import aiosqlite
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Form, Path, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from lollms_client import LollmsClient



# -------------------------------- Mock OpenWebUI client --------------------------------
class OpenWebUIClient:
    """
    Mock client – replace with the real implementation.
    """
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def chat(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        lc = LollmsClient("openwebui",llm_binding_config={
            "host_address":OPENWEBUI_URL,
            "service_key":OPENWEBUI_API_KEY,
            "model_name":model,
            "verify_ssl_certificate":False
        })
        return {"response": lc.generate_from_messages(messages)}


# -------------------------------- Configuration --------------------------------
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")          # admin login password
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")            # admin login username
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey")        # change in prod
JWT_ALGORITHM = "HS256"
SQLITE_DB = os.getenv("SQLITE_DB", "data/lollms.db")
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://localhost:8000")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "openwebui_key")

# Ensure data directory exists
os.makedirs(os.path.dirname(SQLITE_DB), exist_ok=True)

# -------------------------------- FastAPI app --------------------------------
app = FastAPI(title="LollMS Proxy Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------------- JWT utilities --------------------------------
security = HTTPBearer()


def create_jwt_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=4),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# -------------------------------- DB helpers --------------------------------
async def init_db():
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                allowed_models TEXT   -- JSON encoded list
            )
            """
        )
        await db.commit()


async def get_app(key: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(SQLITE_DB) as db:
        cursor = await db.execute("SELECT name, allowed_models FROM applications WHERE key = ?", (key,))
        row = await cursor.fetchone()
        if not row:
            return None
        name, allowed_models_json = row
        allowed = json.loads(allowed_models_json) if allowed_models_json else []
        return {"key": key, "name": name, "allowed_models": allowed}


async def create_app(app_obj: Dict[str, Any]) -> None:
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute(
            "INSERT INTO applications (key, name, allowed_models) VALUES (?, ?, ?)",
            (app_obj["key"], app_obj["name"], json.dumps(app_obj.get("allowed_models", []))),
        )
        await db.commit()


async def update_app(key: str, data: Dict[str, Any]) -> None:
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute(
            "UPDATE applications SET name = ?, allowed_models = ? WHERE key = ?",
            (data["name"], json.dumps(data.get("allowed_models", [])), key),
        )
        await db.commit()


async def delete_app(key: str) -> None:
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute("DELETE FROM applications WHERE key = ?", (key,))
        await db.commit()


async def list_apps() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(SQLITE_DB) as db:
        cursor = await db.execute("SELECT key, name, allowed_models FROM applications")
        rows = await cursor.fetchall()
        result = []
        for key, name, allowed_models_json in rows:
            allowed = json.loads(allowed_models_json) if allowed_models_json else []
            result.append({"key": key, "name": name, "allowed_models": allowed})
        return result


# -------------------------------- Startup event --------------------------------
@app.on_event("startup")
async def on_startup():
    await init_db()


# -------------------------------- Models --------------------------------
class Application(BaseModel):
    name: str
    key: str
    allowed_models: List[str] = []  # empty = all models allowed


class AddAppPayload(BaseModel):
    name: str
    key: Optional[str] = Field(default=None, description="If omitted, a UUID will be generated")
    models: Optional[str] = None   # comma separated string


class LoginPayload(BaseModel):
    username: str
    password: str


class Message(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    app_key: str
    model: str
    messages: List[Message]


class UpdateAppPayload(BaseModel):
    name: Optional[str] = None
    models: Optional[str] = None   # comma separated


# -------------------------------- Routes --------------------------------

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """
    Serves the static admin UI (admin.html).
    """
    with open("static/admin.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.post("/admin/login")
async def admin_login(payload: LoginPayload):
    """
    Simple login returning a JWT token.
    """
    if payload.username != ADMIN_USERNAME or payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    token = create_jwt_token(payload.username)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/admin/add_app")
async def add_application(
    payload: AddAppPayload,
    _: str = Depends(verify_jwt_token)  # JWT protected
):
    """
    Create a new application. If `key` is omitted, a UUID4 key is generated.
    """
    # Autogenerate key when missing
    app_key = payload.key or str(uuid.uuid4())
    if await get_app(app_key):
        raise HTTPException(status_code=400, detail="Application key already exists")
    allowed = [m.strip() for m in payload.models.split(",")] if payload.models else []
    app_obj = {"name": payload.name, "key": app_key, "allowed_models": allowed}
    await create_app(app_obj)
    return {"status": "created", "application": app_obj}


@app.get("/admin/apps", response_model=List[Application])
async def admin_list_apps(_: str = Depends(verify_jwt_token)):
    apps = await list_apps()
    return apps


@app.put("/admin/apps/{app_key}")
async def admin_update_app(
    app_key: str,
    payload: UpdateAppPayload,
    _: str = Depends(verify_jwt_token)
):
    app = await get_app(app_key)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if payload.name is not None:
        app["name"] = payload.name
    if payload.models is not None:
        app["allowed_models"] = [m.strip() for m in payload.models.split(",")] if payload.models else []
    await update_app(app_key, app)
    return {"status": "updated", "application": app}


@app.delete("/admin/apps/{app_key}")
async def admin_delete_app(
    app_key: str,
    _: str = Depends(verify_jwt_token)
):
    app = await get_app(app_key)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await delete_app(app_key)
    return {"status": "deleted", "key": app_key}


@app.get("/demo", response_class=HTMLResponse)
async def demo():
    """
    Serves the demo chat UI (test.html).
    """
    with open("test.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    # Validate application
    app_obj = await get_app(req.app_key)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")

    # Model whitelist check
    if app_obj.get("allowed_models") and req.model not in app_obj["allowed_models"]:
        raise HTTPException(status_code=403, detail="Model not allowed for this application")

    client = OpenWebUIClient(base_url=OPENWEBUI_URL, api_key=OPENWEBUI_API_KEY)
    try:
        response = await client.chat(model=req.model, messages=[m.dict() for m in req.messages])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error contacting OpenWebUI: {exc}")

    return JSONResponse(content=response)


# -------------------------------- Server entry point --------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LollMS proxy server")
    parser = argparse.ArgumentParser(description="LollMS proxy server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--ssl-keyfile", help="Path to SSL key file")
    parser.add_argument("--ssl-certfile", help="Path to SSL certificate file")
    args = parser.parse_args()

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
        log_level="info",
        reload=False,
    )
