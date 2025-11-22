#!/bin/bash
# End-to-End Integration Test for VibeForge Architecture
# Tests: Frontend → NeuroForge → DataForge

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  VibeForge V2 - Full Stack Integration Test              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function
test_endpoint() {
    local name="$1"
    local url="$2"
    local headers="$3"
    local expected_status="$4"
    
    echo -e "${BLUE}Testing:${NC} $name"
    status=$(curl -s -o /dev/null -w "%{http_code}" $headers "$url")
    
    if [ "$status" == "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $status)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $status)"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Service Health Checks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# DataForge
test_endpoint "DataForge Health" \
    "http://localhost:5000/health" \
    "" \
    "200"

# NeuroForge
test_endpoint "NeuroForge Models" \
    "http://localhost:8000/api/v1/models" \
    "-H 'x-user-id: test'" \
    "200"

# VibeForge Frontend
test_endpoint "VibeForge Frontend" \
    "http://localhost:5174/" \
    "" \
    "200"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. NeuroForge API Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

api_status=$(curl -s -H "x-user-id: test" http://localhost:8000/api/v1/api-status)
echo "$api_status" | python3 -m json.tool
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Execute Test Prompt (NeuroForge → DataForge)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

WORKSPACE_ID="e2e_test_$(date +%s)"
echo "Workspace: $WORKSPACE_ID"
echo ""

execution_result=$(curl -s -X POST http://localhost:8000/api/v1/execute \
  -H "Content-Type: application/json" \
  -H "x-user-id: e2e_test" \
  -d "{
    \"workspace_id\": \"$WORKSPACE_ID\",
    \"prompt\": \"Write a one-sentence description of what makes a good API design\",
    \"context_blocks\": [],
    \"model_ids\": [\"gpt-3.5-turbo\"],
    \"stream\": false
  }")

if echo "$execution_result" | grep -q "\"status\":\"completed\""; then
    echo -e "${GREEN}✓ Execution completed${NC}"
    run_id=$(echo "$execution_result" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")
    echo "Run ID: $run_id"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ Execution failed${NC}"
    echo "$execution_result" | python3 -m json.tool
    ((TESTS_FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Verify Persistence in DataForge"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sleep 1
runs=$(curl -s "http://localhost:5000/api/v1/runs?workspace_id=$WORKSPACE_ID" \
  -H "x-user-id: e2e_test")

run_count=$(echo "$runs" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])")

if [ "$run_count" -gt "0" ]; then
    echo -e "${GREEN}✓ Run persisted in DataForge${NC}"
    echo "Total runs in workspace: $run_count"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ Run not found in DataForge${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Multi-Model Execution Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

multi_result=$(curl -s -X POST http://localhost:8000/api/v1/execute \
  -H "Content-Type: application/json" \
  -H "x-user-id: e2e_test" \
  -d "{
    \"workspace_id\": \"$WORKSPACE_ID\",
    \"prompt\": \"List 3 benefits of microservices\",
    \"context_blocks\": [],
    \"model_ids\": [\"gpt-4o\", \"claude-3.5-haiku\"],
    \"stream\": false
  }")

completed_count=$(echo "$multi_result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for r in data if r['status']=='completed'))")

if [ "$completed_count" == "2" ]; then
    echo -e "${GREEN}✓ Both models executed successfully${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ Multi-model execution failed${NC}"
    echo "Completed: $completed_count / 2"
    ((TESTS_FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Architecture Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}Architecture:${NC}"
echo "  VibeForge (Frontend)  → http://localhost:5174"
echo "       ↓ HTTP API"
echo "  NeuroForge (Compute)  → http://localhost:8000"
echo "       ↓ POST /api/v1/runs"
echo "  DataForge (Data)      → http://localhost:5000"
echo ""

# Verify stateless NeuroForge
echo -e "${BLUE}Stateless Test:${NC} Restart NeuroForge and verify data persists"
pkill -f test_prompt_api
sleep 1
cd /home/charles/projects/Coding2025/Forge/NeuroForge && ./venv/bin/python test_prompt_api.py &> /tmp/neuroforge_restart.log &
sleep 2

runs_after_restart=$(curl -s "http://localhost:5000/api/v1/runs?workspace_id=$WORKSPACE_ID" \
  -H "x-user-id: e2e_test" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])")

if [ "$runs_after_restart" -gt "0" ]; then
    echo -e "${GREEN}✓ Data persisted after NeuroForge restart${NC}"
    echo "Runs still available: $runs_after_restart"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ Data lost after restart${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  TEST SUMMARY                                             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "Full stack is operational:"
    echo "  • VibeForge frontend: Ready"
    echo "  • NeuroForge compute: Ready (LLM execution)"
    echo "  • DataForge persistence: Ready (PostgreSQL)"
    echo "  • End-to-end flow: Verified"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    exit 1
fi
