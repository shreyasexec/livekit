# CLAUDE.md - Voice AI Platform

> **Quick Reference**: Essential rules and endpoints. See `docs/` for detailed guides.

---

## 🎯 PROJECT OVERVIEW

**100% on-premises, open-source** LiveKit-based AI voice agent platform.

| Component | Technology | Endpoint |
|-----------|------------|----------|
| STT | WhisperLiveKit | `ws://192.168.1.120:8765/` |
| TTS | Piper | `http://192.168.20.62:5500/` |
| LLM | Ollama (llama3.1:8b) | `http://192.168.1.120:11434` |
| WebRTC | LiveKit Server | `ws://192.168.20.62:7880` |
| Backend | FastAPI | `http://192.168.20.62:8000` |
| Frontend | React/TypeScript | `https://192.168.20.62:3000/` |
| Redis | Redis | `redis://localhost:6379` |
| SIP | LiveKit SIP | `192.168.20.62:5060` (UDP) |

---

## 🚨 CRITICAL RULES

### 1. Documentation-First (MANDATORY)
```
BEFORE making ANY code change:
1. Check official documentation
2. Verify API signatures
3. Look for official examples
4. Search GitHub Issues
```

**Official Docs:**
- LiveKit Agents: https://docs.livekit.io/agents/
- WhisperLive: https://github.com/collabora/WhisperLive
- Piper TTS: https://github.com/rhasspy/piper
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md

### 2. Code Separation (STRICT)
```
livekit/
├── backend/        ◄── DEVELOPMENT ONLY
├── frontend/       ◄── DEVELOPMENT ONLY
├── test/           ◄── TESTING ONLY
└── docs/           ◄── Reference documentation
```

### 3. Technology Constraints
```
⚠️ NO LiveKit Cloud - Self-hosted only
⚠️ NO external APIs - All AI on-prem
⚠️ Use WhisperLiveKit at ws://192.168.1.120:8765/
⚠️ Use Ollama at http://192.168.1.120:11434
⚠️ EMERGENCY CALL system - optimize for latency
```

### 4. Performance Targets
```
VAD:   < 100ms
STT:   < 500ms
LLM:   < 1000ms
TTS:   < 300ms
TOTAL: < 2000ms
```

### 5. Never Create Docs Unprompted
```
❌ Do NOT create README.md, DOCS.md unless asked
✅ Only create code files
```

---

## 📁 PROJECT STRUCTURE

```
livekit/
├── backend/
│   ├── agent/
│   │   ├── worker.py          # Entry point
│   │   ├── stt_handler.py     # WhisperLiveKit
│   │   ├── tts_handler.py     # Piper
│   │   └── llm_handler.py     # Ollama
│   ├── api/routes/
│   │   ├── rooms.py
│   │   ├── tokens.py
│   │   ├── sip.py
│   │   └── transcripts.py
│   ├── config/settings.py
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── room/
│       │   ├── transcript/
│       │   ├── voice-agent/
│       │   ├── sip/
│       │   └── dashboard/
│       └── hooks/
│           ├── useTranscript.ts
│           └── useMetadata.ts
├── test/voice_automation/
│   ├── tests/{api,webrtc,e2e,multilang}/
│   ├── resources/{libraries,keywords,locales}/
│   └── run_tests.sh
├── docs/                      # Detailed references
└── docker-compose.yaml
```

---

## 🔧 QUICK COMMANDS

### Development
```bash
docker-compose up -d                    # Start all
docker-compose logs -f agent-worker     # Agent logs
docker-compose restart agent-worker     # Restart agent
```

### Testing
```bash
cd test/voice_automation
./setup_test.sh                # One-time setup
./run_tests.sh api             # API tests
./run_tests.sh webrtc          # WebRTC tests
./run_tests.sh e2e             # End-to-end
./run_tests.sh multilang       # All languages
./run_tests.sh lang-hindi      # Hindi only
./run_tests.sh all             # Everything
```

### Health Checks
```bash
# Ollama
curl http://192.168.1.120:11434/api/tags

# Piper
curl http://192.168.20.62:5500/health

# WhisperLiveKit
python3 -c "import asyncio,websockets; asyncio.run(websockets.connect('ws://192.168.1.120:8765/'))"

# Backend
curl http://localhost:8000/health
```

---

## 🌐 ENVIRONMENT VARIABLES

### Development (.env in livekit/)
```bash
LIVEKIT_URL=http://livekit:7880
LIVEKIT_PUBLIC_URL=wss://192.168.20.62:7880
OLLAMA_URL=http://192.168.1.120:11434
OLLAMA_MODEL=llama3.1:8b
WHISPERLIVE_URL=ws://192.168.1.120:8765/
PIPER_URL=http://192.168.20.62:5500/
REDIS_URL=redis://redis:6379
```

### Testing (.env in test/voice_automation/)
```bash
APP_URL=https://192.168.20.62:3000/
WHISPER_LIVEKIT_WS_URL=ws://192.168.1.120:8765/
OLLAMA_URL=http://192.168.1.120:11434
PIPER_URL=http://192.168.20.62:5500/
LIVEKIT_URL=ws://192.168.20.62:7880
```

---

## 🔄 ITERATION WORKFLOW

```
RUN TEST → PASS? → Next Test
              ↓ NO
         Analyze Failure
              ↓
    Test code issue? → Fix test → Re-run
              ↓ NO
    Check official docs
              ↓
    Search GitHub Issues
              ↓
    Implement fix (with doc reference)
              ↓
         Re-run test

⚠️ DO NOT STOP until ALL tests pass!
```

---

## 🔧 COMMON FIXES

| Issue | Check | Fix |
|-------|-------|-----|
| API Connection Error | `curl http://192.168.1.120:11434/api/tags` | Check firewall, network |
| No transcription | WhisperLiveKit logs | Restart, wait 30s |
| No TTS output | Piper health endpoint | Rebuild piper-tts |
| Agent not joining | agent-worker logs | Restart agent-worker |
| SIP not connecting | UDP 5060, 10000-20000 | Use `network_mode: host` |
| WebRTC no audio | Browser permissions | Check mic access |
| High latency | Performance metrics | Profile each stage |

---

## ✅ SUCCESS CRITERIA

All must pass before completion:

- [ ] WhisperLiveKit STT working
- [ ] Ollama LLM responding < 1000ms
- [ ] Piper TTS generating audio
- [ ] Full pipeline < 2000ms
- [ ] WebRTC connection established
- [ ] All 4 languages working (EN, HI, KN, MR)
- [ ] E2E scenarios passing
- [ ] UI components functional

---

## 📚 DETAILED DOCUMENTATION

For comprehensive guides, see:

| Document | Content |
|----------|---------|
| `docs/DEVELOPMENT.md` | Code patterns, handlers, hooks |
| `docs/TESTING.md` | Test structure, scenarios, locales |
| `docs/INFRASTRUCTURE.md` | Docker, networking, services |
| `docs/TROUBLESHOOTING.md` | Detailed debug guides |
| `docs/UI_REQUIREMENTS.md` | Component specifications |

---

## 🗣️ MULTI-LANGUAGE SUPPORT

| Language | Code | Voice Model |
|----------|------|-------------|
| English | en | en_US-lessac-medium |
| Hindi | hi | hi_IN-swara-medium |
| Kannada | kn | kn_IN-wavenet |
| Marathi | mr | mr_IN-wavenet |

---

## 📝 KEY FILES TO EDIT

| Purpose | File |
|---------|------|
| Agent logic | `backend/agent/worker.py` |
| STT | `backend/agent/stt_handler.py` |
| TTS | `backend/agent/tts_handler.py` |
| LLM | `backend/agent/llm_handler.py` |
| API | `backend/api/routes/*.py` |
| React | `frontend/src/components/**/*.tsx` |
| Tests | `test/voice_automation/tests/**/*.robot` |

---

**END OF CLAUDE.md** (~6,000 chars - well under 40k limit)