"""
AI assistant schema definitions for TrailBlazeApp API.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class QuestionRequest(BaseModel):
    """Schema for AI question request."""
    question: str = Field(..., min_length=2, max_length=1000, 
                         description="The question to ask the AI assistant")
    event_id: Optional[int] = Field(None, 
                                   description="Optional event ID to provide context")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What time does the 50-mile ride start?",
                "event_id": 123
            }
        }
    )


class AnswerResponse(BaseModel):
    """Schema for AI answer response."""
    answer: str
    success: bool
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "The 50-mile ride starts at 6:30 AM on Saturday, March 28th.",
                "success": True
            }
        }
    )
