# LiveKit AI Voice & Video Agent Platform

A comprehensive **100% on-premises, open-source** LiveKit-based AI communication platform with voice calls, video calls, messaging, and AI agent capabilities. Integrates with SIP for telephony, uses self-hosted AI models (Ollama, WhisperLiveKit, Piper TTS), and provides a React frontend with real-time transcription.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LIVEKIT AI VOICE AGENT                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Frontend   │    │   Backend    │    │   LiveKit    │                  │
│  │  (React UI)  │◄──►│  (FastAPI)   │◄──►│   Server     │                  │
│  │  Port 3000   │    │  Port 8000   │    │  Port 7880   │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│         │                   │                   │                          │
│         │                   │                   ▼                          │
│         │                   │           ┌──────────────┐                   │
│         │                   │           │ Agent Worker │                   │
│         │                   │           │   (Python)   │                   │
│         │                   │           └──────────────┘                   │
│         │                   │                   │                          │
│         ▼                   ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VOICE PROCESSING PIPELINE                      │   │
│  │                                                                     │   │
│  │  ┌─────────┐   ┌─────────────┐   ┌─────────┐   ┌─────────────┐     │   │
│  │  │ Silero  │   │WhisperLive- │   │ Ollama  │   │   Piper     │     │   │
│  │  │   VAD   │──►│    Kit      │──►│   LLM   │──►│    TTS      │     │   │
│  │  │ (local) │   │ Port 8765   │   │Port11434│   │  Port 5500  │     │   │
│  │  └─────────┘   └─────────────┘   └─────────┘   └─────────────┘     │   │
│  │                                                                     │   │
│  │  Voice       Speech-to-Text    Language       Text-to-Speech       │   │
│  │  Detection   (Whisper small)   Model          (Neural voices)      │   │
│  │  ~50ms       ~500ms-2s         ~300ms-2s      ~1.3-1.7s            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │    Redis     │    │    NGINX     │    │  LiveKit SIP │                  │
│  │  Port 6379   │    │  Port 443    │    │  Port 5060   │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Voice Pipeline Components
| Component | Technology | Port | Function | Avg Latency |
|-----------|------------|------|----------|-------------|
| **VAD** | Silero VAD v6 | Local | Voice Activity Detection | ~50ms |
| **STT** | WhisperLiveKit (Whisper small) | 8765 | Speech-to-Text | 500ms-2s |
| **LLM** | Ollama (llama3.1:8b) | 11434 | Language Model | 300ms-1.7s |
| **TTS** | Piper (lessac-medium) | 5500 | Text-to-Speech | 1.3-1.7s |

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

## 📊 Performance Metrics & Analysis

### Measured Component Latencies (Benchmarked December 2025)

| Component | Operation | Measured Latency | Notes |
|-----------|-----------|------------------|-------|
| **Ollama LLM** | Short response ("Hi") | ~280ms | Warm model, cached |
| **Ollama LLM** | Medium response | ~1.65s | 50-60 tokens output |
| **Piper TTS** | Short text (3 words) | ~1.5s | CPU inference |
| **Piper TTS** | Medium text (15 words) | ~1.66s | ~100KB audio output |
| **WhisperLiveKit** | Transcription | 500ms-2s | Depends on speech length |
| **Silero VAD** | Speech detection | ~50ms | Local, very fast |

### Total Pipeline Latency Breakdown

```
User speaks → Agent responds: 3-6 seconds total

Breakdown:
├── VAD Detection:        ~50ms   (negligible)
├── STT Processing:       ~500ms-2s (WhisperLiveKit)
├── LLM Generation:       ~300ms-1.7s (Ollama)
├── TTS Synthesis:        ~1.3-1.7s (Piper)
└── Network/Audio:        ~100-200ms (WebRTC)
```

### Performance Insights & Bottlenecks

#### 🔴 Critical Bottlenecks Identified:

1. **TTS (Piper) - Highest Latency (~1.5s)**
   - Running on CPU without GPU acceleration
   - Synthesizes complete audio before returning (non-streaming)
   - **Optimization**: Use GPU or switch to streaming TTS

2. **STT (WhisperLiveKit) - Variable Latency**
   - `lag=` values in logs show 2-17 seconds buffer lag
   - Buffer resets causing "No ASR output" warnings
   - **Optimization**: Reduce `--min-chunk-size`, tune VAD settings

3. **LLM (Ollama) - Network Dependent**
   - Running on external server (192.168.1.120)
   - Network latency adds ~50-100ms
   - **Optimization**: Run Ollama locally or use faster model

#### 🟡 Areas for Improvement:

| Issue | Current State | Recommended Fix |
|-------|---------------|-----------------|
| WhisperLiveKit VAD | Disabled (--no-vad) | Good - LiveKit VAD handles it |
| Duplicate transcripts | "Skipping already finalized" logs | Fixed with deduplication |
| TTS blocking | Async with chunked output | Implemented but still slow |
| End-of-speech delay | min_endpointing_delay=0.3 | Can reduce to 0.2 |

### Monitoring Commands

```bash
# Real-time latency monitoring
docker-compose logs -f agent-worker | grep -E "\[TIMING\]|\[STATE\]|\[VAD\]|\[TTS\]"

# WhisperLiveKit buffer status
docker-compose logs -f whisperlivekit | grep -E "lag=|buffer="

# Piper TTS synthesis times
docker-compose logs -f piper-tts | grep -v "GET /health"

# Component health check
curl -s http://localhost:5500/health && \
curl -s http://localhost:8000/health && \
curl -s http://192.168.1.120:11434/api/tags | head -1
```

---

## 💻 Source Code Documentation

### Project Structure

```
livekit/
├── docker-compose.yaml          # Main service orchestration (10 services)
├── .env                         # Environment configuration
├── CLAUDE.md                    # AI assistant context file
├── README.md                    # This documentation
│
├── configs/
│   ├── livekit.yaml            # LiveKit server configuration
│   └── sip.yaml                # SIP server configuration (optional)
│
├── backend/
│   ├── main.py                 # FastAPI REST API server
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Agent worker container
│   ├── Dockerfile.api          # API server container
│   │
│   └── agent/
│       └── worker.py           # Main AI agent worker (see below)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main app with room join UI
│   │   ├── App.css             # Global styles
│   │   ├── index.css           # Tailwind imports + custom CSS
│   │   ├── main.tsx            # React entry point
│   │   │
│   │   └── components/
│   │       ├── VoiceAgent.tsx  # Main voice UI with visualizer
│   │       ├── TranscriptPanel.tsx  # Real-time transcript display
│   │       └── Room.tsx        # Basic room component
│   │
│   ├── package.json            # Node dependencies
│   ├── vite.config.ts          # Vite build configuration
│   └── Dockerfile              # Frontend container
│
├── tts-service/
│   ├── api_server.py           # Piper TTS HTTP API
│   └── Dockerfile              # TTS container with Piper
│
└── whisperlivekit/
    └── Dockerfile              # WhisperLiveKit STT container
```

### Key Source Files

#### 1. `backend/agent/worker.py` - AI Agent Worker

The main voice agent implementation (~770 lines):

```python
# Key Components:

class WhisperLiveKitSTT(stt.STT):
    """
    Custom STT plugin for WhisperLiveKit WebSocket integration.
    - Connects to ws://whisperlivekit:8765/asr
    - Sends raw PCM audio (s16le, 16kHz, mono)
    - Receives JSON transcription with interim/final results
    - Implements stable text timeout for force-finalization
    """

class AsyncPiperTTS(tts.TTS):
    """
    Async TTS implementation for Piper with chunked output.
    - Uses aiohttp for non-blocking HTTP requests
    - Chunks audio output (4096 bytes) for smooth playback
    - Prevents event loop blocking (fixes stuttering issue)
    """

def create_voice_pipeline(...):
    """Creates STT, LLM, TTS, VAD components for AgentSession."""
    # Returns: (stt, llm, tts, vad) tuple

async def entrypoint(ctx: JobContext):
    """
    Main agent entry point.
    - Creates voice pipeline components
    - Configures AgentSession with optimized settings
    - Sets up timing instrumentation for latency analysis
    - Generates initial greeting after session.start()
    """
```

**Configuration Options:**
```python
# VAD Settings (Silero)
vad=silero.VAD.load(
    min_speech_duration=0.05,    # Faster speech detection
    min_silence_duration=0.25,   # End-of-speech threshold
    activation_threshold=0.45,   # Speech detection sensitivity
)

# Session Settings
AgentSession(
    turn_detection="vad",
    min_endpointing_delay=0.3,   # Delay before processing
)
```

#### 2. `frontend/src/components/VoiceAgent.tsx` - Voice UI

React component with LiveKit integration (~205 lines):

```typescript
// Key Features:
- LiveKitRoom connection with audio-only mode
- useVoiceAssistant() hook for agent state
- Real-time transcript display with speaker identification
- BarVisualizer for audio feedback
- Speaking status indicators (user/agent)

// Data Channel Topics:
- "transcripts": Real-time speech transcription
- "agent_status": Agent state changes
- "user_status": User speaking state
```

#### 3. `tts-service/api_server.py` - Piper TTS API

FastAPI server wrapping Piper CLI (~280 lines):

```python
# Endpoints:
POST /api/synthesize     # Full WAV synthesis
POST /api/synthesize/stream  # Streaming PCM (lower latency)
GET  /voices             # List available voices
GET  /health             # Health check

# Audio Format:
- Sample Rate: 22050 Hz
- Channels: Mono
- Bit Depth: 16-bit signed PCM
```

#### 4. `docker-compose.yaml` - Service Orchestration

10 containerized services:

| Service | Image | Purpose |
|---------|-------|---------|
| `redis` | redis:7-alpine | Message broker, state storage |
| `livekit` | livekit/livekit-server | WebRTC signaling server |
| `livekit-sip` | livekit/sip | SIP gateway (optional) |
| `whisperlivekit` | Custom build | Speech-to-text service |
| `piper-tts` | Custom build | Text-to-speech service |
| `agent-worker` | Custom build | AI agent Python worker |
| `backend` | Custom build | FastAPI REST API |
| `nginx` | Custom build | SSL reverse proxy |
| `frontend` | Custom build | React web UI |

---

## 🎨 UI Enrichment Opportunities

### Current UI Features
- Room join form with validation
- Voice visualizer (BarVisualizer)
- Real-time transcript panel
- Speaking indicators (user/agent)
- Dark theme with Tailwind CSS

### Suggested Enhancements

#### 1. **Performance Dashboard**
```
Add a collapsible panel showing:
- Current latency metrics (STT, LLM, TTS)
- Connection quality indicator
- Buffer status from WhisperLiveKit
```

#### 2. **Enhanced Transcript View**
```
- Timestamps with relative time ("2s ago")
- Copy transcript button
- Export conversation as text/JSON
- Highlight keywords or entities
```

#### 3. **Agent Status Details**
```
- Show current processing stage (listening/thinking/speaking)
- Display token count for LLM responses
- Show audio duration for TTS output
```

#### 4. **Settings Panel**
```
- Microphone selection
- Volume controls
- Voice speed adjustment
- Language selection
```

#### 5. **Visual Improvements**
```
- Animated waveform instead of bars
- Avatar for agent with lip-sync animation
- Typing indicator during LLM processing
- Sound effects for state changes
```

---

## 📚 Documentation

- **LiveKit Agents**: https://docs.livekit.io/agents/
- **LiveKit SIP**: https://docs.livekit.io/sip/
- **WhisperLiveKit**: https://github.com/QuentinFuxa/WhisperLiveKit
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
