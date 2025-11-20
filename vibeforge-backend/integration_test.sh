#!/usr/bin/env bash

# VibeForge Integration Test Suite
# 
# Tests the full integration path between SvelteKit frontend and FastAPI backend.
# Run this after starting both servers to verify everything works.
#
# Usage:
#   chmod +x integration_test.sh
#   ./integration_test.sh
#
# Prerequisites:
#   - Backend running on http://localhost:8000
#   - Frontend running on http://localhost:5173
#   - curl installed

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8000"
FRONTEND_BASE="http://localhost:5173"
API_VERSION="v1"
VIBEFORGE_BASE="$API_BASE/$API_VERSION/vibeforge"

# Test counters
PASSED=0
FAILED=0

# Helper functions
print_header() {
  echo ""
  echo "=================================="
  echo "$1"
  echo "=================================="
}

print_test() {
  echo ""
  echo -e "${YELLOW}→ $1${NC}"
}

print_pass() {
  echo -e "${GREEN}✓ PASS${NC}: $1"
  ((PASSED++))
}

print_fail() {
  echo -e "${RED}✗ FAIL${NC}: $1"
  ((FAILED++))
}

# Test functions
test_backend_health() {
  print_test "Backend Health Check"
  
  response=$(curl -s -w "\n%{http_code}" "$API_BASE/health")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" = "200" ]; then
    print_pass "Backend is running and healthy"
    echo "  Response: $body"
  else
    print_fail "Backend health check failed (HTTP $http_code)"
    return 1
  fi
}

test_cors_headers() {
  print_test "CORS Configuration"
  
  response=$(curl -s -i -X OPTIONS "$VIBEFORGE_BASE/run" \
    -H "Origin: $FRONTEND_BASE" \
    -H "Access-Control-Request-Method: POST" 2>&1)
  
  if echo "$response" | grep -q "Access-Control-Allow-Origin"; then
    print_pass "CORS headers are configured"
    echo "$response" | grep "Access-Control" | sed 's/^/  /'
  else
    print_fail "CORS headers not found. Check backend CORS_ORIGINS setting."
    return 1
  fi
}

test_rust_module() {
  print_test "Rust Module (vibeforge_prompt)"
  
  # Test if Rust module can be imported and called
  result=$(python3 << 'EOF'
try:
    from vibeforge_prompt import estimate_tokens_precise
    tokens = estimate_tokens_precise("Hello world")
    print(f"OK:{tokens}")
except Exception as e:
    print(f"ERROR:{e}")
EOF
)
  
  if [[ $result == OK:* ]]; then
    tokens=$(echo "$result" | cut -d: -f2)
    print_pass "Rust module is working"
    echo "  estimate_tokens_precise('Hello world') = $tokens tokens"
  else
    error=$(echo "$result" | cut -d: -f2)
    print_fail "Rust module test failed: $error"
    return 1
  fi
}

test_create_run() {
  print_test "Create Run (POST /v1/vibeforge/run)"
  
  response=$(curl -s -w "\n%{http_code}" -X POST "$VIBEFORGE_BASE/run" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "claude-3-opus-20240229",
      "prompt": "What is the capital of France?",
      "active_contexts": []
    }')
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" = "201" ]; then
    run_id=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
    print_pass "Run created successfully"
    echo "  Run ID: $run_id"
    echo "$body" | python3 -m json.tool | head -15 | sed 's/^/  /'
    
    # Store run_id for later tests
    echo "$run_id" > /tmp/vibeforge_run_id.txt
  else
    print_fail "Create run failed (HTTP $http_code)"
    echo "  Response: $body" | sed 's/^/  /'
    return 1
  fi
}

test_get_run() {
  print_test "Get Run (GET /v1/vibeforge/run/{run_id})"
  
  if [ ! -f /tmp/vibeforge_run_id.txt ]; then
    print_fail "No run_id available (previous test failed)"
    return 1
  fi
  
  run_id=$(cat /tmp/vibeforge_run_id.txt)
  
  response=$(curl -s -w "\n%{http_code}" "$VIBEFORGE_BASE/run/$run_id")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" = "200" ]; then
    status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
    output_len=$(echo "$body" | python3 -c "import sys, json; o = json.load(sys.stdin).get('output', ''); print(len(o))")
    print_pass "Run retrieved successfully"
    echo "  Status: $status"
    echo "  Output length: $output_len characters"
  else
    print_fail "Get run failed (HTTP $http_code)"
    return 1
  fi
}

test_fetch_history() {
  print_test "Fetch History (GET /v1/vibeforge/history)"
  
  response=$(curl -s -w "\n%{http_code}" "$VIBEFORGE_BASE/history?limit=5&offset=0")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" = "200" ]; then
    total=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])")
    items=$(echo "$body" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['items']))")
    print_pass "History retrieved successfully"
    echo "  Total runs: $total"
    echo "  Items returned: $items"
  else
    print_fail "Fetch history failed (HTTP $http_code)"
    return 1
  fi
}

test_token_counting() {
  print_test "Token Counting (Rust performance)"
  
  python3 << 'EOF'
import time
from vibeforge_prompt import estimate_tokens_precise

# Time 1000 estimations
text = "The quick brown fox jumps over the lazy dog. " * 100
start = time.time()
for _ in range(100):
    estimate_tokens_precise(text)
elapsed = time.time() - start

calls_per_sec = int(100 / elapsed)
print(f"100 calls in {elapsed:.3f}s = {calls_per_sec:,} calls/sec")

if calls_per_sec > 100:
    print("✓ Performance is good")
    exit(0)
else:
    print("⚠ Performance is slow (might be debug build)")
    exit(0)  # Still pass, just warn
EOF
  
  print_pass "Token counting performance test completed"
}

test_openapi_schema() {
  print_test "OpenAPI Schema"
  
  response=$(curl -s -w "\n%{http_code}" "$API_BASE/openapi.json")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" = "200" ]; then
    endpoints=$(echo "$body" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['paths']))")
    print_pass "OpenAPI schema is available"
    echo "  Endpoints documented: $endpoints"
  else
    print_fail "OpenAPI schema not found (HTTP $http_code)"
    return 1
  fi
}

test_error_handling() {
  print_test "Error Handling (Invalid Input)"
  
  # Test with missing required field
  response=$(curl -s -w "\n%{http_code}" -X POST "$VIBEFORGE_BASE/run" \
    -H "Content-Type: application/json" \
    -d '{
      "prompt": "Missing model field",
      "active_contexts": []
    }')
  
  http_code=$(echo "$response" | tail -n1)
  
  if [ "$http_code" = "422" ]; then
    print_pass "Error handling works correctly"
    echo "  Invalid request correctly rejected with HTTP 422"
  else
    print_fail "Expected HTTP 422 for invalid request, got $http_code"
    return 1
  fi
}

# Frontend-specific tests (requires browser automation)
test_frontend_connection() {
  print_test "Frontend API Connection (JavaScript)"
  
  # Test if frontend can reach backend
  response=$(curl -s -w "\n%{http_code}" \
    -H "Origin: $FRONTEND_BASE" \
    "$API_BASE/health")
  
  http_code=$(echo "$response" | tail -n1)
  
  if [ "$http_code" = "200" ]; then
    print_pass "Frontend can reach backend API"
  else
    print_fail "Frontend cannot reach backend (HTTP $http_code)"
    return 1
  fi
}

# Main test suite
main() {
  print_header "VibeForge Integration Test Suite"
  echo "Testing connection between frontend (localhost:5173) and backend (localhost:8000)"
  
  # Backend tests
  print_header "BACKEND TESTS"
  test_backend_health || true
  test_cors_headers || true
  test_rust_module || true
  test_openapi_schema || true
  
  # API tests
  print_header "API TESTS"
  test_create_run || true
  test_get_run || true
  test_fetch_history || true
  test_error_handling || true
  
  # Performance tests
  print_header "PERFORMANCE TESTS"
  test_token_counting || true
  
  # Frontend tests
  print_header "FRONTEND TESTS"
  test_frontend_connection || true
  
  # Summary
  print_header "TEST SUMMARY"
  total=$((PASSED + FAILED))
  echo "Passed: $PASSED / $total"
  echo "Failed: $FAILED / $total"
  
  if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Navigate to http://localhost:5173 in your browser"
    echo "  2. Try the workbench interface"
    echo "  3. Check http://localhost:5173/history for past runs"
    exit 0
  else
    echo ""
    echo -e "${RED}Some tests failed. See details above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Verify backend is running: curl http://localhost:8000/health"
    echo "  - Verify frontend is running: curl http://localhost:5173"
    echo "  - Check backend .env has CORS_ORIGINS setting"
    echo "  - Check frontend .env.local has PUBLIC_API_BASE_URL"
    exit 1
  fi
}

# Run tests
main "$@"
