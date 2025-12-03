# Quick Command Reference

## 🚀 Starting Services

### Start Everything
```bash
docker compose up -d
```

### Start Specific Services
```bash
# Backend services only
docker compose up -d redis livekit backend

# AI pipeline only
docker compose up -d whisperlive piper-tts agent-worker

# Frontend only
docker compose up -d frontend
```

### Start with SIP
```bash
docker compose --profile sip up -d
```

---

## 🛑 Stopping Services

### Stop All
```bash
docker compose down
```

### Stop and Remove Volumes
```bash
docker compose down -v
```

### Stop Specific Service
```bash
docker compose stop agent-worker
```

---

## 🔄 Restarting Services

### Restart All
```bash
docker compose restart
```

### Restart Specific Service
```bash
docker compose restart agent-worker
docker compose restart backend
docker compose restart whisperlive
```

### Rebuild and Restart
```bash
docker compose up -d --build agent-worker
```

---

## 📊 Monitoring

### View Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f agent-worker
docker compose logs -f backend
docker compose logs -f whisperlive
docker compose logs -f piper-tts

# Last 100 lines
docker compose logs --tail=100 agent-worker

# With timestamps
docker compose logs -f --timestamps agent-worker
```

### Resource Usage
```bash
docker stats
```

---

## 🧪 Testing

### Health Checks
```bash
# Backend API
curl http://localhost:8000/health

# Piper TTS
curl http://localhost:5500/health

# LiveKit Server
curl http://localhost:7880

# Ollama
curl http://localhost:11434/api/tags
```

### Create Room
```bash
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name": "test-room"}'
```

### Generate Token
```bash
curl -X POST http://localhost:8000/api/token \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "test-room",
    "participant_name": "TestUser"
  }'
```

### List Rooms
```bash
curl http://localhost:8000/api/rooms
```

---

## 🔧 Debugging

### Access Container Shell
```bash
docker compose exec agent-worker bash
docker compose exec backend bash
```

### Test Connectivity from Container
```bash
docker compose exec agent-worker curl http://whisperlive:9090
docker compose exec agent-worker curl http://piper-tts:5500/health
docker compose exec agent-worker curl http://livekit:7880
docker compose exec agent-worker curl http://172.17.0.1:11434/api/tags
```

### View Container Inspect
```bash
docker compose exec agent-worker env
docker inspect livekit-agent-worker-1
```

---

## 📦 Managing Images

### Pull Images
```bash
docker compose pull
```

### Pull Specific Image
```bash
docker pull ghcr.io/collabora/whisperlive-cpu:latest
docker pull livekit/livekit-server:latest
```

### List Images
```bash
docker images
```

### Remove Unused Images
```bash
docker image prune -a
```

---

## 🧹 Cleanup

### Remove Everything
```bash
# Stop and remove containers
docker compose down

# Remove volumes (WARNING: deletes data!)
docker compose down -v

# Clean system
docker system prune -a --volumes
```

### Remove Specific Volume
```bash
docker volume rm livekit_redis_data
docker volume rm livekit_piper_voices
```

---

## 🔐 SIP Setup

### Run SIP Setup Script
```bash
python3 setup_sip.py
```

### With Custom Configuration
```bash
# Set environment variables
export SIP_NUMBER="+9876543210"
export AGENT_ROOM="my-ai-room"
export LOCAL_IP="192.168.1.150"

python3 setup_sip.py
```

---

## 🌐 Frontend

### Install Dependencies
```bash
cd frontend
npm install
```

### Start Development Server
```bash
npm run dev
```

### Build for Production
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

---

## 🔍 Quick Diagnostics

### Check All Services Healthy
```bash
docker compose ps | grep -E "healthy|running"
```

### Test Full Stack
```bash
curl http://localhost:8000/health && \
curl http://localhost:5500/health && \
echo "Backend & TTS OK"
```

### Check Logs for Errors
```bash
docker compose logs | grep -i error
docker compose logs | grep -i failed
```

---

## 📝 Common Workflows

### Fresh Start
```bash
docker compose down -v
docker compose pull
docker compose up -d
docker compose ps
```

### Update Single Service
```bash
docker compose build agent-worker
docker compose up -d --no-deps agent-worker
```

### View Real-time Logs
```bash
# Split terminal and run:
# Terminal 1:
docker compose logs -f agent-worker

# Terminal 2:
docker compose logs -f backend

# Terminal 3:
docker compose logs -f whisperlive
```

---

## 💡 Tips

1. **Always use `docker compose` (V2), not `docker-compose` (V1)**
   - ❌ Wrong: `docker-compose up -d`
   - ✅ Correct: `docker compose up -d`
2. **Wait 60 seconds after `up -d` for services to be healthy** (WhisperLive needs time to load model)
3. **Check logs if something doesn't work: `docker compose logs -f`**
4. **Use `--build` flag if you changed code: `docker compose up -d --build`**
5. **Services depend on each other - start in order if having issues**
6. **WhisperLive failing? See WHISPERLIVE_TROUBLESHOOTING.md**

---

## 🆘 Emergency Commands

### Services Won't Start
```bash
docker compose down
docker system prune -f
docker compose up -d
```

### Agent Not Responding
```bash
docker compose restart agent-worker
docker compose logs -f agent-worker
```

### Port Conflicts
```bash
# Find process using port
sudo lsof -i :7880
# Or on Windows:
netstat -ano | findstr :7880

# Kill process or change port in docker-compose.yaml
```

### Out of Disk Space
```bash
docker system df
docker system prune -a --volumes
```
