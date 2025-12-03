#!/bin/bash
# LiveKit AI Voice Agent - Quick Start (Ubuntu/Linux)

set -e

echo "============================================================"
echo "LiveKit AI Voice Agent - Quick Start (Ubuntu/Linux)"
echo "============================================================"
echo

echo "Checking prerequisites..."
echo

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running!"
    echo "Please start Docker and try again:"
    echo "  sudo systemctl start docker"
    exit 1
fi
echo "[OK] Docker is running"

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[OK] Ollama is running on localhost"
    export OLLAMA_URL="http://172.17.0.1:11434"
else
    echo "[WARNING] Ollama not detected on localhost"
    echo "Make sure Ollama is running: ollama serve"
    echo "Or update OLLAMA_URL in .env file"
fi

echo
echo "Starting all services..."
echo

docker-compose up -d

echo
echo "Waiting for services to start..."
sleep 15

echo
echo "============================================================"
echo "Service Status:"
echo "============================================================"
docker-compose ps

echo
echo "============================================================"
echo "Access URLs:"
echo "============================================================"
echo "- Backend API: http://localhost:8000"
echo "- Health Check: http://localhost:8000/health"
echo "- Piper TTS: http://localhost:5500/health"
echo "- LiveKit Server: http://localhost:7880"
echo
echo "============================================================"
echo "Logs:"
echo "============================================================"
echo "To view logs, run: docker-compose logs -f"
echo "To view agent logs: docker-compose logs -f agent-worker"
echo
echo "Press Ctrl+C to stop viewing logs, then run:"
echo "  docker-compose logs -f"
echo

# Follow logs
docker-compose logs -f
