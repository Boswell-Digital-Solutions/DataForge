#!/bin/bash
# Test Stack Profiles API

set -e

echo "======================================"
echo "Stack Profiles API Test Suite"
echo "======================================"
echo ""

BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_count=0
pass_count=0

run_test() {
    local name="$1"
    local endpoint="$2"
    local method="${3:-GET}"
    local data="${4:-}"
    
    test_count=$((test_count + 1))
    echo -e "${BLUE}Test $test_count: $name${NC}"
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s "$BASE_URL$endpoint")
    fi
    
    if echo "$response" | jq -e '.success == true' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        pass_count=$((pass_count + 1))
        echo "$response" | jq '.'
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "$response" | jq '.'
    fi
    echo ""
}

# Test 1: List all stacks
run_test "List All Stacks" "/api/v1/stacks"

# Test 2: Get popular stacks
run_test "Get Popular Stacks" "/api/v1/stacks/popular?limit=3"

# Test 3: Get categories
run_test "Get Categories" "/api/v1/stacks/categories"

# Test 4: Get specific stack
run_test "Get T3 Stack" "/api/v1/stacks/t3-stack"

# Test 5: Filter by category
run_test "Filter by Web Category" "/api/v1/stacks?category=web"

# Test 6: Search stacks
run_test "Search for 'react'" "/api/v1/stacks?search=react"

# Test 7: Get alternatives
run_test "Get Alternatives for T3" "/api/v1/stacks/t3-stack/alternatives"

# Test 8: Compare stacks
run_test "Compare T3 vs MERN" "/api/v1/stacks/t3-stack/compare/mern-stack"

# Test 9: Get recommendations
run_test "Get Recommendations" "/api/v1/stacks/recommend" "POST" '{
  "project_intent": {
    "goal": "Build a modern web application",
    "description": "I want to build a SaaS application with TypeScript"
  },
  "requirements": {
    "category": "web",
    "complexity": "intermediate",
    "time_to_market": "fast"
  }
}'

echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "Total: $test_count"
echo -e "${GREEN}Passed: $pass_count${NC}"
echo -e "${RED}Failed: $((test_count - pass_count))${NC}"
echo ""

if [ $pass_count -eq $test_count ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
