from typing import Optional
from sqlalchemy.orm import Session
from app.services.embedding_service import get_text_embedding
from app.services.llm_service import generate_answer
from app.services.cache_service import get_cached_answer, set_cached_answer
from app.services.openai_service import OpenAIServiceError
from app.services.vector_store_service import search_qdrant
from app.services.rerank_service import rerank_chunks


def ask_rag(question: str, db: Session, document_id: Optional[str] = None) -> dict:
    cache_key = f"ask:{document_id or 'all'}:{question.strip().lower()}"
    cached_answer = get_cached_answer(cache_key)

    if cached_answer:
        return {
            "answer": cached_answer,
            "document_id": document_id,
            "snippets": [],
        }

    try:
        question_embedding = get_text_embedding(question)
    except OpenAIServiceError:
        return {
            "answer": "Сервис OpenAI временно недоступен. Попробуйте повторить запрос чуть позже.",
            "document_id": document_id,
            "snippets": [],
        }

    similar_chunks = search_qdrant(
        question_embedding=question_embedding,
        document_id=document_id,
        top_k=8,
    )

    if not similar_chunks:
        return {
            "answer": "Недостаточно данных в документе, чтобы уверенно ответить на вопрос.",
            "document_id": document_id,
            "snippets": [],
        }

    best_similarity = max(chunk.get("similarity", 0.0) for chunk in similar_chunks)

    if best_similarity < 0.2:
        snippets = [chunk["text"][:300] for chunk in similar_chunks[:3]]
        return {
            "answer": "Недостаточно данных в документе, чтобы уверенно ответить на вопрос.",
            "document_id": document_id,
            "snippets": snippets,
        }

    try:
        reranked_chunks = rerank_chunks(
            question=question,
            candidate_chunks=similar_chunks,
            top_n=3,
        )
    except OpenAIServiceError:
        reranked_chunks = similar_chunks[:3]

    snippets = [chunk["text"][:300] for chunk in reranked_chunks[:3]]

    try:
        answer = generate_answer(
            question=question,
            context_chunks=reranked_chunks,
        )
    except OpenAIServiceError:
        return {
            "answer": "Не удалось сгенерировать ответ из-за временной ошибки OpenAI. Попробуйте еще раз позже.",
            "document_id": document_id,
            "snippets": snippets,
        }

    set_cached_answer(cache_key, answer, ttl_seconds=3600)

    return {
        "answer": answer,
        "document_id": document_id,
        "snippets": snippets,
    }
