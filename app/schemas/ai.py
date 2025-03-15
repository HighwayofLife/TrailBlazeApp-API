from typing import Optional
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Schema for AI question request."""
    question: str = Field(..., min_length=2, max_length=1000)
    event_id: Optional[int] = None


class AnswerResponse(BaseModel):
    """Schema for AI answer response."""
    answer: str
    success: bool
