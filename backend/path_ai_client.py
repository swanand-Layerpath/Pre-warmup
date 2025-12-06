"""Client for interacting with Path AI backend API."""

import os
import httpx
import uuid
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Configuration from environment
from dotenv import load_dotenv
load_dotenv()  # Ensure .env is loaded

PATH_AI_API_URL = os.getenv("PATH_AI_API_URL", "http://localhost:8000/api/v1")
AGENT_ID = os.getenv("PATH_AI_AGENT_ID")
WORKSPACE_ID = os.getenv("PATH_AI_WORKSPACE_ID")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4000")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

logger.info(f"🔧 Config loaded: MOCK_MODE={MOCK_MODE}, PATH_AI_API_URL={PATH_AI_API_URL}")


async def create_path_ai_session_with_context(
    invitee_email: str,
    invitee_name: str,
    meeting_time: str,
    initial_context: str,
    calendly_event_uri: str
) -> Dict[str, Any]:
    """
    Create a Path AI session with pre-loaded context.

    This calls the existing /connect endpoint with metadata containing
    the initial context that should be injected into the system prompt.

    Args:
        invitee_email: Email of person who booked the meeting
        invitee_name: Name of person who booked the meeting
        meeting_time: ISO 8601 formatted meeting start time
        initial_context: Context to inject into system prompt
        calendly_event_uri: Calendly event URI for reference

    Returns:
        Dict with session_id, session_url, room_url, token
    """

    # Create unique visitor ID for this pre-warm session
    visitor_id = f"pre-warm-{invitee_email}"

    logger.info(f"Creating Path AI session for {invitee_name} ({invitee_email})")

    # Mock mode - simulate Path AI response without backend
    if MOCK_MODE:
        logger.info("🎭 MOCK MODE: Simulating Path AI session creation")
        session_id = str(uuid.uuid4())
        room_url = f"https://daily.co/mock-room-{session_id[:8]}"
        token = f"mock-token-{session_id[:8]}"
        session_url = f"{FRONTEND_URL}/voice?room={room_url}&token={token}"

        logger.info(f"✅ Mock session created: {session_id}")
        logger.info(f"📝 Initial context length: {len(initial_context)} chars")

        return {
            "session_id": session_id,
            "room_url": room_url,
            "token": token,
            "session_url": session_url
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Call existing Path AI /connect endpoint
        response = await client.post(
            f"{PATH_AI_API_URL}/connect",
            json={
                "agent_id": AGENT_ID,
                "workspace_id": WORKSPACE_ID,
                "visitor_id": visitor_id,
                "browser_timezone": "UTC",
                # Store metadata about this pre-warm session
                "metadata": {
                    "mode": "pre_warm",
                    "invitee_email": invitee_email,
                    "invitee_name": invitee_name,
                    "meeting_time": meeting_time,
                    "calendly_event_uri": calendly_event_uri,
                    # CRITICAL: Store initial context here
                    # This needs to be picked up by PathVoiceAssistant
                    "initial_context": initial_context
                }
            }
        )

        response.raise_for_status()
        data = response.json()

        room_url = data["room_url"]
        token = data["token"]

        # Extract session ID from the response or generate
        # The /connect endpoint should return session_id
        session_id = data.get("session_id", room_url.split("/")[-1])

        # Build session URL for frontend
        # Format: https://pathai.app/voice?room=<room_url>&token=<token>
        session_url = f"{FRONTEND_URL}/voice?room={room_url}&token={token}"

        logger.info(f"Created session {session_id} with URL: {session_url}")

        return {
            "session_id": session_id,
            "room_url": room_url,
            "token": token,
            "session_url": session_url
        }


async def get_session_transcript(session_id: str) -> Dict[str, Any]:
    """
    Fetch conversation transcript from Path AI.

    Uses the PathChatHistory table to retrieve the conversation.

    Args:
        session_id: Session ID from Path AI

    Returns:
        Dict with chat_history, duration, audio_url, conversation_summary
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        # This endpoint might need to be added to Path AI backend
        # For now, this is a placeholder for future implementation
        response = await client.get(
            f"{PATH_AI_API_URL}/session/{session_id}/transcript",
            params={
                "workspace_id": WORKSPACE_ID,
                "agent_id": AGENT_ID
            }
        )

        response.raise_for_status()
        return response.json()
