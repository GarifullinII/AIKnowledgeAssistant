from typing import Optional, List
from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    document_id: Optional[str] = Field(
        default=None,
        description="Optional document ID to restrict search"
    )

class AskResponse(BaseModel):
    answer: str
    document_id: Optional[str] = None
    snippets: List[str] = Field(default_factory=list)