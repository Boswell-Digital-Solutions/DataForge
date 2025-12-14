#!/bin/bash
# Start all Forge backend services in background

FORGE_DIR="/home/charles/projects/Coding2025/Forge"
cd "$FORGE_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================="
echo "Starting All Forge Backend Services"
echo "======================================="
echo ""

# Function to start a service
start_service() {
    local name=$1
    local port=$2
    local directory=$3
    local command=$4

    echo -e "${YELLOW}Starting $name on port $port...${NC}"

    # Check if port is already in use
    if lsof -i :$port >/dev/null 2>&1; then
        echo -e "  ${RED}✗ Port $port already in use${NC}"
        echo "  Kill with: lsof -ti:$port | xargs kill -9"
        return 1
    fi

    cd "$directory"

    # Start service in background
    eval "$command" > /tmp/${name}_service.log 2>&1 &
    local pid=$!

    echo "  PID: $pid"
    echo "  Log: /tmp/${name}_service.log"

    # Wait a moment for startup
    sleep 2

    # Check if still running
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Started successfully${NC}"
        echo "$pid" > /tmp/${name}_service.pid
        return 0
    else
        echo -e "  ${RED}✗ Failed to start (check log)${NC}"
        return 1
    fi
}

# Start each service
cd "$FORGE_DIR"

start_service "DataForge" "8788" \
    "$FORGE_DIR/DataForge" \
    "venv/bin/python -m uvicorn app.main:app --port 8788"

echo ""

start_service "NeuroForge" "8000" \
    "$FORGE_DIR/NeuroForge" \
    "DATABASE_URL=sqlite:///./neuroforge_telemetry.db neuroforge_backend/.venv/bin/uvicorn neuroforge_backend.main:app --port 8000"

echo ""

start_service "ForgeAgents" "8787" \
    "$FORGE_DIR/forge_agents_bds_api" \
    "venv/bin/python -m uvicorn app.main:app --port 8787"

echo ""

start_service "Rake" "8002" \
    "$FORGE_DIR/rake" \
    "venv/bin/python -m uvicorn main:app --port 8002"

echo ""
echo "======================================="
echo "Startup Complete"
echo "======================================="
echo ""
echo "Services running:"
lsof -i:8788,8000,8787,8002 | grep LISTEN || echo "No services detected"
echo ""
echo "To stop all services:"
echo "  bash stop_all_services.sh"
echo ""
echo "To view logs:"
echo "  tail -f /tmp/DataForge_service.log"
echo "  tail -f /tmp/NeuroForge_service.log"
echo "  tail -f /tmp/ForgeAgents_service.log"
echo "  tail -f /tmp/Rake_service.log"
echo ""
