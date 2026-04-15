from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.query import AskRequest, AskResponse
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.schemas.chunk import ChunkListResponse
from app.services.rag_service import ask_rag
from app.services.document_service import (
    save_uploaded_document,
    list_documents,
    validate_upload_file,
    get_document_by_id,
)
from app.services.queue_service import enqueue_document_processing
from app.services.chunk_service import get_chunks_by_document_id
from app.db.database import get_db

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    result = ask_rag(
        question=payload.question,
        document_id=payload.document_id,
        db=db,
    )
    return AskResponse(**result)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    validate_upload_file(file)
    document = await save_uploaded_document(file, db)
    enqueue_document_processing(document["id"])
    return DocumentResponse(**document)


@router.get("/documents", response_model=DocumentListResponse)
def get_documents(db: Session = Depends(get_db)):
    return DocumentListResponse(documents=list_documents(db))


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = get_document_by_id(document_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**document)


@router.get("/documents/{document_id}/chunks", response_model=ChunkListResponse)
def get_document_chunks(document_id: str, db: Session = Depends(get_db)):
    chunks = get_chunks_by_document_id(document_id, db)
    return ChunkListResponse(chunks=chunks)
