# Setup Guide - Platform Specific

This guide covers setup for both Windows and Ubuntu/Linux systems.

## 📋 Prerequisites

### Common Requirements
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose V2
- Ollama installed and running
- 8GB+ RAM
- 10GB+ disk space

---

## 🪟 Windows Setup

### 1. Install Prerequisites

**Docker Desktop:**
- Download from: https://www.docker.com/products/docker-desktop/
- Install and start Docker Desktop
- Ensure WSL 2 backend is enabled

**Ollama:**
- Download from: https://ollama.com/download
- Install and it will start automatically
- Open Command Prompt and run:
  ```cmd
  ollama serve
  ollama pull llama3.1
  ```

### 2. Configure Environment

The `.env` file is already configured for Windows with:
```env
OLLAMA_URL=http://host.docker.internal:11434
```

This special hostname `host.docker.internal` allows Docker containers to access services running on your Windows host machine.

### 3. Start Services

**Option 1: Using the batch script**
```cmd
start.bat
```

**Option 2: Manual start**
```cmd
docker-compose up -d
```

### 4. Verify Services

```cmd
REM Check all services
docker-compose ps

REM Check individual services
curl http://localhost:8000/health
curl http://localhost:5500/health

REM View logs
docker-compose logs -f
```

### 5. Common Windows Issues

**Problem: "unexpected EOF" when pulling WhisperLive**
- **Solution**: The docker-compose file now uses CPU version which is more stable
- If issue persists, pull image manually:
  ```cmd
  docker pull ghcr.io/collabora/whisperlive-cpu:latest
  ```

**Problem: Ollama not accessible from containers**
- **Solution**: Make sure Ollama is running on Windows (not in WSL)
- Check: `ollama list` should show your models
- Firewall: Allow Docker to access localhost:11434

**Problem: Port already in use**
- Check what's using the port:
  ```cmd
  netstat -ano | findstr :7880
  ```
- Stop the conflicting service or change ports in docker-compose.yaml

---

## 🐧 Ubuntu/Linux Setup

### 1. Install Prerequisites

**Docker Engine:**
```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Logout and login again, then verify
docker --version
```

**Docker Compose (if not included):**
```bash
# Docker Compose V2 is usually included with Docker Engine
docker compose version

# If not installed:
sudo apt-get install docker-compose-plugin
```

**Ollama:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve &

# Pull model
ollama pull llama3.1
```

### 2. Configure Environment

Edit `.env` file and change Ollama URL:

```bash
# For Ollama running on host
OLLAMA_URL=http://172.17.0.1:11434

# OR use your machine's local IP
OLLAMA_URL=http://192.168.1.120:11434
```

**Find your local IP:**
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

**Docker bridge network IP (usually works):**
```bash
# Docker's default bridge network gateway
# Use: http://172.17.0.1:11434
```

### 3. Make scripts executable

```bash
chmod +x start.sh
```

### 4. Start Services

**Option 1: Using the shell script**
```bash
./start.sh
```

**Option 2: Manual start**
```bash
docker-compose up -d
```

### 5. Verify Services

```bash
# Check all services
docker-compose ps

# Check individual services
curl http://localhost:8000/health
curl http://localhost:5500/health

# View logs
docker-compose logs -f
```

### 6. Common Linux Issues

**Problem: Permission denied on Docker socket**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
```

**Problem: Cannot connect to Ollama from containers**
```bash
# Option 1: Use Docker bridge IP
OLLAMA_URL=http://172.17.0.1:11434

# Option 2: Use host machine IP
ip addr show

# Option 3: Run Ollama with host network binding
ollama serve --host 0.0.0.0

# Check Ollama is accessible
curl http://172.17.0.1:11434/api/tags
```

**Problem: SIP service fails to start**
```bash
# SIP uses host networking which may conflict
# Start without SIP first:
docker-compose up -d redis livekit whisperlive piper-tts agent-worker backend

# Start SIP separately if needed:
docker-compose --profile sip up -d livekit-sip
```

---

## 🔧 Platform-Specific Configuration

### Ollama URL Configuration

| Platform | Recommended URL | Alternative |
|----------|----------------|-------------|
| **Windows** | `http://host.docker.internal:11434` | N/A |
| **macOS** | `http://host.docker.internal:11434` | N/A |
| **Ubuntu/Linux** | `http://172.17.0.1:11434` | `http://YOUR_IP:11434` |

### Network Mode for SIP

The SIP service uses `network_mode: host` which:
- **Works on Linux**: Full access to host network
- **Limited on Windows/Mac**: May have restrictions
- **Solution**: Use SIP profile (it's optional)

To enable SIP on Ubuntu:
```bash
docker-compose --profile sip up -d
```

---

## 🧪 Testing After Setup

### 1. Health Checks

**Windows (Command Prompt):**
```cmd
curl http://localhost:8000/health
curl http://localhost:5500/health
```

**Ubuntu (Terminal):**
```bash
curl http://localhost:8000/health
curl http://localhost:5500/health
```

### 2. Test Ollama Connection

**Check from host:**
```bash
# Windows
curl http://localhost:11434/api/tags

# Ubuntu
curl http://localhost:11434/api/tags
```

**Check from container:**
```bash
# Windows
docker-compose exec agent-worker curl http://host.docker.internal:11434/api/tags

# Ubuntu
docker-compose exec agent-worker curl http://172.17.0.1:11434/api/tags
```

### 3. View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agent-worker
docker-compose logs -f whisperlive
docker-compose logs -f piper-tts
```

---

## 🛠️ Troubleshooting

### Service won't start

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs <service-name>

# Restart a specific service
docker-compose restart <service-name>

# Rebuild and restart
docker-compose up -d --build <service-name>
```

### Clear everything and restart

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Rebuild and start
docker-compose up -d --build
```

### Check resource usage

```bash
# View resource usage
docker stats

# View disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

---

## 📊 Monitoring

### Check Service Health

```bash
# Get health status of all containers
docker-compose ps

# Inspect specific container
docker inspect <container-name> | grep -A 10 Health
```

### View Real-time Logs

```bash
# Follow logs of all services
docker-compose logs -f

# Follow specific service with timestamps
docker-compose logs -f --timestamps agent-worker

# View last 100 lines
docker-compose logs --tail=100 agent-worker
```

---

## 🚀 Next Steps

Once all services are running:

1. **Test the API**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Create a test room**:
   ```bash
   curl -X POST http://localhost:8000/api/rooms \
     -H "Content-Type: application/json" \
     -d '{"name": "test-room"}'
   ```

3. **Generate a token**:
   ```bash
   curl -X POST http://localhost:8000/api/token \
     -H "Content-Type: application/json" \
     -d '{"room_name": "test-room", "participant_name": "TestUser"}'
   ```

4. **Build the frontend** (coming soon)

---

## 📚 Additional Resources

- **Docker Documentation**: https://docs.docker.com/
- **Ollama Documentation**: https://ollama.com/
- **LiveKit Documentation**: https://docs.livekit.io/
- **Project README**: See README.md for full documentation
