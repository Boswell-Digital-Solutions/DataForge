#!/bin/bash
# DataForge Test Runner Script

set -e  # Exit on error

echo "╔════════════════════════════════════════════╗"
echo "║       DataForge Test Suite Runner          ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating venv..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}❌ Virtual environment not found. Run: python -m venv venv${NC}"
        exit 1
    fi
fi

# Install test dependencies if needed
echo "📦 Checking test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov pytest-mock

echo ""
echo "Running tests..."
echo ""

# Parse command line arguments
TEST_TYPE="${1:-all}"

case $TEST_TYPE in
    unit)
        echo "🧪 Running unit tests only..."
        pytest tests/test_unit/ -v -m unit
        ;;
    integration)
        echo "🔗 Running integration tests only..."
        pytest tests/test_integration/ -v -m integration
        ;;
    api)
        echo "🌐 Running API tests only..."
        pytest tests/test_api/ -v
        ;;
    auth)
        echo "🔐 Running authentication tests only..."
        pytest -v -m auth
        ;;
    search)
        echo "🔍 Running search tests only..."
        pytest -v -m search
        ;;
    coverage)
        echo "📊 Running tests with coverage report..."
        pytest --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}✅ Coverage report generated in htmlcov/index.html${NC}"
        ;;
    fast)
        echo "⚡ Running fast tests only (unit tests)..."
        pytest tests/test_unit/ -v --tb=short
        ;;
    all)
        echo "🚀 Running all tests..."
        pytest -v
        ;;
    *)
        echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [type]"
        echo ""
        echo "Available types:"
        echo "  all         - Run all tests (default)"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  api         - Run API endpoint tests only"
        echo "  auth        - Run authentication tests only"
        echo "  search      - Run search tests only"
        echo "  coverage    - Run tests with coverage report"
        echo "  fast        - Run fast tests only"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

