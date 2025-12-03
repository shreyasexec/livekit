# Quick Start Guide

Get the LiveKit AI Voice Agent running in 5 minutes!

## ⚡ Prerequisites

Before you begin, make sure you have:

1. ✅ **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux) - Running
2. ✅ **Ollama** installed and running with model pulled
3. ✅ **8GB+ RAM** available
4. ✅ **Internet connection** for downloading images

---

## 🚀 5-Minute Setup

### Step 1: Verify Ollama (2 minutes)

**Windows:**
```cmd
REM Check Ollama is running
ollama list

REM If not installed, download from: https://ollama.com/download
REM Then pull the model
ollama pull llama3.1
```

**Ubuntu:**
```bash
# Check Ollama is running
ollama list

# If not installed:
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1
```

### Step 2: Start Services (3 minutes)

**Windows:**
```cmd
REM Simply run the start script
start.bat
```

**Ubuntu:**
```bash
# Make script executable
chmod +x start.sh

# Run it
./start.sh
```

**Or manually:**
```bash
# Pre-pull WhisperLive image (fixes EOF error)
docker pull ghcr.io/collabora/whisperlive-cpu:latest

# Start all services
docker-compose up -d
```

### Step 3: Verify (30 seconds)

```bash
# Check all services are running
docker-compose ps

# Test the backend API
curl http://localhost:8000/health
```

Expected output:
```json
{"status":"ok","service":"Trinity LiveKit API","timestamp":"...","livekit_url":"..."}
```

---

## 🎯 Test the Platform

### 1. Create a Room

```bash
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name": "test-room"}'
```

### 2. Generate Access Token

```bash
curl -X POST http://localhost:8000/api/token \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "test-room",
    "participant_name": "TestUser"
  }'
```

You'll get a response with a JWT token and WebSocket URL!

### 3. Check Agent Logs

```bash
# View agent worker logs
docker-compose logs -f agent-worker
```

You should see:
```
Agent starting for room: ...
WhisperLive STT initialized: whisperlive:9090
Ollama LLM initialized: http://host.docker.internal:11434
Piper TTS initialized: http://piper-tts:5500
Agent session started successfully
```

---

## 🎬 What's Running?

| Service | Port | Status | Description |
|---------|------|--------|-------------|
| **Backend API** | 8000 | 🟢 | REST API for tokens, rooms, SIP |
| **LiveKit Server** | 7880 | 🟢 | WebRTC signaling server |
| **Redis** | 6379 | 🟢 | Message broker |
| **WhisperLive** | 9090 | 🟢 | Speech-to-Text service |
| **Piper TTS** | 5500 | 🟢 | Text-to-Speech service |
| **AI Agent Worker** | - | 🟢 | Voice pipeline processor |
| **Ollama** | 11434 | 🟢 | LLM (running on host) |

---

## 🔍 View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agent-worker
docker-compose logs -f whisperlive
docker-compose logs -f piper-tts
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100
```

---

## 🛑 Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

---

## ⚠️ Common Issues

### Issue: "unexpected EOF" when starting

**Fix:**
```bash
# Pre-pull the image first
docker pull ghcr.io/collabora/whisperlive-cpu:latest

# Then start
docker-compose up -d
```

### Issue: Agent can't connect to Ollama

**Windows Fix:**
- Make sure Ollama is running on Windows (not WSL)
- Check `.env` has: `OLLAMA_URL=http://host.docker.internal:11434`

**Ubuntu Fix:**
- Edit `.env`: `OLLAMA_URL=http://172.17.0.1:11434`
- Or use your machine's IP: `OLLAMA_URL=http://192.168.1.X:11434`

### Issue: Port already in use

**Fix:**
```cmd
# Windows - find what's using the port
netstat -ano | findstr :7880

# Ubuntu
sudo lsof -i :7880

# Kill the process or change ports in docker-compose.yaml
```

### More Issues?
See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

---

## 📚 Next Steps

Once everything is running:

1. **Explore the API**
   - API Documentation: http://localhost:8000/docs
   - Interactive API: http://localhost:8000/redoc

2. **Build the Frontend** (Coming soon)
   - React frontend with LiveKit components
   - Real-time video conference
   - Live transcription display

3. **Configure SIP** (Optional)
   - Set up SIP trunk for phone calls
   - Configure Linphone for testing
   - See [README.md](README.md#sip-integration-linphone) for details

4. **Customize the Agent**
   - Edit `backend/agent/worker.py` to change behavior
   - Add custom functions to `AssistantFunctions` class
   - Modify system prompt for different personalities

---

## 🎓 Learn More

- **Full Documentation**: [README.md](README.md)
- **Platform Setup**: [SETUP.md](SETUP.md)
- **Architecture**: [CLAUDE.md](CLAUDE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## ✅ Success Checklist

- [x] Docker is running
- [x] Ollama is running with llama3.1 model
- [x] All services started successfully
- [x] Backend API responds to health check
- [x] Agent worker shows no errors in logs
- [ ] Frontend built and accessible (Coming soon)
- [ ] SIP integration configured (Optional)

---

## 💡 Tips

1. **First time setup takes longer** due to image downloads and model downloads
2. **WhisperLive takes ~30 seconds to start** - be patient
3. **Piper TTS downloads voices on first build** - takes a few minutes
4. **Check logs frequently** during setup to catch issues early
5. **Use `docker-compose ps`** to see service health status

---

## 🎉 You're Ready!

Your LiveKit AI Voice Agent platform is now running!

The agent is ready to:
- 🎤 Listen to voice input (via WhisperLive)
- 🧠 Process with AI (via Ollama)
- 🔊 Respond with speech (via Piper TTS)
- 📞 Handle SIP calls (optional)
- 💬 Show real-time transcriptions

**Happy building! 🚀**
