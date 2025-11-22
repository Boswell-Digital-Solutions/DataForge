#!/bin/bash
echo "=== End-to-End Authentication Test ==="
echo ""

# Test 1: Login and get token
echo "1. Testing login endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"username": "e2e_test_user", "password": "test123"}')

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "   ✅ Login successful - Token received"
    echo "   Token: ${TOKEN:0:40}..."
else
    echo "   ❌ Login failed"
    echo "   Response: $RESPONSE"
    exit 1
fi
echo ""

# Test 2: Access protected endpoint with token
echo "2. Testing protected endpoint with JWT..."
CHAINS=$(curl -s http://localhost:8000/api/v1/workbench/chains \
  -H "Authorization: Bearer $TOKEN")

if echo "$CHAINS" | jq . > /dev/null 2>&1; then
    COUNT=$(echo "$CHAINS" | jq 'length')
    echo "   ✅ Protected endpoint accessible with JWT"
    echo "   Found $COUNT chains"
else
    echo "   ❌ Failed to access protected endpoint"
    exit 1
fi
echo ""

# Test 3: Create a resource with JWT
echo "3. Creating a chain with JWT authentication..."
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/workbench/chains \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E2E Test Chain",
    "nodes": [{"id": "n1", "prompt_id": "p1", "prompt_name": "Test", "x": 0, "y": 0}],
    "connections": []
  }')

CHAIN_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
if [ -n "$CHAIN_ID" ] && [ "$CHAIN_ID" != "null" ]; then
    echo "   ✅ Chain created successfully"
    echo "   Chain ID: $CHAIN_ID"
else
    echo "   ❌ Failed to create chain"
    echo "   Response: $CREATE_RESPONSE"
    exit 1
fi
echo ""

# Test 4: Retrieve the resource
echo "4. Retrieving chain with JWT..."
RETRIEVE=$(curl -s http://localhost:8000/api/v1/workbench/chains/$CHAIN_ID \
  -H "Authorization: Bearer $TOKEN")

CHAIN_NAME=$(echo "$RETRIEVE" | jq -r '.name')
if [ "$CHAIN_NAME" = "E2E Test Chain" ]; then
    echo "   ✅ Chain retrieved successfully"
    echo "   Name: $CHAIN_NAME"
else
    echo "   ❌ Failed to retrieve chain"
    exit 1
fi
echo ""

# Test 5: Test without authentication (should fail)
echo "5. Testing endpoint without authentication..."
UNAUTH=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/v1/workbench/chains)
HTTP_CODE=$(echo "$UNAUTH" | tail -1)

if [ "$HTTP_CODE" = "401" ]; then
    echo "   ✅ Unauthenticated request properly rejected (401)"
else
    echo "   ❌ Should have rejected unauthenticated request"
    echo "   Got HTTP $HTTP_CODE"
    exit 1
fi
echo ""

echo "=== All E2E Tests Passed! ==="
echo ""
echo "Summary:"
echo "✅ JWT login working"
echo "✅ Protected endpoints accessible with token"
echo "✅ Resource creation with authentication"
echo "✅ Resource retrieval with authentication"
echo "✅ Unauthenticated requests rejected"
echo ""
echo "Full authentication system validated end-to-end! 🎉"
