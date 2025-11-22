#!/bin/bash
# End-to-End Authentication Integration Test
# Tests the complete authentication flow: Backend → Frontend → API Calls

set -e

echo "=========================================="
echo "E2E Authentication Integration Test"
echo "=========================================="
echo ""

# Configuration
NEUROFORGE_URL="http://localhost:8000"
DATAFORGE_URL="http://localhost:5000"
FRONTEND_URL="http://localhost:5173"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

# Test 1: Check all services are running
echo "Test 1: Verify all services are running"
echo "----------------------------------------"

if curl -s "$NEUROFORGE_URL/health" > /dev/null 2>&1; then
    pass_test "NeuroForge backend is running"
else
    fail_test "NeuroForge backend is not running"
    echo "Please start NeuroForge: cd NeuroForge && source venv/bin/activate && uvicorn workbench_app:app --port 8000"
    exit 1
fi

if curl -s "$DATAFORGE_URL/health" > /dev/null 2>&1; then
    pass_test "DataForge backend is running"
else
    fail_test "DataForge backend is not running"
    echo "Please start DataForge"
    exit 1
fi

if curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
    pass_test "Frontend dev server is running"
else
    fail_test "Frontend dev server is not running"
    echo "Please start frontend: cd vibeforge && pnpm dev"
    exit 1
fi

echo ""

# Test 2: Test authentication endpoints
echo "Test 2: Authentication Endpoints"
echo "----------------------------------------"

# Test 2a: Login with valid credentials
info "Testing login with valid credentials..."
LOGIN_RESPONSE=$(curl -s -X POST "$NEUROFORGE_URL/api/v1/auth/login/json" \
    -H "Content-Type: application/json" \
    -d '{"username": "testuser", "password": "testpass"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    pass_test "Login returns JWT token"
    info "Token: ${TOKEN:0:30}..."
else
    fail_test "Login did not return valid token"
    echo "Response: $LOGIN_RESPONSE"
fi

# Test 2b: Test invalid credentials
info "Testing login with invalid credentials..."
INVALID_LOGIN=$(curl -s -w "\n%{http_code}" -X POST "$NEUROFORGE_URL/api/v1/auth/login/json" \
    -H "Content-Type: application/json" \
    -d '{"username": "", "password": ""}')
HTTP_CODE=$(echo "$INVALID_LOGIN" | tail -1)
if [ "$HTTP_CODE" == "401" ]; then
    pass_test "Invalid credentials correctly rejected (401)"
else
    fail_test "Invalid credentials not rejected properly (got $HTTP_CODE)"
fi

echo ""

# Test 3: Test protected endpoints
echo "Test 3: Protected Endpoint Access Control"
echo "----------------------------------------"

# Test 3a: Access without authentication
info "Testing access without authentication..."
UNAUTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$NEUROFORGE_URL/api/v1/workbench/chains")
HTTP_CODE=$(echo "$UNAUTH_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "401" ]; then
    pass_test "Unauthenticated request rejected (401)"
else
    fail_test "Unauthenticated request not rejected (got $HTTP_CODE)"
fi

# Test 3b: Access with invalid token
info "Testing access with invalid token..."
INVALID_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" "$NEUROFORGE_URL/api/v1/workbench/chains" \
    -H "Authorization: Bearer invalid_token_here")
HTTP_CODE=$(echo "$INVALID_TOKEN_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "401" ]; then
    pass_test "Invalid token rejected (401)"
else
    fail_test "Invalid token not rejected (got $HTTP_CODE)"
fi

# Test 3c: Access with valid JWT token
info "Testing access with valid JWT token..."
VALID_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" "$NEUROFORGE_URL/api/v1/workbench/chains" \
    -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$VALID_TOKEN_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Valid JWT token grants access (200)"
else
    fail_test "Valid JWT token did not grant access (got $HTTP_CODE)"
fi

# Test 3d: Backward compatibility with x-user-id
info "Testing backward compatibility (x-user-id header)..."
XUSER_RESPONSE=$(curl -s -w "\n%{http_code}" "$NEUROFORGE_URL/api/v1/workbench/chains" \
    -H "x-user-id: testuser")
HTTP_CODE=$(echo "$XUSER_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "200" ]; then
    pass_test "x-user-id header backward compatibility works"
else
    fail_test "x-user-id header not working (got $HTTP_CODE)"
fi

echo ""

# Test 4: Test CRUD operations with authentication
echo "Test 4: Authenticated CRUD Operations"
echo "----------------------------------------"

# Test 4a: Create a chain with JWT
info "Creating chain with JWT authentication..."
CREATE_RESPONSE=$(curl -s -X POST "$NEUROFORGE_URL/api/v1/workbench/chains" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "E2E Auth Test Chain",
        "nodes": [{"id": "n1", "prompt_id": "p1", "prompt_name": "Test", "x": 0, "y": 0}],
        "connections": []
    }')

CHAIN_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
if [ -n "$CHAIN_ID" ] && [ "$CHAIN_ID" != "null" ]; then
    pass_test "Chain created with JWT authentication"
    info "Chain ID: $CHAIN_ID"
else
    fail_test "Failed to create chain"
    echo "Response: $CREATE_RESPONSE"
fi

# Test 4b: Retrieve the chain
if [ -n "$CHAIN_ID" ] && [ "$CHAIN_ID" != "null" ]; then
    info "Retrieving chain with JWT authentication..."
    RETRIEVE_RESPONSE=$(curl -s "$NEUROFORGE_URL/api/v1/workbench/chains/$CHAIN_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    RETRIEVED_NAME=$(echo "$RETRIEVE_RESPONSE" | jq -r '.name')
    if [ "$RETRIEVED_NAME" == "E2E Auth Test Chain" ]; then
        pass_test "Chain retrieved successfully"
    else
        fail_test "Failed to retrieve chain"
        echo "Response: $RETRIEVE_RESPONSE"
    fi
fi

echo ""

# Test 5: Test rate limiting
echo "Test 5: Rate Limiting"
echo "----------------------------------------"

info "Testing rate limiting (5 requests per minute)..."
RATE_LIMIT_TRIGGERED=false

for i in {1..7}; do
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$NEUROFORGE_URL/api/v1/auth/login/json" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"ratelimit_test_$i\", \"password\": \"test\"}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    
    if [ "$HTTP_CODE" == "429" ]; then
        RATE_LIMIT_TRIGGERED=true
        break
    fi
    
    sleep 0.5
done

if [ "$RATE_LIMIT_TRIGGERED" == "true" ]; then
    pass_test "Rate limiting working (429 after 5 requests)"
else
    fail_test "Rate limiting not triggered"
fi

echo ""

# Test 6: Test security configuration
echo "Test 6: Security Configuration"
echo "----------------------------------------"

# Check logs for security warnings
info "Checking for security warnings in logs..."
if [ -f "NeuroForge/workbench.log" ]; then
    if grep -q "Using development SECRET_KEY" NeuroForge/workbench.log; then
        pass_test "Security warning present for development SECRET_KEY"
    else
        info "No development SECRET_KEY warning (may be using production key)"
    fi
fi

# Verify environment configuration
if [ -f "NeuroForge/.env.example" ]; then
    pass_test "Environment configuration template exists"
else
    fail_test "Missing .env.example file"
fi

echo ""

# Test 7: Frontend integration
echo "Test 7: Frontend Integration"
echo "----------------------------------------"

info "Checking frontend files..."

if [ -f "vibeforge/src/lib/auth.ts" ]; then
    pass_test "Frontend auth service exists"
else
    fail_test "Missing frontend auth service"
fi

if [ -f "vibeforge/src/routes/login/+page.svelte" ]; then
    pass_test "Login page component exists"
else
    fail_test "Missing login page component"
fi

# Check if frontend can reach backend
info "Testing frontend → backend connectivity..."
CORS_TEST=$(curl -s -X OPTIONS "$NEUROFORGE_URL/api/v1/auth/login/json" \
    -H "Origin: $FRONTEND_URL" \
    -H "Access-Control-Request-Method: POST" \
    -w "\n%{http_code}")
HTTP_CODE=$(echo "$CORS_TEST" | tail -1)

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "204" ]; then
    pass_test "CORS configured correctly"
else
    info "CORS preflight returned $HTTP_CODE (may need configuration)"
fi

echo ""

# Test 8: Data persistence
echo "Test 8: Data Persistence"
echo "----------------------------------------"

info "Verifying data persists in DataForge..."
DATAFORGE_RUNS=$(curl -s "$DATAFORGE_URL/api/v1/runs" -H "x-user-id: testuser")
RUN_COUNT=$(echo "$DATAFORGE_RUNS" | jq 'length')

if [ "$RUN_COUNT" -gt 0 ]; then
    pass_test "Data persisted in DataForge ($RUN_COUNT runs)"
else
    fail_test "No data found in DataForge"
fi

echo ""

# Final Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Authentication system is fully functional:"
    echo "  • JWT authentication working"
    echo "  • Protected endpoints secured"
    echo "  • Rate limiting active"
    echo "  • CRUD operations authenticated"
    echo "  • Frontend integration ready"
    echo "  • Data persistence verified"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo "Please review the failures above and fix the issues."
    echo ""
    exit 1
fi
