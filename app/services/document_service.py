import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Chunk, Document
from app.services.chunk_service import enrich_chunks_with_embeddings, split_into_chunks
from app.services.vector_store_service import upsert_chunks_to_qdrant


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}


def validate_upload_metadata(filename: str | None, content_type: str | None) -> None:
    if not filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    filename_lower = filename.lower()

    is_allowed_by_type = content_type in ALLOWED_CONTENT_TYPES
    is_allowed_by_ext = (
        filename_lower.endswith(".pdf")
        or filename_lower.endswith(".txt")
        or filename_lower.endswith(".md")
    )

    if not (is_allowed_by_type or is_allowed_by_ext):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: .pdf, .txt, .md",
        )


def validate_upload_file(file: UploadFile) -> None:
    validate_upload_metadata(file.filename, file.content_type)


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


def _serialize_document(doc: Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size": doc.size,
        "uploaded_at": doc.uploaded_at,
        "stored_path": doc.stored_path,
        "text_length": doc.text_length,
        "preview": doc.preview,
        "processing_status": doc.processing_status,
        "processing_error": doc.processing_error,
        "source": doc.source,
    }


def create_document_record(
    filename: str,
    content_type: str | None,
    content: bytes,
    db: Session,
    source: str,
) -> dict:
    validate_upload_metadata(filename, content_type)

    upload_dir = _ensure_upload_dir()

    document_id = str(uuid4())
    safe_filename = filename.replace(" ", "_")
    stored_filename = f"{document_id}_{safe_filename}"
    stored_path = upload_dir / stored_filename
    stored_path.write_bytes(content)

    db_document = Document(
        id=document_id,
        filename=filename,
        content_type=content_type,
        size=len(content),
        uploaded_at=datetime.utcnow(),
        stored_path=str(stored_path),
        text_length=0,
        preview="",
        full_text="",
        processing_status="queued",
        processing_error=None,
        source=source,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return _serialize_document(db_document)


def process_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.processing_status = "processing"
        doc.processing_error = None
        db.commit()

        stored_path = Path(doc.stored_path)
        extracted_text = extract_text(stored_path)
        preview = extracted_text[:300] if extracted_text else ""

        db.query(Chunk).filter(Chunk.document_id == document_id).delete()

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

        doc.text_length = len(extracted_text)
        doc.preview = preview
        doc.full_text = extracted_text
        doc.processing_status = "completed"
        doc.processing_error = None
        db.commit()

        upsert_chunks_to_qdrant(chunks_with_embeddings)
    except Exception as exc:
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = "failed"
            doc.processing_error = str(exc)[:1000]
            db.commit()
        raise
    finally:
        db.close()


async def save_uploaded_document(file: UploadFile, db: Session) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    content = await file.read()
    return create_document_record(
        filename=file.filename,
        content_type=file.content_type,
        content=content,
        db=db,
        source="api",
    )


async def save_telegram_document(
    filename: str,
    content_type: str | None,
    content: bytes,
    db: Session,
) -> dict:
    return create_document_record(
        filename=filename,
        content_type=content_type,
        content=content,
        db=db,
        source="telegram",
    )


def list_documents(db: Session) -> list[dict]:
    documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [_serialize_document(doc) for doc in documents]


def get_document_by_id(document_id: str, db: Session) -> dict | None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None
    return _serialize_document(doc)

