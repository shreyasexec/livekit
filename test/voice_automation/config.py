"""
Voice AI Test Automation Configuration
"""
import os

# Application URLs
APP_URL = os.getenv("APP_URL", "https://192.168.20.62:3000/")
API_URL = os.getenv("API_URL", "https://192.168.20.62/api")

# STT Service - WhisperLiveKit
WHISPER_WS_URL = os.getenv("WHISPER_WS_URL", "ws://192.168.1.120:8765/")

# LLM Service - Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.1.120:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# TTS Service - Piper
PIPER_URL = os.getenv("PIPER_URL", "http://192.168.20.62:5500/")

# LiveKit Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

# Browser Configuration
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
BROWSER_SLOWMO = int(os.getenv("BROWSER_SLOWMO", "0"))

# Timeouts
RESPONSE_TIMEOUT = int(os.getenv("RESPONSE_TIMEOUT", "15"))
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))
WEBRTC_TIMEOUT = int(os.getenv("WEBRTC_TIMEOUT", "20"))

# Language Support
SUPPORTED_LANGUAGES = ["english", "hindi", "kannada", "marathi"]
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "english")

# Language codes mapping
LANGUAGE_CODES = {
    "english": "en",
    "hindi": "hi",
    "kannada": "kn",
    "marathi": "mr"
}

# Audio Configuration
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2  # 16-bit

# Test Configuration
TEST_ROOM_PREFIX = "test-room-"
TEST_PARTICIPANT_PREFIX = "test-user-"
MAX_CONVERSATION_TURNS = 10

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Performance thresholds (in milliseconds)
PERF_STT_MAX_LATENCY = 2000
PERF_LLM_MAX_LATENCY = 5000
PERF_TTS_MAX_LATENCY = 1000
PERF_E2E_MAX_LATENCY = 8000
