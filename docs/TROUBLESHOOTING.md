# TROUBLESHOOTING.md - Voice AI Platform Debug Guide

## Quick Diagnosis Commands

```bash
# Check all services at once
docker-compose ps
docker-compose logs --tail=50

# Check specific service
docker-compose logs -f agent-worker
docker-compose logs -f backend
docker-compose logs -f livekit
```

---

## Common Issues and Fixes

### 1. "API Error: Connection error" (Ollama)

**Diagnosis:**
```bash
# Check Ollama is running
curl http://192.168.1.120:11434/api/tags

# Check network connectivity
ping 192.168.1.120

# Check from Docker network
docker-compose exec backend curl http://192.168.1.120:11434/api/tags

# Check if port is open
nc -zv 192.168.1.120 11434

# Check firewall
sudo ufw status
sudo iptables -L
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Ollama not running | Start Ollama: `systemctl start ollama` |
| Firewall blocking | `sudo ufw allow from 192.168.20.0/24` |
| Wrong URL | Check OLLAMA_URL in .env |
| Timeout | Increase client timeout to 60s |
| Model not loaded | `curl http://192.168.1.120:11434/api/pull -d '{"name":"llama3.1:8b"}'` |

---

### 2. No Transcription (WhisperLiveKit)

**Diagnosis:**
```bash
# Check WhisperLiveKit connectivity
python3 -c "
import asyncio, websockets
async def check():
    try:
        ws = await websockets.connect('ws://192.168.1.120:8765/')
        print('Connected!')
        await ws.close()
    except Exception as e:
        print(f'Failed: {e}')
asyncio.run(check())
"

# Check from Docker
docker-compose exec agent-worker python3 -c "
import asyncio, websockets
asyncio.run(websockets.connect('ws://192.168.1.120:8765/'))
"
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Service not running | Start WhisperLiveKit container |
| Wrong URL | Check WHISPERLIVE_URL (include trailing /) |
| Connection refused | Check port 8765 is open |
| GPU issue | Check CUDA/GPU drivers |
| Model loading | Wait 30-60s after startup |

---

### 3. No TTS Output (Piper)

**Diagnosis:**
```bash
# Check Piper health
curl http://192.168.20.62:5500/health

# Test TTS synthesis
curl -X POST http://192.168.20.62:5500/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "voice": "en_US-lessac-medium"}' \
  --output test.wav

# Check Piper logs
docker-compose logs piper-tts
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Service not running | `docker-compose restart piper-tts` |
| Missing voice model | Check /voices directory has models |
| Wrong voice name | Verify voice model name in VOICES dict |
| Memory issue | Increase container memory limit |

---

### 4. Agent Not Joining Room

**Diagnosis:**
```bash
# Check agent-worker logs
docker-compose logs -f agent-worker

# Check LiveKit connection
curl http://192.168.20.62:7880

# Verify API credentials
echo "Key: $LIVEKIT_API_KEY"
echo "Secret: $LIVEKIT_API_SECRET"
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Wrong credentials | Regenerate and update .env |
| LiveKit not running | `docker-compose restart livekit` |
| Network issue | Check container networking |
| Code error | Check agent-worker logs for stack trace |

---

### 5. SIP Not Connecting

**Diagnosis:**
```bash
# Check SIP service
docker-compose logs livekit-sip

# Check UDP port
netstat -ulnp | grep 5060
ss -ulnp | grep 5060

# Test SIP port
nc -u -zv 192.168.20.62 5060
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| UDP blocked | Open ports 5060, 10000-20000 UDP |
| Wrong network mode | Use `network_mode: host` for livekit-sip |
| Missing trunk config | Configure SIP trunk via API |
| NAT issue | Configure STUN/TURN |

---

### 6. WebRTC No Audio in Browser

**Diagnosis:**
```bash
# Check browser console for errors
# Common issues in DevTools:
# - "Permission denied" -> Microphone blocked
# - "ICE failed" -> Network/firewall issue
# - "Track ended" -> Audio device issue
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Mic permission | Click allow in browser prompt |
| HTTPS required | Use https:// not http:// |
| ICE failure | Check firewall allows UDP 7882 |
| Self-signed cert | Accept certificate or use --ignore-https-errors |

---

### 7. High Latency

**Diagnosis:**
```bash
# Measure each stage
# In agent logs, look for timing info

# Test Ollama latency
time curl -X POST http://192.168.1.120:11434/api/generate \
  -d '{"model":"llama3.1:8b","prompt":"Hi","stream":false}'

# Test Piper latency
time curl -X POST http://192.168.20.62:5500/api/tts \
  -d '{"text":"Hello world","voice":"en_US-lessac-medium"}' -o /dev/null
```

**Optimization:**

| Stage | Target | Optimization |
|-------|--------|--------------|
| VAD | < 100ms | Use Silero VAD |
| STT | < 500ms | Use streaming mode |
| LLM | < 1000ms | Use smaller context, stream tokens |
| TTS | < 300ms | Use streaming synthesis |

---

### 8. Redis Connection Issues

**Diagnosis:**
```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Check from backend
docker-compose exec backend python3 -c "
import redis
r = redis.from_url('redis://redis:6379')
print(r.ping())
"
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Redis not running | `docker-compose restart redis` |
| Wrong URL | Check REDIS_URL in .env |
| Data corruption | `docker-compose down -v` and restart |

---

### 9. Frontend Build Errors

**Diagnosis:**
```bash
# Check frontend logs
docker-compose logs frontend

# Build locally to see errors
cd frontend
npm install
npm run build
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Missing deps | `npm install` |
| Type errors | Fix TypeScript errors |
| Env vars | Check VITE_* variables |

---

### 10. SSL Certificate Errors

**Diagnosis:**
```bash
# Test HTTPS
curl -k https://192.168.20.62:3000/

# Check certificate
openssl s_client -connect 192.168.20.62:3000
```

**Fixes:**

| Cause | Solution |
|-------|----------|
| Expired cert | Regenerate certificate |
| Wrong domain | Update cert CN to match IP |
| Browser rejection | Use `--ignore-https-errors` in tests |

---

## Full Health Check Script

```bash
#!/bin/bash
# full_health_check.sh

echo "========================================="
echo "Voice AI Platform Health Check"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

check() {
    if $2; then
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "${RED}❌ $1${NC}"
        return 1
    fi
}

# Backend
check "Backend API" "curl -sf http://localhost:8000/health > /dev/null"

# Piper TTS
check "Piper TTS" "curl -sf http://192.168.20.62:5500/health > /dev/null"

# LiveKit
check "LiveKit Server" "curl -sf http://192.168.20.62:7880 > /dev/null 2>&1"

# Ollama
check "Ollama LLM" "curl -sf http://192.168.1.120:11434/api/tags > /dev/null"

# Redis
check "Redis" "docker-compose exec -T redis redis-cli ping > /dev/null 2>&1"

# WhisperLiveKit
check "WhisperLiveKit" "python3 -c \"
import asyncio, websockets
async def c():
    async with websockets.connect('ws://192.168.1.120:8765/', close_timeout=3):
        pass
asyncio.run(c())
\" 2>/dev/null"

# Frontend
check "Frontend" "curl -sfk https://192.168.20.62:3000/ > /dev/null"

echo "========================================="
```

---

## Log Analysis Tips

### Agent Worker Logs
```bash
# Look for these patterns:
docker-compose logs agent-worker | grep -E "(ERROR|Exception|Traceback)"
docker-compose logs agent-worker | grep "connected"
docker-compose logs agent-worker | grep "participant"
```

### LiveKit Logs
```bash
# Connection issues
docker-compose logs livekit | grep -E "(error|failed|connection)"

# Room events
docker-compose logs livekit | grep "room"
```

### Performance Profiling
```bash
# Add timing to agent code:
import time
start = time.perf_counter()
# ... operation ...
print(f"Operation took {(time.perf_counter() - start)*1000:.2f}ms")
```