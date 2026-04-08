from uuid import uuid4
from app.db.memory_store import chunks_store


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
            }
            chunks.append(chunk)

        start += chunk_size - overlap
        chunk_index += 1

    return chunks


def save_chunks(chunks: list[dict]) -> None:
    chunks_store.extend(chunks)


def get_chunks_by_document_id(document_id: str) -> list[dict]:
    return [chunk for chunk in chunks_store if chunk["document_id"] == document_id]