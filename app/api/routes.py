from fastapi import APIRouter, UploadFile, File
from app.schemas.query import AskRequest, AskResponse
from app.services.rag_service import ask_rag
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.document_service import (
    save_uploaded_document,
    list_documents,
    validate_upload_file
)

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
async def upload_document(file: UploadFile = File(...)):
    validate_upload_file(file)
    document = await save_uploaded_document(file)
    return DocumentResponse(**document)

@router.get("/documents", response_model=DocumentListResponse)
def get_documents():
    return DocumentListResponse(documents=list_documents())
