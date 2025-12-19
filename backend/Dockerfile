FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libterm-readline-perl-perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download turn detector model files
RUN python agent/worker.py download-files

ENV PYTHONPATH=/app
ENV PATH="/root/.local/bin:$PATH"

CMD ["python", "agent/worker.py", "dev"]