import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent.core import run_agent
import uvicorn


app = FastAPI(title="GitPilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory chat history per session (good enough for demo)
chat_sessions: dict = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.get("/health")
def health():
    return {"status": "ok", "agent": "GitPilot"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        history = chat_sessions.get(req.session_id, [])
        response = run_agent(req.message, history)
        # history is mutated in-place inside run_agent, save it
        chat_sessions[req.session_id] = history
        return ChatResponse(response=response, session_id=req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{session_id}")
def clear_session(session_id: str):
    chat_sessions.pop(session_id, None)
    return {"cleared": session_id}

# Serve frontend
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8080, reload=True)