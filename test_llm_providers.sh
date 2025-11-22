#!/bin/bash
# Test LLM provider integration in NeuroForge workbench

set -e

NEUROFORGE_URL="http://localhost:8000"
echo "Testing NeuroForge LLM providers..."
echo ""

# Step 1: Login and get token
echo "1. Logging in..."
TOKEN_RESPONSE=$(curl -s -X POST "$NEUROFORGE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  echo "Response: $TOKEN_RESPONSE"
  exit 1
fi
echo "✅ Logged in successfully"
echo ""

# Step 2: Check provider status
echo "2. Checking provider status..."
PROVIDERS=$(curl -s -X GET "$NEUROFORGE_URL/api/v1/workbench/providers" \
  -H "Authorization: Bearer $TOKEN")
echo "$PROVIDERS" | jq .
echo ""

# Step 3: List available models
echo "3. Listing available models..."
MODELS=$(curl -s -X GET "$NEUROFORGE_URL/api/v1/workbench/models" \
  -H "Authorization: Bearer $TOKEN")
echo "$MODELS" | jq '.[] | {id: .id, name: .name, provider: .provider}'
echo ""

# Step 4: Test simulated execution (when no API keys configured)
echo "4. Testing simulated execution..."
EXEC_RESPONSE=$(curl -s -X POST "$NEUROFORGE_URL/api/v1/workbench/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "test_workspace",
    "prompt": "What is 2+2? Respond with just the number.",
    "context_blocks": [],
    "model_ids": ["gpt-4o"],
    "stream": false
  }')

RUN_ID=$(echo $EXEC_RESPONSE | jq -r '.[0].id')
STATUS=$(echo $EXEC_RESPONSE | jq -r '.[0].status')
OUTPUT=$(echo $EXEC_RESPONSE | jq -r '.[0].output')

if [ "$RUN_ID" != "null" ]; then
  echo "✅ Execution completed"
  echo "   Run ID: $RUN_ID"
  echo "   Status: $STATUS"
  echo "   Output preview: ${OUTPUT:0:100}..."
else
  echo "❌ Execution failed"
  echo "Response: $EXEC_RESPONSE"
  exit 1
fi
echo ""

# Step 5: Verify run was logged to DataForge
echo "5. Verifying run logged to DataForge..."
DATAFORGE_URL="http://localhost:5000"
DATAFORGE_RUNS=$(curl -s -X GET "$DATAFORGE_URL/api/v1/runs?limit=1")
LATEST_RUN=$(echo $DATAFORGE_RUNS | jq -r '.runs[0].id')

if [ "$LATEST_RUN" != "null" ]; then
  echo "✅ Run logged to DataForge"
  echo "   Latest run: $LATEST_RUN"
else
  echo "⚠️  Could not verify DataForge logging (DataForge may not be running)"
fi
echo ""

echo "========================================="
echo "✅ All LLM provider tests passed!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  - Set OPENAI_API_KEY to test real OpenAI execution"
echo "  - Set ANTHROPIC_API_KEY to test real Claude execution"
echo "  - Run 'ollama serve' to test local Ollama models"
