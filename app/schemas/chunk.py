from pydantic import BaseModel, Field

class ChunkResponse(BaseModel):
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Document identifier")
    chunk_index: int = Field(..., ge=0, description="Chunk position inside the document")
    text: str = Field(..., description="Chunk text content")


class ChunkListResponse(BaseModel):
    chunks: list[ChunkResponse] = Field(..., description="List of document chunks")