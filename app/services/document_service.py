from datetime import datetime, timezone
from uuid import uuid4
from fastapi import UploadFile, HTTPException

from app.db.memory_store import documents_store


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}


async def save_uploaded_document(file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    content = await file.read()
    size = len(content)

    document = {
        "id": str(uuid4()),
        "filename": file.filename,
        "content_type": file.content_type,
        "size": size,
        "uploaded_at": datetime.now(timezone.utc),
    }

    documents_store.append(document)
    return document


def list_documents() -> list[dict]:
    return documents_store


def validate_upload_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    filename_lower = file.filename.lower()

    is_allowed_by_type = file.content_type in ALLOWED_CONTENT_TYPES
    is_allowed_by_ext = (
        filename_lower.endswith(".pdf")
        or filename_lower.endswith(".txt")
        or filename_lower.endswith(".md")
    )

    if not (is_allowed_by_type or is_allowed_by_ext):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: .pdf, .txt, .md"
        )