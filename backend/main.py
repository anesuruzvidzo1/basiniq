import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select
from sentence_transformers import SentenceTransformer, CrossEncoder
from db import init_db, AsyncSessionLocal, Session
from es_client import init_es
from router import route_query


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_es()
    app.state.bi_encoder = SentenceTransformer("all-MiniLM-L6-v2")
    app.state.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    yield


app = FastAPI(title="BasinIQ API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://*.vercel.app"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query")
async def query(request: Request):
    body = await request.json()
    question = body.get("question", "").strip()
    session_id = body.get("session_id")

    if not question:
        return JSONResponse({"error": "question is required"}, status_code=400)

    # load conversation history for this session
    history: list[dict] = []
    async with AsyncSessionLocal() as db:
        if session_id:
            result = await db.execute(select(Session).where(Session.id == session_id))
            existing = result.scalar_one_or_none()
            if existing:
                history = existing.messages or []
        else:
            session_id = str(uuid.uuid4())

    result = await route_query(
        question,
        request.app.state.bi_encoder,
        request.app.state.cross_encoder,
        history=history,
    )

    # persist only the clean user/assistant exchange — not internal tool calls
    updated_history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": result["answer"]},
    ]

    async with AsyncSessionLocal() as db:
        existing = await db.get(Session, session_id)
        if existing:
            existing.messages = updated_history
        else:
            db.add(Session(id=session_id, messages=updated_history))
        await db.commit()

    return {**result, "session_id": session_id}
