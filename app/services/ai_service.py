import json
import asyncio
from typing import Dict, Optional, Any, List
import aiohttp

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger("services.ai")
settings = get_settings()


async def get_ai_response(question: str, event_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get a response from the Gemini AI model.
    
    Args:
        question: The user's question
        event_context: Optional event data to provide context
        
    Returns:
        AI-generated answer
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("No Gemini API key configured, returning placeholder response")
        return "I'm sorry, the AI service is currently unavailable. Please try again later."
    
    # Build the prompt with context if available
    prompt = _build_prompt(question, event_context)
    
    try:
        response = await _call_gemini_api(prompt)
        return response
    except Exception as e:
        logger.exception(f"Error calling Gemini API: {str(e)}")
        return "I encountered an error while processing your question. Please try again later."


def _build_prompt(question: str, event_context: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Build a prompt for the Gemini API.
    
    Args:
        question: The user's question
        event_context: Optional event data to provide context
        
    Returns:
        Formatted prompt
    """
    system_message = (
        "You are an assistant for the TrailBlaze app, specialized in providing information about endurance "
        "riding events. Provide concise, accurate answers based on the available information. "
        "If you don't know the answer, honestly say so and suggest the user contact the ride manager directly."
    )
    
    messages = [
        {"role": "system", "content": system_message}
    ]
    
    # Add event context if available
    if event_context:
        context_message = (
            f"Here is information about the event '{event_context['name']}': \n"
            f"Date: {event_context['date']}\n"
            f"Location: {event_context['location']}\n"
        )
        
        if 'description' in event_context and event_context['description']:
            context_message += f"Description: {event_context['description']}\n"
            
        messages.append({"role": "system", "content": context_message})
    
    # Add the user's question
    messages.append({"role": "user", "content": question})
    
    return messages


async def _call_gemini_api(messages: List[Dict[str, str]]) -> str:
    """
    Call the Gemini API.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        AI-generated response
    """
    api_url = f"https://generativelanguage.googleapis.com/v1/models/{settings.GEMINI_MODEL}:generateContent"
    params = {"key": settings.GEMINI_API_KEY}
    
    data = {
        "contents": [
            {
                "role": msg["role"],
                "parts": [{"text": msg["content"]}]
            }
            for msg in messages
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(api_url, params=params, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Gemini API error: {response.status}, {error_text}")
                    raise Exception(f"API returned status {response.status}")
                
                result = await response.json()
                
                # Extract the text response
                return result["candidates"][0]["content"]["parts"][0]["text"]
                
        except aiohttp.ClientError as e:
            logger.exception(f"HTTP error when calling Gemini API: {str(e)}")
            raise
