from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

qdrant_client = QdrantClient(url=settings.qdrant_url)


def ensure_collection(vector_size: int) -> None:
    existing_collections = qdrant_client.get_collections().collections
    existing_names = [collection.name for collection in existing_collections]

    if settings.qdrant_collection_name not in existing_names:
        qdrant_client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )


def upsert_chunks_to_qdrant(chunks: list[dict]) -> None:
    if not chunks:
        return

    first_embedding = chunks[0].get("embedding", [])
    if not first_embedding:
        return

    ensure_collection(vector_size=len(first_embedding))

    points = []
    for chunk in chunks:
        point = PointStruct(
            id=chunk["chunk_id"],
            vector=chunk["embedding"],
            payload={
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
            },
        )
        points.append(point)

    qdrant_client.upsert(
        collection_name=settings.qdrant_collection_name,
        points=points,
    )


def search_qdrant(
    question_embedding: list[float],
    document_id: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    query_filter = None

    if document_id:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    response = qdrant_client.query_points(
    collection_name=settings.qdrant_collection_name,
    query=question_embedding,
    query_filter=query_filter,
    limit=top_k,
)


    chunks = []
    for result in response.points:
        chunks.append(
            {
                "chunk_id": str(result.id),
                "document_id": result.payload.get("document_id"),
                "chunk_index": result.payload.get("chunk_index"),
                "text": result.payload.get("text"),
                "similarity": result.score,
            }
        )

    return chunks