FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libterm-readline-perl-perl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
#RUN pip install --no-cache-dir -r requirements.txt

# Install Python dependencies (ensures console scripts are created)
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir livekit-agents


# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Default command (will be overridden in docker-compose)
CMD ["python", "-m", "agent.worker"]
