import os
import asyncio
import uuid
import json
from pathlib import Path
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select
from sentence_transformers import SentenceTransformer, CrossEncoder
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from db import init_db, AsyncSessionLocal, Session
from router import route_query, stream_query


async def _auto_setup(bi_encoder: SentenceTransformer):
    from seed import seed
    from ingest_docs import ingest_pdf

    await seed()

    pdfs = sorted(Path("/data").glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in /data — skipping ingest.")
        return
    for pdf_path in pdfs:
        await ingest_pdf(str(pdf_path), bi_encoder)
    print("Auto-setup complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.bi_encoder = SentenceTransformer("all-MiniLM-L6-v2")
    app.state.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    asyncio.create_task(_auto_setup(app.state.bi_encoder))
    yield


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="BasinIQ API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_API_KEY = os.getenv("BASINIQ_API_KEY")


async def _require_api_key(x_api_key: str | None = Header(None)):
    if _API_KEY and x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query")
@limiter.limit("10/minute")
async def query(request: Request, _: None = Depends(_require_api_key)):
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


@app.post("/query/stream")
@limiter.limit("10/minute")
async def query_stream(request: Request, _: None = Depends(_require_api_key)):
    body = await request.json()
    question = body.get("question", "").strip()
    session_id = body.get("session_id")

    if not question:
        return JSONResponse({"error": "question is required"}, status_code=400)

    history: list[dict] = []
    async with AsyncSessionLocal() as db:
        if session_id:
            result = await db.execute(select(Session).where(Session.id == session_id))
            existing = result.scalar_one_or_none()
            if existing:
                history = existing.messages or []
        else:
            session_id = str(uuid.uuid4())

    bi_encoder = request.app.state.bi_encoder
    cross_encoder = request.app.state.cross_encoder

    async def generate():
        answer = ""
        async for chunk in stream_query(question, bi_encoder, cross_encoder, history):
            if chunk.startswith("data: "):
                try:
                    evt = json.loads(chunk[6:])
                    if evt.get("type") == "done":
                        answer = evt.get("answer", "")
                        updated_history = history + [
                            {"role": "user", "content": question},
                            {"role": "assistant", "content": answer},
                        ]
                        async with AsyncSessionLocal() as db:
                            existing = await db.get(Session, session_id)
                            if existing:
                                existing.messages = updated_history
                            else:
                                db.add(Session(id=session_id, messages=updated_history))
                            await db.commit()
                        evt["session_id"] = session_id
                        yield f"data: {json.dumps(evt)}\n\n"
                        continue
                except Exception:
                    pass
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
