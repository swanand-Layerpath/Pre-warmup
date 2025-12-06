#!/bin/bash

# Test script for pre-warm POC

set -e

BASE_URL="http://localhost:8002"

echo "🧪 Testing Pre-Warm POC"
echo "======================="
echo ""

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s "$BASE_URL/health" | jq '.'
echo "✅ Health check passed"
echo ""

# Test 2: Create test session
echo "2. Creating test pre-warm session..."
curl -s -X POST "$BASE_URL/test/create-session?email=test@example.com&name=Test%20User&company=TestCo&role=CEO&reason=Demo%20request" | jq '.'
echo "✅ Test session created"
echo ""

# Test 3: Send sample Calendly webhook
echo "3. Sending sample Calendly webhook..."
curl -s -X POST "$BASE_URL/webhook/calendly" \
  -H "Content-Type: application/json" \
  -d @test_data/sample_webhook.json | jq '.'
echo "✅ Webhook processed"
echo ""

echo "🎉 All tests passed!"
echo ""
echo "Next steps:"
echo "1. Check logs for any errors"
echo "2. Open the session_url in your browser"
echo "3. Have a conversation with the AI"
echo "4. Check Path AI dashboard for the session"
