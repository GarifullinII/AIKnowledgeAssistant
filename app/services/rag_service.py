from typing import Optional
from sqlalchemy.orm import Session
from app.services.embedding_service import get_text_embedding
from app.services.chunk_service import search_similar_chunks
from app.services.llm_service import generate_answer
from app.services.cache_service import get_cached_answer, set_cached_answer


def ask_rag(question: str, db: Session, document_id: Optional[str] = None) -> dict:
    cache_key = f"ask:{document_id or 'all'}:{question.strip().lower()}"
    cached_answer = get_cached_answer(cache_key)

    if cached_answer:
        similar_chunks = search_similar_chunks(
            question_embedding=get_text_embedding(question),
            db=db,
            document_id=document_id,
            top_k=3,
        )
        snippets = [chunk["text"][:300] for chunk in similar_chunks]

        return {
            "answer": cached_answer,
            "document_id": document_id,
            "snippets": snippets,
        }

    question_embedding = get_text_embedding(question)

    similar_chunks = search_similar_chunks(
        question_embedding=question_embedding,
        db=db,
        document_id=document_id,
        top_k=3,
    )

    snippets = [chunk["text"][:300] for chunk in similar_chunks]

    if not similar_chunks or similar_chunks[0]["similarity"] < 0.2:
        return {
            "answer": "Недостаточно данных в документе, чтобы уверенно ответить на вопрос.",
            "document_id": document_id,
            "snippets": snippets,
        }

    answer = generate_answer(
        question=question,
        context_chunks=similar_chunks,
    )

    set_cached_answer(cache_key, answer, ttl_seconds=3600)

    return {
        "answer": answer,
        "document_id": document_id,
        "snippets": snippets,
    }