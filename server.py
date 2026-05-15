"""
Agent Product Studio — FastAPI Backend
Wraps the ADK orchestrator in a WebSocket-enabled API.
Serves the vanilla JS frontend as static files.
"""
import asyncio
import json
import os
import uuid
import base64
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from orchestrator.agent import root_agent
from orchestrator.tools.gcs_tools import list_projects, read_file

app = FastAPI(title="Agent Product Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Shared ADK infrastructure ──────────────────────────────────────────────
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="agent-product-studio",
    session_service=session_service,
)
initialized_sessions: set = set()

# ─── Chat history persistence ───────────────────────────────────────────────
SESSIONS_DIR = Path(__file__).parent / ".adk" / "studio_sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_chat_session(session_id: str, data: dict):
    (SESSIONS_DIR / f"{session_id}.json").write_text(json.dumps(data, indent=2, default=str))


def load_chat_session(session_id: str) -> dict | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def get_all_chat_sessions() -> list[dict]:
    sessions = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            sessions.append(json.loads(f.read_text()))
        except Exception:
            pass
    return sorted(sessions, key=lambda x: x.get("timestamp", ""), reverse=True)


# ─── Agent metadata ─────────────────────────────────────────────────────────
AGENT_META = {
    "orchestrator":    {"icon": "brain",   "color": "#a78bfa", "label": "Orchestrator"},
    "architect_agent": {"icon": "compass", "color": "#60a5fa", "label": "Architect"},
    "coder_agent":     {"icon": "code",    "color": "#34d399", "label": "Coder"},
    "infra_agent":     {"icon": "server",  "color": "#fb923c", "label": "Infra"},
    "reviewer_agent":  {"icon": "search",  "color": "#22d3ee", "label": "Reviewer"},
}


# ─── WebSocket: streaming chat ──────────────────────────────────────────────
@app.websocket("/api/chat")
async def chat_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        data = await ws.receive_json()
        session_id = data.get("session_id", str(uuid.uuid4()))
        user_id = data.get("user_id", "kathan")
        message = data.get("message", "")
        files = data.get("files", [])

        # Initialize ADK session if needed
        if session_id not in initialized_sessions:
            await session_service.create_session(
                app_name="agent-product-studio",
                user_id=user_id,
                session_id=session_id,
            )
            initialized_sessions.add(session_id)

        # Build content parts
        parts = []
        if message:
            parts.append(types.Part.from_text(text=message))
        for f in files:
            file_data = base64.b64decode(f["data"])
            parts.append(types.Part.from_data(data=file_data, mime_type=f["type"]))
        if not message and files:
            parts.append(types.Part.from_text(text="Please analyze these attached files."))

        content = types.Content(role="user", parts=parts)

        # Stream agent events to the frontend
        active_project = None
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            author = event.author or "orchestrator"
            meta = AGENT_META.get(author, {"icon": "bot", "color": "#94a3b8", "label": author})

            # Notify on sub-agent activation
            if event.author and event.author != "orchestrator":
                await ws.send_json({
                    "type": "agent_start",
                    "agent": author,
                    **meta,
                })

            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = dict(fc.args) if fc.args else {}
                        if "project_name" in args:
                            active_project = args["project_name"]
                        # Check if a mockup was just written
                        is_preview = (fc.name == "write_file" and
                                      args.get("path", "").endswith("mockup.html"))
                        await ws.send_json({
                            "type": "tool_call",
                            "agent": author,
                            **meta,
                            "tool": fc.name,
                            "args": args,
                            "preview_ready": is_preview,
                        })
                    elif hasattr(part, "text") and part.text:
                        if author == "orchestrator" or not event.author:
                            await ws.send_json({
                                "type": "text_delta",
                                "content": part.text,
                            })

        await ws.send_json({
            "type": "done",
            "active_project": active_project,
        })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ─── REST endpoints ─────────────────────────────────────────────────────────
@app.get("/api/projects")
async def get_projects():
    try:
        projects = list_projects()
        if projects and projects[0] != "(no projects yet)":
            return {"projects": projects}
        return {"projects": []}
    except Exception:
        return {"projects": []}


@app.get("/api/preview/{project_name}")
async def get_preview(project_name: str):
    try:
        html = read_file(project_name, "mockup.html")
        if html and not html.startswith("Not found:") and not html.startswith("Error"):
            return HTMLResponse(content=html)
        return HTMLResponse(content="", status_code=404)
    except Exception:
        return HTMLResponse(content="", status_code=500)


@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": get_all_chat_sessions()}


@app.post("/api/sessions/{session_id}")
async def save_session(session_id: str, data: dict):
    save_chat_session(session_id, data)
    return {"ok": True}


@app.get("/api/agents")
async def get_agents():
    return {"agents": AGENT_META}


# ─── Serve frontend ─────────────────────────────────────────────────────────
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    @app.get("/")
    async def serve_index():
        return FileResponse(frontend_dir / "index.html")

    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
