#!/bin/bash
# Test script to verify all Forge backend services can start

set -e

FORGE_DIR="/home/charles/projects/Coding2025/Forge"
cd "$FORGE_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================="
echo "Testing Forge Backend Services"
echo "======================================="
echo ""

# Function to test service
test_service() {
    local name=$1
    local port=$2
    local directory=$3
    local command=$4

    echo -e "${YELLOW}Testing $name (Port $port)${NC}"

    cd "$directory"

    # Start service in background
    echo "  Starting service..."
    eval "$command" > /tmp/${name}_test.log 2>&1 &
    local pid=$!

    # Wait for startup
    sleep 6

    # Check if process is still running
    if ps -p $pid > /dev/null 2>&1; then
        # Test health endpoint
        if curl -s -f http://127.0.0.1:${port}/health > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Service started successfully${NC}"
            echo -e "  ${GREEN}✓ Health endpoint responding${NC}"
            status="success"
        elif curl -s -f http://127.0.0.1:${port}/ > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Service started successfully${NC}"
            echo -e "  ${YELLOW}⚠ Health endpoint not found (root responds)${NC}"
            status="success"
        else
            echo -e "  ${GREEN}✓ Service started${NC}"
            echo -e "  ${YELLOW}⚠ HTTP endpoint not responding yet${NC}"
            status="partial"
        fi
    else
        echo -e "  ${RED}✗ Service failed to start${NC}"
        echo "  Check log: /tmp/${name}_test.log"
        status="failed"
    fi

    # Kill the service
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true

    echo ""

    return 0
}

# Test each service
cd "$FORGE_DIR"

test_service "DataForge" "8001" \
    "$FORGE_DIR/DataForge" \
    "venv/bin/python -m uvicorn app.main:app --port 8001"

test_service "NeuroForge" "8000" \
    "$FORGE_DIR/NeuroForge" \
    "neuroforge_backend/.venv/bin/python -m uvicorn neuroforge_backend.main:app --port 8000"

test_service "ForgeAgents" "8010" \
    "$FORGE_DIR/forge_agents_bds_api" \
    "venv/bin/uvicorn app.main:app --port 8010"

test_service "Rake" "8002" \
    "$FORGE_DIR/rake" \
    "venv/bin/uvicorn main:app --port 8002"

echo "======================================="
echo "Test Complete"
echo "======================================="
echo ""
echo "Review individual logs in /tmp/*_test.log for details"
echo ""
