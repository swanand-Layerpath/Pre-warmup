"""Generate summaries from Path AI conversation transcripts."""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .lead_scorer import score_lead

load_dotenv()

logger = logging.getLogger(__name__)

# Supabase connection details from Path AI
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dvzrcusywjqyrfnpiygh.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


async def fetch_transcript_from_db(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch transcript directly from Supabase PathChatHistory table.

    Args:
        session_id: Session ID from Path AI

    Returns:
        Dict with chatHistory and metadata, or None if not found
    """
    try:
        import httpx

        if not SUPABASE_KEY:
            logger.error("SUPABASE_KEY not configured")
            return None

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/PathChatHistory",
                params={
                    "select": "id,sessionId,chatHistory,workspaceId,agentId,visitorId",
                    "sessionId": f"eq.{session_id}",
                    "limit": "1"
                },
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )

            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                logger.warning(f"No transcript found for session {session_id}")
                return None

            return data[0]

    except Exception as e:
        logger.error(f"Error fetching transcript from DB: {e}")
        return None


def format_transcript(chat_history: list) -> str:
    """
    Format chat history into readable transcript.

    Args:
        chat_history: List of messages from PathChatHistory

    Returns:
        Formatted transcript string
    """
    transcript = []

    for msg in chat_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            transcript.append(f"Prospect: {content}")
        elif role == "assistant":
            transcript.append(f"AI: {content}")
        elif role == "system":
            # Skip system messages in transcript
            continue

    return "\n\n".join(transcript)


def generate_summary(chat_history: list, invitee_name: str, invitee_email: str) -> str:
    """
    Generate a simple summary from the conversation.

    For V0, this is just formatting. Later can use LLM for smart summarization.

    Args:
        chat_history: List of messages from PathChatHistory
        invitee_name: Name of the prospect
        invitee_email: Email of the prospect

    Returns:
        Formatted summary string
    """

    # Extract user messages (what the prospect said)
    user_messages = [
        msg.get("content", "")
        for msg in chat_history
        if msg.get("role") == "user"
    ]

    # Count messages
    total_exchanges = len([m for m in chat_history if m.get("role") in ["user", "assistant"]])

    # Format full transcript for scoring
    transcript_text = format_transcript(chat_history)

    # Score the lead
    scoring_result = score_lead(transcript_text)

    # Extract key information from user messages
    company_info = "Unknown company"
    role_info = "Unknown role"
    pain_point = "Not specified"
    timeline = "Not specified"
    current_tools = "Not specified"

    # Simple extraction from transcript
    transcript_lower = transcript_text.lower()

    # Try to extract from user messages
    for msg in user_messages:
        msg_lower = msg.lower()

        # Extract company info (usually first substantial answer)
        if len(msg.split()) > 5 and "company" not in msg_lower and company_info == "Unknown company":
            company_info = msg[:100]  # First meaningful response

        # Extract role
        if any(word in msg_lower for word in ["founder", "ceo", "cto", "director", "manager", "lead", "head"]):
            role_info = msg[:50]

        # Extract pain point/need
        if any(word in msg_lower for word in ["help", "need", "trying", "want", "looking", "hoping", "problem"]):
            pain_point = msg[:100]

        # Extract timeline
        if any(word in msg_lower for word in ["timeline", "when", "month", "quarter", "week", "asap", "soon"]):
            timeline = msg[:80]

        # Extract current tools
        if any(word in msg_lower for word in ["using", "tool", "currently", "right now", "we use"]):
            current_tools = msg[:80]

    # Build concise summary
    summary = f"""🎯 LEAD SCORE: {scoring_result['category']} ({scoring_result['score']}/{scoring_result['max_score']} pts)

{invitee_name} / {role_info} @ {company_info}. {pain_point}. Timeline: {timeline}. Current tools: {current_tools}.

Assessment: {scoring_result['summary']}

---
FULL TRANSCRIPT:
{transcript_text}
---"""

    return summary


async def get_session_summary(session_id: str, invitee_name: str, invitee_email: str) -> Optional[str]:
    """
    Fetch transcript and generate summary for a completed session.

    Args:
        session_id: Path AI session ID
        invitee_name: Name of the prospect
        invitee_email: Email of the prospect

    Returns:
        Summary string, or None if transcript not available yet
    """

    logger.info(f"Fetching summary for session {session_id}")

    # Fetch transcript from database
    record = await fetch_transcript_from_db(session_id)

    if not record:
        logger.warning(f"No transcript available yet for {session_id}")
        return None

    chat_history = record.get("chatHistory", [])

    if not chat_history or len(chat_history) == 0:
        logger.warning(f"Empty chat history for {session_id}")
        return None

    # Generate summary
    summary = generate_summary(chat_history, invitee_name, invitee_email)

    logger.info(f"Generated summary for {session_id} ({len(chat_history)} messages)")

    return summary
