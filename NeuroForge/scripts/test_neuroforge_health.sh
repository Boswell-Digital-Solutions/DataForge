#!/bin/bash
# Test NeuroForge health endpoint with extended timeout

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

export DATABASE_URL="${DATABASE_URL:-sqlite:///./neuroforge_telemetry.db}"

echo "Starting NeuroForge..."
neuroforge_backend/.venv/bin/uvicorn neuroforge_backend.main:app --port 8000 > /tmp/neuroforge_detailed.log 2>&1 &
PID=$!

echo "NeuroForge PID: $PID"
echo "Waiting 10 seconds for startup..."
sleep 10

echo "Testing health endpoint..."
if curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null; then
    echo -e "\n✅ Health endpoint working!"
else
    echo "❌ Health check failed"
fi

echo "Stopping NeuroForge..."
kill $PID 2>/dev/null
wait $PID 2>/dev/null || true
echo "Done"
