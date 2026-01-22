import os
import json
import datetime
import uuid
from typing import List, Dict, Any, Optional

import uvicorn
import jwt
import aiosqlite
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Form, Path, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from lollms_client import LollmsClient

# --- Configuration ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey")
JWT_ALGORITHM = "HS256"
SQLITE_DB = os.getenv("SQLITE_DB", "data/lollms.db")

os.makedirs(os.path.dirname(SQLITE_DB), exist_ok=True)

app = FastAPI(title="tinyLollMS Proxy Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

security = HTTPBearer()

# --- JWT & DB Utils ---
def create_jwt_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def init_db():
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                binding TEXT NOT NULL,
                host_address TEXT,
                service_key TEXT,
                allowed_models TEXT
            )
        """)
        await db.commit()

# --- Schemas ---
class AppPayload(BaseModel):
    name: str
    binding: str
    host_address: Optional[str] = ""
    service_key: Optional[str] = ""
    models: Optional[str] = ""

class LoginPayload(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    app_key: str
    model: str
    messages: List[Dict[str, str]]

# --- Routes ---

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    with open("static/admin.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    with open("test.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/admin/login")
async def admin_login(payload: LoginPayload):
    if payload.username != ADMIN_USERNAME or payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    return {"access_token": create_jwt_token(payload.username), "token_type": "bearer"}

@app.get("/admin/apps")
async def list_apps_route(_: str = Depends(verify_jwt_token)):
    async with aiosqlite.connect(SQLITE_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM applications")
        rows = await cursor.fetchall()
        return [dict(r, allowed_models=json.loads(r["allowed_models"])) for r in rows]

@app.post("/admin/add_app")
async def add_app(payload: AppPayload, _: str = Depends(verify_jwt_token)):
    app_key = str(uuid.uuid4())
    models = [m.strip() for m in payload.models.split(",")] if payload.models else []
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute(
            "INSERT INTO applications (key, name, binding, host_address, service_key, allowed_models) VALUES (?, ?, ?, ?, ?, ?)",
            (app_key, payload.name, payload.binding, payload.host_address, payload.service_key, json.dumps(models))
        )
        await db.commit()
    return {"status": "created", "key": app_key}

@app.put("/admin/apps/{app_key}")
async def update_app(app_key: str, payload: AppPayload, _: str = Depends(verify_jwt_token)):
    models = [m.strip() for m in payload.models.split(",")] if payload.models else []
    async with aiosqlite.connect(SQLITE_DB) as db:
        await db.execute(
            "UPDATE applications SET name=?, binding=?, host_address=?, service_key=?, allowed_models=? WHERE key=?",
            (payload.name, payload.binding, payload.host_address, payload.service_key, json.dumps(models), app_key)
        )
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
    
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")

    allowed = json.loads(app_obj["allowed_models"])
    if allowed and req.model not in allowed:
        raise HTTPException(status_code=403, detail="Model not allowed for this application key")

    try:
        lc = LollmsClient(app_obj["binding"], llm_binding_config={
            "host_address": app_obj["host_address"],
            "service_key": app_obj["service_key"],
            "model_name": req.model,
            "verify_ssl_certificate": False
        })
        response = lc.generate_from_messages(req.messages)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
