from uuid import NAMESPACE_URL, uuid5
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
                "chunk_id": str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk_index}")),
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
