# Path AI Backend Modifications for Pre-Warm Support

This document outlines the minimal changes needed to the existing Path AI backend to support pre-warm conversations with initial context injection.

## 🎯 Goal

Enable the `/connect` endpoint to accept an `initial_context` parameter that gets prepended to the agent's system prompt, allowing pre-loaded context from Calendly bookings.

## 📝 Required Changes

### 1. Modify `/connect` Endpoint

**File:** `/home/user/path-ai/backend/src/router/path_router.py` (around line 502)

**Current code:**
```python
@router.post("/connect")
async def rtvi_connect(request: Request):
    data = await request.json()
    agent_id, workspace_id, visitor_id = (
        data.get("agent_id"),
        data.get("workspace_id"),
        data.get("visitor_id"),
    )
    browser_timezone = data.get("browser_timezone")
    logger.info(f"agent_id: {agent_id}, workspace_id: {workspace_id}")

    manager = request.app.state.manager
    session_id = str(uuid.uuid4())
    room_url, bot_token = await manager.create_room_and_token(
        workspace_id, agent_id, session_id
    )

    try:
        manager.start_flow_in_worker(
            session_id, room_url, bot_token, agent_id, workspace_id, visitor_id, browser_timezone=browser_timezone
        )
    except Exception as e:
        logger.error(f"Error starting bot in worker: {e}")
        raise HTTPException(status_code=500, detail="Failed to process!")

    return {"room_url": room_url, "token": bot_token}
```

**New code:**
```python
@router.post("/connect")
async def rtvi_connect(request: Request):
    data = await request.json()
    agent_id, workspace_id, visitor_id = (
        data.get("agent_id"),
        data.get("workspace_id"),
        data.get("visitor_id"),
    )
    browser_timezone = data.get("browser_timezone")

    # NEW: Extract metadata and initial_context
    metadata = data.get("metadata", {})
    initial_context = metadata.get("initial_context")

    logger.info(f"agent_id: {agent_id}, workspace_id: {workspace_id}")
    if initial_context:
        logger.info(f"Pre-warm mode with initial_context (length: {len(initial_context)})")

    manager = request.app.state.manager
    session_id = str(uuid.uuid4())
    room_url, bot_token = await manager.create_room_and_token(
        workspace_id, agent_id, session_id
    )

    try:
        manager.start_flow_in_worker(
            session_id,
            room_url,
            bot_token,
            agent_id,
            workspace_id,
            visitor_id,
            browser_timezone=browser_timezone,
            initial_context=initial_context  # NEW: Pass to worker
        )
    except Exception as e:
        logger.error(f"Error starting bot in worker: {e}")
        raise HTTPException(status_code=500, detail="Failed to process!")

    return {"room_url": room_url, "token": bot_token, "session_id": session_id}  # Also return session_id
```

**Changes:**
- Extract `metadata` and `initial_context` from request
- Pass `initial_context` to `start_flow_in_worker()`
- Return `session_id` in response (useful for tracking)
- Add logging for pre-warm mode

---

### 2. Update ConnectionManager

**File:** `/home/user/path-ai/backend/src/lib/manager.py` (around line 291)

**Current code:**
```python
def start_flow_in_worker(
    self,
    session_id: str,
    room_url: str,
    bot_token: str,
    agent_id: str,
    workspace_id: str,
    visitor_id: str,
    sip_endpoint: str | None = None,
    call_sid: str | None = None,
    caller_phone: str | None = None,
    browser_timezone: str | None = None,
):
    self.ensure_voice_worker_pool()
    worker_id = next((i for i, busy in self._worker_busy.items() if not busy), None)
    if worker_id is None:
        raise HTTPException(status_code=503, detail="No available voice workers")

    cmd = {
        "type": "start_flow",
        "session_id": session_id,
        "room_url": room_url,
        "bot_token": bot_token,
        "agent_id": agent_id,
        "workspace_id": workspace_id,
        "visitor_id": visitor_id,
        "browser_timezone": browser_timezone,
    }
```

**New code:**
```python
def start_flow_in_worker(
    self,
    session_id: str,
    room_url: str,
    bot_token: str,
    agent_id: str,
    workspace_id: str,
    visitor_id: str,
    sip_endpoint: str | None = None,
    call_sid: str | None = None,
    caller_phone: str | None = None,
    browser_timezone: str | None = None,
    initial_context: str | None = None,  # NEW
):
    self.ensure_voice_worker_pool()
    worker_id = next((i for i, busy in self._worker_busy.items() if not busy), None)
    if worker_id is None:
        raise HTTPException(status_code=503, detail="No available voice workers")

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
```

**Changes:**
- Add `initial_context` parameter to function signature
- Add `initial_context` to command dict sent to worker

---

### 3. Update Voice Worker

**File:** `/home/user/path-ai/backend/src/services/voice_worker.py`

Find where `start_flow` command is processed (look for `cmd["type"] == "start_flow"`), and extract `initial_context`:

**Add this line:**
```python
initial_context = cmd.get("initial_context")
```

Then pass it to `PathVoiceAssistant.create()`:

```python
bot = await PathVoiceAssistant.create(
    url=room_url,
    bot_token=bot_token,
    agent_id=agent_id,
    workspace_id=workspace_id,
    session_id=session_id,
    visitor_id=visitor_id,
    browser_timezone=browser_timezone,
    initial_context=initial_context,  # NEW
)
```

---

### 4. Update PathVoiceAssistant

**File:** `/home/user/path-ai/backend/src/services/path_voice_assistant.py`

#### 4a. Update `create()` classmethod (around line 600)

**Add parameter:**
```python
@classmethod
async def create(
    cls,
    url: str,
    bot_token: str,
    agent_id: str,
    workspace_id: str,
    session_id: str,
    visitor_id: str,
    browser_timezone: str | None = None,
    initial_context: str | None = None,  # NEW
):
    # ... existing code to fetch agent_config and past_sessions ...

    return cls(
        url=url,
        bot_token=bot_token,
        agent_id=agent_id,
        workspace_id=workspace_id,
        session_id=session_id,
        visitor_id=visitor_id,
        agent_config=agent_config,
        past_sessions_context=past_sessions_context,
        browser_timezone=browser_timezone,
        initial_context=initial_context,  # NEW
    )
```

#### 4b. Update `__init__()` method (around line 635)

**Add parameter:**
```python
def __init__(
    self,
    url: str,
    bot_token: str,
    agent_id: str,
    workspace_id: str,
    session_id: str,
    visitor_id: str,
    agent_config: dict = {},
    past_sessions_context: list = [],
    browser_timezone: str | None = None,
    initial_context: str | None = None,  # NEW
):
    self.url = url
    self.bot_token = bot_token
    self.agent_id = agent_id
    self.workspace_id = workspace_id
    self.session_id = session_id
    self.visitor_id = visitor_id
    self.agent_config = agent_config
    self.past_sessions_context = past_sessions_context
    self.browser_timezone = browser_timezone
    self.initial_context = initial_context  # NEW
```

#### 4c. Modify system prompt construction (around line 872)

**Current code:**
```python
# Get global prompt from database (agent_config), fallback to local constant if not available
global_prompt = (
    self.agent_config.get("globalPrompt") if self.agent_config else None
)

if not global_prompt or not global_prompt.strip():
    from src.constants.experimental_prompts import (
        LAYERPATH_AI_AGENT_PROMPT_V2_EXPERIMENTAL_DEMO_WITH_NAVIGATION,
    )
    global_prompt = (
        LAYERPATH_AI_AGENT_PROMPT_V2_EXPERIMENTAL_DEMO_WITH_NAVIGATION
    )

global_prompt = global_prompt.replace(
    "<<PAST_SESSIONS_CONTEXT>>", past_sessions_context_str
)

messages = [
    {
        "role": "system",
        "content": global_prompt,
    },
]
```

**New code:**
```python
# Get global prompt from database (agent_config), fallback to local constant if not available
global_prompt = (
    self.agent_config.get("globalPrompt") if self.agent_config else None
)

if not global_prompt or not global_prompt.strip():
    from src.constants.experimental_prompts import (
        LAYERPATH_AI_AGENT_PROMPT_V2_EXPERIMENTAL_DEMO_WITH_NAVIGATION,
    )
    global_prompt = (
        LAYERPATH_AI_AGENT_PROMPT_V2_EXPERIMENTAL_DEMO_WITH_NAVIGATION
    )

global_prompt = global_prompt.replace(
    "<<PAST_SESSIONS_CONTEXT>>", past_sessions_context_str
)

# NEW: Prepend initial_context if provided (for pre-warm mode)
if self.initial_context:
    logger.bind(session_id=self.session_id).info(
        f"Prepending initial_context for pre-warm mode (length: {len(self.initial_context)})"
    )
    global_prompt = f"{self.initial_context}\n\n---\n\n{global_prompt}"

messages = [
    {
        "role": "system",
        "content": global_prompt,
    },
]
```

**Changes:**
- Check if `self.initial_context` exists
- If yes, prepend it to `global_prompt` with a separator
- Add logging for debugging

---

## 🧪 Testing the Changes

After making these modifications, test with:

```bash
# From the pre-warm-poc directory
curl -X POST http://localhost:8002/test/create-session?email=test@example.com&name=Test
```

This will:
1. Call Path AI `/connect` with `initial_context` in metadata
2. Path AI will create a session with pre-loaded context
3. Return a session URL
4. Open the URL and verify the AI starts with context awareness

## 🔍 Verification

To verify it's working:

1. **Check logs** for "Pre-warm mode with initial_context"
2. **Start a conversation** and see if the AI knows the context
3. **Ask the AI** "What do you know about me?" - it should reference the Calendly info

Example expected behavior:
```
User: "Hi!"
AI: "Hi! Thanks for taking time to prep for your call with Vinay on December 3rd.
     I see from your Calendly form that you're building a SaaS Design Studio in Figma
     and you're interested in onboarding help. Tell me more about your product..."
```

## 📊 Impact Assessment

**Files modified:** 4
**Lines added:** ~20
**Breaking changes:** None (backward compatible)
**Risk level:** Low

All changes are additive and backward compatible:
- Existing `/connect` calls without `initial_context` work as before
- Only when `initial_context` is provided does behavior change
- Falls back gracefully if parameter is missing

## 🚀 Deployment

1. Make changes in a feature branch
2. Test locally with pre-warm POC
3. Deploy to staging
4. Test end-to-end flow
5. Deploy to production

## 📝 Alternative Approaches

If modifying the core Path AI backend is not desired, consider:

**Option A: Separate endpoint**
Create `/connect-prewarm` endpoint specifically for pre-warm sessions

**Option B: Agent config**
Store pre-warm templates in `PathAgentConfig` and reference them

**Option C: Visitor context**
Store initial context in `PathVisitors` table and load it

The approach outlined above is recommended because it's:
- ✅ Minimal changes
- ✅ Backward compatible
- ✅ Flexible for future use cases
- ✅ Follows existing patterns
