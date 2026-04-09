from fastapi import APIRouter, BackgroundTasks, UploadFile, File
from app.schemas.query import AskRequest, AskResponse
from app.services.rag_service import ask_rag
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.schemas.chunk import ChunkListResponse
from app.services.document_service import (
    save_uploaded_document,
    list_documents,
    validate_upload_file
)
from app.services.chunk_service import enrich_document_chunks_with_embeddings, get_chunks_by_document_id

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest):
    result = ask_rag(
        question=payload.question,
        document_id=payload.document_id
    )
    return AskResponse(**result)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(background_tasks: BackgroundTasks,file: UploadFile = File(...)):
    validate_upload_file(file)
    document = await save_uploaded_document(file)
    background_tasks.add_task(enrich_document_chunks_with_embeddings, document["id"])
    return DocumentResponse(**document)

@router.get("/documents", response_model=DocumentListResponse)
def get_documents():
    return DocumentListResponse(documents=list_documents())

@router.get("/documents/{document_id}/chunks", response_model=ChunkListResponse)
def get_document_chunks(document_id: str):
    chunks = get_chunks_by_document_id(document_id)
    return ChunkListResponse(chunks=chunks)