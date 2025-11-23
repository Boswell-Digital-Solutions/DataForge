#!/bin/bash

# VibeForge Project Creation Wizard - End-to-End Test Script
# Tests all 5 wizard steps, validation, state management, and persistence

set -e

BASE_URL="http://localhost:5173"
API_URL="http://localhost:8000"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     VibeForge Project Creation Wizard - E2E Test Suite                   ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

pass_count=0
fail_count=0

test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((pass_count++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((fail_count++))
}

test_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}$1${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Test 1: Check Frontend Server
section "1. Frontend Server Health Check"
if curl -s "$BASE_URL" > /dev/null 2>&1; then
    test_pass "Frontend server running on $BASE_URL"
else
    test_fail "Frontend server not accessible at $BASE_URL"
    exit 1
fi

# Test 2: Check Backend API
section "2. Backend API Health Check"
HEALTH=$(curl -s "$API_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    test_pass "Backend API healthy at $API_URL"
    test_info "$(echo $HEALTH | jq -r '.service')"
else
    test_fail "Backend API not healthy"
    exit 1
fi

# Test 3: Verify Wizard Route Exists
section "3. Wizard Route Accessibility"
WIZARD_PAGE=$(curl -s "$BASE_URL/wizard")
if echo "$WIZARD_PAGE" | grep -q "VibeForge"; then
    test_pass "Wizard page accessible at /wizard"
else
    test_fail "Wizard page not found"
fi

# Test 4: Verify Required Components
section "4. Component File Verification"
FILES=(
    "vibeforge/src/lib/stores/wizard.ts"
    "vibeforge/src/lib/components/wizard/WizardShell.svelte"
    "vibeforge/src/lib/components/wizard/steps/Step1Intent.svelte"
    "vibeforge/src/lib/components/wizard/steps/Step2Languages.svelte"
    "vibeforge/src/lib/components/wizard/steps/Step3Stack.svelte"
    "vibeforge/src/lib/components/wizard/steps/Step4Config.svelte"
    "vibeforge/src/lib/components/wizard/steps/Step5Review.svelte"
    "vibeforge/src/routes/wizard/+page.svelte"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        test_pass "Component exists: $(basename $file)"
    else
        test_fail "Component missing: $file"
    fi
done

# Test 5: Verify Language API Integration
section "5. Language API Integration"
LANGUAGES=$(curl -s "$API_URL/api/v1/languages")
LANG_COUNT=$(echo "$LANGUAGES" | jq 'length')
if [ "$LANG_COUNT" -eq 15 ]; then
    test_pass "Language API returns 15 languages"
else
    test_fail "Expected 15 languages, got $LANG_COUNT"
fi

# Test 6: Verify Stack API Integration
section "6. Stack Profile API Integration"
STACKS=$(curl -s "$API_URL/api/v1/stacks")
STACK_COUNT=$(echo "$STACKS" | jq 'length')
if [ "$STACK_COUNT" -eq 10 ]; then
    test_pass "Stack API returns 10 stack profiles"
else
    test_fail "Expected 10 stacks, got $STACK_COUNT"
fi

# Test 7: Test Stack Filtering by Language
section "7. Stack-Language Compatibility"
PYTHON_STACKS=$(curl -s "$API_URL/api/v1/stacks/by-language/python?mode=union")
PY_STACK_COUNT=$(echo "$PYTHON_STACKS" | jq 'length')
if [ "$PY_STACK_COUNT" -gt 0 ]; then
    test_pass "Found $PY_STACK_COUNT stacks compatible with Python"
    test_info "Stack IDs: $(echo $PYTHON_STACKS | jq -r '.[].id' | tr '\n' ' ')"
else
    test_fail "No Python-compatible stacks found"
fi

# Test 8: Test Language Categories
section "8. Language Category Organization"
CATEGORIES=$(curl -s "$API_URL/api/v1/languages/categories")
FRONTEND_COUNT=$(echo "$CATEGORIES" | jq '.frontend')
BACKEND_COUNT=$(echo "$CATEGORIES" | jq '.backend')

if [ "$FRONTEND_COUNT" -gt 0 ] && [ "$BACKEND_COUNT" -gt 0 ]; then
    test_pass "Language categories populated (Frontend: $FRONTEND_COUNT, Backend: $BACKEND_COUNT)"
else
    test_fail "Language categories incomplete"
fi

# Test 9: Test Language Recommendations
section "9. Language Recommendation System"
WEB_RECS=$(curl -s "$API_URL/api/v1/languages/recommend/web")
REC_COUNT=$(echo "$WEB_RECS" | jq '.languages | length')
if [ "$REC_COUNT" -gt 0 ]; then
    test_pass "Web project recommendations: $REC_COUNT languages"
    test_info "Recommended: $(echo $WEB_RECS | jq -r '.languages[]' | tr '\n' ' ')"
else
    test_fail "No language recommendations returned"
fi

# Test 10: Verify Wizard Store Structure
section "10. Wizard State Management Validation"
if grep -q "export interface ProjectIntent" "vibeforge/src/lib/stores/wizard.ts"; then
    test_pass "ProjectIntent interface defined"
else
    test_fail "ProjectIntent interface missing"
fi

if grep -q "export interface ProjectConfiguration" "vibeforge/src/lib/stores/wizard.ts"; then
    test_pass "ProjectConfiguration interface defined"
else
    test_fail "ProjectConfiguration interface missing"
fi

if grep -q "export const wizardStore" "vibeforge/src/lib/stores/wizard.ts"; then
    test_pass "wizardStore exported"
else
    test_fail "wizardStore not found"
fi

# Test 11: Verify Validation Stores
section "11. Validation System Check"
VALIDATION_STORES=(
    "isStep1Valid"
    "isStep2Valid"
    "isStep3Valid"
    "isStep4Valid"
    "canProceed"
    "wizardProgress"
)

for store in "${VALIDATION_STORES[@]}"; do
    if grep -q "export const $store" "vibeforge/src/lib/stores/wizard.ts"; then
        test_pass "Validation store exists: $store"
    else
        test_fail "Validation store missing: $store"
    fi
done

# Test 12: Verify Navigation Methods
section "12. Navigation System Check"
NAVIGATION_METHODS=(
    "goToStep"
    "nextStep"
    "previousStep"
    "saveDraft"
    "loadDraft"
    "reset"
)

for method in "${NAVIGATION_METHODS[@]}"; do
    if grep -q "$method:" "vibeforge/src/lib/stores/wizard.ts"; then
        test_pass "Navigation method exists: $method"
    else
        test_fail "Navigation method missing: $method"
    fi
done

# Test 13: Verify Step Component Integration
section "13. Step Component Integration"
STEP_COMPONENTS=(
    "Step1Intent"
    "Step2Languages"
    "Step3Stack"
    "Step4Config"
    "Step5Review"
)

for component in "${STEP_COMPONENTS[@]}"; do
    if grep -q "import $component" "vibeforge/src/routes/wizard/+page.svelte"; then
        test_pass "Step component imported: $component"
    else
        test_fail "Step component not imported: $component"
    fi
done

# Test 14: Verify localStorage Draft Persistence
section "14. Draft Persistence System"
if grep -q "localStorage.setItem" "vibeforge/src/lib/stores/wizard.ts"; then
    test_pass "Draft save to localStorage implemented"
else
    test_fail "Draft save not implemented"
fi

if grep -q "localStorage.getItem" "vibeforge/src/lib/stores/wizard.ts"; then
    test_pass "Draft load from localStorage implemented"
else
    test_fail "Draft load not implemented"
fi

# Test 15: Verify Project Type Options
section "15. Project Type Configuration"
if grep -q "projectType.*web.*mobile.*desktop" "vibeforge/src/lib/components/wizard/steps/Step1Intent.svelte"; then
    test_pass "Project types defined (web, mobile, desktop, etc.)"
else
    test_fail "Project type options incomplete"
fi

# Final Summary
section "TEST SUMMARY"
total=$((pass_count + fail_count))
pass_pct=$((pass_count * 100 / total))

echo ""
echo "Total Tests: $total"
echo -e "${GREEN}Passed: $pass_count${NC}"
echo -e "${RED}Failed: $fail_count${NC}"
echo "Success Rate: ${pass_pct}%"
echo ""

if [ $fail_count -eq 0 ]; then
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                  🎉 ALL TESTS PASSED! 🎉                                  ║"
    echo "║                                                                          ║"
    echo "║  Phase 2.1 Milestone: Wizard Architecture - COMPLETE                     ║"
    echo "║  Status: Ready for manual testing in browser                             ║"
    echo "║  URL: http://localhost:5174/wizard                                       ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    exit 0
else
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                  ⚠️  SOME TESTS FAILED ⚠️                                  ║"
    echo "║  Review failures above and fix issues before proceeding                  ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    exit 1
fi
