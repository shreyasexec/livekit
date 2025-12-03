# Troubleshooting Guide

Common issues and solutions for the LiveKit AI Voice Agent platform.

## 🔴 WhisperLive "unexpected EOF" Error

### Problem
```
whisperlive [⣿⣿⣿] Pulling
unexpected EOF
```

### Solutions

**Solution 1: Pre-pull the image**
```bash
# Windows
docker pull ghcr.io/collabora/whisperlive-cpu:latest

# Ubuntu
docker pull ghcr.io/collabora/whisperlive-cpu:latest
```

Then start services:
```bash
docker-compose up -d
```

**Solution 2: Clean Docker cache and retry**
```bash
# Stop all services
docker-compose down

# Clean build cache
docker system prune -a

# Restart Docker Desktop (Windows) or Docker daemon (Linux)
# Windows: Restart Docker Desktop
# Linux: sudo systemctl restart docker

# Try again
docker-compose up -d
```

**Solution 3: Use alternative image source**
If GitHub Container Registry is blocked, you can build WhisperLive locally:

```yaml
# Edit docker-compose.yaml, replace whisperlive service with:
whisperlive:
  build:
    context: https://github.com/collabora/WhisperLive.git
    dockerfile: docker/Dockerfile.cpu
  ports:
    - "9090:9090"
  # ... rest of configuration
```

---

## 🔴 "version is obsolete" Warning

### Problem
```
the attribute `version` is obsolete
```

### Solution
This is just a warning in Docker Compose V2. The configuration has been updated to remove the `version` field. If you still see this, it's safe to ignore.

---

## 🔴 Ollama Not Accessible from Containers

### Problem
Agent worker logs show:
```
Failed to connect to Ollama: Connection refused
```

### Windows Solutions

**Solution 1: Verify Ollama is running on Windows (not WSL)**
```cmd
# Check Ollama status
ollama list

# If not running, start it
ollama serve

# Pull the model
ollama pull llama3.1
```

**Solution 2: Check .env configuration**
```env
# Should be set to:
OLLAMA_URL=http://host.docker.internal:11434
```

**Solution 3: Test connectivity from container**
```cmd
docker-compose exec agent-worker curl http://host.docker.internal:11434/api/tags
```

### Ubuntu Solutions

**Solution 1: Use Docker bridge IP**
```bash
# Edit .env file
OLLAMA_URL=http://172.17.0.1:11434
```

**Solution 2: Use host machine IP**
```bash
# Find your IP
ip addr show | grep "inet " | grep -v 127.0.0.1

# Update .env
OLLAMA_URL=http://192.168.1.XXX:11434
```

**Solution 3: Test Ollama accessibility**
```bash
# From host
curl http://localhost:11434/api/tags

# From container
docker-compose exec agent-worker curl http://172.17.0.1:11434/api/tags
```

---

## 🔴 Port Already in Use

### Problem
```
Error: port is already allocated
```

### Solution

**Find what's using the port:**

Windows:
```cmd
netstat -ano | findstr :7880
taskkill /PID <PID> /F
```

Ubuntu:
```bash
sudo lsof -i :7880
sudo kill <PID>
```

**Or change the port:**
Edit `docker-compose.yaml`:
```yaml
livekit:
  ports:
    - "7881:7880"  # Changed from 7880:7880
```

---

## 🔴 Services Failing Health Checks

### Problem
```
Service unhealthy
```

### Solution

**Check specific service logs:**
```bash
docker-compose logs <service-name>
```

**Common fixes:**

1. **Increase health check timeout:**
```yaml
healthcheck:
  start_period: 60s  # Give more time to start
  interval: 30s
  timeout: 10s
```

2. **Restart the service:**
```bash
docker-compose restart <service-name>
```

3. **Rebuild the service:**
```bash
docker-compose up -d --build <service-name>
```

---

## 🔴 Piper TTS Voice Model Download Fails

### Problem
Piper TTS fails to download voice models during build.

### Solution

**Manual download:**
```bash
# Create voices directory
mkdir -p tts-service/voices

# Download voice model
cd tts-service/voices
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Rebuild
cd ../..
docker-compose up -d --build piper-tts
```

---

## 🔴 SIP Service Fails to Start

### Problem
```
livekit-sip exited with code 1
```

### Solution

**On Windows/Mac:**
SIP uses `network_mode: host` which has limitations. SIP is optional for basic functionality.

**Skip SIP for now:**
```bash
# Start without SIP
docker-compose up -d redis livekit whisperlive piper-tts agent-worker backend
```

**On Ubuntu (if you need SIP):**
```bash
# Start with SIP profile
docker-compose --profile sip up -d
```

---

## 🔴 Agent Worker Crashes

### Problem
```
agent-worker exited with code 1
```

### Solution

**Check logs:**
```bash
docker-compose logs agent-worker
```

**Common issues:**

1. **Missing API keys:**
```bash
# Check .env file has:
LIVEKIT_API_KEY=<your-key>
LIVEKIT_API_SECRET=<your-secret>
```

2. **Can't connect to dependencies:**
```bash
# Restart all services in order
docker-compose down
docker-compose up -d redis
docker-compose up -d livekit
docker-compose up -d whisperlive piper-tts
docker-compose up -d agent-worker backend
```

3. **Python import errors:**
```bash
# Rebuild with no cache
docker-compose build --no-cache agent-worker
docker-compose up -d agent-worker
```

---

## 🔴 Memory/Resource Issues

### Problem
Services running slowly or crashing due to memory.

### Solution

**Check resource usage:**
```bash
docker stats
```

**Increase Docker Desktop resources (Windows/Mac):**
1. Open Docker Desktop
2. Settings → Resources
3. Increase Memory to 8GB+
4. Increase CPU to 4+ cores
5. Apply & Restart

**On Linux:**
```bash
# Check system resources
free -h
df -h

# Clean up Docker
docker system prune -a
docker volume prune
```

---

## 🔴 Complete Reset

### When all else fails:

**Full cleanup:**
```bash
# Stop everything
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove all images
docker system prune -a --volumes

# Pull fresh images
docker pull ghcr.io/collabora/whisperlive-cpu:latest
docker pull livekit/livekit-server:latest
docker pull livekit/sip:latest
docker pull redis:7-alpine

# Start fresh
docker-compose up -d --build
```

---

## 📊 Diagnostic Commands

### Check Service Status
```bash
docker-compose ps
```

### View All Logs
```bash
docker-compose logs -f
```

### View Specific Service Logs
```bash
docker-compose logs -f agent-worker
docker-compose logs -f whisperlive
docker-compose logs -f piper-tts
docker-compose logs -f livekit
```

### Test Connectivity
```bash
# Backend API
curl http://localhost:8000/health

# Piper TTS
curl http://localhost:5500/health

# WhisperLive (should return error, but confirms it's running)
curl http://localhost:9090

# Ollama
curl http://localhost:11434/api/tags
```

### Inspect Container
```bash
docker-compose exec agent-worker bash
# Then inside container:
curl http://whisperlive:9090
curl http://piper-tts:5500/health
curl http://livekit:7880
```

---

## 🆘 Getting Help

If you're still stuck:

1. **Collect diagnostic info:**
```bash
docker-compose ps > status.txt
docker-compose logs > logs.txt
docker system info > system-info.txt
```

2. **Check the documentation:**
   - `README.md` - General documentation
   - `SETUP.md` - Platform-specific setup
   - `CLAUDE.md` - Architecture details

3. **Common log patterns to look for:**
   - `Connection refused` → Service not running
   - `Connection timeout` → Firewall or network issue
   - `Permission denied` → Docker permissions or file access
   - `Cannot allocate memory` → Increase Docker resources
   - `No such file or directory` → Volume mount issue

---

## ✅ Verification Checklist

Use this checklist to verify everything is working:

- [ ] Docker Desktop/Engine is running
- [ ] Ollama is running (`ollama list` works)
- [ ] Model is pulled (`ollama pull llama3.1`)
- [ ] All containers are running (`docker-compose ps`)
- [ ] Backend API is healthy (`curl http://localhost:8000/health`)
- [ ] Piper TTS is healthy (`curl http://localhost:5500/health`)
- [ ] No error logs (`docker-compose logs | grep -i error`)
- [ ] Agent worker is connected to all services

---

## 📝 Logging Best Practices

**Enable debug logging for troubleshooting:**

Edit `docker-compose.yaml`:
```yaml
agent-worker:
  environment:
    - LOG_LEVEL=DEBUG
```

Then restart:
```bash
docker-compose restart agent-worker
docker-compose logs -f agent-worker
```
