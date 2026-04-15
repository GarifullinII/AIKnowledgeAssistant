from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    filename: str = Field(..., min_length=1, description="Name of the downloaded file")
    content_type: Optional[str] = Field(None, description="MIME file type")
    size: Optional[int] = Field(None, ge=0, description="File size in bytes")


class DocumentResponse(DocumentBase):
    id: str = Field(..., description="Unique document identifier")
    uploaded_at: datetime = Field(..., description="Date and time of upload")
    stored_path: str = Field(..., description="Path where the file is stored")
    text_length: int = Field(..., ge=0, description="Number of extracted text characters")
    preview: str = Field(..., description="Short preview of the document text")
    processing_status: str = Field(..., description="Document processing status")
    processing_error: Optional[str] = Field(None, description="Document processing error")
    source: Optional[str] = Field(None, description="Document upload source")


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse] = Field(..., description="List of documents")
