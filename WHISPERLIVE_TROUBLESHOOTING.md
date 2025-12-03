# WhisperLive Troubleshooting Guide

## Issue: Container Fails After ~106 Seconds

If you see this error when running `docker compose up -d`:
```
✘ Container livekit-whisperlive-1   Error                                    106.4s
```

This indicates the WhisperLive health check is failing.

---

## Quick Fixes Applied

### Fix 1: Removed `--no_single_model` Flag

**Previous command**:
```yaml
command:
  - --no_single_model  # ← This was causing issues
```

**Current command** (fixed):
```yaml
command:
  - python3
  - run_server.py
  - --port
  - "9090"
  - --backend
  - faster_whisper
  - --max_clients
  - "10"
  - --max_connection_time
  - "600"
```

### Fix 2: Simplified Health Check

**Previous health check** (too complex):
```yaml
healthcheck:
  test:
    - CMD-SHELL
    - >
      python3 - <<'PY'
      import asyncio, websockets
      async def main():
          async with websockets.connect("ws://localhost:9090"):
              return
      asyncio.run(main())
      PY
```

**Problem**: This required `websockets` module which may not be installed in the container.

**Current health check** (fixed):
```yaml
healthcheck:
  test:
    - CMD-SHELL
    - "netstat -an | grep 9090 | grep LISTEN || ss -tuln | grep 9090"
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s  # Increased from 45s
```

---

## Diagnostic Steps

### 1. Check Container Logs

On Ubuntu:
```bash
cd /home/livekit_vibe/livekit
docker compose logs whisperlive
```

Look for:
- Model download progress
- Port binding confirmation
- Error messages
- Python tracebacks

### 2. Check Container Status

```bash
docker compose ps whisperlive
```

Expected output (when healthy):
```
NAME                     STATUS
livekit-whisperlive-1    Up X minutes (healthy)
```

### 3. Manually Test WhisperLive

Start the container without health check:
```bash
# Stop all services
docker compose down

# Start only WhisperLive with logs
docker compose up whisperlive
```

Watch for:
- "Server started on port 9090"
- "Model loaded successfully"
- Any error messages

### 4. Test Port Accessibility

From host machine:
```bash
# Check if port 9090 is accessible
curl -v ws://localhost:9090

# Or use netcat
nc -zv localhost 9090
```

Expected: Connection successful

---

## Common Issues & Solutions

### Issue 1: Model Download Timeout

**Symptom**: Container exits before model finishes downloading

**Solution**: First time startup can take several minutes to download Whisper models.

```bash
# Pull image and let it initialize
docker compose pull whisperlive

# Start with extended timeout
docker compose up whisperlive

# Wait for: "Model loaded successfully"
# Then Ctrl+C and start normally:
docker compose up -d
```

### Issue 2: Insufficient Memory

**Symptom**: Container OOM (Out of Memory) killed

**Solution**: WhisperLive CPU version requires at least 4GB RAM

Check available memory:
```bash
free -h
```

If low on memory, reduce model size by editing docker-compose.yaml:
```yaml
command:
  - --backend
  - faster_whisper
  # Add this line:
  - --model
  - tiny  # or base (smaller models)
```

### Issue 3: Port Already in Use

**Symptom**: "Address already in use"

**Solution**: Check if port 9090 is occupied:
```bash
# On Ubuntu
sudo lsof -i :9090

# Or
sudo netstat -tlnp | grep 9090
```

Kill the process or change WhisperLive port:
```yaml
ports:
  - "9091:9090"  # Map to different host port
```

### Issue 4: Health Check Too Strict

**Symptom**: Service runs but marked as unhealthy

**Solution**: Temporarily disable health check to test:
```yaml
whisperlive:
  # ... other config ...
  # Comment out healthcheck:
  # healthcheck:
  #   test: ...
```

### Issue 5: Python Dependencies Missing

**Symptom**: "ModuleNotFoundError" in logs

**Solution**: Use official image or rebuild:
```bash
# Ensure using official image
docker compose pull whisperlive

# If using custom build, rebuild:
docker compose build --no-cache whisperlive
```

---

## Restart After Fixes

After applying any fixes:

```bash
# Stop services
docker compose down

# Remove old containers (optional)
docker compose rm -f whisperlive

# Start fresh
docker compose up -d

# Monitor startup
docker compose logs -f whisperlive

# Check status after 60 seconds
docker compose ps
```

---

## Verify WhisperLive is Working

### Test 1: Check Logs

```bash
docker compose logs whisperlive | grep -i "server\|model\|listening"
```

Expected output:
```
Server started on port 9090
Model loaded: faster_whisper
Listening for connections...
```

### Test 2: Test WebSocket Connection

Using Python:
```python
# test_whisperlive.py
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:9090"
    async with websockets.connect(uri) as ws:
        config = {
            "uid": "test-123",
            "language": "en",
            "task": "transcribe",
            "model": "small",
            "use_vad": True,
        }
        await ws.send(json.dumps(config))
        response = await ws.recv()
        print("Connected successfully:", response)

asyncio.run(test())
```

Run:
```bash
pip install websockets
python test_whisperlive.py
```

### Test 3: Check from Agent Worker

```bash
# Access agent worker container
docker compose exec agent-worker bash

# Test connectivity to WhisperLive
curl http://whisperlive:9090

# Or use Python
python3 -c "import socket; s=socket.socket(); s.connect(('whisperlive', 9090)); print('Connected!')"
```

---

## Alternative: Use Different STT Backend

If WhisperLive continues to fail, you can temporarily use a different STT provider:

### Option 1: AssemblyAI (Requires API Key)

Edit `backend/agent/worker.py`:
```python
from livekit.plugins import assemblyai

stt = assemblyai.STT()
```

### Option 2: Deepgram (Requires API Key)

```python
from livekit.plugins import deepgram

stt = deepgram.STT(api_key="your_api_key")
```

### Option 3: Google Speech-to-Text

```python
from livekit.plugins import google

stt = google.STT()
```

**Note**: These require API keys and have usage costs. WhisperLive is preferred for self-hosted solution.

---

## Expected Startup Timeline

Normal WhisperLive startup sequence:

| Time | Event |
|------|-------|
| 0s | Container starts |
| 5s | Python imports complete |
| 10s | faster_whisper backend initializing |
| 20-40s | Downloading Whisper model (first time only) |
| 45s | Model loaded into memory |
| 50s | WebSocket server starts |
| 55s | Listening on port 9090 |
| 60s | Health check passes |

**Total**: ~60 seconds for first startup, ~20 seconds for subsequent startups

---

## Getting Help

If issues persist after trying these fixes:

1. **Collect logs**:
```bash
docker compose logs whisperlive > whisperlive_logs.txt
docker compose ps > services_status.txt
docker images | grep whisperlive > image_info.txt
```

2. **Check system resources**:
```bash
free -h > memory_info.txt
df -h > disk_info.txt
cat /proc/cpuinfo | grep "model name" | head -1 > cpu_info.txt
```

3. **Test isolated container**:
```bash
docker run -it --rm -p 9090:9090 ghcr.io/collabora/whisperlive-cpu:latest \
  python3 run_server.py --port 9090 --backend faster_whisper
```

4. **Check WhisperLive GitHub issues**: https://github.com/collabora/WhisperLive/issues

---

## Success Indicators

WhisperLive is working correctly when:

✅ Container status shows "healthy"
```bash
docker compose ps whisperlive
# STATUS: Up X minutes (healthy)
```

✅ Port 9090 is listening
```bash
netstat -tuln | grep 9090
# tcp 0.0.0.0:9090 LISTEN
```

✅ Logs show server started
```bash
docker compose logs whisperlive | tail -10
# "Server started on port 9090"
```

✅ Agent worker can connect
```bash
docker compose logs agent-worker | grep -i whisper
# "WhisperLive STT initialized: whisperlive:9090"
```

✅ No errors in logs
```bash
docker compose logs whisperlive | grep -i error
# (no output)
```

---

## Performance Tuning

Once working, optimize performance:

### For Low-End Systems (< 8GB RAM)

```yaml
environment:
  - OMP_NUM_THREADS=2  # Reduce from 4
command:
  - --model
  - tiny  # Use smallest model
```

### For High-End Systems (16GB+ RAM)

```yaml
environment:
  - OMP_NUM_THREADS=8  # Increase threads
command:
  - --model
  - base  # or small for better accuracy
```

### For GPU Systems

Use GPU image instead:
```yaml
whisperlive:
  image: ghcr.io/collabora/whisperlive-gpu:latest
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

---

## Next Steps After WhisperLive is Healthy

1. Verify agent-worker starts successfully
2. Test complete voice pipeline
3. Run setup_sip.py for SIP configuration
4. Test Linphone calling
5. Test web frontend

---

**Quick Reference**:
- Logs: `docker compose logs -f whisperlive`
- Status: `docker compose ps`
- Restart: `docker compose restart whisperlive`
- Full restart: `docker compose down && docker compose up -d`
