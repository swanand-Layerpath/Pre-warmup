"""Pre-Warm POC - FastAPI application for Calendly to Path AI integration."""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .calendly_handler import process_calendly_booking
from .models import CalendlyPayload
from .summary_generator import get_session_summary

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Pre-Warm POC",
    description="Calendly webhook integration for Path AI pre-warm conversations",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "service": "pre-warm-poc",
        "status": "ok",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/webhook/calendly")
async def calendly_webhook(request: Request):
    """
    Receive Calendly invitee.created webhook.

    Trigger: When someone books a meeting in Calendly

    Payload structure:
    {
      "event": "invitee.created",
      "payload": {
        "event": {
          "uri": "https://...",
          "name": "30 Minute Meeting",
          "start_time": "2025-11-29T10:00:00Z",
          "end_time": "2025-11-29T10:30:00Z"
        },
        "invitee": {
          "name": "Evan Smith",
          "email": "evan@unicornpack.com",
          "timezone": "America/New_York"
        },
        "questions_and_answers": [
          {"question": "What does your company do?", "answer": "..."},
          {"question": "What's your role?", "answer": "..."}
        ]
      }
    }
    """
    try:
        payload_data = await request.json()
        logger.info(f"Received Calendly webhook: {payload_data.get('event')}")

        # Only process invitee.created events
        if payload_data.get("event") != "invitee.created":
            logger.info(f"Ignoring event type: {payload_data.get('event')}")
            return {"status": "ignored", "reason": "not invitee.created"}

        # Parse and validate payload
        payload = CalendlyPayload(**payload_data)

        # Process booking
        result = await process_calendly_booking(payload)

        logger.info(f"Created pre-warm session: {result['session_id']}")

        return {
            "status": "success",
            "session_id": result["session_id"],
            "session_url": result["session_url"]
        }

    except Exception as e:
        logger.error(f"Error processing Calendly webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/create-session")
async def test_create_session(
    email: str = "test@example.com",
    name: str = "Test User",
    company: Optional[str] = None,
    role: Optional[str] = None,
    reason: Optional[str] = None,
    meeting_date: Optional[str] = None
):
    """
    Test endpoint to manually create a pre-warm session with LLM intelligence.

    This simulates a Calendly booking without needing an actual webhook.
    Uses LLM to analyze the prospect and generate a consultative conversation strategy.

    Query params:
    - email: Email address of the invitee
    - name: Name of the invitee
    - company: (Optional) Company name
    - role: (Optional) Job role
    - reason: (Optional) Reason for booking
    - meeting_date: (Optional) Meeting date in ISO format (e.g., 2025-12-02T10:00:00Z)

    Example:
    curl -X POST "http://localhost:8002/test/create-session?email=swanand@layerpath.com&name=Alex&company=ASTERX&role=CTO&reason=Evaluating+product+tour+platforms&meeting_date=2025-12-02T10:00:00Z"
    """

    logger.info(f"🧪 Test session request: {name} ({role}) at {company}")

    # Use defaults if not provided
    company = company or "Unknown Company"
    role = role or "Unknown Role"
    reason = reason or "Interested in product"

    # 🆕 ANALYZE WITH LLM
    from .llm_intelligence import analyze_prospect_smart, build_consultative_system_prompt

    try:
        analysis = await analyze_prospect_smart(
            name=name,
            email=email,
            company=company,
            role=role,
            reason=reason
        )

        # 🆕 BUILD SMART SYSTEM PROMPT
        system_prompt = build_consultative_system_prompt(
            name=name,
            company=company,
            role=role,
            reason=reason,
            analysis=analysis
        )

        # Log for debugging
        logger.info(f"📊 Analysis: {analysis['intelligence']['industry']} | {analysis['intelligence']['seniority']}")
        logger.info(f"📝 Opening: {analysis['conversation_strategy']['opening_message'][:100]}...")

    except Exception as e:
        logger.error(f"⚠️ LLM analysis failed, using fallback: {e}")
        # Fallback: use old system without LLM
        analysis = None
        system_prompt = None

    # Parse meeting date or use default (tomorrow)
    if meeting_date:
        start_time = meeting_date
        # Parse the ISO format date to add 30 minutes for end time
        meeting_dt = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
        end_time = (meeting_dt + timedelta(minutes=30)).isoformat()
        if not end_time.endswith('Z'):
            end_time += 'Z'
    else:
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, minutes=30)).isoformat() + "Z"

    # Build questions and answers for Calendly payload (still needed for fallback)
    qa = []
    if company:
        qa.append({"question": "What does your company do?", "answer": company})
    if role:
        qa.append({"question": "What's your role?", "answer": role})
    if reason:
        qa.append({"question": "What brings you to Layerpath?", "answer": reason})

    # Mock Calendly payload
    mock_payload = {
        "event": "invitee.created",
        "payload": {
            "event": {
                "uri": "https://calendly.com/test/event-123",
                "name": "30 Minute Meeting",
                "start_time": start_time,
                "end_time": end_time
            },
            "invitee": {
                "name": name,
                "email": email,
                "timezone": "UTC"
            },
            "questions_and_answers": qa
        }
    }

    try:
        # If we have LLM analysis, use smart prompt directly
        if analysis and system_prompt:
            from .path_ai_client import create_path_ai_session_with_context

            session = await create_path_ai_session_with_context(
                invitee_email=email,
                invitee_name=name,
                meeting_time=start_time,
                initial_context=system_prompt,
                calendly_event_uri=f"test-{email}-{datetime.now().timestamp()}"
            )

            logger.info(f"✅ Session created with LLM intelligence: {session['session_id']}")

            return {
                "status": "success",
                "message": "Smart pre-warm session created with LLM analysis",
                "session_id": session["session_id"],
                "session_url": session["session_url"],
                "invitee_email": email,

                # 🆕 RETURN ANALYSIS (for debugging)
                "analysis": {
                    "industry": analysis['intelligence']['industry'],
                    "seniority": analysis['intelligence']['seniority'],
                    "is_decision_maker": analysis['intelligence']['is_decision_maker'],
                    "urgency_level": analysis['intelligence']['urgency_level'],
                    "opening_message": analysis['conversation_strategy']['opening_message'],
                    "pain_points": analysis['intelligence']['pain_points_likely'],
                    "demo_focus": analysis['conversation_strategy']['demo_focus']
                }
            }
        else:
            # Fallback to old flow
            payload = CalendlyPayload(**mock_payload)
            result = await process_calendly_booking(payload)

            return {
                "status": "success",
                "message": "Test pre-warm session created (fallback mode - no LLM)",
                "session_id": result["session_id"],
                "session_url": result["session_url"],
                "invitee_email": result["invitee_email"]
            }

    except Exception as e:
        logger.error(f"Error in test endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary/{session_id}")
async def get_summary(
    session_id: str,
    name: str = "Unknown",
    email: str = "unknown@example.com"
):
    """
    Fetch conversation summary for a completed pre-warm session.

    This endpoint retrieves the transcript from PathChatHistory and
    generates a formatted summary that can be logged or sent to Slack.

    Args:
        session_id: Path AI session ID
        name: Name of the prospect (optional, for summary header)
        email: Email of the prospect (optional, for summary header)

    Example:
        GET /summary/abc-123-xyz?name=Evan%20Smith&email=evan@unicornpack.com

    Returns:
        JSON with summary text and raw transcript
    """
    try:
        logger.info(f"Fetching summary for session {session_id}")

        summary = await get_session_summary(session_id, name, email)

        if not summary:
            raise HTTPException(
                status_code=404,
                detail="Transcript not available yet. Conversation may still be in progress."
            )

        # Log the summary
        logger.info(f"\n{'='*80}\nSUMMARY FOR SESSION {session_id}\n{'='*80}\n{summary}\n{'='*80}")

        return {
            "status": "success",
            "session_id": session_id,
            "summary": summary,
            "message": "Summary logged to console. Check server logs."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Pre-Warm POC server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
