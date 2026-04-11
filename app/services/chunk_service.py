import json
from math import sqrt
from uuid import uuid4
from sqlalchemy.orm import Session
from app.db.models import Chunk
from app.services.embedding_service import get_text_embedding


def split_into_chunks(
    text: str,
    document_id: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[dict]:
    if not text.strip():
        return []

    chunks = []
    start = 0
    chunk_index = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunk = {
                "chunk_id": str(uuid4()),
                "document_id": document_id,
                "chunk_index": chunk_index,
                "text": chunk_text,
                "embedding": [],
            }
            chunks.append(chunk)

        start += chunk_size - overlap
        chunk_index += 1

    return chunks


def enrich_chunks_with_embeddings(chunks: list[dict]) -> list[dict]:
    enriched_chunks = []

    for chunk in chunks:
        embedding = get_text_embedding(chunk["text"])
        updated_chunk = {
            **chunk,
            "embedding": embedding,
        }
        enriched_chunks.append(updated_chunk)

    return enriched_chunks


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sqrt(sum(a * a for a in vec1))
    norm2 = sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def get_chunks_by_document_id(document_id: str, db: Session) -> list[dict]:
    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
        .all()
    )

    return [
        {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
        }
        for chunk in chunks
    ]


def search_similar_chunks(
    question_embedding: list[float],
    db: Session,
    document_id: str | None = None,
    top_k: int = 3,
) -> list[dict]:
    query = db.query(Chunk)

    if document_id:
        query = query.filter(Chunk.document_id == document_id)

    candidate_chunks = query.all()

    scored_chunks = []
    for chunk in candidate_chunks:
        chunk_embedding = json.loads(chunk.embedding_json)
        similarity = cosine_similarity(question_embedding, chunk_embedding)

        scored_chunks.append({
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "similarity": similarity,
        })

    scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
    return scored_chunks[:top_k]