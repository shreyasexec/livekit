# Complete Start Guide for Ubuntu

## 🚀 Quick Start (3 Steps)

### Step 1: Start All Services

```bash
# Make sure you're in the project directory
cd /home/livekit_vibe/livekit

# Start all services (use docker compose, NOT docker-compose)
docker compose up -d
```

### Step 2: Setup SIP for Linphone

```bash
# Wait for services to be healthy
docker compose ps

# Run SIP setup script
python3 setup_sip.py
```

This will create:
- Room: `ai-agent-room`
- SIP Trunk for number: `+1234567890`
- Dispatch rule routing calls to the AI agent

### Step 3: Configure Linphone

Use the configuration printed by the setup script above.

---

## 📋 Detailed Instructions

### Fix: Docker Compose Version Error

You're getting the error because you're using old `docker-compose` (v1.29.2).

**Solution**: Use `docker compose` (V2) instead:

```bash
# OLD (causes errors)
docker-compose up -d

# NEW (correct)
docker compose up -d
```

### Configure Your IP Address

Edit `.env` file and update Ollama URL:

```bash
nano .env
```

Change:
```env
OLLAMA_URL=http://172.17.0.1:11434
```

To use your actual IP if Ollama is running on host:
```bash
# Find your IP
ip addr show | grep "inet " | grep -v 127.0.0.1

# Update .env with your IP
OLLAMA_URL=http://192.168.1.100:11434
```

### Start Services

```bash
# Stop any running services first
docker compose down

# Start fresh
docker compose up -d

# Check status
docker compose ps

# Should see all services as "healthy" or "running"
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f agent-worker
docker compose logs -f backend
docker compose logs -f livekit
docker compose logs -f whisperlive
```

---

## 🎯 Configure SIP & Make Test Call

### 1. Run SIP Setup Script

```bash
python3 setup_sip.py
```

Expected output:
```
====================================

========
LiveKit SIP Setup for AI Agent
============================================================
✓ Backend API is accessible
✓ Room created: ai-agent-room
✓ SIP trunk created
  Trunk ID: ST_xxxxx
  Number: +1234567890
✓ Dispatch rule created
  Calls to +1234567890 will join room: ai-agent-room
============================================================
Linphone Configuration
============================================================
...
```

### 2. Configure Linphone

Open Linphone and add a new SIP account:

| Field | Value |
|-------|-------|
| **Username** | your_username |
| **SIP Domain** | `192.168.1.100:5060` (your Ubuntu IP) |
| **Password** | (leave empty) |
| **Transport** | UDP |

### 3. Make Test Call

In Linphone, dial:
```
+1234567890@192.168.1.100:5060
```

The AI agent should answer and greet you!

---

## 🔍 Verify Everything is Working

### Check Services

```bash
docker compose ps
```

All services should show "healthy" status.

### Test Backend API

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status":"ok","service":"Trinity LiveKit API",...}
```

### Test Piper TTS

```bash
curl http://localhost:5500/health
```

Expected:
```json
{"status":"ok","service":"Piper TTS API",...}
```

### Check Agent Worker Logs

```bash
docker compose logs agent-worker | tail -50
```

Should see:
```
Agent starting for room: ...
WhisperLive STT initialized: whisperlive:9090
Ollama LLM initialized: http://172.17.0.1:11434
Piper TTS initialized: http://piper-tts:5500
Agent session started successfully
```

---

## 🌐 Access Frontend

The React frontend is now available!

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Then open browser: http://localhost:3000

Or use Docker:
```bash
# From project root
docker compose up -d frontend

# Access at http://localhost:3000
```

---

## 🐛 Troubleshooting

### Error: "ContainerConfig" KeyError

This is from old docker-compose v1. Use `docker compose` (V2) instead.

### Error: Can't connect to Ollama

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running:
ollama serve

# Check from inside agent container
docker compose exec agent-worker curl http://172.17.0.1:11434/api/tags
```

### Error: WhisperLive not starting

```bash
# Check logs
docker compose logs whisperlive

# Restart service
docker compose restart whisperlive

# Check health after 30 seconds
docker compose ps whisperlive
```

### SIP Service Won't Start

SIP uses host networking which can be tricky. It's optional for testing the AI agent.

```bash
# Start without SIP
docker compose up -d redis livekit whisperlive piper-tts agent-worker backend frontend

# Test without SIP using web frontend
```

---

## 📝 Complete Workflow

### For Local Testing (No SIP)

1. Start services:
   ```bash
   docker compose up -d
   ```

2. Open frontend:
   ```bash
   cd frontend && npm run dev
   ```

3. Access: http://localhost:3000

4. Join room: `ai-agent-room`

5. Speak and get AI response!

### For SIP Testing (With Linphone)

1. Start services (including SIP):
   ```bash
   docker compose --profile sip up -d
   ```

2. Setup SIP:
   ```bash
   python3 setup_sip.py
   ```

3. Configure Linphone with printed settings

4. Call: `+1234567890@YOUR_IP:5060`

5. AI agent answers!

---

## ✅ Success Checklist

- [ ] Using `docker compose` (not `docker-compose`)
- [ ] All services show "healthy" status
- [ ] Backend API responds: `curl http://localhost:8000/health`
- [ ] Ollama accessible from agent container
- [ ] SIP setup script ran successfully
- [ ] Linphone configured correctly
- [ ] Frontend accessible at http://localhost:3000
- [ ] Test call to AI agent works

---

## 🆘 Need Help?

1. Check logs:
   ```bash
   docker compose logs -f
   ```

2. Verify service health:
   ```bash
   docker compose ps
   ```

3. Test connectivity:
   ```bash
   # From inside agent container
   docker compose exec agent-worker bash
   curl http://whisperlive:9090
   curl http://piper-tts:5500/health
   curl http://livekit:7880
   ```

4. See detailed troubleshooting: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
