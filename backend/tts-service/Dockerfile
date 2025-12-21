# =============================================================================
# Piper TTS Dockerfile - Performance Optimized
# =============================================================================
# Performance optimizations:
# - Model preloading at startup (saves ~200ms first request)
# - Native piper-tts package (in-memory model, no subprocess)
# - Optimized ONNX runtime settings
#
# For GPU support, use Dockerfile.gpu instead or set:
#   docker build --build-arg USE_GPU=true
# =============================================================================

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    wget \
    curl \
    libterm-readline-perl-perl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python packages
# piper-tts includes onnxruntime for CPU inference
ARG USE_GPU=false
RUN if [ "$USE_GPU" = "true" ]; then \
        echo "Installing with GPU support..." && \
        pip install --no-cache-dir \
            onnxruntime-gpu \
            piper-tts \
            fastapi \
            uvicorn[standard]; \
    else \
        echo "Installing CPU version..." && \
        pip install --no-cache-dir \
            piper-tts \
            fastapi \
            uvicorn[standard]; \
    fi

# Download voice models
# You can add more voices from: https://huggingface.co/rhasspy/piper-voices
RUN mkdir -p /app/voices && \
    cd /app/voices && \
    wget -q https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget -q https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Copy API server
COPY api_server.py /app/

# ONNX Runtime performance settings
ENV OMP_NUM_THREADS=4
ENV ORT_DISABLE_ALL_GC=1

# Expose port
EXPOSE 5500

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5500/health || exit 1

# Run API server with optimized settings
CMD ["python", "-u", "api_server.py"]
