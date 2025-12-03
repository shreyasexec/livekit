# LiveKit AI Voice & Video Agent Platform

A comprehensive LiveKit-based AI communication platform with voice calls, video calls, messaging, and AI agent capabilities. Integrates with SIP for telephony, uses self-hosted AI models (Ollama, WhisperLive, Piper TTS), and provides a React frontend with real-time transcription.

## 🏗️ Architecture

```
SIP Caller → LiveKit SIP → LiveKit Server → AI Agent Worker
                                ↓
                        VAD → STT → LLM → TTS
                                ↓
                        Audio back to caller
```

### Voice Pipeline
1. **VAD (Silero)**: Voice Activity Detection (local)
2. **STT (WhisperLive)**: Speech-to-Text via WebSocket (Port 9090)
3. **LLM (Ollama)**: Language Model via OpenAI-compatible API (Port 11434)
4. **TTS (Piper)**: Text-to-Speech synthesis (Port 5500)

## 📋 Prerequisites

### Required Software
- **Docker & Docker Compose**: Latest version
- **Ollama**: Running on host machine or external server
- **Git**: For cloning repository

### Ollama Setup
```bash
# Install Ollama (if not already installed)
# Visit: https://ollama.com/download

# Start Ollama server
ollama serve

# Pull the model
ollama pull llama3.1
```

### System Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **GPU**: Optional (for WhisperLive GPU acceleration)
- **Storage**: 10GB+ for models and voice data

## 🚀 Quick Start

### 1. Clone & Configure

```bash
cd D:/RND/trinityCHATBOT/voiceagent/livekit

# Copy environment file
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

### 2. Generate API Keys

```bash
# Generate LiveKit API keys
openssl rand -base64 32  # Use as LIVEKIT_API_KEY
openssl rand -base64 32  # Use as LIVEKIT_API_SECRET

# Update configs/livekit.yaml with these keys
```

### 3. Configure Ollama URL

Update `.env` file:
```env
OLLAMA_URL=http://192.168.1.120:11434  # Replace with your Ollama server IP
```

### 4. Start All Services

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f
```

### 5. Verify Services

```bash
# Check LiveKit
curl http://localhost:7880

# Check Backend API
curl http://localhost:8000/health

# Check Piper TTS
curl http://localhost:5500/health

# Check WhisperLive
curl http://localhost:9090

# Check Ollama (external)
curl http://192.168.1.120:11434/api/tags
```

## 🎯 Usage

### Web Client Access

1. Open browser: `http://localhost:3000`
2. Enter room name (e.g., `test-room`)
3. Enter your name
4. Click "Connect"
5. Speak into microphone - AI agent will respond!

### SIP Integration (Linphone)

#### Create SIP Trunk
```bash
curl -X POST http://localhost:8000/api/sip/trunk \
  -H "Content-Type: application/json" \
  -d '{
    "name": "linphone-trunk",
    "numbers": ["+1234567890"],
    "allowed_addresses": ["0.0.0.0/0"]
  }'
```

#### Create Dispatch Rule
```bash
curl -X POST http://localhost:8000/api/sip/dispatch \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "ai-agent-room",
    "trunk_ids": ["trunk_xxxxxxxxxx"],
    "pin": ""
  }'
```

#### Configure Linphone
1. Open Linphone
2. Settings → SIP Accounts → Add
3. Configure:
   - **Username**: your_username
   - **SIP Domain**: `YOUR_SERVER_IP:5060`
   - **Transport**: UDP
4. Call: `+1234567890@YOUR_SERVER_IP:5060`

## 📁 Project Structure

```
livekit/
├── docker-compose.yaml          # Service orchestration
├── .env                         # Environment variables
├── configs/
│   ├── livekit.yaml            # LiveKit server config
│   └── sip.yaml                # SIP server config
├── backend/
│   ├── main.py                 # FastAPI REST API
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Agent worker image
│   ├── Dockerfile.api          # API server image
│   └── agent/
│       ├── worker.py           # AI agent worker
│       ├── stt_handler.py      # WhisperLive STT
│       ├── llm_handler.py      # Ollama LLM
│       └── tts_handler.py      # Piper TTS
└── tts-service/
    ├── Dockerfile              # Piper TTS service
    └── api_server.py           # TTS API server
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LIVEKIT_API_KEY` | LiveKit API key | `devkey` |
| `LIVEKIT_API_SECRET` | LiveKit API secret | `secret` |
| `OLLAMA_URL` | Ollama server URL | `http://192.168.1.120:11434` |
| `WHISPERLIVE_HOST` | WhisperLive hostname | `whisperlive` |
| `PIPER_URL` | Piper TTS URL | `http://piper-tts:5500` |

### Port Configuration

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| LiveKit Server | 7880 | TCP/WS | WebSocket signaling |
| LiveKit Server | 7881 | TCP | WebRTC over TCP |
| LiveKit Server | 50000-50100 | UDP | WebRTC media |
| LiveKit SIP | 5060 | UDP | SIP signaling |
| Redis | 6379 | TCP | Message broker |
| FastAPI Backend | 8000 | TCP | REST API |
| React Frontend | 3000 | TCP | Web UI |
| WhisperLive | 9090 | TCP/WS | STT service |
| Piper TTS | 5500 | TCP | TTS service |
| Ollama | 11434 | TCP | LLM service |

## 🐛 Troubleshooting

### WhisperLive Container Failing

If you see `✘ Container livekit-whisperlive-1 Error`, see the comprehensive guide:
**→ [WHISPERLIVE_TROUBLESHOOTING.md](WHISPERLIVE_TROUBLESHOOTING.md)**

Quick fixes:
```bash
# Check logs
docker compose logs whisperlive

# Verify port listening
docker compose exec whisperlive netstat -tuln | grep 9090

# Restart with extended startup time
docker compose down
docker compose up -d
```

### Agent Not Responding

```bash
# Check agent logs
docker compose logs -f agent-worker

# Verify Ollama is accessible
curl http://192.168.1.120:11434/api/tags

# Check WhisperLive
docker compose logs -f whisperlive

# Verify Piper TTS
curl http://localhost:5500/health
```

### SIP Not Connecting

```bash
# Verify SIP service is using host network
docker compose ps livekit-sip

# Check firewall
sudo ufw allow 5060/udp
sudo ufw allow 10000:20000/udp
```

### No Audio in Browser

- Check browser permissions (microphone/camera)
- Verify WebRTC connectivity in browser console
- Test with local network first

### WhisperLive High Latency

```bash
# Use GPU backend (if available)
# Edit docker-compose.yaml: use whisperlive-gpu image

# Or reduce model size
# Edit .env: WHISPERLIVE_MODEL=tiny
```

### Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| WhisperLive fails | See dedicated guide | [WHISPERLIVE_TROUBLESHOOTING.md](WHISPERLIVE_TROUBLESHOOTING.md) |
| Docker Compose V1 error | Use `docker compose` not `docker-compose` | [FIXES_SUMMARY.md](FIXES_SUMMARY.md) |
| Missing frontend | Run `npm install` in frontend/ | [frontend/README.md](frontend/README.md) |
| SIP not configured | Run `setup_sip.py` script | [START_GUIDE.md](START_GUIDE.md) |
| Ollama timeout | Check connectivity and increase timeout | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |

## 📊 Monitoring

```bash
# View all service logs
docker-compose logs -f

# View specific service
docker-compose logs -f agent-worker

# Check service health
docker-compose ps

# Resource usage
docker stats
```

## 🔒 Production Deployment

### Security Checklist

- [ ] Generate unique API keys
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable Redis persistence
- [ ] Configure CORS for specific domains
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Enable rate limiting
- [ ] Backup transcripts and recordings

### SSL/TLS Setup

Update nginx reverse proxy:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

## 🧪 Testing

### Test Voice Pipeline

```bash
# Monitor agent logs
docker-compose logs -f agent-worker

# You should see:
# 1. "User said: [transcription]" (from WhisperLive)
# 2. "Agent said: [response]" (from Ollama → Piper)
# 3. Audio published to room
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Create room
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name": "test-room"}'

# List rooms
curl http://localhost:8000/api/rooms

# Generate token
curl -X POST http://localhost:8000/api/token \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "test-room",
    "participant_name": "TestUser"
  }'
```

## 📚 Documentation

- **LiveKit Agents**: https://docs.livekit.io/agents/
- **LiveKit SIP**: https://docs.livekit.io/sip/
- **WhisperLive**: https://github.com/collabora/WhisperLive
- **Ollama**: https://ollama.com/
- **Piper TTS**: https://github.com/rhasspy/piper

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the [Troubleshooting](#-troubleshooting) section
- Review [CLAUDE.md](CLAUDE.md) for detailed architecture
- Open an issue on GitHub

## 🎉 Acknowledgments

- LiveKit for the real-time communication framework
- Collabora for WhisperLive
- Ollama for local LLM inference
- Rhasspy for Piper TTS
