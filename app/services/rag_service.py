from typing import Optional
from sqlalchemy.orm import Session
from app.services.embedding_service import get_text_embedding
from app.services.llm_service import generate_answer
from app.services.cache_service import get_cached_answer, set_cached_answer
from app.services.vector_store_service import search_qdrant


def ask_rag(question: str, db: Session, document_id: Optional[str] = None) -> dict:
    cache_key = f"ask:{document_id or 'all'}:{question.strip().lower()}"
    cached_answer = get_cached_answer(cache_key)

    question_embedding = get_text_embedding(question)

    similar_chunks = search_qdrant(
        question_embedding=question_embedding,
        document_id=document_id,
        top_k=5,
    )

    snippets = [chunk["text"][:300] for chunk in similar_chunks[:3]]

    if cached_answer:
        return {
            "answer": cached_answer,
            "document_id": document_id,
            "snippets": snippets,
        }

    if not similar_chunks or similar_chunks[0]["similarity"] < 0.2:
        return {
            "answer": "Недостаточно данных в документе, чтобы уверенно ответить на вопрос.",
            "document_id": document_id,
            "snippets": snippets,
        }

    answer = generate_answer(
        question=question,
        context_chunks=similar_chunks[:3],
    )

    set_cached_answer(cache_key, answer, ttl_seconds=3600)

    return {
        "answer": answer,
        "document_id": document_id,
        "snippets": snippets,
    }