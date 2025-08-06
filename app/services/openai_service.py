"""Service for OpenAI API operations."""

import json
import requests
from typing import Dict, Any, Optional

from ..config import settings
from ..core.exceptions import OpenAIAPIError
from ..utils.logging import get_logger
from ..models.schemas import ChatCompletionRequest

logger = get_logger(__name__)


class OpenAIService:
    """Service for handling OpenAI API interactions."""
    
    def __init__(self):
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
    
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to OpenAI API with error handling."""
        if not settings.openai_api_key:
            raise OpenAIAPIError("OpenAI API key not configured")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}"
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=settings.openai_timeout
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"OpenAI API returned status {response.status_code}: {error_text}")
                raise OpenAIAPIError(f"OpenAI API error {response.status_code}: {error_text}")
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise OpenAIAPIError(f"OpenAI API request failed: {str(e)}")
    
    async def transcribe_voice(self, audio_blob: str) -> Dict[str, str]:
        """Transcribe voice audio using OpenAI Whisper API."""
        # TODO: Implement voice transcription
        # This would involve:
        # 1. Decode base64 audio data
        # 2. Send to OpenAI Whisper API
        # 3. Return transcription
        
        logger.info("Voice transcription requested (not yet implemented)")
        return {"transcription": "Voice transcription endpoint - implementation needed"}
    
    async def classify_intent(self, command: str) -> Dict[str, Any]:
        """Classify user intent using OpenAI Chat Completions API."""
        system_prompt = """You are a voice command classifier for a music application. 
        
        Analyze the user's voice command and return ONLY a JSON response with this structure:
        {
            "intent": "record|play|stop|generate|loop|toggle_recording|demo|chat",
            "confidence": 0.0-1.0,
            "parameters": {...any additional params...}
        }
    
        Intent definitions:
        - "record": User wants to start recording MIDI input (examples: "record", "capture", "start recording")
        - "play": User wants to play/hear music or arrangements (examples: "play", "jam", "hear it", "play it", "can you play", "let me hear", "start playing")
        - "stop": User wants to stop playback (examples: "stop", "pause", "cancel")
        - "generate": User wants to create/arrange music (examples: "generate", "arrange", "make music")
        - "loop": User wants to enable/toggle looping (examples: "loop", "repeat")
        - "toggle_recording": User wants to include/exclude their recording in playback (examples: "add my recording", "include my recording", "turn on my recording", "play my recording too", "remove my recording", "turn off my recording", "don't play my recording")
        - "demo": User is starting a demo or presentation (examples: "this is a demo", "we're demoing", "demo mode", "presenting to audience", "show the audience")
        - "chat": General conversation, questions, or unclear commands
    
        Examples:
        "let's record this" → {"intent": "record", "confidence": 0.9}
        "play that arrangement" → {"intent": "play", "confidence": 0.9}
        "add my recording to the mix" → {"intent": "toggle_recording", "confidence": 0.9}
        "include my recording" → {"intent": "toggle_recording", "confidence": 0.8}
        "turn off my recording" → {"intent": "toggle_recording", "confidence": 0.9}
        "play my recording with the arrangement" → {"intent": "toggle_recording", "confidence": 0.8}
        "this is a demo" → {"intent": "demo", "confidence": 0.9}
        "we're presenting this" → {"intent": "demo", "confidence": 0.8}
        "demo mode" → {"intent": "demo", "confidence": 0.9}"""
        
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command}
            ],
            "max_tokens": settings.openai_max_tokens,
            "temperature": 0.1
        }
        
        try:
            result = self._make_request(payload)
            ai_response = result["choices"][0]["message"]["content"]
            
            # Parse the JSON response
            intent_data = json.loads(ai_response)
            return intent_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            raise OpenAIAPIError(f"Invalid response from AI model: {str(e)}")
    
    async def handle_conversational_chat(self, request: ChatCompletionRequest) -> Dict[str, str]:
        """Handle conversational chat using OpenAI Chat Completions API."""
        # Build context message from analysis if available
        context_message = ""
        if request.has_current_analysis and request.analysis_context:
            result = request.analysis_context
            if result.get("detected_type") == "chord_progression":
                chords = result.get("chord_progression", [])
                context_message = f"Current analyzed chord progression: {' → '.join(chords)}. Key: {result.get('key', 'Unknown')}."
            elif result.get("harmonizations"):
                style = "simple_pop"  # Default style
                harmonizations = result.get("harmonizations", {})
                if style in harmonizations:
                    chords = harmonizations[style].get("progression", [])
                    context_message = f"Current melody harmonized as: {' → '.join(chords)}. Key: {result.get('key', 'Unknown')}."
        
        # Different system prompts based on whether they've recorded anything
        if request.has_current_analysis:
            system_prompt = """You're a music co-pilot for songwriters and composers. Keep responses under 30 words since this is voice interaction.
    
    The user has already recorded and analyzed their music. For ANY requests about arrangements, instruments, backing tracks, or making music fuller, always suggest they say "generate" to create an arrangement.
    
    Your role:
    - For arrangement requests: Always suggest saying "generate" to create backing instruments
    - For musical questions: Give specific, actionable advice about their chord progression
    - For general music chat: Be supportive and knowledgeable
    - Keep everything concise and natural
    
    If they ask about adding instruments, backing tracks, fuller sound, or arrangements, respond like: "Say 'generate' and I'll create backing instruments for your [melody/chords]!\""""
        else:
            system_prompt = """You're a music co-pilot for songwriters and composers. Keep responses under 30 words since this is voice interaction.
    
    The user hasn't recorded anything yet. Your main job is to recognize when they're describing musical goals (especially about arrangements, adding instruments, or making music fuller) and guide them to record first.
    
    RECOGNIZE THESE AS ARRANGEMENT INTENTIONS:
    - "I have a melody and want to see how it sounds with instruments"
    - "I'd like to add backing to this tune I have"
    - "How would this sound with more instruments"
    - "I want to create an arrangement"
    - "Can we build on this melody"
    - Any mention of adding instruments, backing tracks, fuller sound, arrangements
    
    FOR ARRANGEMENT INTENTIONS: Respond enthusiastically and guide them to record first, like:
    "That sounds awesome! First, let's capture your melody. Ask me to record you when you're ready to play it, then I'll help add instruments!"
    
    FOR OTHER MUSIC QUESTIONS: Be helpful and supportive but concise.
    
    Always be encouraging about their musical ideas!\""""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context about current analysis if available
        if context_message:
            messages.append({"role": "system", "content": context_message})
        
        # Add user command
        messages.append({"role": "user", "content": request.command})
        
        payload = {
            "model": settings.openai_model,
            "messages": messages,
            "max_tokens": settings.openai_max_tokens,
            "temperature": 0.7
        }
        
        result = self._make_request(payload)
        ai_response = result["choices"][0]["message"]["content"]
        
        return {"response": ai_response}


# Global OpenAI service instance
openai_service = OpenAIService()