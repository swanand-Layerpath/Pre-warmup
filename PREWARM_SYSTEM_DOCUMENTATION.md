# Pre-Warm System Documentation

## Overview

The Pre-Warm POC is a Calendly-to-Path-AI integration system that automatically creates pre-call qualification conversations. When someone books a meeting via Calendly, the system:

1. Receives the booking webhook
2. Extracts context from Calendly form responses
3. Creates a Path AI session with pre-loaded context
4. Sends an email with a link to the pre-warm session
5. Prospect completes a brief AI-guided conversation before the actual call
6. System generates a lead score and summary for the sales rep

**Purpose**: Eliminate manual discovery work by gathering key information through an AI conversation that happens *before* the main meeting.

## Architecture Components

### Key Files

| Component | File | Responsibility |
|-----------|------|----------------|
| **API Server** | [backend/main.py](backend/main.py) | FastAPI app, webhook routing, test endpoints |
| **Calendly Handler** | [backend/calendly_handler.py](backend/calendly_handler.py) | Process bookings, build initial context |
| **Path AI Client** | [backend/path_ai_client.py](backend/path_ai_client.py) | Call Path AI `/connect` API |
| **Email Sender** | [backend/email_sender.py](backend/email_sender.py) | SMTP-based email delivery |
| **Data Models** | [backend/models.py](backend/models.py) | Pydantic validation models |
| **Lead Scorer** | [backend/lead_scorer.py](backend/lead_scorer.py) | Analyze transcripts, assign HOT/WARM/COLD scores |
| **LLM Intelligence** | [backend/llm_intelligence.py](backend/llm_intelligence.py) | GPT-4 analysis for smart conversations |
| **Summary Generator** | [backend/summary_generator.py](backend/summary_generator.py) | Extract transcripts, generate briefs |

## Execution Flow

### Phase 1: Trigger (Calendly Booking)

```
User books via Calendly → Calendly sends webhook
```

**Endpoint**: `POST /webhook/calendly`

**Expected Payload Structure**:
```json
{
  "event": "invitee.created",
  "payload": {
    "event": {
      "uri": "https://api.calendly.com/scheduled_events/abc123",
      "name": "30 Minute Demo Call",
      "start_time": "2025-12-03T14:00:00Z",
      "end_time": "2025-12-03T14:30:00Z"
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
```

**Code Flow** ([backend/main.py:59-113](backend/main.py#L59-L113)):
```python
@app.post("/webhook/calendly")
async def calendly_webhook(request: Request):
    # 1. Parse JSON
    payload_data = await request.json()

    # 2. Validate it's invitee.created event
    if payload_data.get("event") != "invitee.created":
        return {"status": "ignored"}

    # 3. Parse with Pydantic validation
    payload = CalendlyPayload(**payload_data)

    # 4. Process the booking
    result = await process_calendly_booking(payload)

    return {"status": "success", "session_id": result["session_id"]}
```

### Phase 2: Context Building

**File**: [backend/calendly_handler.py](backend/calendly_handler.py)

**Function**: `build_initial_context()` ([calendly_handler.py:66-165](backend/calendly_handler.py#L66-L165))

This function constructs a natural, consultative system prompt that gets injected into Path AI. The context includes:

1. **Meeting Info**: Date, time, prospect name, company
2. **Form Responses**: Q&A from Calendly form
3. **Conversation Script**: Natural opening flow with embedded discovery questions

**Key Variables Built**:
- `invitee_name`, `first_name` - Prospect's name
- `company_name` - Extracted from Q&A or defaulted
- `meeting_time_formatted` - Human-readable date/time
- `qa_text` - Formatted Q&A responses

**Example Output Context**:
```
You're having a quick friendly call with Evan from UnicornPack (SaaS Design Studio).
They have a demo with you on December 3.

YOUR VIBE: Friendly, curious, genuinely interested. Like you're grabbing coffee with them,
not interrogating.

NATURAL FLOW (don't be rigid, adapt based on what they say):

Start warm and ease in naturally:
"Hey Evan! Good to meet you! How's your day going?"

Wait for their response, engage with it genuinely, then transition:
"Awesome. So yeah, I know we've got the full demo scheduled for December 3, which I'm
looking forward to. But I wanted to hop on real quick before that..."

[continues with natural discovery questions]
```

The context emphasizes a **conversational, consultative tone** rather than interrogation.

### Phase 3: Path AI Session Creation

**File**: [backend/path_ai_client.py](backend/path_ai_client.py)

**Function**: `create_path_ai_session_with_context()` ([path_ai_client.py:24-115](backend/path_ai_client.py#L24-L115))

This calls the Path AI `/connect` endpoint with the context embedded in metadata.

**Request to Path AI**:
```python
{
    "agent_id": AGENT_ID,
    "workspace_id": WORKSPACE_ID,
    "visitor_id": f"pre-warm-{invitee_email}",
    "browser_timezone": "UTC",
    "metadata": {
        "mode": "pre_warm",
        "invitee_email": invitee_email,
        "invitee_name": invitee_name,
        "meeting_time": meeting_time,
        "calendly_event_uri": calendly_event_uri,
        "initial_context": initial_context  # <-- CRITICAL
    }
}
```

**Configuration** (from environment variables):
- `PATH_AI_API_URL` - Path AI backend URL (default: `http://localhost:8000/api/v1`)
- `PATH_AI_AGENT_ID` - Agent to use
- `PATH_AI_WORKSPACE_ID` - Workspace context
- `FRONTEND_URL` - Frontend domain (default: `https://pathai.app`)

**Response Expected**:
```json
{
    "room_url": "https://daily.co/room/...",
    "token": "token-...",
    "session_id": "uuid"
}
```

**Mock Mode** ([path_ai_client.py:54-69](backend/path_ai_client.py#L54-L69)): For testing without Path AI, can simulate responses:
```python
if MOCK_MODE:  # Enable with MOCK_MODE=true env var
    session_id = str(uuid.uuid4())
    room_url = f"https://daily.co/mock-room-{session_id[:8]}"
    token = f"mock-token-{session_id[:8]}"
    session_url = f"{FRONTEND_URL}/voice?room={room_url}&token={token}"
    return {...}
```

### Phase 4: Email Delivery

**File**: [backend/email_sender.py](backend/email_sender.py)

**Function**: `send_pre_warm_email()` ([email_sender.py:20-136](backend/email_sender.py#L20-L136))

Sends personalized HTML email via SMTP with:
- Prospect name
- Meeting date/time
- Call-to-action button linking to session
- Context about what to expect

**Configuration**:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
PRE_WARM_FROM_EMAIL=team@layerpath.com
```

### Phase 5: Prospect Conversation

1. Prospect clicks link in email
2. Browser opens Path AI frontend: `https://pathai.app/voice?room=<room>&token=<token>`
3. Path AI creates Daily.co video room
4. Voice worker starts with injected context
5. AI initiates consultative conversation

**What Gets Prewarmed**:
- AI **knows** prospect's name, company, role, reason for booking
- AI **uses** this context to personalize opening
- AI **guides** conversation toward 5 key discovery points naturally

### Phase 6: Summary & Scoring

**File**: [backend/summary_generator.py](backend/summary_generator.py)

**Endpoint**: `GET /summary/{session_id}`

**Process**:
1. Fetch transcript from Supabase `PathChatHistory` table
2. Format messages into readable transcript
3. Run through `score_lead()` function
4. Extract key insights
5. Generate formatted summary

**Scoring Logic** ([backend/lead_scorer.py](backend/lead_scorer.py)):

Analyzes transcript for 5 signals (max 12 points):

| Signal | Points | Indicators |
|--------|--------|-----------|
| **Urgency** | 0-3 | "asap", "this week", "deadline", "Q1", "soon" |
| **Pain Point** | 0-3 | "problem", "struggling", "need help", "frustrated" |
| **Authority** | 0-2 | "CEO", "CTO", "founder", "director", "VP" |
| **Current Solution** | 0-2 | Manual, spreadsheet, or competitor tools |
| **Engagement** | 0-2 | Response length, quality of answers |

**Scoring Thresholds**:
- **7-12 points**: 🔥 HOT - "High-priority lead. Strong signals for close."
- **4-6 points**: 🌡️ WARM - "Qualified lead. Nurture and follow up."
- **0-3 points**: ❄️ COLD - "Low priority. May need more education."

**Summary Output**:
```
🎯 LEAD SCORE: 🔥 HOT (9/12 pts)

Evan Smith / Co-founder & CEO @ UnicornPack (SaaS Design Studio).
Struggling with onboarding complexity. Timeline: Q2 2026. Current tools: Building own.

Assessment: High-priority lead. Strong signals for close.

---
FULL TRANSCRIPT:
[conversation details]
---
```

## Key Functions & Responsibilities

### Main Entry Points

| Function | File | Purpose |
|----------|------|---------|
| `calendly_webhook()` | [main.py:59](backend/main.py#L59) | Receive Calendly webhook, trigger processing |
| `test_create_session()` | [main.py:116](backend/main.py#L116) | Manual testing endpoint (no Calendly needed) |
| `get_summary()` | [main.py:272](backend/main.py#L272) | Retrieve & score completed session |

### Processing Functions

| Function | File | Purpose |
|----------|------|---------|
| `process_calendly_booking()` | [calendly_handler.py:14](backend/calendly_handler.py#L14) | Orchestrate: context → session → email |
| `build_initial_context()` | [calendly_handler.py:66](backend/calendly_handler.py#L66) | Generate consultative system prompt |
| `create_path_ai_session_with_context()` | [path_ai_client.py:24](backend/path_ai_client.py#L24) | Call Path AI /connect with metadata |
| `send_pre_warm_email()` | [email_sender.py:20](backend/email_sender.py#L20) | Send SMTP email with session link |

### Analysis Functions

| Function | File | Purpose |
|----------|------|---------|
| `score_lead()` | [lead_scorer.py:10](backend/lead_scorer.py#L10) | Analyze transcript, assign HOT/WARM/COLD |
| `extract_key_insights()` | [lead_scorer.py:176](backend/lead_scorer.py#L176) | Pull out company, role, pain point, tools |
| `get_session_summary()` | [summary_generator.py:170](backend/summary_generator.py#L170) | Orchestrate transcript fetch + scoring |
| `fetch_transcript_from_db()` | [summary_generator.py:18](backend/summary_generator.py#L18) | Query Supabase PathChatHistory |
| `generate_summary()` | [summary_generator.py:90](backend/summary_generator.py#L90) | Format summary with scores |

### Smart LLM Functions (Optional but Enhanced)

| Function | File | Purpose |
|----------|------|---------|
| `analyze_prospect_smart()` | [llm_intelligence.py:13](backend/llm_intelligence.py#L13) | GPT-4 analyzes prospect → intelligence |
| `build_consultative_system_prompt()` | [llm_intelligence.py:155](backend/llm_intelligence.py#L155) | Creates advanced system prompt |

## Data Models

**File**: [backend/models.py](backend/models.py)

```python
class CalendlyQA(BaseModel):
    question: str
    answer: str

class CalendlyInvitee(BaseModel):
    name: str
    email: EmailStr
    timezone: Optional[str] = "UTC"
    uri: Optional[str] = None

class CalendlyEvent(BaseModel):
    uri: str
    name: str
    start_time: str  # ISO 8601
    end_time: str    # ISO 8601

class CalendlyPayloadData(BaseModel):
    event: CalendlyEvent
    invitee: CalendlyInvitee
    questions_and_answers: Optional[List[CalendlyQA]] = []

class CalendlyPayload(BaseModel):
    event: str  # e.g., "invitee.created"
    payload: CalendlyPayloadData

class PreWarmSession(BaseModel):
    session_id: str
    session_url: str
    room_url: str
    token: str
    invitee_email: str
    invitee_name: str
    meeting_time: str
    calendly_event_uri: str
```

## Configuration & Environment Variables

**File**: [.env.example](.env.example)

```env
# Path AI Backend Configuration
PATH_AI_API_URL=http://localhost:8000/api/v1
PATH_AI_AGENT_ID=cmes7xkl70001itz0qd7ffysf
PATH_AI_WORKSPACE_ID=cmav3386q0001js0d4lelupen

# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
PRE_WARM_FROM_EMAIL=team@layerpath.com

# Frontend URL
FRONTEND_URL=https://pathai.app

# Calendly (optional)
CALENDLY_WEBHOOK_SECRET=your_calendly_webhook_secret

# Server
PORT=8002
HOST=0.0.0.0

# Optional: For LLM Intelligence
OPENAI_API_KEY=sk-...

# Optional: For Summary Generation
SUPABASE_URL=https://dvzrcusywjqyrfnpiygh.supabase.co
SUPABASE_KEY=...

# Optional: Mock mode (for testing without Path AI)
MOCK_MODE=false
```

## What Gets "Prewarmed"

The system pre-warms:

1. **AI Awareness**:
   - Prospect's name, company, role
   - What they do, why they booked, their pain point
   - Meeting date/time context

2. **Conversation Strategy**:
   - Natural opening that acknowledges their context
   - Embedded discovery questions (not interrogation)
   - Value examples based on their role/industry
   - Demo focus points for sales rep

3. **Sales Rep Preparation**:
   - Lead score (HOT/WARM/COLD)
   - Extracted insights (company, role, pain point, timeline, tools)
   - Full transcript for reference
   - Qualification signals

**Why It Matters**:
- **Before**: Sales rep walks into meeting with no context, wastes 10-15 minutes on discovery
- **After**: Sales rep has full brief, knows if lead is HOT, and can jump straight to demo/solution

## Required Path AI Modifications

The Pre-Warm POC requires modifications to Path AI backend to support `initial_context` injection.

**File**: [PATH_AI_MODIFICATIONS.md](PATH_AI_MODIFICATIONS.md)

**Modified Files in Path AI** (not in this repo, but documented):

1. **`path_router.py`** - Extract `initial_context` from metadata, pass to worker
2. **`manager.py`** - Add `initial_context` parameter, include in command dict
3. **`voice_worker.py`** - Extract from command, pass to PathVoiceAssistant
4. **`path_voice_assistant.py`** - Prepend `initial_context` to system prompt

**Key Change**:
```python
# In path_voice_assistant.py, around line 872
if self.initial_context:
    global_prompt = f"{self.initial_context}\n\n---\n\n{global_prompt}"
```

This ensures the pre-warm context is available to the AI before conversation starts.

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | Root/health check |
| `GET` | `/health` | Health check |
| `POST` | `/webhook/calendly` | Receive Calendly booking webhook |
| `POST` | `/test/create-session` | Manual session creation (for testing) |
| `GET` | `/summary/{session_id}` | Fetch & score completed session |

### POST /test/create-session

Manual testing endpoint that simulates a Calendly booking.

**Query Parameters**:
- `email` - Invitee email (required)
- `name` - Invitee name (required)
- `company` - Company name (optional)
- `role` - Job role (optional)
- `reason` - Reason for booking (optional)
- `meeting_date` - ISO 8601 date (optional)

**Example**:
```bash
curl -X POST "http://localhost:8002/test/create-session?email=evan@example.com&name=Evan&company=UnicornPack&role=CEO&reason=Evaluate+product"
```

**Response**:
```json
{
    "status": "success",
    "message": "Smart pre-warm session created with LLM analysis",
    "session_id": "abc-123-xyz",
    "session_url": "https://pathai.app/voice?room=...&token=...",
    "analysis": {
        "industry": "SaaS",
        "seniority": "C-Level",
        "is_decision_maker": true,
        "urgency_level": "High",
        "opening_message": "Hi Evan! Since you're CEO at UnicornPack..."
    }
}
```

## Dependencies

**File**: [pyproject.toml](pyproject.toml)

```toml
dependencies = [
    "fastapi>=0.115.0",           # Web framework
    "uvicorn[standard]>=0.32.0",  # ASGI server
    "httpx>=0.27.2",              # Async HTTP client
    "python-dotenv>=1.0.1",       # Environment variables
    "pydantic[email]>=2.9.2",     # Data validation
    "pydantic-settings>=2.6.0",   # Settings management
    "openai>=1.0.0",              # GPT-4 integration
]
```

## Flow Diagram

```
┌─────────────┐
│   Calendly  │ 1. Booking created
└──────┬──────┘
       │
       │ webhook: invitee.created
       ↓
┌──────────────────────────┐
│  Pre-Warm POC API        │ 2. Receive webhook
│  (Port 8002)             │    Parse & validate
└──────┬───────────────────┘
       │
       ├─→ process_calendly_booking()
       │   ├─→ build_initial_context()
       │   ├─→ create_path_ai_session_with_context()
       │   └─→ send_pre_warm_email()
       │
       ↓
┌──────────────────────────┐
│   Path AI Backend        │ 3. Create Daily.co room
│   (Port 8000)            │    Start voice worker
└──────┬───────────────────┘    Inject initial_context
       │
       │ return: room_url, token, session_id
       ↓
┌──────────────────────────┐
│  Pre-Warm POC API        │ 4. Send email
└──────┬───────────────────┘
       │
       │ SMTP email with link
       ↓
┌──────────────────────────┐
│     Prospect             │ 5. Receive email
└──────┬───────────────────┘
       │
       │ click link
       ↓
┌──────────────────────────┐
│  Path AI Frontend        │ 6. Open session
│  (pathai.app)            │    AI starts with context
└──────┬───────────────────┘
       │
       │ conversation: 5-10 min
       ↓
┌──────────────────────────┐
│   Path AI Backend        │ 7. Store in PathChatHistory
│   (Supabase DB)          │
└──────┬───────────────────┘
       │
       │ conversation ends
       ↓
┌──────────────────────────┐
│  Pre-Warm POC API        │ 8. /summary/{session_id}
│  (summary generation)    │    Fetch transcript
└──────┬───────────────────┘    Score lead
       │                        Extract insights
       │ HOT/WARM/COLD brief
       ↓
┌──────────────────────────┐
│  Sales Rep              │  Ready for call!
│  (with full brief)      │
└──────────────────────────┘
```

## Modes & Testing

### Production Mode
- Real Calendly webhooks trigger flow
- Uses real Path AI backend
- Uses real SMTP email delivery
- Queries Supabase for transcripts

### Mock Mode (for testing without Path AI)
Enable with environment variable:
```bash
MOCK_MODE=true
```

Simulates Path AI responses without actual backend.

### Test Endpoint (`/test/create-session`)
Manual testing without Calendly:
```bash
curl -X POST "http://localhost:8002/test/create-session?email=test@example.com&name=Test"
```

### Local Testing with ngrok
For Calendly webhook testing locally:
```bash
ngrok http 8002
# Use ngrok URL in Calendly: https://abc123.ngrok.io/webhook/calendly
```

## Future Enhancements (Currently Deferred)

- Session monitoring (detect when conversation ends)
- Slack integration (post briefs to sales channel)
- CRM sync (HubSpot/Salesforce integration)
- Analytics & tracking (conversion correlations)
- Company enrichment (Clearbit/Apollo API)
- Multi-channel outreach (SMS reminders, WhatsApp)
- Advanced lead scoring (ML model based)

## Getting Started

### Prerequisites

1. Python 3.9+
2. Path AI backend running (or `MOCK_MODE=true`)
3. SMTP credentials (Gmail app password recommended)
4. Supabase database (for summary generation)

### Installation

```bash
# Clone the repository
cd /home/user/pre-warm-poc

# Install dependencies with uv
uv sync

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Running the Server

```bash
# Development
uv run uvicorn backend.main:app --reload --port 8002

# Production
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8002
```

### Testing

```bash
# Test session creation
curl -X POST "http://localhost:8002/test/create-session?email=test@example.com&name=Test+User&company=TestCo&role=CEO"

# Check summary (replace with actual session_id)
curl "http://localhost:8002/summary/YOUR_SESSION_ID"
```

## Troubleshooting

### Common Issues

1. **Email not sending**
   - Verify SMTP credentials in `.env`
   - Check Gmail "Less secure app access" or use App Password
   - Review logs for SMTP errors

2. **Path AI connection fails**
   - Verify `PATH_AI_API_URL` is correct
   - Check Path AI backend is running
   - Enable `MOCK_MODE=true` for testing

3. **Summary returns empty**
   - Verify Supabase credentials
   - Check session exists in `PathChatHistory` table
   - Ensure conversation completed (has messages)

4. **Calendly webhook not triggering**
   - Use ngrok for local testing
   - Verify webhook URL in Calendly settings
   - Check webhook logs in Calendly dashboard

## Support

For issues or questions:
- Review the [PATH_AI_MODIFICATIONS.md](PATH_AI_MODIFICATIONS.md) for integration details
- Check logs: `uv run uvicorn backend.main:app --log-level debug`
- Test with `/test/create-session` endpoint first
