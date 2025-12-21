# TESTING.md - Voice AI Platform Testing Guide

## Test Directory Structure

```
test/
└── voice_automation/
    ├── .env                              # Test environment
    ├── requirements_voice_test.txt       # Test dependencies
    ├── config.py                         # Configuration
    │
    ├── resources/
    │   ├── libraries/
    │   │   ├── WhisperLiveKitClient.py   # STT test client
    │   │   ├── OllamaClient.py           # LLM test client
    │   │   ├── PiperTTSClient.py         # TTS test client
    │   │   ├── WebRTCHandler.py          # Browser WebRTC
    │   │   ├── LiveKitClient.py          # LiveKit operations
    │   │   └── PerformanceTracker.py     # Metrics
    │   │
    │   ├── keywords/
    │   │   ├── api_keywords.py           # Direct API tests
    │   │   ├── browser_keywords.py       # Browser automation
    │   │   ├── audio_keywords.py         # TTS/STT keywords
    │   │   ├── webrtc_keywords.py        # WebRTC keywords
    │   │   ├── livekit_keywords.py       # LiveKit keywords
    │   │   └── validation_keywords.py    # Response validation
    │   │
    │   ├── locales/
    │   │   ├── english.py
    │   │   ├── hindi.py
    │   │   ├── kannada.py
    │   │   └── marathi.py
    │   │
    │   └── common.robot
    │
    ├── tests/
    │   ├── api/
    │   │   ├── test_whisper_stt.robot
    │   │   ├── test_ollama_llm.robot
    │   │   ├── test_piper_tts.robot
    │   │   └── test_full_pipeline.robot
    │   │
    │   ├── webrtc/
    │   │   ├── test_webrtc_connect.robot
    │   │   ├── test_webrtc_audio.robot
    │   │   ├── test_webrtc_ui_flow.robot
    │   │   └── test_webrtc_conversation.robot
    │   │
    │   ├── e2e/
    │   │   ├── 01_greeting.robot
    │   │   ├── 02_customer_support.robot
    │   │   ├── 03_booking.robot
    │   │   └── 04_error_handling.robot
    │   │
    │   ├── multilang/
    │   │   ├── test_english.robot
    │   │   ├── test_hindi.robot
    │   │   ├── test_kannada.robot
    │   │   ├── test_marathi.robot
    │   │   └── test_language_switch.robot
    │   │
    │   └── performance/
    │       ├── test_latency.robot
    │       └── test_load.robot
    │
    ├── cli_agent/
    │   └── voice_agent.py
    │
    ├── reports/
    ├── recordings/
    ├── setup_test.sh
    └── run_tests.sh
```

---

## Test Environment Variables

```bash
# test/voice_automation/.env

# Application Under Test
APP_URL=https://192.168.20.62:3000/

# WhisperLiveKit (STT)
WHISPER_LIVEKIT_WS_URL=ws://192.168.1.120:8765/

# Ollama (LLM)
OLLAMA_URL=http://192.168.1.120:11434
OLLAMA_MODEL=llama3.1:8b

# Piper (TTS)
PIPER_URL=http://192.168.20.62:5500/

# LiveKit
LIVEKIT_URL=ws://192.168.20.62:7880
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

# Test Settings
HEADLESS=true
RESPONSE_TIMEOUT=15
DEFAULT_LANGUAGE=english
SUPPORTED_LANGUAGES=english,hindi,kannada,marathi
```

---

## Test Dependencies

```
# requirements_voice_test.txt

# Robot Framework
robotframework>=6.1
robotframework-browser>=17.0

# Audio Processing
soundfile
numpy
scipy

# WebSocket
websockets>=11.0

# HTTP Client
httpx
aiohttp

# Utilities
python-dotenv
pydantic
```

---

## Multi-Language Test Scenarios

### English (locales/english.py)
```python
LANG_CODE = "en"
VOICE_MODEL = "en_US-lessac-medium"

SCENARIOS = {
    "greeting": {
        "name": "Basic Greeting",
        "turns": [
            {
                "user": "Hello, how are you?",
                "expect": ["hello", "hi", "help", "assist"],
                "not_expect": ["error", "sorry"]
            },
            {
                "user": "I am doing great, thank you",
                "expect": ["great", "glad", "help"],
                "not_expect": ["error"]
            },
            {
                "user": "Goodbye, have a nice day",
                "expect": ["bye", "goodbye", "thank", "day"],
                "not_expect": ["error"]
            }
        ]
    },
    "customer_support": {
        "name": "Customer Support Flow",
        "turns": [
            {"user": "I need help with my account", "expect": ["help", "account", "assist"]},
            {"user": "I forgot my password", "expect": ["password", "reset", "email"]},
            {"user": "My email is john@example.com", "expect": ["email", "sent", "link"]},
            {"user": "I received it, thank you", "expect": ["welcome", "else", "help"]},
            {"user": "No, that's all, goodbye", "expect": ["bye", "thank", "day"]}
        ]
    },
    "emergency": {
        "name": "Emergency Call",
        "turns": [
            {"user": "This is an emergency", "expect": ["emergency", "help", "urgent"], "not_expect": ["wait", "hold"]},
            {"user": "I need immediate assistance", "expect": ["immediate", "assist", "help", "connect"]}
        ]
    }
}
```

### Hindi (locales/hindi.py)
```python
LANG_CODE = "hi"
VOICE_MODEL = "hi_IN-swara-medium"

SCENARIOS = {
    "greeting": {
        "name": "हिंदी अभिवादन",
        "turns": [
            {"user": "नमस्ते, आप कैसे हैं?", "expect": ["नमस्ते", "हैलो", "मदद", "सहायता"]},
            {"user": "मैं अच्छा हूं, धन्यवाद", "expect": ["अच्छा", "बढ़िया", "मदद"]},
            {"user": "अलविदा, शुभ दिन", "expect": ["अलविदा", "फिर", "मिलेंगे", "शुभ"]}
        ]
    },
    "customer_support": {
        "name": "ग्राहक सहायता",
        "turns": [
            {"user": "मुझे अपने खाते में मदद चाहिए", "expect": ["खाते", "मदद", "सहायता"]},
            {"user": "मैं अपना पासवर्ड भूल गया", "expect": ["पासवर्ड", "रीसेट", "ईमेल"]},
            {"user": "मेरा ईमेल john@example.com है", "expect": ["ईमेल", "भेजा", "लिंक"]},
            {"user": "मिल गया, धन्यवाद", "expect": ["स्वागत", "और", "मदद"]},
            {"user": "नहीं, बस इतना ही, अलविदा", "expect": ["अलविदा", "धन्यवाद"]}
        ]
    }
}
```

### Kannada (locales/kannada.py)
```python
LANG_CODE = "kn"
VOICE_MODEL = "kn_IN-wavenet"

SCENARIOS = {
    "greeting": {
        "name": "ಕನ್ನಡ ಶುಭಾಶಯ",
        "turns": [
            {"user": "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?", "expect": ["ನಮಸ್ಕಾರ", "ಹಲೋ", "ಸಹಾಯ"]},
            {"user": "ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ, ಧನ್ಯವಾದ", "expect": ["ಚೆನ್ನಾಗಿ", "ಒಳ್ಳೆಯ", "ಸಹಾಯ"]},
            {"user": "ವಿದಾಯ, ಶುಭ ದಿನ", "expect": ["ವಿದಾಯ", "ಮತ್ತೆ", "ಸಿಗೋಣ"]}
        ]
    },
    "customer_support": {
        "name": "ಗ್ರಾಹಕ ಬೆಂಬಲ",
        "turns": [
            {"user": "ನನಗೆ ನನ್ನ ಖಾತೆಯಲ್ಲಿ ಸಹಾಯ ಬೇಕು", "expect": ["ಖಾತೆ", "ಸಹಾಯ"]},
            {"user": "ನಾನು ನನ್ನ ಪಾಸ್‌ವರ್ಡ್ ಮರೆತಿದ್ದೇನೆ", "expect": ["ಪಾಸ್‌ವರ್ಡ್", "ರೀಸೆಟ್"]},
            {"user": "ನನ್ನ ಇಮೇಲ್ john@example.com", "expect": ["ಇಮೇಲ್", "ಕಳುಹಿಸಲಾಗಿದೆ"]},
            {"user": "ಸಿಕ್ಕಿತು, ಧನ್ಯವಾದ", "expect": ["ಸ್ವಾಗತ", "ಬೇರೆ"]},
            {"user": "ಇಲ್ಲ, ಅಷ್ಟೇ, ವಿದಾಯ", "expect": ["ವಿದಾಯ", "ಧನ್ಯವಾದ"]}
        ]
    }
}
```

### Marathi (locales/marathi.py)
```python
LANG_CODE = "mr"
VOICE_MODEL = "mr_IN-wavenet"

SCENARIOS = {
    "greeting": {
        "name": "मराठी अभिवादन",
        "turns": [
            {"user": "नमस्कार, तुम्ही कसे आहात?", "expect": ["नमस्कार", "हॅलो", "मदत"]},
            {"user": "मी चांगला आहे, धन्यवाद", "expect": ["चांगले", "छान", "मदत"]},
            {"user": "निरोप, शुभ दिवस", "expect": ["निरोप", "पुन्हा", "भेटू"]}
        ]
    },
    "customer_support": {
        "name": "ग्राहक सेवा",
        "turns": [
            {"user": "मला माझ्या खात्यात मदत हवी आहे", "expect": ["खाते", "मदत", "सहाय्य"]},
            {"user": "मी माझा पासवर्ड विसरलो", "expect": ["पासवर्ड", "रीसेट", "ईमेल"]},
            {"user": "माझा ईमेल john@example.com आहे", "expect": ["ईमेल", "पाठवले", "लिंक"]},
            {"user": "मिळाले, धन्यवाद", "expect": ["स्वागत", "आणखी"]},
            {"user": "नाही, एवढेच, निरोप", "expect": ["निरोप", "धन्यवाद"]}
        ]
    }
}
```

---

## Test Scripts

### setup_test.sh
```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "🚀 Setting up Voice AI Test Automation..."

python3 -m venv venv
source venv/bin/activate
pip install -r requirements_voice_test.txt
rfbrowser init
mkdir -p reports recordings

echo "✅ Setup complete!"
echo "Run tests: ./run_tests.sh all"
```

### run_tests.sh
```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"
source venv/bin/activate
export $(cat .env | xargs)

if [ "$HEADLESS" = "true" ]; then
    export DISPLAY=:99
    Xvfb :99 -screen 0 1920x1080x24 &
    XVFB_PID=$!
    sleep 2
fi

SUITE="${1:-all}"

case $SUITE in
    api)        robot --outputdir reports tests/api/ ;;
    webrtc)     robot --outputdir reports tests/webrtc/ ;;
    e2e)        robot --outputdir reports tests/e2e/ ;;
    multilang)  robot --outputdir reports tests/multilang/ ;;
    lang-english)  robot --outputdir reports tests/multilang/test_english.robot ;;
    lang-hindi)    robot --outputdir reports tests/multilang/test_hindi.robot ;;
    lang-kannada)  robot --outputdir reports tests/multilang/test_kannada.robot ;;
    lang-marathi)  robot --outputdir reports tests/multilang/test_marathi.robot ;;
    performance)   robot --outputdir reports tests/performance/ ;;
    all)        robot --outputdir reports tests/ ;;
    *)
        echo "Usage: ./run_tests.sh [api|webrtc|e2e|multilang|lang-*|performance|all]"
        exit 1
        ;;
esac

EXIT_CODE=$?
[ -n "$XVFB_PID" ] && kill $XVFB_PID 2>/dev/null
exit $EXIT_CODE
```

---

## Test Commands Quick Reference

| Command | Description |
|---------|-------------|
| `./run_tests.sh api` | Test WhisperLiveKit, Ollama, Piper APIs |
| `./run_tests.sh webrtc` | Test WebRTC connections |
| `./run_tests.sh e2e` | End-to-end conversation tests |
| `./run_tests.sh multilang` | All language tests |
| `./run_tests.sh lang-hindi` | Hindi only |
| `./run_tests.sh performance` | Latency tests |
| `./run_tests.sh all` | Run everything |
| `HEADLESS=false ./run_tests.sh webrtc` | With visible browser |

---

## Success Criteria Checklist

### API Tests
- [ ] WhisperLiveKit connection successful
- [ ] WhisperLiveKit transcription accurate
- [ ] Ollama responds correctly
- [ ] Ollama response time < 1000ms
- [ ] Piper generates audio
- [ ] Full pipeline round-trip < 2000ms

### WebRTC Tests
- [ ] Browser connects to app
- [ ] WebRTC connection established
- [ ] Audio tracks active
- [ ] Audio injection works (headless)

### E2E Tests
- [ ] Greeting scenario passes
- [ ] Customer support scenario passes
- [ ] Booking scenario passes
- [ ] Error handling scenario passes

### Multi-Language Tests
- [ ] English conversations work
- [ ] Hindi conversations work
- [ ] Kannada conversations work
- [ ] Marathi conversations work
- [ ] Language switching works

### Performance Tests
- [ ] VAD latency < 100ms
- [ ] STT latency < 500ms
- [ ] LLM latency < 1000ms
- [ ] TTS latency < 300ms
- [ ] Total round-trip < 2000ms