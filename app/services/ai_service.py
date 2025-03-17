import json
from typing import Dict, Optional, Any, List

from google import genai

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger("services.ai")
settings = get_settings()


class AIService:
    """Service for interacting with AI models."""
    
    def __init__(self):
        """Initialize the AI service."""
        self.settings = get_settings()
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """Initialize the GenAI client."""
        if self.settings.GEMINI_API_KEY:
            # Create the client with API key
            self.client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
            logger.info(f"Initialized GenAI client with model: {self.settings.GEMINI_MODEL}")
        else:
            logger.warning("No Gemini API key configured, AI service will be limited")
    
    async def generate_text(self, prompt: str) -> str:
        """
        Generate text using the AI model.
        
        Args:
            prompt: The prompt to send to the AI model
            
        Returns:
            Generated text response
        """
        if not self.client:
            logger.warning("GenAI client not initialized, returning placeholder response")
            return "I'm sorry, the AI service is currently unavailable. Please try again later."
        
        try:
            # Create the content with system instruction and user prompt
            system_instruction = "You are an assistant for the TrailBlaze app, specialized in extracting structured information about endurance riding events."
            
            # Get the model
            model = self.client.models.get(self.settings.GEMINI_MODEL)
            
            # Generate content
            response = model.generate_content(
                contents=[
                    {
                        "role": "system",
                        "parts": [{"text": system_instruction}]
                    },
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                generation_config={
                    "temperature": 0.2,
                    "top_k": 40,
                    "top_p": 0.95,
                    "max_output_tokens": 1024,
                }
            )
            
            # Return the text from the response
            if hasattr(response, 'text'):
                return response.text
            else:
                # Access the text field based on the actual API structure
                return response.candidates[0].content.parts[0].text
                
        except Exception as e:
            logger.exception(f"Error generating text with GenAI: {str(e)}")
            return "I encountered an error while processing your request. Please try again later."
    
    async def close(self):
        """Clean up any resources."""
        # No need to close anything with the GenAI client
        pass


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
    
    try:
        # Initialize GenAI client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Create system message
        system_message = (
            "You are an assistant for the TrailBlaze app, specialized in providing information about endurance "
            "riding events. Provide concise, accurate answers based on the available information. "
            "If you don't know the answer, honestly say so and suggest the user contact the ride manager directly."
        )
        
        # Get the model
        model = client.models.get(settings.GEMINI_MODEL)
        
        # Prepare the content
        contents = [
            {
                "role": "system",
                "parts": [{"text": system_message}]
            }
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
                
            contents.append({
                "role": "system",
                "parts": [{"text": context_message}]
            })
        
        # Add the user's question
        contents.append({
            "role": "user",
            "parts": [{"text": question}]
        })
        
        # Generate the response
        response = model.generate_content(
            contents=contents,
            generation_config={
                "temperature": 0.2,
                "top_k": 40,
                "top_p": 0.95,
                "max_output_tokens": 1024,
            }
        )
        
        # Return the text from the response
        if hasattr(response, 'text'):
            return response.text
        else:
            # Access the text field based on the actual API structure
            return response.candidates[0].content.parts[0].text
        
    except Exception as e:
        logger.exception(f"Error calling Gemini API: {str(e)}")
        return "I encountered an error while processing your question. Please try again later."
