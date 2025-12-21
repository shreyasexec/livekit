# INFRASTRUCTURE.md - Voice AI Platform Infrastructure

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INFRASTRUCTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐                                                   │
│  │    Voice AI App      │ ◄── User Browser                                  │
│  │ https://192.168.20.62:3000                                               │
│  └──────────┬───────────┘                                                   │
│             │                                                               │
│             ▼                                                               │
│  ┌──────────────────────┐      ┌──────────────────────┐                    │
│  │   LiveKit Server     │      │      Backend API     │                    │
│  │ ws://192.168.20.62:7880     │ http://192.168.20.62:8000                  │
│  └──────────┬───────────┘      └──────────┬───────────┘                    │
│             │                              │                                │
│             ▼                              ▼                                │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                        AGENT WORKER                              │       │
│  │  ┌─────────┐    ┌─────────────┐    ┌─────────┐    ┌─────────┐  │       │
│  │  │   VAD   │───▶│WhisperLiveKit│───▶│ Ollama  │───▶│  Piper  │  │       │
│  │  │ Silero  │    │192.168.1.120 │    │  LLM    │    │   TTS   │  │       │
│  │  └─────────┘    │    :8765     │    │ :11434  │    │  :5500  │  │       │
│  │                 └─────────────┘    └─────────┘    └─────────┘  │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Endpoints Reference

| Service | URL | Protocol | Port |
|---------|-----|----------|------|
| Voice AI App | `https://192.168.20.62:3000/` | HTTPS | 3000 |
| LiveKit Server | `ws://192.168.20.62:7880` | WebSocket | 7880 |
| Backend API | `http://192.168.20.62:8000` | HTTP | 8000 |
| WhisperLiveKit (STT) | `ws://192.168.1.120:8765/` | WebSocket | 8765 |
| Ollama (LLM) | `http://192.168.1.120:11434` | HTTP | 11434 |
| Piper (TTS) | `http://192.168.20.62:5500/` | HTTP | 5500 |
| Redis | `redis://localhost:6379` | TCP | 6379 |
| SIP | `192.168.20.62:5060` | UDP | 5060 |

---

## Docker Compose Services

| Service | Image | Network | Purpose |
|---------|-------|---------|---------|
| livekit | livekit/livekit-server:latest | bridge | WebRTC server |
| livekit-sip | livekit/sip:latest | **host** | SIP gateway (needs UDP) |
| redis | redis:7-alpine | bridge | State management |
| whisperlive | ghcr.io/collabora/whisperlive-gpu | bridge | STT service |
| piper-tts | custom build | bridge | TTS service |
| agent-worker | custom build | bridge | Voice agent |
| backend | custom build | bridge | API server |
| frontend | custom build | bridge | Web UI |

---

## Docker Compose Configuration

```yaml
# docker-compose.yaml
version: '3.8'

services:
  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7882:7882/udp"
    environment:
      - LIVEKIT_KEYS=${LIVEKIT_API_KEY}:${LIVEKIT_API_SECRET}
    command: --config /etc/livekit.yaml
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml:ro

  livekit-sip:
    image: livekit/sip:latest
    network_mode: host  # Required for SIP UDP
    environment:
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - LIVEKIT_URL=ws://localhost:7880
      - SIP_PORT=5060

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  piper-tts:
    build: ./piper
    ports:
      - "5500:5500"
    volumes:
      - ./piper/voices:/voices

  agent-worker:
    build: ./backend
    depends_on:
      - livekit
      - redis
    environment:
      - LIVEKIT_URL=${LIVEKIT_URL}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - OLLAMA_URL=${OLLAMA_URL}
      - WHISPERLIVE_URL=${WHISPERLIVE_URL}
      - PIPER_URL=${PIPER_URL}
      - REDIS_URL=${REDIS_URL}

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - livekit
      - redis
    environment:
      - LIVEKIT_URL=${LIVEKIT_URL}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - REDIS_URL=${REDIS_URL}

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_LIVEKIT_URL=${VITE_LIVEKIT_URL}
      - VITE_API_URL=${VITE_API_URL}

volumes:
  redis_data:
```

---

## Network Configuration

### Port Requirements

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 3000 | HTTPS | Frontend | Self-signed cert |
| 7880 | WS/WSS | LiveKit Signaling | WebSocket |
| 7881 | TCP | LiveKit ICE (TCP) | Fallback |
| 7882 | UDP | LiveKit ICE (UDP) | Primary media |
| 8000 | HTTP | Backend API | REST API |
| 5060 | UDP | SIP | Telephony signaling |
| 5500 | HTTP | Piper TTS | TTS API |
| 8765 | WS | WhisperLiveKit | STT WebSocket |
| 11434 | HTTP | Ollama | LLM API |
| 6379 | TCP | Redis | Cache |
| 10000-20000 | UDP | RTP | SIP media |

### Firewall Rules
```bash
# Allow internal network to access Ollama
sudo ufw allow from 192.168.20.0/24 to 192.168.1.120 port 11434

# Allow WhisperLiveKit access
sudo ufw allow from 192.168.20.0/24 to 192.168.1.120 port 8765

# LiveKit ports
sudo ufw allow 7880/tcp
sudo ufw allow 7881/tcp
sudo ufw allow 7882/udp

# SIP ports
sudo ufw allow 5060/udp
sudo ufw allow 10000:20000/udp
```

---

## Environment Variables

### Root .env File
```bash
# LiveKit Server
LIVEKIT_API_KEY=<generated>
LIVEKIT_API_SECRET=<generated>
LIVEKIT_URL=http://livekit:7880
LIVEKIT_PUBLIC_URL=wss://192.168.20.62:7880
LIVEKIT_NODE_IP=192.168.20.62

# Ollama LLM (DO NOT CHANGE)
OLLAMA_URL=http://192.168.1.120:11434
OLLAMA_MODEL=llama3.1:8b

# WhisperLiveKit STT (DO NOT CHANGE)
WHISPERLIVE_URL=ws://192.168.1.120:8765/
WHISPERLIVE_HOST=192.168.1.120
WHISPERLIVE_PORT=8765

# Piper TTS
PIPER_URL=http://192.168.20.62:5500/

# Redis
REDIS_URL=redis://redis:6379

# Frontend
VITE_LIVEKIT_URL=wss://192.168.20.62:7880
VITE_API_URL=https://192.168.20.62:8000
VITE_DEBUG_TRANSACTIONS=true
```

---

## Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "Checking services..."

# Backend
curl -s http://localhost:8000/health && echo "✅ Backend OK" || echo "❌ Backend FAIL"

# Piper TTS
curl -s http://192.168.20.62:5500/health && echo "✅ Piper OK" || echo "❌ Piper FAIL"

# LiveKit
curl -s http://192.168.20.62:7880 && echo "✅ LiveKit OK" || echo "❌ LiveKit FAIL"

# Ollama
curl -s http://192.168.1.120:11434/api/tags && echo "✅ Ollama OK" || echo "❌ Ollama FAIL"

# Redis
docker-compose exec redis redis-cli ping && echo "✅ Redis OK" || echo "❌ Redis FAIL"

# WhisperLiveKit
python3 -c "
import asyncio, websockets
async def check():
    try:
        async with websockets.connect('ws://192.168.1.120:8765/', close_timeout=5):
            print('✅ WhisperLiveKit OK')
    except Exception as e:
        print(f'❌ WhisperLiveKit FAIL: {e}')
asyncio.run(check())
"
```

---

## Common Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f                    # All services
docker-compose logs -f agent-worker       # Agent only
docker-compose logs -f livekit            # LiveKit only

# Restart specific service
docker-compose restart agent-worker
docker-compose restart backend

# Rebuild and restart
docker-compose up -d --build agent-worker

# Stop all
docker-compose down

# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## SSL/TLS Configuration

The frontend uses self-signed certificates for HTTPS. For testing:

```bash
# Generate self-signed cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout frontend/ssl/key.pem \
  -out frontend/ssl/cert.pem \
  -subj "/CN=192.168.20.62"
```

Browser testing requires `--ignore-https-errors` flag or accepting the certificate.

---

## SIP Configuration

LiveKit SIP requires `network_mode: host` for proper UDP handling.

### SIP Trunk Configuration
```yaml
# Configure via LiveKit API
trunk:
  name: "Main Trunk"
  numbers:
    - "+1234567890"
  allowed_addresses:
    - "0.0.0.0/0"  # Restrict in production
```

### Dispatch Rules
```yaml
dispatch_rule:
  trunk_ids:
    - "trunk_id_here"
  room_name: "incoming-calls"
  metadata: '{"type": "sip"}'
```