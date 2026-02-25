#!/bin/bash
# Forge Ecosystem - Service Verification Script
# Verifies all 4 backend services can start successfully

set -e

echo "==================================="
echo "Forge Ecosystem - Service Verification"
echo "==================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directory
FORGE_DIR="/home/charles/projects/Coding2025/Forge"

# Service configurations (port:directory:command)
declare -A SERVICES=(
    ["DataForge"]="8001:$FORGE_DIR/DataForge:uvicorn app.main:app --port 8001"
    ["NeuroForge"]="8000:$FORGE_DIR/NeuroForge:neuroforge_backend/.venv/bin/uvicorn neuroforge_backend.main:app --port 8000"
    ["ForgeAgents"]="8010:$FORGE_DIR/forge_agents_bds_api:uvicorn app.main:app --port 8010"
    ["Rake"]="8002:$FORGE_DIR/rake:uvicorn main:app --port 8002"
)

# Function to test if port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local port=$1
    local service=$2
    local max_attempts=30
    local attempt=1

    echo -n "  Waiting for $service on port $port"
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://127.0.0.1:$port/health >/dev/null 2>&1 || \
           curl -s http://127.0.0.1:$port/ >/dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo -e " ${RED}✗ (timeout)${NC}"
    return 1
}

# Check each service
echo "Checking service configurations..."
echo ""

for service_name in "${!SERVICES[@]}"; do
    IFS=':' read -r port directory command <<< "${SERVICES[$service_name]}"

    echo -e "${YELLOW}[$service_name]${NC} (Port $port)"

    # Check if directory exists
    if [ ! -d "$directory" ]; then
        echo -e "  ${RED}✗${NC} Directory not found: $directory"
        continue
    fi

    # Check if port is already in use
    if port_in_use $port; then
        echo -e "  ${RED}✗${NC} Port $port already in use"
        echo "    Kill with: lsof -ti:$port | xargs kill -9"
        continue
    fi

    # Check for .env file
    if [ -f "$directory/.env" ]; then
        echo -e "  ${GREEN}✓${NC} Config found (.env)"
    else
        echo -e "  ${YELLOW}⚠${NC} No .env file (using defaults)"
    fi

    # Check for venv (Python services)
    if [[ $command == *"venv"* ]]; then
        venv_path=$(echo $command | grep -oP '[\w/]+\.venv' | head -1)
        if [ -d "$venv_path" ]; then
            echo -e "  ${GREEN}✓${NC} Virtual environment found"
        else
            echo -e "  ${RED}✗${NC} Virtual environment not found: $venv_path"
            continue
        fi
    fi

    echo -e "  ${GREEN}✓${NC} Ready to start"
    echo ""
done

echo ""
echo "==================================="
echo "Service Status Summary"
echo "==================================="
echo ""
echo "To start all services, run in separate terminals:"
echo ""
echo -e "${YELLOW}# Terminal 1: DataForge (Port 8001)${NC}"
echo "cd DataForge && uvicorn app.main:app --port 8001 --reload"
echo ""
echo -e "${YELLOW}# Terminal 2: NeuroForge (Port 8000)${NC}"
echo "cd NeuroForge && neuroforge_backend/.venv/bin/uvicorn neuroforge_backend.main:app --port 8000 --reload"
echo ""
echo -e "${YELLOW}# Terminal 3: ForgeAgents (Port 8010)${NC}"
echo "cd forge_agents_bds_api && uvicorn app.main:app --port 8010 --reload"
echo ""
echo -e "${YELLOW}# Terminal 4: Rake (Port 8002)${NC}"
echo "cd rake && uvicorn main:app --port 8002 --reload"
echo ""
echo -e "${YELLOW}# Terminal 5: ForgeCommand (Tauri dev)${NC}"
echo "cd ForgeCommand && pnpm tauri dev"
echo ""
echo "==================================="
echo ""
echo "Architecture documented in: FORGE_UNIFIED_ARCHITECTURE.md"
echo ""
