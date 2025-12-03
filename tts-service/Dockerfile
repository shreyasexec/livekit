FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS
RUN pip install --no-cache-dir piper-tts fastapi uvicorn[standard]

# Create app directory
WORKDIR /app

# Download voice models
# You can add more voices from: https://huggingface.co/rhasspy/piper-voices
RUN mkdir -p /app/voices && \
    cd /app/voices && \
    wget -q https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget -q https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Copy API server
COPY api_server.py /app/

# Expose port
EXPOSE 5500

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5500/health || exit 1

# Run API server
CMD ["python", "api_server.py"]
