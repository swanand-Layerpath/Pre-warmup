# Local Testing Guide with Real Calendly

This guide walks you through testing the Pre-Warm POC with your actual Calendly account.

## 🎯 What You'll Need

1. ✅ Calendly Pro account (for webhooks)
2. ✅ Path AI backend running (localhost:8000)
3. ✅ ngrok installed (for webhook tunnel)
4. ✅ SendGrid API key (optional, can test without)

## 📋 Step-by-Step Setup

### Step 1: Configure Environment Variables

Edit `.env` file with your actual credentials:

```bash
# Path AI Configuration (get from your Path AI backend)
PATH_AI_API_URL=http://localhost:8000/api/v1
PATH_AI_AGENT_ID=<your_agent_id>
PATH_AI_WORKSPACE_ID=<your_workspace_id>

# Email (optional for first test)
SENDGRID_API_KEY=<your_sendgrid_key>
PRE_WARM_FROM_EMAIL=<your_verified_sender_email>

# Frontend
FRONTEND_URL=https://pathai.app

# Server
PORT=8002
HOST=0.0.0.0
```

**Where to find Path AI credentials:**
- Check your Path AI dashboard or database
- Or ask your team for the agent_id and workspace_id

### Step 2: Start Pre-Warm POC Server

```bash
# Make sure you're in the pre-warm-poc directory
cd /home/user/pre-warm-poc

# Start the server
uv run python -m backend.main
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8002
```

Keep this terminal open!

### Step 3: Test Without Calendly First

In a **new terminal**, test the endpoint manually:

```bash
curl -X POST "http://localhost:8002/test/create-session?email=YOUR_EMAIL@example.com&name=Test%20User&company=TestCo&role=Founder&reason=Testing%20pre-warm"
```

Replace `YOUR_EMAIL@example.com` with your actual email.

**Expected response:**
```json
{
  "status": "success",
  "session_id": "abc-123-xyz",
  "session_url": "https://pathai.app/voice?room=...&token=...",
  "invitee_email": "YOUR_EMAIL@example.com"
}
```

**If this works:** ✅ Your setup is correct!
**If this fails:** ❌ Check your Path AI credentials in `.env`

### Step 4: Setup ngrok Tunnel

ngrok creates a public URL that Calendly can send webhooks to.

```bash
# In a new terminal
ngrok http 8002
```

You'll see output like:
```
Forwarding  https://abc123def456.ngrok.io -> http://localhost:8002
```

Copy the `https://...ngrok.io` URL - you'll need it for Calendly!

**Important:** Keep this terminal open too!

### Step 5: Configure Calendly Webhook

1. Go to [Calendly Webhooks Settings](https://calendly.com/integrations/webhooks)

2. Click **"Create Webhook"** or **"Add Webhook Subscription"**

3. Fill in:
   - **Webhook URL:** `https://YOUR-NGROK-URL.ngrok.io/webhook/calendly`
     - Example: `https://abc123def456.ngrok.io/webhook/calendly`
   - **Events to subscribe:** Select **"Invitee Created"**
   - **Signing key:** (optional for testing)

4. Click **Save**

### Step 6: Book a Test Meeting

1. Go to your Calendly booking page
   - Example: `calendly.com/YOUR-USERNAME/30min`

2. Book a meeting (can be with yourself)

3. Fill out the form questions (these will be used for context):
   - What does your company do?
   - What's your role?
   - What brings you to Layerpath?

4. Complete the booking

### Step 7: Watch the Magic Happen! ✨

**In the Pre-Warm POC terminal**, you should see:
```
INFO: Received Calendly webhook: invitee.created
INFO: Processing booking for Your Name (your@email.com)
INFO: Creating Path AI session...
INFO: Created session abc-123 with URL: https://pathai.app/voice?...
INFO: Successfully sent pre-warm email to your@email.com
INFO: Successfully created pre-warm session abc-123
```

**In your email inbox**, you'll receive:
> **Subject:** Quick prep before our call on [date]
>
> Hi [Your Name]! 👋
>
> Thanks for booking time with us...
>
> [Start Quick Prep →]

### Step 8: Test the Conversation

1. Click the **"Start Quick Prep"** button in the email

2. You'll be taken to Path AI chat

3. The AI should greet you with **context from your Calendly form**:
   ```
   AI: Hi [Name]! Thanks for taking time to prep for your call.
       I see from your Calendly form that [context from your answers].
       Tell me more about [relevant follow-up question]...
   ```

4. Answer 3-5 questions naturally

5. AI will thank you and end the conversation

### Step 9: Check the Summary (Future)

For now, you can check:
- Path AI dashboard for the session
- PathChatHistory table in database
- Console logs for the conversation

In V1, this will automatically post to Slack!

## 🔍 Troubleshooting

### "Connection refused" when testing endpoint

**Problem:** Path AI backend not running

**Solution:**
```bash
# Check if Path AI is running
curl http://localhost:8000/health

# If not, start it
cd /home/user/path-ai/backend
uv run python main.py
```

### Calendly webhook not triggering

**Problem:** ngrok URL might be wrong or ngrok stopped

**Check:**
1. Is ngrok still running? Check the terminal
2. Copy the FULL ngrok URL including `/webhook/calendly`
3. Test webhook manually:
   ```bash
   curl -X POST https://YOUR-NGROK-URL.ngrok.io/webhook/calendly \
     -H "Content-Type: application/json" \
     -d @test_data/sample_webhook.json
   ```

### Email not sending

**Problem:** SENDGRID_API_KEY not set or invalid

**Solution:**
- For testing, this is OK! The webhook will still work
- You'll see the session URL in the console logs
- Copy the URL and open it manually
- To fix: Get valid SendGrid API key and update `.env`

### "Agent not found" error

**Problem:** Wrong agent_id or workspace_id

**Solution:**
1. Check your Path AI database or dashboard
2. Look for `PathAgent` table entries
3. Update `.env` with correct IDs
4. Restart the server

### AI doesn't have context from Calendly

**Problem:** Path AI backend hasn't been modified yet

**Solution:**
- The Path AI backend needs modifications to accept `initial_context`
- See [PATH_AI_MODIFICATIONS.md](PATH_AI_MODIFICATIONS.md)
- This is the next step after testing the basic flow works

## 📊 What to Test

Create different scenarios:

### Test 1: Hot Lead
```
Company: "Fast-growing SaaS, 10K users"
Role: "VP Product"
Reason: "Need to implement onboarding ASAP, budget approved"
```

Expected: AI should identify urgency and ask about timeline

### Test 2: Cold Lead
```
Company: "Early stage startup, pre-launch"
Role: "Founder"
Reason: "Just exploring options"
```

Expected: AI should focus on education and future timing

### Test 3: Minimal Info
```
Company: "SaaS company"
Role: "Sales"
Reason: "Demo"
```

Expected: AI should ask more detailed discovery questions

## 🎉 Success Criteria

You've successfully tested when:

- ✅ Calendly booking triggers webhook
- ✅ Pre-Warm POC receives webhook
- ✅ Path AI session created
- ✅ Email delivered (or URL logged if no SendGrid)
- ✅ You can open the session and chat
- ✅ Conversation saves to PathChatHistory

## 🚀 Next Steps

Once basic flow works:

1. **Modify Path AI backend** to inject `initial_context`
   - See [PATH_AI_MODIFICATIONS.md](PATH_AI_MODIFICATIONS.md)
   - Test that AI has context awareness

2. **Add Slack integration**
   - Post summaries to #sales channel
   - Format with deal strength indicators

3. **Test with real prospects**
   - Get feedback from sales team
   - Iterate on AI questions and prompts

## 📝 Testing Checklist

- [ ] Dependencies installed (`uv sync`)
- [ ] `.env` configured with Path AI credentials
- [ ] Pre-Warm POC server running (port 8002)
- [ ] Path AI backend running (port 8000)
- [ ] ngrok tunnel active
- [ ] Calendly webhook configured
- [ ] Test booking created
- [ ] Webhook received in logs
- [ ] Email received (or URL logged)
- [ ] Session opens successfully
- [ ] Conversation works
- [ ] Chat history saved

## 💡 Pro Tips

**Use ngrok's web interface:**
- Open `http://localhost:4040` while ngrok is running
- See all webhook requests in real-time
- Replay failed requests
- Debug payloads

**Check logs:**
- Pre-Warm POC logs show webhook processing
- Path AI logs show session creation
- Look for errors in both

**Test email formatting:**
- Send test emails to different clients
- Check mobile rendering
- Verify links work

**Monitor Daily.co rooms:**
- Check Daily.co dashboard
- See active sessions
- Monitor for room creation issues

---

**Ready to go?** Start with Step 1 and work through each step!

**Questions?** Check [README.md](README.md) or open an issue.
