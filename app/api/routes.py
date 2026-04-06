from fastapi import APIRouter
from app.schemas.query import AskRequest, AskResponse
from app.services.rag_service import ask_rag

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
