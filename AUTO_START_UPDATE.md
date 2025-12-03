# Auto-Start Configuration Update

## What Changed

I've updated the `docker-compose.yaml` to automatically start **SIP** and **Frontend** services when you run `docker compose up -d`.

---

## Changes Made

### 1. LiveKit SIP Service - Auto-Start Enabled

**Before:**
```yaml
livekit-sip:
  image: livekit/sip:latest
  network_mode: host
  volumes:
    - ./configs/sip.yaml:/sip.yaml
  environment:
    - SIP_CONFIG_FILE=/sip.yaml
  restart: unless-stopped
  profiles:
    - sip  # ← Required --profile sip flag to start
```

**After:**
```yaml
livekit-sip:
  image: livekit/sip:latest
  network_mode: host
  volumes:
    - ./configs/sip.yaml:/sip.yaml
  environment:
    - SIP_CONFIG_FILE=/sip.yaml
  restart: unless-stopped
  depends_on:
    - redis
    - livekit
  # Removed profiles to auto-start with docker compose up
```

**What this means:**
- ✅ SIP service now starts automatically
- ✅ Linphone calling works immediately without extra flags
- ✅ No need for `docker compose --profile sip up -d` anymore

### 2. Frontend Service - Added to Docker Compose

**New service added:**
```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  ports:
    - "3000:3000"
  environment:
    - VITE_LIVEKIT_URL=${VITE_LIVEKIT_URL:-ws://localhost:7880}
    - VITE_API_URL=${VITE_API_URL:-http://localhost:8000}
  depends_on:
    backend:
      condition: service_healthy
  networks:
    - livekit-network
  restart: unless-stopped
```

**What this means:**
- ✅ Frontend (React web UI) starts automatically
- ✅ Available at http://localhost:3000
- ✅ Waits for backend to be healthy before starting
- ✅ Auto-restarts if it crashes

---

## Your Working Configuration Preserved

I carefully preserved all your working changes:

### ✅ WhisperLive Health Check (Socket-based)
```yaml
healthcheck:
  test:
    - CMD-SHELL
    - python3 - <<'PY'
      import socket
      s = socket.socket()
      s.settimeout(2)
      s.connect(("localhost", 9090))
      s.close()
      PY
```
**Status:** ✅ Kept as-is (this is working great!)

### ✅ Agent Worker Command
```yaml
command: ["livekit-agents", "devserver", "agent.worker:server"]
```
**Status:** ✅ Kept as-is (correct LiveKit Agents v1.3+ pattern)

### ✅ WhisperLive `--no_single_model` Flag
```yaml
command:
  - --no_single_model  # Your working config
```
**Status:** ✅ Kept as-is (if it's working for you, don't change it!)

### ✅ Agent Dependency on WhisperLive
```yaml
depends_on:
  whisperlive:
    condition: service_started  # Not service_healthy
```
**Status:** ✅ Kept as-is (smart compromise for faster startup)

---

## New Startup Behavior

### Single Command Starts Everything

```bash
docker compose up -d
```

Now starts **8 services automatically**:

| # | Service | Port | Purpose |
|---|---------|------|---------|
| 1 | **redis** | 6379 | Message broker |
| 2 | **livekit** | 7880, 7881 | LiveKit server |
| 3 | **livekit-sip** | 5060 | SIP for Linphone |
| 4 | **whisperlive** | 9090 | Speech-to-Text |
| 5 | **piper-tts** | 5500 | Text-to-Speech |
| 6 | **agent-worker** | - | AI agent pipeline |
| 7 | **backend** | 8000 | REST API |
| 8 | **frontend** | 3000 | Web UI |

### Startup Order (with dependencies)

```
1. redis (independent)
   ↓
2. livekit (waits for redis)
   ↓
3. livekit-sip (waits for livekit + redis)
   whisperlive (independent)
   piper-tts (independent)
   ↓
4. agent-worker (waits for livekit, redis, whisperlive, piper-tts)
   backend (waits for livekit, redis)
   ↓
5. frontend (waits for backend)
```

**Total startup time:** ~60-90 seconds for all services

---

## Testing the New Configuration

### 1. Restart Services

```bash
# Stop all services
docker compose down

# Start with new auto-start configuration
docker compose up -d

# Monitor startup
docker compose logs -f
```

### 2. Verify All Services Running

```bash
docker compose ps
```

**Expected output:**
```
NAME                       STATUS
livekit-redis-1            Up X minutes (healthy)
livekit-livekit-1          Up X minutes (healthy)
livekit-livekit-sip-1      Up X minutes  ← NEW (auto-started)
livekit-whisperlive-1      Up X minutes
livekit-piper-tts-1        Up X minutes (healthy)
livekit-agent-worker-1     Up X minutes
livekit-backend-1          Up X minutes (healthy)
livekit-frontend-1         Up X minutes  ← NEW (auto-started)
```

### 3. Test Frontend Access

```bash
# Check frontend is running
curl http://localhost:3000

# Or open in browser
# Windows: start http://localhost:3000
# Ubuntu: xdg-open http://localhost:3000
```

### 4. Test SIP Calling

**Configure Linphone:**
- Domain: `YOUR_IP:5060`
- Username: any
- Transport: UDP

**Make test call:**
```
+1234567890@YOUR_IP:5060
```

SIP service is now running automatically, ready for calls!

---

## Environment Variables

All variables are already configured in `.env`:

```env
# Frontend (already configured)
VITE_LIVEKIT_URL=ws://localhost:7880
VITE_API_URL=http://localhost:8000
```

If you need to customize:
```bash
# Edit .env file
nano .env

# Restart services to apply changes
docker compose down
docker compose up -d
```

---

## Benefits of Auto-Start

### Before (Manual Start)
```bash
# Start core services
docker compose up -d

# Start SIP separately
docker compose --profile sip up -d

# Start frontend separately
cd frontend
npm install
npm run dev
```

### After (Auto-Start) ✅
```bash
# One command does everything!
docker compose up -d
```

**Advantages:**
- ✅ **Simpler workflow** - Single command
- ✅ **Consistent environment** - All services in Docker
- ✅ **Auto-restart** - Services recover from crashes
- ✅ **Proper dependencies** - Services start in correct order
- ✅ **Ready for production** - No manual npm commands needed

---

## Troubleshooting

### Frontend Build Issues

If frontend fails to build:
```bash
# Check logs
docker compose logs frontend

# Common fix: Clear node_modules
cd frontend
rm -rf node_modules package-lock.json
cd ..

# Rebuild
docker compose build frontend
docker compose up -d frontend
```

### SIP Not Accessible

If Linphone can't connect:
```bash
# Check SIP service is running
docker compose ps livekit-sip

# Check logs
docker compose logs livekit-sip

# Verify configs/sip.yaml is correct
cat configs/sip.yaml
```

### Port Conflicts

If ports 3000 or 5060 are in use:

**Change frontend port:**
```yaml
frontend:
  ports:
    - "3001:3000"  # Use 3001 on host
```

**Change SIP port** (in configs/sip.yaml):
```yaml
sip_port: 5061  # Instead of 5060
```

---

## Reverting Changes (If Needed)

If you want to go back to manual control:

### Disable SIP Auto-Start
```yaml
livekit-sip:
  # ... other config ...
  profiles:
    - sip  # Add this line back
```

### Disable Frontend Auto-Start
```yaml
frontend:
  # ... other config ...
  profiles:
    - frontend  # Add this line
```

Then start manually:
```bash
docker compose up -d  # Core services only
docker compose --profile sip up -d  # Add SIP
docker compose --profile frontend up -d  # Add frontend
```

---

## Updated Documentation

I've updated these files to reflect the auto-start configuration:

1. **COMMANDS.md** - Updated startup commands
2. **QUICKSTART.md** - Updated 5-minute guide
3. **docker-compose.yaml** - Added frontend, enabled SIP auto-start

---

## Summary

**What you get now:**

✅ **Full platform with one command**: `docker compose up -d`
- All 8 services start automatically
- SIP ready for Linphone calls
- Frontend accessible at http://localhost:3000
- Proper startup order with dependencies
- Auto-restart on failures

✅ **Your working configuration preserved:**
- WhisperLive socket-based health check
- Agent worker command pattern
- `--no_single_model` flag
- Service dependencies

✅ **No breaking changes:**
- All your fixes are intact
- Same .env configuration
- Same port mappings
- Same network setup

**Next steps:**
1. Run `docker compose down && docker compose up -d`
2. Wait 60-90 seconds for all services
3. Access frontend: http://localhost:3000
4. Configure Linphone and make a test call
5. Enjoy! 🎉

---

**Files modified:**
- `docker-compose.yaml` - SIP auto-start + frontend service
- `COMMANDS.md` - Updated startup documentation
- `QUICKSTART.md` - Updated quick start guide

**Files NOT modified (your working config):**
- All backend code
- All agent worker code
- All configuration files (.env, livekit.yaml, sip.yaml)
- All existing services (redis, livekit, whisperlive, piper-tts, backend)
