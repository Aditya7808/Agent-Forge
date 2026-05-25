import os
import uuid
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Optional
from backend.models import DocumentUploadResponse
from backend.services.vector_store import ingest_documents, clear_session
from backend.config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if not session_id:
        session_id = str(uuid.uuid4())

    session_dir = os.path.join(settings.upload_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)

    processed_count = 0
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            logger.warning(f"Skipping unsupported file: {file.filename}")
            continue

        file_path = os.path.join(session_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            if len(content) > settings.max_upload_size_mb * 1024 * 1024:
                os.remove(file_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File {file.filename} exceeds {settings.max_upload_size_mb}MB limit"
                )
            f.write(content)
        processed_count += 1

    if processed_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid files uploaded. Supported: PDF, DOCX, PPTX, TXT"
        )

    try:
        chunks_created = ingest_documents(session_id, session_dir)
    except Exception as e:
        shutil.rmtree(session_dir, ignore_errors=True)
        logger.exception("Document ingestion failed")
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")

    return DocumentUploadResponse(
        message=f"Successfully processed {processed_count} document(s) into {chunks_created} searchable chunks",
        files_processed=processed_count,
        session_id=session_id,
    )


@router.delete("/{session_id}")
async def delete_session_documents(session_id: str):
    session_dir = os.path.join(settings.upload_dir, session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)
    clear_session(session_id)
    return {"message": "Session documents cleared"}
