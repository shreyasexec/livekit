#!/bin/bash
#
# Run E2E Bottleneck Test for LiveKit Voice Agent
#
# This script:
# 1. Starts fresh agent logs capture
# 2. Runs the E2E conversation test (simulates mic input)
# 3. Parses agent logs for component timing breakdown
#
# Usage:
#   ./test/run_bottleneck_test.sh [duration_seconds]
#
# Example:
#   ./test/run_bottleneck_test.sh 60    # Run for 1 minute
#   ./test/run_bottleneck_test.sh 120   # Run for 2 minutes
#

set -e

DURATION=${1:-60}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "LIVEKIT VOICE AGENT - BOTTLENECK TEST"
echo "============================================================"
echo "Duration: ${DURATION} seconds"
echo "Project:  ${PROJECT_DIR}"
echo ""

# Check if services are running
echo "🔍 Checking services..."

if ! docker-compose ps | grep -q "livekit.*Up"; then
    echo "❌ LiveKit server is not running!"
    echo "   Run: docker-compose up -d"
    exit 1
fi

if ! docker-compose ps | grep -q "agent-worker.*Up"; then
    echo "❌ Agent worker is not running!"
    echo "   Run: docker-compose up -d agent-worker"
    exit 1
fi

if ! docker-compose ps | grep -q "piper-tts.*Up"; then
    echo "❌ Piper TTS is not running!"
    echo "   Run: docker-compose up -d piper-tts"
    exit 1
fi

if ! docker-compose ps | grep -q "whisperlivekit.*Up"; then
    echo "❌ WhisperLiveKit is not running!"
    echo "   Run: docker-compose up -d whisperlivekit"
    exit 1
fi

echo "✅ All services are running"
echo ""

# Create temp file for agent logs
AGENT_LOG=$(mktemp /tmp/agent-logs-XXXXXX.log)
echo "📝 Agent logs will be saved to: ${AGENT_LOG}"

# Get timestamp for filtering new logs only
START_TIME=$(date +%s)

# Start capturing agent logs in background
echo "📡 Starting agent log capture..."
docker-compose logs -f agent-worker > "$AGENT_LOG" 2>&1 &
LOG_PID=$!

# Give a moment for log capture to start
sleep 2

# Run the E2E test
echo ""
echo "🚀 Running E2E conversation test..."
echo "   This will simulate a user speaking through the React UI"
echo "   (No mic needed - using synthetic audio)"
echo ""
echo "============================================================"

docker-compose exec -e TEST_DURATION=$DURATION backend python /app/test/e2e_conversation_test.py $DURATION

# Stop log capture
kill $LOG_PID 2>/dev/null || true

echo ""
echo "============================================================"
echo "📊 PARSING AGENT LOGS FOR COMPONENT TIMING..."
echo "============================================================"
echo ""

# Parse the captured logs
python3 "$SCRIPT_DIR/parse_agent_logs.py" "$AGENT_LOG"

# Cleanup
rm -f "$AGENT_LOG"

echo ""
echo "✅ Test complete!"
echo ""
echo "To run again: ./test/run_bottleneck_test.sh $DURATION"
echo ""
