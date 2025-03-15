from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.ai import QuestionRequest, AnswerResponse
from app.services.ai_service import get_ai_response
from app.logging_config import get_logger
from app.crud.event import get_event

router = APIRouter()
logger = get_logger("api.ai_assistant")


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    question: QuestionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-generated answer to a question.
    
    Optionally provides event context if event_id is provided.
    """
    try:
        # Get event context if provided
        event_context = None
        if question.event_id:
            event = await get_event(db, event_id=question.event_id)
            if event:
                event_context = {
                    "id": event.id,
                    "name": event.name,
                    "date": event.date_start.isoformat(),
                    "location": event.location,
                    "description": event.description,
                    # Add other relevant event details
                }
        
        # Get AI response
        response = await get_ai_response(
            question=question.question,
            event_context=event_context
        )
        
        # Log the question-answer pair in the background
        background_tasks.add_task(
            log_interaction,
            question.question,
            response,
            question.event_id
        )
        
        return {"answer": response, "success": True}
    
    except Exception as e:
        logger.error(f"Error processing AI question: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get AI response")


async def log_interaction(question: str, answer: str, event_id: Optional[int] = None):
    """
    Log the AI interaction for analysis.
    """
    logger.info(
        f"AI Interaction logged",
        extra={
            "question": question,
            "answer_length": len(answer),
            "event_id": event_id
        }
    )
    # Could also store in database for future analysis and training
