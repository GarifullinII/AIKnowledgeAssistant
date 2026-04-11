import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, HTTPException
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, Chunk
from app.services.chunk_service import (
    split_into_chunks,
    enrich_chunks_with_embeddings,
)


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}


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


def _ensure_upload_dir() -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def parse_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")


def parse_md(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")


def parse_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages_text = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    return "\n".join(pages_text).strip()


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return parse_txt(file_path)

    if suffix == ".md":
        return parse_md(file_path)

    if suffix == ".pdf":
        return parse_pdf(file_path)

    raise HTTPException(status_code=400, detail="Unsupported file extension")


async def save_uploaded_document(file: UploadFile, db: Session) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    upload_dir = _ensure_upload_dir()

    document_id = str(uuid4())
    safe_filename = file.filename.replace(" ", "_")
    stored_filename = f"{document_id}_{safe_filename}"
    stored_path = upload_dir / stored_filename

    content = await file.read()
    size = len(content)

    stored_path.write_bytes(content)

    extracted_text = extract_text(stored_path)
    preview = extracted_text[:300] if extracted_text else ""

    db_document = Document(
        id=document_id,
        filename=file.filename,
        content_type=file.content_type,
        size=size,
        uploaded_at=datetime.utcnow(),
        stored_path=str(stored_path),
        text_length=len(extracted_text),
        preview=preview,
        full_text=extracted_text,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    chunks = split_into_chunks(
        text=extracted_text,
        document_id=document_id,
        chunk_size=800,
        overlap=150,
    )
    chunks_with_embeddings = enrich_chunks_with_embeddings(chunks)

    for chunk in chunks_with_embeddings:
        db_chunk = Chunk(
            chunk_id=chunk["chunk_id"],
            document_id=chunk["document_id"],
            chunk_index=chunk["chunk_index"],
            text=chunk["text"],
            embedding_json=json.dumps(chunk["embedding"]),
        )
        db.add(db_chunk)

    db.commit()

    return {
        "id": db_document.id,
        "filename": db_document.filename,
        "content_type": db_document.content_type,
        "size": db_document.size,
        "uploaded_at": db_document.uploaded_at,
        "stored_path": db_document.stored_path,
        "text_length": db_document.text_length,
        "preview": db_document.preview,
    }


def list_documents(db: Session) -> list[dict]:
    documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "size": doc.size,
            "uploaded_at": doc.uploaded_at,
            "stored_path": doc.stored_path,
            "text_length": doc.text_length,
            "preview": doc.preview,
        }
        for doc in documents
    ]


def get_document_by_id(document_id: str, db: Session) -> dict | None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None

    return {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size": doc.size,
        "uploaded_at": doc.uploaded_at,
        "stored_path": doc.stored_path,
        "text_length": doc.text_length,
        "preview": doc.preview,
    }

