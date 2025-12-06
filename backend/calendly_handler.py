"""Calendly webhook handler - processes bookings and creates pre-warm sessions."""

from typing import Dict, Any
from datetime import datetime
import logging

from .path_ai_client import create_path_ai_session_with_context
from .email_sender import send_pre_warm_email
from .models import CalendlyPayload

logger = logging.getLogger(__name__)


async def process_calendly_booking(payload: CalendlyPayload) -> Dict[str, Any]:
    """
    Process Calendly booking and create Path AI pre-warm session.

    Flow:
    1. Extract invitee and event details from Calendly payload
    2. Build initial context from Calendly form responses
    3. Create Path AI session with this context pre-loaded
    4. Send email with session link to invitee

    Args:
        payload: CalendlyPayload from webhook

    Returns:
        Dict with session_id, session_url, invitee_email
    """

    event_data = payload.payload.event
    invitee = payload.payload.invitee
    qa = payload.payload.questions_and_answers or []

    logger.info(f"Processing booking for {invitee.name} ({invitee.email})")

    # Build context from Calendly form
    context = build_initial_context(invitee.dict(), event_data.dict(), qa)

    # Create Path AI session with this context
    session = await create_path_ai_session_with_context(
        invitee_email=invitee.email,
        invitee_name=invitee.name,
        meeting_time=event_data.start_time,
        initial_context=context,
        calendly_event_uri=event_data.uri
    )

    # Send email with session link
    await send_pre_warm_email(
        to_email=invitee.email,
        invitee_name=invitee.name,
        meeting_time=event_data.start_time,
        session_url=session["room_url"]  # Use Daily.co room URL directly
    )

    logger.info(f"Successfully created pre-warm session {session['session_id']}")

    return {
        "session_id": session["session_id"],
        "session_url": session["session_url"],
        "invitee_email": invitee.email
    }


def build_initial_context(invitee: Dict, event: Dict, qa: list) -> str:
    """
    Build system context for Path AI from Calendly data.

    This context will be prepended to the agent's system prompt,
    giving the AI background information about the prospect before
    the conversation starts.

    Args:
        invitee: Invitee details (name, email, timezone)
        event: Event details (name, start_time, end_time)
        qa: List of question/answer dicts from Calendly form

    Returns:
        Formatted context string to inject into system prompt
    """

    # Format Q&A from Calendly form
    if qa:
        qa_text = "\n".join([
            f"Q: {item.question}\nA: {item.answer}" if hasattr(item, 'question') else f"Q: {item['question']}\nA: {item['answer']}"
            for item in qa
        ])
    else:
        qa_text = "No pre-call questions answered yet."

    # Parse meeting time
    try:
        meeting_time = datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
        meeting_time_formatted = meeting_time.strftime('%B %d, %Y at %I:%M %p %Z')
    except Exception as e:
        logger.warning(f"Failed to parse meeting time: {e}")
        meeting_time_formatted = event["start_time"]

    # Extract meeting date for natural references
    meeting_date = meeting_time.strftime('%B %d') if isinstance(meeting_time, datetime) else 'your scheduled date'
    first_name = invitee['name'].split()[0] if invitee['name'] else 'there'

    # Extract company name from QA if available
    company_name = "your company"
    if qa:
        for item in qa:
            q = item.question if hasattr(item, 'question') else item.get('question', '')
            a = item.answer if hasattr(item, 'answer') else item.get('answer', '')
            if 'company' in q.lower() or 'organization' in q.lower():
                company_name = a
                break

    # Build pre-sales discovery context
    context = f"""You're having a quick friendly call with {first_name} from {company_name}. They have a demo with you on {meeting_date}.

YOUR VIBE: Friendly, curious, genuinely interested. Like you're grabbing coffee with them, not interrogating.

NATURAL FLOW (don't be rigid, adapt based on what they say):

Start warm and ease in naturally:
"Hey {first_name}! Good to meet you! How's your day going?"

Wait for their response, engage with it genuinely, then transition:
"Awesome. So yeah, I know we've got the full demo scheduled for {meeting_date}, which I'm looking forward to. But I wanted to hop on real quick before that - it just helps me show up way more prepared and make sure we're focusing on the right stuff for you, you know?"

Pause, let them acknowledge, then naturally flow into discovery:
"So I'd love to just learn a bit about what you're working on. Tell me about {company_name} - what do you guys do?"

Listen and engage naturally. When they finish, respond with genuine interest:
- If interesting: "Oh that's cool!" or "Interesting!" or "Nice!"
- Ask follow-up: "And what do you do there?" or "What's your role?"

After they share their role, engage with it:
- React naturally: "Ah got it" or "Makes sense" or "Oh okay"
- Curious transition: "So what brought you to us? Like what are you trying to solve?" or "What are you hoping we can help with?"

When they explain the problem, really listen and acknowledge:
- Reference what they said: "Yeah I hear you on [their pain point]"
- Natural follow-up: "And how are you handling this today? Like what tools are you using for this workflow?"

After they explain current tools:
- Acknowledge: "Okay, interesting" or "Got it"
- Ask timing naturally: "When's this becoming urgent for you?" or "What's your timeline on this?"

Wrap up warmly:
- Quick summary: "Cool, so basically you need [summarize their need] and you're currently using [their tools] - we can definitely cover that on {meeting_date}"
- Natural close: "Alright {first_name}, this was helpful! I'll see you on the {meeting_date}. Have a good one!"

KEY BEHAVIORS:
- React to EVERYTHING they say with genuine interest
- Use natural filler ("you know", "like", "basically")
- Don't rush - pause, acknowledge, then continue
- If they elaborate, let them! Don't interrupt to ask next question
- Sound excited about what they're building
- If they ask about product: "Oh for sure - let's get into that on the demo, I want to show you properly"

MUST EXTRACT (5 key things):
1. What their company does
2. Their role
3. What they're hoping to solve
4. Current tools/workflow
5. Timeline/urgency"""

    return context
