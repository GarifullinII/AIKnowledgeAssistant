from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag_service import ask_rag

router = APIRouter(prefix="/api")


class AskRequest(BaseModel):
    question: str


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/ask")
def ask(request: AskRequest):
    answer = ask_rag(request.question)
    return {"answer": answer}
