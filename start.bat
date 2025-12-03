@echo off
echo ============================================================
echo LiveKit AI Voice Agent - Quick Start (Windows)
echo ============================================================
echo.

echo Checking prerequisites...
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker is running

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama is running
) else (
    echo [WARNING] Ollama not detected on localhost
    echo Make sure Ollama is running:
    echo   1. Open Command Prompt
    echo   2. Run: ollama serve
    echo   3. In another terminal: ollama pull llama3.1
    echo.
)

echo.
echo Pulling required images (this may take a few minutes)...
echo.

REM Pull WhisperLive CPU image explicitly
echo Pulling WhisperLive CPU image...
docker pull ghcr.io/collabora/whisperlive-cpu:latest

echo.
echo Starting all services...
echo.

docker-compose up -d

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start services!
    echo.
    echo Troubleshooting steps:
    echo 1. Check Docker Desktop is running
    echo 2. Run: docker-compose down
    echo 3. Run: docker-compose up -d
    echo.
    pause
    exit /b 1
)

echo.
echo Waiting for services to start (30 seconds)...
timeout /t 30 /nobreak >nul

echo.
echo ============================================================
echo Service Status:
echo ============================================================
docker-compose ps

echo.
echo ============================================================
echo Health Checks:
echo ============================================================
echo.
echo Checking Backend API...
curl -s http://localhost:8000/health
echo.
echo.
echo Checking Piper TTS...
curl -s http://localhost:5500/health
echo.

echo.
echo ============================================================
echo Access URLs:
echo ============================================================
echo - Backend API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Health Check: http://localhost:8000/health
echo - Piper TTS: http://localhost:5500
echo - LiveKit Server: http://localhost:7880
echo.
echo ============================================================
echo Useful Commands:
echo ============================================================
echo - View all logs: docker-compose logs -f
echo - View agent logs: docker-compose logs -f agent-worker
echo - Stop services: docker-compose down
echo - Restart services: docker-compose restart
echo.
echo ============================================================
echo.
echo Services started successfully!
echo.
set /p VIEWLOGS="View logs now? (y/n): "
if /i "%VIEWLOGS%"=="y" (
    docker-compose logs -f
) else (
    echo.
    echo To view logs later, run: docker-compose logs -f
    echo.
)
