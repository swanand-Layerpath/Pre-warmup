# Pre-Warm POC

A proof-of-concept system that creates pre-call qualification conversations by integrating Calendly bookings with Path AI chat sessions.

## 🎯 What It Does

When someone books a meeting via Calendly:
1. **Webhook triggered** → System receives booking details
2. **Path AI session created** → With pre-loaded context from Calendly form
3. **Email sent** → Prospect gets link to chat before the call
4. **AI conversation** → Asks 3-5 smart follow-up questions
5. **Summary generated** → Sales rep gets formatted brief (future: Slack integration)

## 📁 Project Structure

```
pre-warm-poc/
├── backend/
│   ├── __init__.py
│   ├── main.py                # FastAPI app with webhook endpoints
│   ├── calendly_handler.py    # Process Calendly bookings
│   ├── path_ai_client.py      # Call Path AI /connect API
│   ├── email_sender.py        # SendGrid email integration
│   └── models.py              # Pydantic models
├── test_data/
│   └── sample_webhook.json    # Example Calendly payload
├── .env.example               # Environment template
├── pyproject.toml            # Dependencies
└── README.md                 # This file
```

## 🚀 Setup

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Path AI Configuration
PATH_AI_API_URL=http://localhost:8000/api/v1
PATH_AI_AGENT_ID=your_agent_id_here
PATH_AI_WORKSPACE_ID=your_workspace_id_here

# Email Configuration
SENDGRID_API_KEY=your_sendgrid_api_key
PRE_WARM_FROM_EMAIL=team@layerpath.com

# Frontend URL
FRONTEND_URL=https://pathai.app

# Server
PORT=8002
HOST=0.0.0.0
```

### 3. Run the Server

```bash
# Using Python
python -m backend.main

# Or using uvicorn directly
uvicorn backend.main:app --host 0.0.0.0 --port 8002 --reload
```

Server will start on `http://localhost:8002`

## 🧪 Testing

### Manual Test (No Calendly Required)

Test endpoint to create a session without Calendly:

```bash
# Basic test
curl -X POST "http://localhost:8002/test/create-session?email=test@example.com&name=Test%20User"

# With full details
curl -X POST "http://localhost:8002/test/create-session?email=vinay@layerpath.com&name=Vinay&company=SaaS%20Startup&role=CEO&reason=Demo%20request"
```

Response:
```json
{
  "status": "success",
  "session_id": "abc-123-xyz",
  "session_url": "https://pathai.app/voice?room=...&token=...",
  "invitee_email": "test@example.com"
}
```

### Test with Sample Webhook Payload

```bash
curl -X POST http://localhost:8002/webhook/calendly \
  -H "Content-Type: application/json" \
  -d @test_data/sample_webhook.json
```

### Health Check

```bash
curl http://localhost:8002/health
```

## 🔗 Calendly Integration

### Setting Up Calendly Webhook

1. Go to [Calendly Webhooks](https://calendly.com/integrations/webhooks)
2. Click "Create Webhook"
3. Set URL: `https://your-domain.com/webhook/calendly`
4. Select event: `invitee.created`
5. Save

### Testing with ngrok (Local Development)

```bash
# Start ngrok
ngrok http 8002

# Use the ngrok URL in Calendly webhook settings
# Example: https://abc123.ngrok.io/webhook/calendly
```

## 📋 API Endpoints

### `POST /webhook/calendly`
Receives Calendly webhooks when meetings are booked.

**Payload:**
```json
{
  "event": "invitee.created",
  "payload": {
    "event": { ... },
    "invitee": { ... },
    "questions_and_answers": [ ... ]
  }
}
```

### `POST /test/create-session`
Manually create a pre-warm session for testing.

**Query Params:**
- `email` (required): Invitee email
- `name` (required): Invitee name
- `company` (optional): Company name
- `role` (optional): Job title
- `reason` (optional): Reason for booking

### `GET /health`
Health check endpoint.

## ⚙️ How It Works

### 1. Context Building

When a Calendly booking comes in, we extract:
- Invitee details (name, email)
- Meeting details (time, type)
- Calendly form responses (Q&A)

This is transformed into a system prompt:

```
You are preparing for a sales discovery call.

MEETING DETAILS:
- Contact: Evan Smith (evan@unicornpack.com)
- Scheduled: December 3, 2025 at 2:00 PM
- Meeting Type: 30 Minute Demo Call

CALENDLY FORM RESPONSES:
Q: What does your company do?
A: We're building a SaaS Design Studio in Figma

Q: What's your role?
A: Co-founder & CEO

Q: What brings you to Layerpath?
A: Need help with user onboarding

YOUR GOAL:
Ask 3-5 thoughtful follow-up questions to build a comprehensive pre-call brief.
Focus on understanding:
1. Company context and what they do
2. Specific pain points or needs
3. Timeline and urgency
4. Current tools/solutions they're using
5. Decision-making process
```

### 2. Path AI Session

We call the Path AI `/connect` endpoint with:
- `agent_id`, `workspace_id`, `visitor_id`
- `metadata.initial_context` ← **Our pre-warm context**

**⚠️ IMPORTANT:** The Path AI backend needs to be modified to inject `initial_context` into the system prompt. See "Path AI Modifications" section below.

### 3. Email

SendGrid email is sent with:
- Personalized greeting
- Meeting date/time
- Link to chat session
- Clear CTA ("Start Quick Prep")

### 4. Conversation

Prospect clicks link → Opens Path AI chat → AI asks follow-up questions naturally → Prospect answers → AI says thanks!

### 5. Summary (Future)

After conversation ends:
- Extract transcript from PathChatHistory
- Run through DSPy lead extraction
- Format and send to Slack
- Sales rep gets the brief before the call

## 🔧 Path AI Modifications Needed

The existing Path AI backend needs one small modification to support `initial_context`:

### File: `path-ai/backend/src/router/path_router.py`

```python
@router.post("/connect")
async def rtvi_connect(request: Request):
    data = await request.json()
    agent_id = data.get("agent_id")
    workspace_id = data.get("workspace_id")
    visitor_id = data.get("visitor_id")
    browser_timezone = data.get("browser_timezone")

    # NEW: Extract initial_context from metadata
    metadata = data.get("metadata", {})
    initial_context = metadata.get("initial_context")

    # ... existing code ...

    manager.start_flow_in_worker(
        session_id,
        room_url,
        bot_token,
        agent_id,
        workspace_id,
        visitor_id,
        browser_timezone=browser_timezone,
        initial_context=initial_context  # NEW
    )
```

### File: `path-ai/backend/src/lib/manager.py`

```python
def start_flow_in_worker(
    self,
    session_id: str,
    room_url: str,
    bot_token: str,
    agent_id: str,
    workspace_id: str,
    visitor_id: str,
    browser_timezone: str | None = None,
    initial_context: str | None = None,  # NEW
):
    cmd = {
        "type": "start_flow",
        "session_id": session_id,
        "room_url": room_url,
        "bot_token": bot_token,
        "agent_id": agent_id,
        "workspace_id": workspace_id,
        "visitor_id": visitor_id,
        "browser_timezone": browser_timezone,
        "initial_context": initial_context,  # NEW
    }
    # ... rest of code ...
```

### File: `path-ai/backend/src/services/path_voice_assistant.py`

In the `__init__` method around line 872:

```python
# Get global prompt
global_prompt = self.agent_config.get("globalPrompt") if self.agent_config else None

# NEW: Prepend initial_context if provided
if initial_context:
    global_prompt = f"{initial_context}\n\n---\n\n{global_prompt}"

# ... rest of system prompt construction ...
```

## 📊 Future Enhancements (V1+)

- ✅ **Slack Integration**: Post formatted briefs to Slack channel
- ✅ **Session Monitoring**: Detect when conversation ends
- ✅ **CRM Sync**: Write summaries to HubSpot/Salesforce
- ✅ **Analytics**: Track completion rates, correlation to close rates
- ✅ **Smart Scoring**: ML model to predict HOT/WARM/COLD
- ✅ **Enrichment**: Auto-pull company data (Clearbit/Apollo)
- ✅ **Multi-channel**: SMS reminders if chat not completed

## 🐛 Troubleshooting

### Email not sending?
- Check `SENDGRID_API_KEY` is set correctly
- Verify sender email is verified in SendGrid
- Check logs for SendGrid API errors

### Session not created?
- Ensure Path AI backend is running on `PATH_AI_API_URL`
- Check `PATH_AI_AGENT_ID` and `PATH_AI_WORKSPACE_ID` are correct
- Verify Path AI `/connect` endpoint is accessible

### Webhook not receiving?
- Test with `/test/create-session` first
- Check Calendly webhook configuration
- Use ngrok for local testing
- Check server logs for errors

## 📝 Example Flow

```
1. Evan books call with Vinay via Calendly
   └─> Fills form: Company, Role, Reason

2. Calendly sends webhook to our server
   └─> POST /webhook/calendly

3. We create Path AI session with context
   └─> POST path-ai.com/api/v1/connect

4. Send email to Evan
   └─> "Quick prep before our call"

5. Evan clicks link, chats with AI
   └─> Answers 3-5 questions

6. System generates summary
   └─> (Future: Post to Slack)

7. Vinay reviews brief before call
   └─> Walks in 100% prepared!
```

## 📄 License

MIT

## 🙋 Support

For questions or issues, contact the Layerpath team.
