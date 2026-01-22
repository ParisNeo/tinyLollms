import os
import json
import datetime
import uuid
import importlib
import sys
from typing import List, Dict, Any, Optional

import uvicorn
import jwt
import aiosqlite
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from lollms_client import LollmsClient
import importlib.util

# --- Configuration ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey")
JWT_ALGORITHM = "HS256"
SQLITE_DB = os.getenv("SQLITE_DB", "data/lollms.db")
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", 8002))
SSL_KEYFILE = os.getenv("SSL_KEYFILE", None)
SSL_CERTFILE = os.getenv("SSL_CERTFILE", None)

os.makedirs(os.path.dirname(SQLITE_DB), exist_ok=True)

app = FastAPI(title="tinyLollMS Proxy Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")
security = HTTPBearer()

# --- Helper for Dynamic Imports ---
def get_lollms_client(binding, config):
    try:
        return LollmsClient(binding, llm_binding_config=config)
    except (ImportError, ModuleNotFoundError):
        importlib.invalidate_caches()
        return LollmsClient(binding, llm_binding_config=config)

# --- JWT & DB Utils ---
def create_jwt_token(username: str) -> str:
    payload = {"sub": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8), "iat": datetime.datetime.utcnow()}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
async def init_db():
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                key TEXT PRIMARY KEY, name TEXT NOT NULL, binding TEXT NOT NULL,
                host_address TEXT, service_key TEXT, verify_ssl INTEGER DEFAULT 1,
                cert_file_path TEXT, allowed_models TEXT, active INTEGER DEFAULT 1,
                welcome_message TEXT
            )
        """)
        
        # Migration logic
        cursor = await db.execute("PRAGMA table_info(applications)")
        columns = [row[1] for row in await cursor.fetchall()]
        cols_to_add = {
            "welcome_message": "TEXT",
            "active": "INTEGER DEFAULT 1",
            "binding": "TEXT DEFAULT 'lollms'",
            "host_address": "TEXT",
            "service_key": "TEXT",
            "verify_ssl": "INTEGER DEFAULT 1",
            "cert_file_path": "TEXT"
        }
        for col, definition in cols_to_add.items():
            if col not in columns:
                await db.execute(f"ALTER TABLE applications ADD COLUMN {col} {definition}")
        
        # Default demo app
        cursor = await db.execute("SELECT active FROM applications WHERE key = 'demo-key'")
        if not await cursor.fetchone():
            await db.execute(
                "INSERT INTO applications (key, name, binding, host_address, allowed_models, active, welcome_message) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("demo-key", "Demo Application", "ollama", "http://localhost:11434", "[]", 0, "Hello! How can I help you today?")
            )
        await db.commit()

# --- Schemas ---
class AppPayload(BaseModel):
    name: str
    binding: str
    host_address: str = ""
    service_key: str = ""
    verify_ssl: bool = True
    cert_file_path: str = ""
    models: str = ""
    active: bool = True

class FetchModelsPayload(BaseModel):
    binding: str
    host_address: str
    service_key: str = ""
    verify_ssl: bool = True
    cert_file_path: str = ""

class ChatRequest(BaseModel):
    app_key: str
    model: str
    messages: List[Dict[str, str]]

# --- Routes ---
@app.on_event("startup")
async def on_startup():
    await init_db()

@app.post("/admin/login")
async def admin_login(payload: dict):
    if payload.get("username") != ADMIN_USERNAME or payload.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    return {"access_token": create_jwt_token(payload["username"])}

@app.get("/admin/apps")
async def list_apps(_: str = Depends(verify_jwt_token)):
    async with aiosqlite.connect(SQLITE_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM applications")
        rows = await cursor.fetchall()
        return [dict(r, allowed_models=json.loads(r["allowed_models"]), verify_ssl=bool(r["verify_ssl"]), active=bool(r["active"])) for r in rows]

@app.post("/admin/fetch_models")
async def fetch_models(payload: FetchModelsPayload, _: str = Depends(verify_jwt_token)):
    try:
        config = {"host_address": payload.host_address, "service_key": payload.service_key, "verify_ssl_certificate": payload.verify_ssl, "certificate_file_path": payload.cert_file_path if payload.cert_file_path else None}
        lc = get_lollms_client(payload.binding, config)
        raw_models = lc.list_models()
        processed_models = [m['model_name'] if isinstance(m, dict) and 'model_name' in m else m for m in raw_models]
        return {"models": processed_models}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/admin/add_app")
async def add_app(p: AppPayload, _: str = Depends(verify_jwt_token)):
    app_key = str(uuid.uuid4())
    models = [m.strip() for m in p.models.split(",")] if p.models else []
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute("INSERT INTO applications (key, name, binding, host_address, service_key, verify_ssl, cert_file_path, allowed_models, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (app_key, p.name, p.binding, p.host_address, p.service_key, int(p.verify_ssl), p.cert_file_path, json.dumps(models), int(p.active)))
        await db.commit()
    return {"status": "created"}

@app.put("/admin/apps/{app_key}")
async def update_app(app_key: str, p: AppPayload, _: str = Depends(verify_jwt_token)):
    models = [m.strip() for m in p.models.split(",")] if p.models else []
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute("UPDATE applications SET name=?, binding=?, host_address=?, service_key=?, verify_ssl=?, cert_file_path=?, allowed_models=?, active=? WHERE key=?", (p.name, p.binding, p.host_address, p.service_key, int(p.verify_ssl), p.cert_file_path, json.dumps(models), int(p.active), app_key))
        await db.commit()
    return {"status": "updated"}

@app.delete("/admin/apps/{app_key}")
async def delete_app(app_key: str, _: str = Depends(verify_jwt_token)):
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute("DELETE FROM applications WHERE key = ?", (app_key,))
        await db.commit()
    return {"status": "deleted"}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    async with aiosqlite.connect(SQLITE_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM applications WHERE key = ?", (req.app_key,))
        app_obj = await cursor.fetchone()
    if not app_obj: raise HTTPException(status_code=404, detail="App not found")
    if not bool(app_obj["active"]): raise HTTPException(status_code=403, detail="Application deactivated")
    allowed = json.loads(app_obj["allowed_models"])
    if allowed and req.model not in allowed: raise HTTPException(status_code=403, detail="Model forbidden")
    try:
        config = {"host_address": app_obj["host_address"], "service_key": app_obj["service_key"], "model_name": req.model, "verify_ssl_certificate": bool(app_obj["verify_ssl"]), "certificate_file_path": app_obj["cert_file_path"] if app_obj["cert_file_path"] else None}
        lc = get_lollms_client(app_obj["binding"], config)
        return {"response": lc.generate_from_messages(req.messages)}
    except Exception as e: raise HTTPException(status_code=502, detail=str(e))

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    with open("static/admin.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    async with aiosqlite.connect(SQLITE_DB) as db:
        cursor = await db.execute("SELECT active FROM applications WHERE key = 'demo-key'")
        row = await cursor.fetchone()
        if not row or not bool(row[0]):
            return HTMLResponse(content="<h1>403 Forbidden</h1><p>Demo page is deactivated. Enable 'Demo Application' in Admin.</p>", status_code=403)
    with open("test.html", "r", encoding="utf-8") as f: return f.read()


# --- Updated App Metadata Route ---
@app.get("/api/app_info/{app_key}")
async def get_app_info(app_key: str):
    async with aiosqlite.connect(SQLITE_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT name, allowed_models, active, welcome_message FROM applications WHERE key = ?", (app_key,))
        app_obj = await cursor.fetchone()
    
    if not app_obj: raise HTTPException(status_code=404)
    return {
        "name": app_obj["name"],
        "active": bool(app_obj["active"]),
        "allowed_models": json.loads(app_obj["allowed_models"]),
        "welcome_message": app_obj["welcome_message"]
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="tinyLollMS proxy server")
    parser.add_argument("--host", default=SERVER_HOST)
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    parser.add_argument("--ssl-keyfile", default=SSL_KEYFILE)
    parser.add_argument("--ssl-certfile", default=SSL_CERTFILE)
    args = parser.parse_args()
    uvicorn.run("main:app", host=args.host, port=args.port, ssl_keyfile=args.ssl_keyfile, ssl_certfile=args.ssl_certfile)
