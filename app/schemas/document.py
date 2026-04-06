from datetime import datetime
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    filename: str = Field(..., min_length=1)
    content_type: str | None = None
    size: int | None = None


class DocumentResponse(DocumentBase):
    id: str
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]