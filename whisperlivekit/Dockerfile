# WhisperLiveKit Dockerfile
# Real-time speech-to-text with --pcm-input mode for LiveKit integration
# See: https://github.com/QuentinFuxa/WhisperLiveKit

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install WhisperLiveKit with faster-whisper backend
# Using pip install for the latest stable version
RUN pip install --no-cache-dir \
    whisperlivekit \
    faster-whisper \
    websockets \
    silero-vad

# Set HuggingFace cache directory explicitly
# This directory will be mounted as a volume to persist the model
ENV HF_HOME=/root/.cache/huggingface

# Create an entrypoint script that ensures model is downloaded before starting server
RUN cat > /app/entrypoint.sh << 'EOF'
#!/bin/bash
set -e

echo "Checking/downloading Whisper model..."
python3 -c "
from faster_whisper import WhisperModel
import os
print('Loading Whisper model (will download if not cached)...')
model = WhisperModel('small', device='cpu', compute_type='int8')
print('Model loaded successfully!')
"

echo "Starting WhisperLiveKit server..."
exec "$@"
EOF

RUN chmod +x /app/entrypoint.sh

# Expose WebSocket port
EXPOSE 8765

# Health check - waits for proper WebSocket endpoint readiness
# Uses longer start_period to allow for model download on first run
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 \
    CMD python3 -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost',8765)); s.close()" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]

# Default command - will be overridden by docker-compose
# --pcm-input: Accept raw PCM (s16le) data, bypasses FFmpeg
# VAD is enabled by default (Silero VAD v6)
CMD ["wlk", "--host", "0.0.0.0", "--port", "8765", "--model", "small", "--language", "en", "--pcm-input"]
