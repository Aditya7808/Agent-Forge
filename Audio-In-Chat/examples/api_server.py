"""FastAPI integration example.

Endpoints:
    POST /ingest    multipart upload of an audio file → indexes it
    POST /query     JSON {"question": "..."} → streamed answer (text/event-stream)
    POST /reset     drop the vector collection and chat history
    GET  /stats     pipeline metadata

Run:
    pip install "audio-chat[api]"  # or: pip install fastapi uvicorn python-multipart
    export OPENAI_API_KEY=sk-...
    uvicorn examples.api_server:app --reload --port 8000
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from audio_chat import AudioChatPipeline
from audio_chat.exceptions import AudioChatError

app = FastAPI(title="audio_chat API", version="1.0.0")
pipeline = AudioChatPipeline.from_env()


class QueryBody(BaseModel):
    question: str
    top_k: int | None = None


@app.get("/stats")
def stats() -> dict:
    return pipeline.stats()


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        return pipeline.ingest_audio(tmp_path)
    except AudioChatError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/query")
def query(body: QueryBody) -> StreamingResponse:
    def gen():
        try:
            for token in pipeline.stream_query(body.question, top_k=body.top_k):
                yield token
        except AudioChatError as e:
            yield f"\n[ERROR] {e}"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/reset")
def reset() -> dict:
    pipeline.reset_index()
    return {"status": "ok"}
