#!/bin/bash
# Test Languages API

set -e

echo "======================================"
echo "Languages API Test Suite"
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
        response=$(curl -s -L -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -L "$BASE_URL$endpoint")
    fi
    
    if echo "$response" | jq -e '.success == true' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        pass_count=$((pass_count + 1))
        echo "$response" | jq '.'
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "$response" | jq '.' || echo "$response"
    fi
    echo ""
}

# Test 1: List all languages
run_test "List All Languages" "/api/v1/languages"

# Test 2: Get categories
run_test "Get Language Categories" "/api/v1/languages/categories"

# Test 3: Get specific language
run_test "Get Python Language" "/api/v1/languages/python"

# Test 4: Filter by category
run_test "Filter by Frontend Category" "/api/v1/languages?category=frontend"

# Test 5: Filter stacks by languages (Python + TypeScript)
run_test "Filter Stacks: Python + TS" "/api/v1/languages/filter-stacks" "POST" '{
  "languages": ["python", "javascript-typescript"],
  "require_all": false
}'

# Test 6: Filter stacks requiring all languages
run_test "Filter Stacks: Require All" "/api/v1/languages/filter-stacks" "POST" '{
  "languages": ["python", "javascript-typescript"],
  "require_all": true
}'

# Test 7: Language recommendations for web project
run_test "Recommend for Web Project" "/api/v1/languages/recommend" "POST" '{
  "project_type": "web",
  "requirements": {}
}'

# Test 8: Language recommendations for mobile project
run_test "Recommend for Mobile Project" "/api/v1/languages/recommend" "POST" '{
  "project_type": "mobile"
}'

# Test 9: Language recommendations for AI project
run_test "Recommend for AI Project" "/api/v1/languages/recommend" "POST" '{
  "project_type": "ai"
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
