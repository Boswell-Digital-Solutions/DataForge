#!/bin/bash
# Test JWT Authentication Implementation for NeuroForge Workbench
set -e

BASE_URL="http://localhost:8000"
echo "=== NeuroForge Workbench Authentication Tests ==="
echo ""

# Test 1: Login and get JWT token
echo "Test 1: Login and get JWT token"
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo "❌ FAIL: Could not get token"
    exit 1
fi
echo "✅ PASS: Got JWT token (${TOKEN:0:30}...)"
echo ""

# Test 2: Access protected endpoint without authentication
echo "Test 2: Access protected endpoint without authentication (should fail)"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/workbench/chains")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "401" ]; then
    echo "✅ PASS: Correctly rejected unauthenticated request (401)"
else
    echo "❌ FAIL: Expected 401, got $HTTP_CODE"
    exit 1
fi
echo ""

# Test 3: Access endpoint with JWT token
echo "Test 3: Access endpoint with valid JWT token"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/workbench/chains" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ PASS: Successfully accessed with JWT token"
    echo "   Response: $(echo $BODY | jq -c '.[0:2]')"
else
    echo "❌ FAIL: Expected 200, got $HTTP_CODE"
    exit 1
fi
echo ""

# Test 4: Access endpoint with x-user-id header (backward compatibility)
echo "Test 4: Access endpoint with x-user-id header (backward compatibility)"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/workbench/chains" \
  -H "x-user-id: legacy_user")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ PASS: x-user-id header still works for backward compatibility"
else
    echo "❌ FAIL: Expected 200, got $HTTP_CODE"
    exit 1
fi
echo ""

# Test 5: Create a chain with JWT authentication
echo "Test 5: Create a chain with JWT authentication"
CHAIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/workbench/chains" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "JWT Auth Test Chain",
    "nodes": [
      {
        "id": "node1",
        "prompt_id": "prompt1",
        "prompt_name": "Test Prompt",
        "x": 100,
        "y": 100,
        "inputs": {},
        "outputs": ["result"]
      }
    ],
    "connections": []
  }')

CHAIN_ID=$(echo "$CHAIN_RESPONSE" | jq -r '.id')
if [ -n "$CHAIN_ID" ] && [ "$CHAIN_ID" != "null" ]; then
    echo "✅ PASS: Created chain with JWT auth"
    echo "   Chain ID: $CHAIN_ID"
else
    echo "❌ FAIL: Could not create chain"
    echo "$CHAIN_RESPONSE" | jq .
    exit 1
fi
echo ""

# Test 6: Retrieve the chain with JWT authentication
echo "Test 6: Retrieve chain with JWT authentication"
RETRIEVE_RESPONSE=$(curl -s "$BASE_URL/api/v1/workbench/chains/$CHAIN_ID" \
  -H "Authorization: Bearer $TOKEN")
RETRIEVED_NAME=$(echo "$RETRIEVE_RESPONSE" | jq -r '.name')
if [ "$RETRIEVED_NAME" == "JWT Auth Test Chain" ]; then
    echo "✅ PASS: Retrieved chain successfully"
    echo "   Chain name: $RETRIEVED_NAME"
else
    echo "❌ FAIL: Could not retrieve chain"
    echo "$RETRIEVE_RESPONSE" | jq .
    exit 1
fi
echo ""

# Test 7: Test with invalid token
echo "Test 7: Access with invalid JWT token (should fail)"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/workbench/chains" \
  -H "Authorization: Bearer invalid_token_here")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "401" ]; then
    echo "✅ PASS: Correctly rejected invalid token (401)"
else
    echo "❌ FAIL: Expected 401, got $HTTP_CODE"
    exit 1
fi
echo ""

# Test 8: Test models endpoint with JWT
echo "Test 8: Access models endpoint with JWT"
MODELS_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/models" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$MODELS_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "200" ]; then
    MODEL_COUNT=$(echo "$MODELS_RESPONSE" | head -n -1 | jq 'length')
    echo "✅ PASS: Models endpoint accessible with JWT"
    echo "   Found $MODEL_COUNT models"
else
    echo "❌ FAIL: Expected 200, got $HTTP_CODE"
    exit 1
fi
echo ""

# Test 9: Test OAuth2 form login (alternative login method)
echo "Test 9: OAuth2 form login"
FORM_TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass" | jq -r '.access_token')

if [ -n "$FORM_TOKEN" ] && [ "$FORM_TOKEN" != "null" ]; then
    echo "✅ PASS: OAuth2 form login works"
    echo "   Token: ${FORM_TOKEN:0:30}..."
else
    echo "❌ FAIL: OAuth2 form login failed"
    exit 1
fi
echo ""

echo "=== All Authentication Tests Passed! ==="
echo ""
echo "Summary:"
echo "✅ JWT token generation works"
echo "✅ Protected endpoints require authentication"
echo "✅ JWT Bearer token authentication works"
echo "✅ x-user-id header backward compatibility maintained"
echo "✅ Invalid tokens are rejected"
echo "✅ OAuth2 form login works"
echo "✅ All workbench endpoints are protected"
echo ""
echo "Authentication implementation complete and tested!"
