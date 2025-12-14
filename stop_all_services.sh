#!/bin/bash
# Stop all Forge backend services

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================="
echo "Stopping All Forge Backend Services"
echo "======================================="
echo ""

# Kill by port
for port in 8788 8000 8787 8002; do
    if lsof -ti:$port >/dev/null 2>&1; then
        echo -e "${YELLOW}Stopping service on port $port...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null
        echo -e "  ${GREEN}✓ Stopped${NC}"
    else
        echo -e "${YELLOW}Port $port:${NC} No service running"
    fi
done

echo ""
echo "Verifying all services stopped..."
if lsof -i:8788,8000,8787,8002 2>/dev/null | grep LISTEN; then
    echo -e "${RED}Some services still running!${NC}"
else
    echo -e "${GREEN}✓ All services stopped${NC}"
fi

echo ""
echo "Cleaning up PID files..."
rm -f /tmp/DataForge_service.pid
rm -f /tmp/NeuroForge_service.pid
rm -f /tmp/ForgeAgents_service.pid
rm -f /tmp/Rake_service.pid
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""
