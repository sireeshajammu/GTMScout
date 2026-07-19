"""GTMScout FastAPI backend.

Stateless service: one real job — turn a chat message into an assistant Message
(a market-entry report or a clarifying reply). Conversations, history, and profile
live client-side in the frontend, which keeps this backend serverless-friendly.
"""
import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator import run_research

load_dotenv()

app = FastAPI(title="GTMScout API", version="1.0.0")

# CORS — set FRONTEND_ORIGIN (comma-separated) in prod; defaults to allow-all.
_origins = os.getenv("FRONTEND_ORIGIN", "*")
allow_origins = ["*"] if _origins.strip() == "*" else [o.strip() for o in _origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryItem(BaseModel):
    role: str
    text: str = ""


class ResearchBody(BaseModel):
    text: str
    history: Optional[List[HistoryItem]] = None
    home_country: Optional[str] = None
    budget: Optional[float] = None
    currency: Optional[str] = None


@app.get("/")
def root():
    return {"service": "GTMScout API", "status": "ok", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok", "model": os.getenv("GTMSCOUT_MODEL", "gpt-4o-mini"),
            "openai_key_present": bool(os.getenv("OPENAI_API_KEY"))}


@app.post("/api/research")
def research(body: ResearchBody):
    """Run the agent pipeline on a chat message and return an assistant Message."""
    if not body.text or not body.text.strip():
        return {"id": "err", "role": "assistant", "kind": "text",
                "text": "Please enter a question about a market.", "created_at": ""}

    history = [h.model_dump() for h in body.history] if body.history else None
    msg = run_research(
        text=body.text.strip(),
        history=history,
        home_country=body.home_country,
        budget=body.budget,
        currency=body.currency,
    )
    # Strip internal-only keys before returning (keeps the Message type clean).
    msg.pop("_cost", None)
    return msg
