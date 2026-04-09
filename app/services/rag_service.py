from typing import Optional
from app.services.embedding_service import get_text_embedding
from app.services.chunk_service import search_similar_chunks
from app.services.llm_service import generate_answer


def ask_rag(question: str, document_id: Optional[str] = None) -> dict:
    question_embedding = get_text_embedding(question)

    similar_chunks = search_similar_chunks(
        question_embedding=question_embedding,
        document_id=document_id,
        top_k=3,
    )

    snippets = [chunk["text"][:300] for chunk in similar_chunks]

    if not similar_chunks or similar_chunks[0]["similarity"] < 0.2:
        return {
            "answer": "There is not enough data in the document to answer the question confidently.",
            "document_id": document_id,
            "snippets": snippets,
        }

    answer = generate_answer(
        question=question,
        context_chunks=similar_chunks,
    )

    return {
        "answer": answer,
        "document_id": document_id,
        "snippets": snippets,
    }
