#!/bin/bash
# Voice AI Test Automation Setup Script
# Sets up the testing environment for Voice AI tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

echo "=== Voice AI Test Automation Setup ==="
echo "Working directory: ${SCRIPT_DIR}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: ${PYTHON_VERSION}"

python3 - <<'PY'
import sys

if sys.version_info < (3, 9):
    raise SystemExit("Error: Python 3.9+ required")
PY

# Create virtual environment
echo ""
echo "=== Creating virtual environment ==="
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
    echo "Virtual environment created: ${VENV_DIR}"
elif [ ! -f "${VENV_DIR}/bin/activate" ]; then
    echo "Virtual environment incomplete, recreating..."
    python3 -m venv --clear "${VENV_DIR}"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source "${VENV_DIR}/bin/activate"

# Upgrade pip
echo ""
echo "=== Upgrading pip ==="
pip install --upgrade pip

# Install dependencies
echo ""
echo "=== Installing dependencies ==="
pip install -r "${SCRIPT_DIR}/requirements_voice_test.txt"

# Install Robot Framework Browser dependencies
echo ""
echo "=== Installing Robot Framework Browser dependencies ==="
rfbrowser init

echo ""
echo "=== Installing Playwright (Python) browsers ==="
python3 -m playwright install

# Verify installations
echo ""
echo "=== Verifying installations ==="

echo -n "Robot Framework: "
robot --version 2>/dev/null | head -1 || echo "NOT INSTALLED"

echo -n "RF Browser: "
rfbrowser --version 2>/dev/null | head -1 || echo "NOT INSTALLED"

echo -n "Playwright (Python): "
python3 -c "from playwright.sync_api import sync_playwright; print('OK')" 2>/dev/null || echo "NOT INSTALLED"

echo -n "httpx: "
python3 -c "import httpx; print('OK')" 2>/dev/null || echo "NOT INSTALLED"

echo -n "websockets: "
python3 -c "import websockets; print('OK')" 2>/dev/null || echo "NOT INSTALLED"

echo -n "soundfile: "
python3 -c "import soundfile; print('OK')" 2>/dev/null || echo "NOT INSTALLED"

echo -n "numpy: "
python3 -c "import numpy; print('OK')" 2>/dev/null || echo "NOT INSTALLED"

# Check service connectivity
echo ""
echo "=== Checking service connectivity ==="

echo -n "Ollama LLM (192.168.1.120:11434): "
curl -s --connect-timeout 5 http://192.168.1.120:11434/api/tags > /dev/null 2>&1 && echo "OK" || echo "UNREACHABLE"

echo -n "Piper TTS (192.168.20.62:5500): "
curl -s --connect-timeout 5 http://192.168.20.62:5500/health > /dev/null 2>&1 && echo "OK" || echo "UNREACHABLE"

echo -n "Voice AI App (192.168.20.62:3000): "
curl -sk --connect-timeout 5 https://192.168.20.62:3000/ > /dev/null 2>&1 && echo "OK" || echo "UNREACHABLE"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the environment:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "To run tests:"
echo "  ./run_tests.sh api      # Run API tests"
echo "  ./run_tests.sh webrtc   # Run WebRTC tests"
echo "  ./run_tests.sh all      # Run all tests"
