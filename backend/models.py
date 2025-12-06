"""Pydantic models for Calendly webhook payloads and internal data structures."""

from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime


class CalendlyQA(BaseModel):
    """Calendly form question and answer."""
    question: str
    answer: str


class CalendlyInvitee(BaseModel):
    """Calendly invitee (person who booked the meeting)."""
    name: str
    email: EmailStr
    timezone: Optional[str] = "UTC"
    uri: Optional[str] = None


class CalendlyEvent(BaseModel):
    """Calendly event (meeting) details."""
    uri: str
    name: str
    start_time: str  # ISO 8601 format
    end_time: str    # ISO 8601 format


class CalendlyPayloadData(BaseModel):
    """Calendly webhook payload data."""
    event: CalendlyEvent
    invitee: CalendlyInvitee
    questions_and_answers: Optional[List[CalendlyQA]] = []


class CalendlyPayload(BaseModel):
    """Complete Calendly webhook payload."""
    event: str  # e.g., "invitee.created"
    payload: CalendlyPayloadData


class PreWarmSession(BaseModel):
    """Pre-warm session details."""
    session_id: str
    session_url: str
    room_url: str
    token: str
    invitee_email: str
    invitee_name: str
    meeting_time: str
    calendly_event_uri: str
