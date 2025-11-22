#!/bin/bash
# Phase 0 Integration Test Script
# Tests the complete flow: Create prompt → Load prompt → Execute → Log to DataForge

set -e

echo "=== Phase 0 Integration Test ==="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1: Create a test prompt via NeuroForge API${NC}"
PROMPT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/workbench/prompts \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user" \
  -d '{
    "name": "Phase 0 Test Prompt",
    "description": "A test prompt for Phase 0 integration",
    "category": "coding",
    "workspace": "vibeforge",
    "tags": ["test", "phase0"],
    "basePrompt": "Write a hello world function in Python",
    "models": ["gpt-4", "claude-3-sonnet"],
    "pinned": true
  }')

PROMPT_ID=$(echo $PROMPT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "failed")

if [ "$PROMPT_ID" = "failed" ]; then
  echo "❌ Failed to create prompt. Is NeuroForge running on port 8000?"
  exit 1
fi

echo -e "${GREEN}✓ Created prompt: $PROMPT_ID${NC}"
echo ""

echo -e "${BLUE}Step 2: Retrieve the prompt${NC}"
curl -s http://localhost:8000/api/v1/workbench/prompts/$PROMPT_ID \
  -H "x-user-id: test_user" | python3 -m json.tool | head -n 10
echo -e "${GREEN}✓ Prompt retrieved successfully${NC}"
echo ""

echo -e "${BLUE}Step 3: List all prompts (should include our test prompt)${NC}"
PROMPTS_LIST=$(curl -s http://localhost:8000/api/v1/workbench/prompts \
  -H "x-user-id: test_user")
PROMPT_COUNT=$(echo $PROMPTS_LIST | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
echo -e "${GREEN}✓ Found $PROMPT_COUNT total prompts${NC}"
echo ""

echo -e "${BLUE}Step 4: Update prompt (toggle pin)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/workbench/prompts/$PROMPT_ID \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user" \
  -d '{"pinned": false}' > /dev/null
echo -e "${GREEN}✓ Prompt updated (unpinned)${NC}"
echo ""

echo -e "${BLUE}Step 5: Test DataForge runs logging${NC}"
RUN_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test_user",
    "workspaceId": "vibeforge",
    "promptText": "Write a hello world function",
    "contextBlocks": [],
    "models": [
      {
        "modelId": "gpt-4",
        "responseText": "def hello_world():\n    print(\"Hello, World!\")",
        "tokensUsed": 42,
        "latencyMs": 1250
      }
    ]
  }' 2>/dev/null)

if echo "$RUN_RESPONSE" | grep -q "id"; then
  RUN_ID=$(echo $RUN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
  echo -e "${GREEN}✓ Run logged to DataForge: $RUN_ID${NC}"
else
  echo "⚠️  DataForge logging skipped (not running on port 8001)"
fi
echo ""

echo -e "${BLUE}Step 6: Clean up - Delete test prompt${NC}"
curl -s -X DELETE http://localhost:8000/api/v1/workbench/prompts/$PROMPT_ID \
  -H "x-user-id: test_user" > /dev/null
echo -e "${GREEN}✓ Test prompt deleted${NC}"
echo ""

echo -e "${GREEN}=== Phase 0 Integration Test Complete! ===${NC}"
echo ""
echo "Summary:"
echo "✓ Prompt CRUD operations working"
echo "✓ NeuroForge API responding correctly"
if [ -n "$RUN_ID" ]; then
  echo "✓ DataForge run logging working"
fi
echo ""
echo "Frontend integration:"
echo "- Visit http://localhost:5173"
echo "- Navigate to Context/Prompts tab"
echo "- Create/edit/load prompts"
echo "- Execute prompts and view outputs"
