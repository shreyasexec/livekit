# LiveKit AI Voice & Video Agent Project - CLAUDE.md

## Project Overview

Build a comprehensive LiveKit-based AI communication platform with full voice call, video call, messaging, and AI agent capabilities. The system integrates with SIP for telephony (tested via Linphone), uses self-hosted AI models (Ollama, Whisper, Piper TTS), and provides a feature-rich React frontend with real-time transcription.

---

## Core Voice Agent Architecture

### End-to-End Voice Conversation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LiveKit Room                                     │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  SIP Caller (via Linphone) - Sends Audio Stream                    │    │
│  └────────────────────────────┬───────────────────────────────────────┘    │
│                                │                                             │
│  ┌─────────────────────────────▼──────────────────────────────────────┐    │
│  │  AI Agent Participant (VoicePipelineAgent)                         │    │
│  │  • Receives audio as AudioFrame objects                            │    │
│  │  • Processes through voice pipeline                                │    │
│  │  • Publishes response audio back to room                           │    │
│  └─────────────────────────────┬──────────────────────────────────────┘    │
└──────────────────────────────────┼───────────────────────────────────────────┘
                                   │
                                   │ Audio Frames
                                   │
                     ┌─────────────▼──────────────┐
                     │   Voice Pipeline Agent     │
                     │   (Local Processing)       │
                     └─────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        │                          ▼                          │
        │                ┌──────────────────┐                 │
        │                │  1. VAD (Silero) │                 │
        │                │  Voice Activity  │                 │
        │                │    Detection     │                 │
        │                └────────┬─────────┘                 │
        │                         │                           │
        │                         │ Speech Detected           │
        │                         │                           │
        │                         ▼                           │
        │              ┌───────────────────────┐              │
        │              │  2. STT (WhisperLive) │              │
        │              │  Speech-to-Text       │              │
        │              │  Port: 9090 (WebSocket│              │
        │              └──────────┬────────────┘              │
        │                         │                           │
        │                         │ Transcription Text        │
        │                         │                           │
        │                         ▼                           │
        │                ┌─────────────────────┐              │
        │                │  3. LLM (Ollama)    │              │
        │                │  Language Model     │              │
        │                │  192.168.1.120:11434│              │
        │                └──────────┬──────────┘              │
        │                           │                         │
        │                           │ Response Text           │
        │                           │                         │
        │                           ▼                         │
        │                  ┌─────────────────┐                │
        │                  │  4. TTS (Piper) │                │
        │                  │  Text-to-Speech │                │
        │                  │  Port: 5500     │                │
        │                  └────────┬────────┘                │
        │                           │                         │
        │                           │ Audio Frames            │
        └───────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
                        ┌────────────────────────┐
                        │ Publish Audio to Room  │
                        │ (agent.say() or        │
                        │  session.publish())    │
                        └────────────┬───────────┘
                                     │
                                     │
                    ┌────────────────▼────────────────┐
                    │     LiveKit Room (Broadcast)    │
                    │  • SIP Caller hears response    │
                    │  • Web clients hear response    │
                    │  • Real-time transcripts sent   │
                    └─────────────────────────────────┘
```

### Key Data Flow Points

| Stage | Input | Output | Service | Port |
|-------|-------|--------|---------|------|
| **1. VAD** | AudioFrame (from caller) | Buffered audio chunks | Silero VAD (local) | N/A |
| **2. STT** | Audio chunks | Transcription string | WhisperLive | 9090 |
| **3. LLM** | Transcription text | Response text | Ollama | 11434 |
| **4. TTS** | Response text | AudioFrame stream | Piper | 5500 |
| **5. Publish** | AudioFrame stream | Audio to room | LiveKit | 7880 |

**Critical Flow Requirements:**
1. **Audio Reception**: AI Agent automatically receives audio from LiveKit room participants (including SIP callers)
2. **Sequential Processing**: VAD → STT → LLM → TTS (cannot skip or reorder)
3. **Real-time Publishing**: TTS audio is immediately published back to the room
4. **Bidirectional**: Caller speaks → Agent responds → Caller hears → Caller speaks (continuous loop)

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **WebRTC Server**: LiveKit Server (self-hosted via Docker)
- **SIP Bridge**: LiveKit SIP Server
- **Message Broker**: Redis
- **AI/ML**:
  - **LLM**: Ollama with Llama 3.1 (`http://192.168.1.120:11434`)
  - **STT**: WhisperLive (collabora/WhisperLive - real-time WebSocket-based)
  - **TTS**: Piper TTS (self-hosted)
  - **VAD**: Silero VAD (local, bundled with LiveKit Agents)

### Frontend
- **Framework**: React 18+ with TypeScript
- **LiveKit SDK**: `@livekit/components-react`, `livekit-client`
- **State Management**: React Context/Zustand
- **Styling**: Tailwind CSS

### Infrastructure
- **Containerization**: Docker Compose (NO Kubernetes)
- **Services**: LiveKit Server, LiveKit SIP, Redis, Egress, Ingress, AI Agent Worker, WhisperLive, Piper TTS

---

## Complete System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Linphone/SIP  │────▶│  LiveKit SIP    │────▶│  LiveKit Server │
│   Client        │     │  (Port 5060)    │     │  (Port 7880)    │
│   (Caller)      │◀────│  UDP: 10000-    │◀────│  TCP: 7881      │
└─────────────────┘     │      20000      │     │  UDP: 50000-    │
                        └─────────────────┘     │       60000     │
                                                └────────┬────────┘
                                                         │
┌─────────────────┐                              ┌──────▼─────────┐
│  React Frontend │◀─────────WebRTC─────────────▶│     Redis      │
│  (Port 3000)    │                              │  (Port 6379)   │
│  • Video Grid   │                              └───────┬────────┘
│  • Transcripts  │                                      │
│  • Chat Panel   │                                      │
└─────────────────┘                              ┌───────▼────────┐
                                                 │  AI Agent      │
┌─────────────────┐                              │  Worker        │
│  FastAPI Backend│◀────────REST API────────────▶│  (Python)      │
│  (Port 8000)    │                              └───────┬────────┘
│  • Token Gen    │                                      │
│  • Room Mgmt    │         ┌────────────────────────────┘
│  • SIP Config   │         │
└─────────────────┘         │
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌──────────────┐
│ WhisperLive   │   │  Ollama LLM   │   │  Piper TTS   │
│  STT Server   │   │  (External)   │   │  Server      │
│  (Port 9090)  │   │  (Port 11434) │   │  (Port 5500) │
│  WebSocket    │   │  192.168.1.120│   │  HTTP API    │
└───────────────┘   └───────────────┘   └──────────────┘
```

---

## Required Features Checklist

### Core Communication
- [ ] Voice calls (WebRTC audio tracks)
- [ ] Video calls (WebRTC video tracks)
- [ ] Text messaging (LiveKit Data Channels)
- [ ] Screen sharing
- [ ] Add/remove participants dynamically

### AI Agent Integration
- [ ] Voice Activity Detection (Silero VAD)
- [ ] Speech-to-Text (WhisperLive - real-time WebSocket streaming)
- [ ] LLM Processing (Ollama Llama 3.1)
- [ ] Text-to-Speech (Piper TTS)
- [ ] Real-time transcription display (scrolling UI)
- [ ] Continuous conversation loop (caller ↔ agent)

### SIP/Telephony
- [ ] LiveKit SIP trunk configuration
- [ ] Inbound call handling (from Linphone)
- [ ] Outbound call capability
- [ ] SIP dispatch rules for room routing
- [ ] AI agent auto-join on SIP call

### React Frontend Features
- [ ] Room joining/leaving
- [ ] Audio/video track management
- [ ] Participant grid layout
- [ ] Chat/messaging panel
- [ ] Screen share controls
- [ ] Real-time transcript panel (caller + AI agent)
- [ ] Connection status indicators
- [ ] Device selection (camera, microphone, speaker)

---

## Documentation References

### LiveKit Official Documentation
Always validate against these sources before implementation:

1. **LiveKit Agents SDK**: https://docs.livekit.io/agents/
2. **LiveKit Agents API Reference**: https://docs.livekit.io/agents/api/
3. **LiveKit React Components**: https://docs.livekit.io/reference/components/react/
4. **LiveKit SIP**: https://docs.livekit.io/sip/
5. **Self-hosting LiveKit**: https://docs.livekit.io/home/self-hosting/vm/
6. **Self-hosting SIP Server**: https://docs.livekit.io/home/self-hosting/sip-server/
7. **Ollama Integration**: https://docs.livekit.io/agents/integrations/llm/ollama/
8. **STT Models**: https://docs.livekit.io/agents/integrations/stt/
9. **TTS Models**: https://docs.livekit.io/agents/integrations/tts/
10. **LiveKit Python SDK**: https://github.com/livekit/python-sdks
11. **LiveKit Agents GitHub**: https://github.com/livekit/agents

### WhisperLive Documentation
12. **WhisperLive GitHub**: https://github.com/collabora/WhisperLive
13. **WhisperLive PyPI**: https://pypi.org/project/whisper-live/
14. **WhisperLive Docker Images**:
    - GPU: `ghcr.io/collabora/whisperlive-gpu:latest`
    - CPU: `ghcr.io/collabora/whisperlive-cpu:latest`
    - TensorRT: Build from `docker/Dockerfile.tensorrt`
    - OpenVINO: `ghcr.io/collabora/whisperlive-openvino`

### PyPI Packages
- `livekit-agents>=1.3.0`
- `livekit-plugins-openai` (for Ollama-compatible LLM)
- `livekit-plugins-silero` (VAD)
- `livekit` (Python SDK)
- `livekit-api` (Server API)
- `websockets` (for WhisperLive WebSocket connection)

### NPM Packages
- `@livekit/components-react`
- `livekit-client`

---

## Project Structure

```
livekit-ai-agent/
├── docker-compose.yaml          # Main orchestration
├── .env                         # Environment variables
├── configs/
│   ├── livekit.yaml            # LiveKit server config
│   ├── sip.yaml                # SIP server config
│   ├── egress.yaml             # Egress service config
│   └── ingress.yaml            # Ingress service config
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── rooms.py            # Room management endpoints
│   │   ├── tokens.py           # Token generation
│   │   ├── sip.py              # SIP management
│   │   └── transcripts.py      # Transcript storage/retrieval
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── worker.py           # Agent worker entry point
│   │   ├── voice_agent.py      # Main AI agent logic
│   │   ├── stt_handler.py      # WhisperLive STT integration
│   │   ├── tts_handler.py      # Piper TTS integration
│   │   └── llm_handler.py      # Ollama LLM integration
│   └── services/
│       ├── __init__.py
│       ├── livekit_service.py  # LiveKit API wrapper
│       └── redis_service.py    # Redis for transcripts
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   ├── components/
│   │   │   ├── VideoConference.tsx
│   │   │   ├── ParticipantTile.tsx
│   │   │   ├── ControlBar.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── TranscriptPanel.tsx
│   │   │   ├── DeviceSelector.tsx
│   │   │   └── ScreenShare.tsx
│   │   ├── hooks/
│   │   │   ├── useRoom.ts
│   │   │   ├── useTranscript.ts
│   │   │   └── useParticipants.ts
│   │   ├── context/
│   │   │   └── RoomContext.tsx
│   │   └── services/
│   │       └── api.ts
│   └── public/
├── stt-service/                 # WhisperLive STT service
│   ├── Dockerfile
│   └── config.yaml
└── tts-service/                 # Piper TTS service
    ├── Dockerfile
    └── config/
```

---

## Implementation Guidelines

### 1. Docker Compose Setup

**CRITICAL**: All services must use Docker Compose. No Kubernetes.

```yaml
# docker-compose.yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - livekit-network

  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"
      - "7881:7881"
      - "50000-50100:50000-50100/udp"
    volumes:
      - ./configs/livekit.yaml:/livekit.yaml
    command: --config /livekit.yaml
    environment:
      - LIVEKIT_CONFIG=/livekit.yaml
    depends_on:
      - redis
    networks:
      - livekit-network

  livekit-sip:
    image: livekit/sip:latest
    network_mode: host  # Required for SIP UDP port handling
    volumes:
      - ./configs/sip.yaml:/sip.yaml
    environment:
      - SIP_CONFIG_FILE=/sip.yaml
    depends_on:
      - redis
      - livekit

  # WhisperLive STT Service (Real-time WebSocket-based)
  whisperlive:
    image: ghcr.io/collabora/whisperlive-gpu:latest
    # For CPU-only environments, use:
    # image: ghcr.io/collabora/whisperlive-cpu:latest
    ports:
      - "9090:9090"
    environment:
      - OMP_NUM_THREADS=4
      - WHISPER_MODEL=small
    command: >
      python3 run_server.py
      --port 9090
      --backend faster_whisper
      --max_clients 10
      --max_connection_time 600
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    # Remove deploy section for CPU-only
    networks:
      - livekit-network

  # Piper TTS Service
  piper-tts:
    build:
      context: ./tts-service
      dockerfile: Dockerfile
    ports:
      - "5500:5500"
    volumes:
      - ./tts-service/voices:/app/voices
    environment:
      - PIPER_VOICE=en_US-lessac-medium
    networks:
      - livekit-network

  # AI Agent Worker
  agent-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - LIVEKIT_URL=ws://livekit:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - REDIS_URL=redis://redis:6379
      - OLLAMA_URL=http://192.168.1.120:11434
      - WHISPERLIVE_HOST=whisperlive
      - WHISPERLIVE_PORT=9090
      - PIPER_URL=http://piper-tts:5500
    depends_on:
      - livekit
      - redis
      - whisperlive
      - piper-tts
    command: python -m agent.worker
    networks:
      - livekit-network

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - LIVEKIT_URL=http://livekit:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - livekit
      - redis
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    networks:
      - livekit-network

  # React Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - VITE_LIVEKIT_URL=ws://localhost:7880
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - livekit-network

networks:
  livekit-network:
    driver: bridge

volumes:
  redis_data:
```

**WhisperLive Backend Options:**

| Backend | Docker Image | Use Case | Performance |
|---------|-------------|----------|-------------|
| faster_whisper | `whisperlive-gpu` or `whisperlive-cpu` | General purpose, good balance | Medium-High |
| tensorrt | Build from Dockerfile.tensorrt | Maximum GPU performance | Highest |
| openvino | `whisperlive-openvino` | Intel CPU/GPU optimization | Medium |

### 2. LiveKit Server Configuration

```yaml
# configs/livekit.yaml
port: 7880
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 50100
  use_external_ip: true
  # For local testing, use local IP
  # node_ip: 192.168.1.100

redis:
  address: redis:6379

keys:
  # Generate with: openssl rand -base64 32
  APIKeyHere: SecretKeyHere

logging:
  level: info
  json: false
  sample: false

room:
  auto_create: true
  empty_timeout: 300
  max_participants: 50

# Enable agent dispatch
agent_dispatch:
  enabled: true
  # Agent will auto-join rooms
```

### 3. SIP Server Configuration

```yaml
# configs/sip.yaml
log_level: debug
api_key: APIKeyHere
api_secret: SecretKeyHere
ws_url: ws://livekit:7880
redis:
  address: redis:6379
sip_port: 5060
rtp_port_range_start: 10000
rtp_port_range_end: 20000
use_external_ip: true
# For local testing
# local_ip: 192.168.1.100
```

### 4. AI Agent Implementation (Voice Pipeline)

**Main Agent Worker** (handles the complete voice conversation loop):

```python
# backend/agent/worker.py
import asyncio
import logging
from typing import AsyncIterable
from livekit import agents, rtc
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    tokenize,
    tts,
)
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero

# Import custom STT/TTS handlers
from .stt_handler import WhisperLiveSTT
from .tts_handler import PiperTTS
from .llm_handler import OllamaLLM

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantFunctions:
    """Functions that the AI agent can call during conversations"""

    @agents.llm.ai_callable()
    async def get_weather(
        self,
        location: str,
    ) -> str:
        """Get current weather for a location.

        Args:
            location: City name or location
        """
        # Implement weather API call
        return f"The weather in {location} is sunny, 72°F"

async def get_transcript_storage(room: rtc.Room, participant: rtc.Participant):
    """Store transcripts in Redis or database"""
    # Implementation for transcript storage
    pass

async def entrypoint(ctx: JobContext):
    """
    Main entry point for the AI voice agent.

    This agent:
    1. Joins the LiveKit room
    2. Listens to audio from participants (including SIP callers)
    3. Processes speech through: VAD → STT → LLM → TTS
    4. Publishes response audio back to the room
    5. Sends transcripts via data channel for UI display
    """
    logger.info(f"Agent connecting to room: {ctx.room.name}")

    # Initialize the agent
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)

    # Create the voice assistant with full pipeline
    assistant = VoiceAssistant(
        # Voice Activity Detection (local, no external service)
        vad=silero.VAD.load(),

        # Speech-to-Text (WhisperLive via WebSocket)
        stt=WhisperLiveSTT(
            host="whisperlive",  # Docker service name
            port=9090,
            lang="en",
            model="small",
            use_vad=True,
        ),

        # Language Model (Ollama - external server)
        llm=OllamaLLM(
            model="llama3.1",
            base_url="http://192.168.1.120:11434",
        ),

        # Text-to-Speech (Piper TTS)
        tts=PiperTTS(
            base_url="http://piper-tts:5500",
            voice="en_US-lessac-medium",
        ),

        # Optional: Add callable functions
        fnc_ctx=AssistantFunctions(),

        # Chat context with initial instructions
        chat_ctx=ChatContext(
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        "You are a helpful AI assistant for the Trinity smart city platform. "
                        "You help users with information about city services, weather, "
                        "transportation, and general inquiries. "
                        "Keep your responses concise and natural for voice conversation. "
                        "Speak in a friendly, conversational tone."
                    ),
                )
            ]
        ),
    )

    # Start the assistant
    assistant.start(ctx.room)

    # Monitor room events
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant connected: {participant.identity}")

        # Check if this is a SIP caller
        if participant.kind == rtc.ParticipantKind.SIP:
            logger.info("SIP caller joined - agent will respond to their audio")

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant disconnected: {participant.identity}")

    # Handle user speech (from STT)
    @assistant.on("user_speech_committed")
    def on_user_speech(msg: str):
        logger.info(f"User said: {msg}")

        # Send transcript to frontend via data channel
        ctx.room.local_participant.publish_data(
            payload=json.dumps({
                "type": "transcript",
                "speaker": "user",
                "text": msg,
                "timestamp": datetime.utcnow().isoformat(),
            }).encode("utf-8"),
            topic="transcripts",
        )

    # Handle agent speech (from TTS)
    @assistant.on("agent_speech_committed")
    def on_agent_speech(msg: str):
        logger.info(f"Agent said: {msg}")

        # Send transcript to frontend via data channel
        ctx.room.local_participant.publish_data(
            payload=json.dumps({
                "type": "transcript",
                "speaker": "agent",
                "text": msg,
                "timestamp": datetime.utcnow().isoformat(),
            }).encode("utf-8"),
            topic="transcripts",
        )

    # Greet the user when they join
    await assistant.say(
        "Hello! I'm the Trinity assistant. How can I help you today?",
        allow_interruptions=True,
    )

    logger.info("Agent is ready and listening...")

if __name__ == "__main__":
    # Run the agent worker
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Configure worker
            request_fnc=None,  # Use default job assignment
            prewarm_fnc=None,  # No prewarming needed
        )
    )
```

### 5. Custom STT (WhisperLive) Integration

**WhisperLive Plugin Implementation**:

```python
# backend/agent/stt_handler.py
"""
Custom STT plugin for WhisperLive integration with LiveKit Agents.

WhisperLive provides real-time streaming transcription via WebSocket.
This plugin connects to a WhisperLive server and streams audio for transcription.
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncIterator, Optional
import websockets
import numpy as np
from livekit import agents
from livekit.agents import stt, utils

logger = logging.getLogger(__name__)


class WhisperLiveSTT(stt.STT):
    """
    Speech-to-Text implementation using WhisperLive WebSocket server.

    WhisperLive provides real-time streaming transcription with support for:
    - Multiple backends (faster_whisper, tensorrt, openvino)
    - Voice Activity Detection (VAD)
    - Multiple languages
    - Real-time streaming with interim results
    """

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 9090,
        lang: str = "en",
        model: str = "small",
        use_vad: bool = True,
        translate: bool = False,
    ):
        """
        Initialize WhisperLive STT.

        Args:
            host: WhisperLive server hostname (use Docker service name in compose)
            port: WhisperLive server port (default 9090)
            lang: Language code (en, es, fr, de, etc.)
            model: Whisper model size (tiny, base, small, medium, large)
            use_vad: Enable Voice Activity Detection on server side
            translate: Translate to English (default False)
        """
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
            )
        )
        self._host = host
        self._port = port
        self._lang = lang
        self._model = model
        self._use_vad = use_vad
        self._translate = translate
        self._sample_rate = 16000  # WhisperLive expects 16kHz

        logger.info(
            f"WhisperLive STT initialized: {host}:{port}, "
            f"model={model}, lang={lang}, vad={use_vad}"
        )

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: Optional[str] = None,
    ) -> stt.SpeechEvent:
        """
        Recognize speech from audio buffer (non-streaming mode).

        Args:
            buffer: Audio buffer containing the audio to transcribe
            language: Override language for this request

        Returns:
            SpeechEvent with final transcription
        """
        # Create a streaming session and process all audio at once
        stream = self.stream(language=language)

        async with stream:
            # Push all frames from buffer
            for frame in buffer:
                await stream.push_frame(frame)

            # Flush and get final result
            await stream.flush()

            # Collect all events and return the last one
            final_event = None
            async for event in stream:
                if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                    final_event = event

            if final_event:
                return final_event
            else:
                # Return empty result if no transcription
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[stt.SpeechData(text="", language=language or self._lang)],
                )

    def stream(
        self,
        *,
        language: Optional[str] = None,
    ) -> "WhisperLiveSTTStream":
        """
        Create a new streaming STT session.

        Args:
            language: Override default language for this stream

        Returns:
            WhisperLiveSTTStream instance
        """
        return WhisperLiveSTTStream(
            stt=self,
            language=language or self._lang,
        )


class WhisperLiveSTTStream(stt.SpeechStream):
    """
    Streaming interface for WhisperLive STT.

    Handles:
    - WebSocket connection to WhisperLive server
    - Real-time audio streaming
    - Receiving transcription events (interim and final)
    """

    def __init__(
        self,
        *,
        stt: WhisperLiveSTT,
        language: str,
    ):
        super().__init__()
        self._stt = stt
        self._language = language
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session_id = str(uuid.uuid4())
        self._closed = False
        self._recv_task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue = asyncio.Queue()

        logger.debug(f"Created WhisperLive stream: session_id={self._session_id}")

    async def _connect(self):
        """Establish WebSocket connection to WhisperLive server."""
        uri = f"ws://{self._stt._host}:{self._stt._port}"

        try:
            self._ws = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=10,
            )

            # Send initial configuration
            config = {
                "uid": self._session_id,
                "language": self._language,
                "task": "translate" if self._stt._translate else "transcribe",
                "model": self._stt._model,
                "use_vad": self._stt._use_vad,
            }

            await self._ws.send(json.dumps(config))
            logger.info(f"Connected to WhisperLive: {uri}, config={config}")

            # Start receiving transcriptions
            self._recv_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            logger.error(f"Failed to connect to WhisperLive: {e}")
            raise

    async def _receive_loop(self):
        """Background task to receive transcription events from WhisperLive."""
        try:
            async for message in self._ws:
                if self._closed:
                    break

                try:
                    data = json.loads(message)

                    # WhisperLive sends segments with transcriptions
                    if "segments" in data:
                        segments = data["segments"]
                        if segments:
                            # Process the latest segment
                            latest = segments[-1]
                            text = latest.get("text", "").strip()

                            if text:
                                # Determine if this is final or interim
                                # WhisperLive marks completed segments
                                is_final = latest.get("completed", False)

                                event = stt.SpeechEvent(
                                    type=(
                                        stt.SpeechEventType.FINAL_TRANSCRIPT
                                        if is_final
                                        else stt.SpeechEventType.INTERIM_TRANSCRIPT
                                    ),
                                    alternatives=[
                                        stt.SpeechData(
                                            text=text,
                                            language=self._language,
                                        )
                                    ],
                                )

                                await self._event_queue.put(event)
                                logger.debug(
                                    f"Transcription: '{text}' (final={is_final})"
                                )

                    # Handle end of transcription signal
                    if data.get("eof"):
                        logger.info("Received EOF from WhisperLive")
                        break

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from WhisperLive: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WhisperLive connection closed")
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
        finally:
            # Signal end of stream
            await self._event_queue.put(None)

    async def _main_task(self):
        """Main task that handles the stream lifecycle."""
        await self._connect()

        # Wait for the receive task to complete
        try:
            if self._recv_task:
                await self._recv_task
        except asyncio.CancelledError:
            pass

    async def aclose(self):
        """Close the stream and cleanup resources."""
        if self._closed:
            return

        self._closed = True

        # Cancel receive task
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self._ws and not self._ws.closed:
            try:
                # Send EOF signal
                await self._ws.send(json.dumps({"eof": True}))
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")

        logger.debug(f"Closed WhisperLive stream: session_id={self._session_id}")

    async def push_frame(self, frame: agents.AudioFrame):
        """
        Push audio frame to WhisperLive for transcription.

        Args:
            frame: Audio frame (will be resampled to 16kHz if needed)
        """
        if self._closed or not self._ws:
            return

        try:
            # Resample to 16kHz if needed (WhisperLive requirement)
            if frame.sample_rate != self._stt._sample_rate:
                # Use LiveKit's audio resampling
                frame = frame.remix_and_resample(
                    sample_rate=self._stt._sample_rate,
                    num_channels=1,
                )

            # Convert to bytes (int16 PCM)
            audio_array = np.frombuffer(frame.data, dtype=np.int16)
            audio_bytes = audio_array.tobytes()

            # Send audio data
            await self._ws.send(audio_bytes)

        except Exception as e:
            logger.error(f"Error pushing frame to WhisperLive: {e}")

    async def flush(self):
        """Signal end of audio input."""
        if self._closed or not self._ws:
            return

        try:
            # Send flush signal to WhisperLive
            await self._ws.send(json.dumps({"eof": True}))
            logger.debug("Flushed WhisperLive stream")
        except Exception as e:
            logger.warning(f"Error flushing stream: {e}")

    async def __anext__(self) -> stt.SpeechEvent:
        """
        Get next transcription event.

        Returns:
            SpeechEvent with transcription

        Raises:
            StopAsyncIteration: When stream is closed
        """
        event = await self._event_queue.get()

        if event is None:
            raise StopAsyncIteration

        return event
```

### 6. Custom LLM (Ollama) Integration

```python
# backend/agent/llm_handler.py
"""
Custom LLM plugin for Ollama integration with LiveKit Agents.

Ollama provides local LLM inference with API compatible with OpenAI.
"""

import logging
import json
from typing import List, Optional, AsyncIterable
import httpx
from livekit.agents import llm

logger = logging.getLogger(__name__)


class OllamaLLM(llm.LLM):
    """
    Language Model implementation using Ollama.

    Ollama provides local LLM inference with models like:
    - llama3.1, llama3, llama2
    - mistral, mixtral
    - codellama, phi, gemma
    """

    def __init__(
        self,
        *,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        timeout: float = 30.0,
    ):
        """
        Initialize Ollama LLM.

        Args:
            model: Ollama model name (must be pulled first with `ollama pull`)
            base_url: Ollama server URL
            temperature: Sampling temperature (0.0 to 1.0)
            timeout: Request timeout in seconds
        """
        super().__init__()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._timeout = timeout

        logger.info(
            f"Ollama LLM initialized: model={model}, url={base_url}"
        )

    async def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        fnc_ctx: Optional[llm.FunctionContext] = None,
        temperature: Optional[float] = None,
        n: int = 1,
    ) -> "OllamaLLMStream":
        """
        Start a chat completion with streaming.

        Args:
            chat_ctx: Chat context with message history
            fnc_ctx: Function calling context (optional)
            temperature: Override default temperature
            n: Number of completions (not supported in streaming)

        Returns:
            OllamaLLMStream for streaming responses
        """
        return OllamaLLMStream(
            llm=self,
            chat_ctx=chat_ctx,
            fnc_ctx=fnc_ctx,
            temperature=temperature or self._temperature,
        )


class OllamaLLMStream(llm.LLMStream):
    """
    Streaming interface for Ollama chat completions.
    """

    def __init__(
        self,
        *,
        llm: OllamaLLM,
        chat_ctx: llm.ChatContext,
        fnc_ctx: Optional[llm.FunctionContext],
        temperature: float,
    ):
        super().__init__(chat_ctx=chat_ctx, fnc_ctx=fnc_ctx)
        self._llm = llm
        self._temperature = temperature
        self._client = httpx.AsyncClient(timeout=llm._timeout)
        self._response_text = ""

    async def _main_task(self):
        """Main task that performs the chat completion."""
        try:
            # Convert chat context to Ollama format
            messages = []
            for msg in self._chat_ctx.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

            # Prepare request
            request_data = {
                "model": self._llm._model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": self._temperature,
                },
            }

            # Add function calling if provided
            if self._fnc_ctx and self._fnc_ctx.ai_functions:
                # Convert functions to Ollama tools format
                tools = []
                for func in self._fnc_ctx.ai_functions.values():
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": func.name,
                            "description": func.description,
                            "parameters": func.parameters,
                        },
                    })
                request_data["tools"] = tools

            # Make streaming request to Ollama
            url = f"{self._llm._base_url}/api/chat"

            async with self._client.stream("POST", url, json=request_data) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)

                        # Check for message content
                        if "message" in chunk:
                            message = chunk["message"]
                            content = message.get("content", "")

                            if content:
                                # Emit text chunk
                                self._response_text += content
                                self._event_queue.put_nowait(
                                    llm.ChatChunk(
                                        choices=[
                                            llm.Choice(
                                                delta=llm.ChoiceDelta(
                                                    content=content,
                                                    role="assistant",
                                                ),
                                                index=0,
                                            )
                                        ]
                                    )
                                )

                            # Check for tool calls
                            if "tool_calls" in message:
                                for tool_call in message["tool_calls"]:
                                    # Emit function call
                                    self._event_queue.put_nowait(
                                        llm.ChatChunk(
                                            choices=[
                                                llm.Choice(
                                                    delta=llm.ChoiceDelta(
                                                        role="assistant",
                                                        tool_calls=[
                                                            llm.ToolCall(
                                                                id=tool_call.get("id", ""),
                                                                type="function",
                                                                function=llm.FunctionCall(
                                                                    name=tool_call["function"]["name"],
                                                                    arguments=tool_call["function"]["arguments"],
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                    index=0,
                                                )
                                            ]
                                        )
                                    )

                        # Check if done
                        if chunk.get("done", False):
                            break

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from Ollama: {e}")

            # Add assistant's response to chat context
            self._chat_ctx.messages.append(
                llm.ChatMessage(
                    role="assistant",
                    content=self._response_text,
                )
            )

        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
        finally:
            await self._client.aclose()

    async def aclose(self):
        """Close the stream and cleanup resources."""
        await self._client.aclose()
```

### 7. Custom TTS (Piper) Integration

```python
# backend/agent/tts_handler.py
"""
Custom TTS plugin for Piper integration with LiveKit Agents.

Piper provides high-quality neural text-to-speech synthesis.
"""

import logging
import asyncio
from typing import AsyncIterable, Optional
import httpx
import numpy as np
from livekit import agents
from livekit.agents import tts

logger = logging.getLogger(__name__)


class PiperTTS(tts.TTS):
    """
    Text-to-Speech implementation using Piper.

    Piper provides fast, high-quality neural TTS with:
    - Multiple languages and voices
    - Low latency
    - No external API dependencies
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:5500",
        voice: str = "en_US-lessac-medium",
        sample_rate: int = 22050,
        timeout: float = 10.0,
    ):
        """
        Initialize Piper TTS.

        Args:
            base_url: Piper server URL
            voice: Voice model name (must be downloaded first)
            sample_rate: Audio sample rate (default 22050)
            timeout: Request timeout in seconds
        """
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=True,
            ),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._base_url = base_url.rstrip("/")
        self._voice = voice
        self._sample_rate = sample_rate
        self._timeout = timeout

        logger.info(
            f"Piper TTS initialized: voice={voice}, url={base_url}, "
            f"sample_rate={sample_rate}"
        )

    def synthesize(
        self,
        text: str,
    ) -> "PiperTTSStream":
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize

        Returns:
            PiperTTSStream for streaming audio
        """
        return PiperTTSStream(
            tts=self,
            text=text,
        )


class PiperTTSStream(tts.SynthesizeStream):
    """
    Streaming interface for Piper TTS synthesis.
    """

    def __init__(
        self,
        *,
        tts: PiperTTS,
        text: str,
    ):
        super().__init__()
        self._tts = tts
        self._text = text
        self._client = httpx.AsyncClient(timeout=tts._timeout)

    async def _main_task(self):
        """Main task that performs the TTS synthesis."""
        try:
            # Prepare request
            request_data = {
                "text": self._text,
                "voice": self._tts._voice,
                "sample_rate": self._tts._sample_rate,
            }

            # Make request to Piper
            url = f"{self._tts._base_url}/api/synthesize"

            logger.debug(f"Synthesizing text: '{self._text[:50]}...'")

            async with self._client.stream("POST", url, json=request_data) as response:
                response.raise_for_status()

                # Stream audio chunks
                chunk_size = 4096  # Read 4KB chunks
                async for chunk in response.aiter_bytes(chunk_size):
                    if not chunk:
                        continue

                    # Convert bytes to audio frame
                    # Piper returns PCM int16 audio
                    audio_array = np.frombuffer(chunk, dtype=np.int16)

                    # Create audio frame
                    frame = agents.AudioFrame(
                        data=audio_array.tobytes(),
                        sample_rate=self._tts._sample_rate,
                        num_channels=1,
                        samples_per_channel=len(audio_array),
                    )

                    # Emit frame
                    self._event_queue.put_nowait(
                        tts.SynthesizedAudio(
                            request_id="",  # Not used
                            frame=frame,
                        )
                    )

            logger.debug(f"Synthesis complete for: '{self._text[:50]}...'")

        except httpx.HTTPError as e:
            logger.error(f"Piper HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Piper error: {e}")
            raise
        finally:
            await self._client.aclose()

    async def aclose(self):
        """Close the stream and cleanup resources."""
        await self._client.aclose()
```

### 8. Piper TTS Service Setup

**Dockerfile for Piper TTS**:

```dockerfile
# tts-service/Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS
RUN pip install --no-cache-dir piper-tts

# Create app directory
WORKDIR /app

# Download voice models (you can add more)
RUN mkdir -p /app/voices && \
    cd /app/voices && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Create API server
COPY api_server.py /app/

EXPOSE 5500

CMD ["python", "api_server.py"]
```

**Piper API Server**:

```python
# tts-service/api_server.py
"""
Simple HTTP API server for Piper TTS.
"""

import asyncio
import json
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import subprocess
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Piper TTS API")

# Voice models directory
VOICES_DIR = Path("/app/voices")


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-medium"
    sample_rate: int = 22050


@app.post("/api/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthesize text to speech using Piper.

    Returns streaming audio/wav response.
    """
    try:
        # Get voice model path
        voice_path = VOICES_DIR / f"{request.voice}.onnx"

        if not voice_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Voice model not found: {request.voice}"
            )

        # Run Piper TTS
        # Piper command: echo "text" | piper --model voice.onnx --output_raw
        process = await asyncio.create_subprocess_exec(
            "piper",
            "--model", str(voice_path),
            "--output_raw",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Send text to stdin
        stdout, stderr = await process.communicate(input=request.text.encode())

        if process.returncode != 0:
            logger.error(f"Piper error: {stderr.decode()}")
            raise HTTPException(
                status_code=500,
                detail="TTS synthesis failed"
            )

        # Return audio as streaming response
        async def audio_stream():
            yield stdout

        return StreamingResponse(
            audio_stream(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            },
        )

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/voices")
async def list_voices():
    """List available voice models."""
    voices = [
        voice.stem
        for voice in VOICES_DIR.glob("*.onnx")
    ]
    return {"voices": voices}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5500)
```

### 9. React Frontend Components

**Main App with LiveKitRoom**:

```tsx
// frontend/src/App.tsx
import { useEffect, useState } from 'react';
import { LiveKitRoom, RoomAudioRenderer } from '@livekit/components-react';
import { Room } from 'livekit-client';
import '@livekit/components-styles';
import VideoConference from './components/VideoConference';
import TranscriptPanel from './components/TranscriptPanel';
import { generateToken } from './services/api';

function App() {
  const [token, setToken] = useState<string>('');
  const [roomName, setRoomName] = useState<string>('');
  const [participantName, setParticipantName] = useState<string>('');
  const [connected, setConnected] = useState<boolean>(false);

  const serverUrl = import.meta.env.VITE_LIVEKIT_URL || 'ws://localhost:7880';

  const handleConnect = async () => {
    if (!roomName || !participantName) {
      alert('Please enter room name and your name');
      return;
    }

    try {
      // Get token from backend
      const tokenData = await generateToken(roomName, participantName);
      setToken(tokenData.token);
      setConnected(true);
    } catch (error) {
      console.error('Failed to connect:', error);
      alert('Failed to connect to room');
    }
  };

  const handleDisconnect = () => {
    setToken('');
    setConnected(false);
  };

  if (!connected) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg w-96">
          <h1 className="text-2xl font-bold mb-6 text-center">
            Trinity AI Voice Agent
          </h1>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Room Name
              </label>
              <input
                type="text"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Enter room name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Name
              </label>
              <input
                type="text"
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Enter your name"
              />
            </div>

            <button
              onClick={handleConnect}
              className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700"
            >
              Connect
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <LiveKitRoom
        token={token}
        serverUrl={serverUrl}
        connect={true}
        audio={true}
        video={true}
        onDisconnected={handleDisconnect}
        className="h-screen"
      >
        <div className="h-full flex flex-col">
          {/* Video Conference Area */}
          <div className="flex-1 p-4">
            <VideoConference />
          </div>

          {/* Transcript Panel */}
          <div className="h-64 border-t border-gray-700">
            <TranscriptPanel />
          </div>
        </div>

        {/* Audio Renderer (handles audio playback) */}
        <RoomAudioRenderer />
      </LiveKitRoom>
    </div>
  );
}

export default App;
```

**Real-time Transcript Panel**:

```tsx
// frontend/src/components/TranscriptPanel.tsx
import { useEffect, useRef, useState } from 'react';
import { useDataChannel } from '@livekit/components-react';

interface TranscriptEntry {
  speaker: 'user' | 'agent';
  text: string;
  timestamp: string;
}

export default function TranscriptPanel() {
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Listen for transcript data from agent via data channel
  const decoder = new TextDecoder();

  useDataChannel('transcripts', (payload) => {
    try {
      const text = decoder.decode(payload);
      const entry: TranscriptEntry = JSON.parse(text);

      setTranscripts((prev) => [...prev, entry]);
    } catch (error) {
      console.error('Failed to parse transcript:', error);
    }
  });

  // Auto-scroll to bottom when new transcripts arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcripts]);

  return (
    <div className="h-full bg-gray-800 flex flex-col">
      <div className="px-4 py-2 border-b border-gray-700">
        <h2 className="text-white font-semibold">Live Transcript</h2>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {transcripts.length === 0 ? (
          <p className="text-gray-400 text-center">
            Transcripts will appear here...
          </p>
        ) : (
          transcripts.map((entry, index) => (
            <div
              key={index}
              className={`p-3 rounded-lg ${
                entry.speaker === 'agent'
                  ? 'bg-blue-900 bg-opacity-50'
                  : 'bg-gray-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`text-xs font-semibold ${
                    entry.speaker === 'agent'
                      ? 'text-blue-300'
                      : 'text-green-300'
                  }`}
                >
                  {entry.speaker === 'agent' ? '🤖 AI Agent' : '👤 User'}
                </span>
                <span className="text-xs text-gray-400">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-white text-sm">{entry.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

**Video Conference Component**:

```tsx
// frontend/src/components/VideoConference.tsx
import {
  ControlBar,
  GridLayout,
  ParticipantTile,
  RoomAudioRenderer,
  useParticipants,
  useTracks,
} from '@livekit/components-react';
import { Track } from 'livekit-client';

export default function VideoConference() {
  const participants = useParticipants();
  const tracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.ScreenShare, withPlaceholder: false },
    ],
    { onlySubscribed: false },
  );

  return (
    <div className="h-full flex flex-col">
      {/* Participant Grid */}
      <div className="flex-1">
        <GridLayout tracks={tracks} style={{ height: '100%' }}>
          <ParticipantTile />
        </GridLayout>
      </div>

      {/* Control Bar */}
      <div className="p-4">
        <ControlBar />
      </div>
    </div>
  );
}
```

### 10. FastAPI Backend Endpoints

```python
# backend/main.py
"""
FastAPI backend for LiveKit AI Agent platform.

Provides:
- Token generation for room access
- Room management
- SIP trunk and dispatch rule configuration
- Transcript storage and retrieval
"""

import os
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "http://livekit:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
    raise ValueError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set")

# Initialize FastAPI app
app = FastAPI(
    title="Trinity LiveKit AI Agent API",
    description="Backend API for LiveKit-based AI voice and video platform",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    metadata: Optional[str] = None


class TokenResponse(BaseModel):
    token: str
    url: str


class CreateRoomRequest(BaseModel):
    name: str
    empty_timeout: int = 300
    max_participants: int = 50


class SIPTrunkRequest(BaseModel):
    name: str
    numbers: list[str]
    allowed_addresses: list[str] = ["0.0.0.0/0"]


class SIPDispatchRuleRequest(BaseModel):
    room_name: str
    trunk_ids: list[str]
    pin: str = ""


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Token generation
@app.post("/api/token", response_model=TokenResponse)
async def generate_token(request: TokenRequest):
    """
    Generate LiveKit access token for a participant.

    The token grants permissions to join a room and publish/subscribe tracks.
    """
    try:
        token = api.AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        # Set participant identity and name
        token.with_identity(request.participant_name)
        token.with_name(request.participant_name)

        if request.metadata:
            token.with_metadata(request.metadata)

        # Grant permissions
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )

        jwt_token = token.to_jwt()

        logger.info(
            f"Generated token for {request.participant_name} "
            f"in room {request.room_name}"
        )

        return TokenResponse(
            token=jwt_token,
            url=LIVEKIT_URL.replace("http", "ws"),
        )

    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Room management
@app.post("/api/rooms")
async def create_room(request: CreateRoomRequest):
    """Create a new LiveKit room."""
    try:
        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        room = await lk_api.room.create_room(
            api.CreateRoomRequest(
                name=request.name,
                empty_timeout=request.empty_timeout,
                max_participants=request.max_participants,
            )
        )

        await lk_api.aclose()

        logger.info(f"Created room: {request.name}")

        return {
            "room": {
                "sid": room.sid,
                "name": room.name,
                "empty_timeout": room.empty_timeout,
                "max_participants": room.max_participants,
                "creation_time": room.creation_time,
            }
        }

    except Exception as e:
        logger.error(f"Failed to create room: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rooms")
async def list_rooms():
    """List all active rooms."""
    try:
        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        rooms = await lk_api.room.list_rooms(api.ListRoomsRequest())

        await lk_api.aclose()

        return {
            "rooms": [
                {
                    "sid": room.sid,
                    "name": room.name,
                    "num_participants": room.num_participants,
                    "creation_time": room.creation_time,
                }
                for room in rooms
            ]
        }

    except Exception as e:
        logger.error(f"Failed to list rooms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# SIP configuration
@app.post("/api/sip/trunk")
async def create_sip_trunk(request: SIPTrunkRequest):
    """
    Create SIP inbound trunk.

    This allows external SIP clients (like Linphone) to call into LiveKit rooms.
    """
    try:
        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        trunk = await lk_api.sip.create_sip_inbound_trunk(
            api.CreateSIPInboundTrunkRequest(
                trunk=api.SIPInboundTrunkInfo(
                    name=request.name,
                    numbers=request.numbers,
                    allowed_addresses=request.allowed_addresses,
                )
            )
        )

        await lk_api.aclose()

        logger.info(f"Created SIP trunk: {request.name}")

        return {"trunk": trunk}

    except Exception as e:
        logger.error(f"Failed to create SIP trunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sip/dispatch")
async def create_sip_dispatch_rule(request: SIPDispatchRuleRequest):
    """
    Create SIP dispatch rule.

    Routes incoming SIP calls to specific LiveKit rooms.
    The AI agent will automatically join when a SIP call arrives.
    """
    try:
        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        rule = await lk_api.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(
                rule=api.SIPDispatchRule(
                    dispatch_rule_direct=api.SIPDispatchRuleDirect(
                        room_name=request.room_name,
                        pin=request.pin,
                    ),
                ),
                trunk_ids=request.trunk_ids,
            )
        )

        await lk_api.aclose()

        logger.info(
            f"Created SIP dispatch rule: calls → room '{request.room_name}'"
        )

        return {"rule": rule}

    except Exception as e:
        logger.error(f"Failed to create SIP dispatch rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 11. SIP Configuration for Linphone Testing

**Setting up SIP Trunk and Dispatch Rules**:

1. **Create SIP Trunk** (via API):
```bash
curl -X POST http://localhost:8000/api/sip/trunk \
  -H "Content-Type: application/json" \
  -d '{
    "name": "linphone-trunk",
    "numbers": ["+1234567890"],
    "allowed_addresses": ["0.0.0.0/0"]
  }'
```

2. **Create Dispatch Rule** (routes calls to AI agent room):
```bash
curl -X POST http://localhost:8000/api/sip/dispatch \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "ai-agent-room",
    "trunk_ids": ["trunk_xxxxxxxxxx"],
    "pin": ""
  }'
```

**Linphone Client Configuration**:

1. Open Linphone
2. Go to Settings → SIP Accounts → Add
3. Configure:
   - **Username**: any username
   - **SIP Domain**: `YOUR_SERVER_IP:5060`
   - **Transport**: UDP
   - **Password**: (leave empty for testing)
4. Save and register
5. Make a call to: `+1234567890@YOUR_SERVER_IP:5060`
6. The call will be routed to `ai-agent-room`
7. AI agent will auto-join and start the conversation

---

## Environment Variables

```env
# .env file

# LiveKit Server
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here
LIVEKIT_URL=ws://localhost:7880

# Redis
REDIS_URL=redis://redis:6379

# AI Services
OLLAMA_URL=http://192.168.1.120:11434
OLLAMA_MODEL=llama3.1

# WhisperLive STT
WHISPERLIVE_HOST=whisperlive
WHISPERLIVE_PORT=9090
WHISPERLIVE_MODEL=small
WHISPERLIVE_BACKEND=faster_whisper

# Piper TTS
PIPER_URL=http://piper-tts:5500
PIPER_VOICE=en_US-lessac-medium

# Frontend
VITE_LIVEKIT_URL=ws://localhost:7880
VITE_API_URL=http://localhost:8000

# SIP (optional - for external IP)
# SIP_EXTERNAL_IP=your.public.ip
# LIVEKIT_EXTERNAL_IP=your.public.ip
```

**Generate API Keys**:
```bash
# Generate API key and secret
openssl rand -base64 32  # API Key
openssl rand -base64 32  # API Secret
```

---

## Port Configuration

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| LiveKit Server | 7880 | TCP/WS | WebSocket signaling |
| LiveKit Server | 7881 | TCP | WebRTC over TCP |
| LiveKit Server | 50000-50100 | UDP | WebRTC media (RTP/RTCP) |
| LiveKit SIP | 5060 | UDP | SIP signaling |
| LiveKit SIP | 10000-20000 | UDP | RTP media (voice) |
| Redis | 6379 | TCP | Message broker & cache |
| FastAPI Backend | 8000 | TCP | REST API |
| React Frontend | 3000 | TCP | Web UI |
| WhisperLive STT | 9090 | TCP/WS | Real-time STT WebSocket |
| Piper TTS | 5500 | TCP | TTS HTTP API |
| Ollama LLM | 11434 | TCP | LLM API (external) |

---

## Testing Workflow

### 1. Start Infrastructure
```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f agent-worker
docker-compose logs -f whisperlive
docker-compose logs -f piper-tts
```

### 2. Verify Services
```bash
# Check LiveKit
curl http://localhost:7880/health

# Check Backend API
curl http://localhost:8000/health

# Check WhisperLive
curl http://localhost:9090/health

# Check Piper TTS
curl http://localhost:5500/health

# Check Ollama (external)
curl http://192.168.1.120:11434/api/tags
```

### 3. Test Web Client
1. Open browser: `http://localhost:3000`
2. Enter room name: `test-room`
3. Enter your name: `User1`
4. Click "Connect"
5. Speak into microphone
6. Verify AI agent responds
7. Check transcripts appear in real-time

### 4. Test SIP Call (Linphone)
1. Configure Linphone with your server IP:5060
2. Ensure SIP trunk and dispatch rule are created
3. Call: `+1234567890@YOUR_IP:5060`
4. Hear AI agent greeting
5. Have a conversation
6. Verify transcripts in web UI (if joined same room)

### 5. Test Voice Pipeline
```bash
# Monitor agent logs for pipeline flow
docker-compose logs -f agent-worker

# You should see:
# 1. "User said: [transcription]" (from WhisperLive)
# 2. "Agent said: [response]" (from Ollama → Piper)
# 3. Audio published to room
```

---

## Common Issues & Solutions

### SIP Not Connecting
- **Issue**: Linphone can't register or call fails
- **Solution**:
  - Ensure `network_mode: host` for `livekit-sip` service
  - Verify UDP ports 5060 and 10000-20000 are open
  - Check firewall rules: `sudo ufw allow 5060/udp`
  - Use server's local IP in Linphone, not localhost

### Agent Not Responding
- **Issue**: No audio response from AI agent
- **Solution**:
  - Check Ollama is running and model is pulled: `ollama list`
  - Verify WhisperLive is receiving audio: check logs
  - Ensure Piper TTS voices are downloaded
  - Check VAD is detecting speech (adjust sensitivity)
  - Review agent worker logs for errors

### No Audio/Video in Browser
- **Issue**: Can't hear/see participants
- **Solution**:
  - Check browser permissions (camera/microphone)
  - Verify WebRTC connectivity (check browser console)
  - For remote access, configure TURN server
  - Test with local network first before exposing externally

### Transcripts Not Displaying
- **Issue**: No transcripts in web UI
- **Solution**:
  - Verify data channel is established (check network tab)
  - Ensure agent is publishing to `transcripts` topic
  - Check frontend is subscribed to data channel
  - Review browser console for errors

### WhisperLive High Latency
- **Issue**: Slow transcription response
- **Solution**:
  - Use GPU backend if available (tensorrt/cuda)
  - Reduce model size: `tiny` or `base` instead of `small`
  - Enable VAD to reduce unnecessary processing
  - Check server resources (CPU/GPU usage)

### Ollama Timeout
- **Issue**: LLM requests timeout
- **Solution**:
  - Verify Ollama server is running: `curl http://192.168.1.120:11434/api/tags`
  - Check network connectivity between containers
  - Increase timeout in `llm_handler.py`
  - Use faster model: `llama3.1:7b` instead of larger variants

---

## Code Quality Requirements

1. **Type Hints**: Use Python type hints and TypeScript strictly
2. **Error Handling**: Comprehensive try/catch with proper logging
3. **Documentation**: Docstrings for all public functions/classes
4. **Testing**: Unit tests for critical pipeline components
5. **Linting**:
   - Python: `black`, `flake8`, `mypy`
   - TypeScript: `eslint`, `prettier`
6. **Logging**: Structured logging with appropriate levels

---

## Deployment Checklist

- [ ] All environment variables configured
- [ ] SSL/TLS certificates for production (HTTPS/WSS)
- [ ] Firewall rules configured for all required ports
- [ ] Redis persistence enabled (`appendonly yes`)
- [ ] Ollama model pre-pulled and verified
- [ ] WhisperLive voice models downloaded
- [ ] Piper TTS voices downloaded
- [ ] LiveKit Egress configured (if recording needed)
- [ ] Logging configured (centralized log aggregation)
- [ ] Health checks implemented for all services
- [ ] Backup strategy for transcripts and recordings
- [ ] Monitoring configured (Prometheus/Grafana)
- [ ] Rate limiting on API endpoints
- [ ] CORS properly configured for production domains

---

## Key Implementation Notes

### LiveKit Agents Voice Pipeline
- **VoiceAssistant** class handles the complete pipeline automatically
- Audio flows: Room → VAD → STT → LLM → TTS → Room
- The agent joins as a participant and publishes audio tracks
- Data channels used for sending transcripts to frontend

### WhisperLive Integration
- Uses WebSocket for real-time streaming transcription
- Supports multiple backends (faster_whisper, tensorrt, openvino)
- Built-in VAD option reduces latency
- Interim and final transcripts available

### Ollama LLM
- Compatible with OpenAI API format
- Runs locally for privacy and control
- Models must be pre-pulled: `ollama pull llama3.1`
- Supports function calling for extended capabilities

### Piper TTS
- Fast, high-quality neural TTS
- Runs completely offline
- Multiple voices available from HuggingFace
- Low latency suitable for real-time conversation

### SIP Integration
- Requires `network_mode: host` for proper UDP handling
- SIP callers appear as regular room participants
- Agent auto-joins based on dispatch rules
- Supports inbound and outbound calls

---

## References for Implementation

When implementing features, always:

1. **Check LiveKit Docs First**: https://docs.livekit.io
2. **Verify API Signatures**: https://docs.livekit.io/reference/
3. **Check WhisperLive GitHub**: https://github.com/collabora/WhisperLive
4. **Review Agent Examples**: https://github.com/livekit/agents/tree/main/examples
5. **Test Incrementally**: Start with basic room, add features one by one
6. **Log Extensively**: Debug WebRTC issues with browser console and server logs

### Critical Documentation Links
- **LiveKit Agents**: https://docs.livekit.io/agents/
- **VoiceAssistant API**: https://docs.livekit.io/agents/api/voice-assistant/
- **Custom Plugins**: https://docs.livekit.io/agents/api/plugins/
- **SIP Setup**: https://docs.livekit.io/sip/
- **React Components**: https://docs.livekit.io/reference/components/react/

---

## Architecture Validation Summary

✅ **Audio Reception**: AI Agent receives audio directly from LiveKit room participants (including SIP callers)

✅ **Voice Pipeline**: Sequential processing through VAD → STT (WhisperLive) → LLM (Ollama) → TTS (Piper)

✅ **Audio Publishing**: TTS audio is published back to room via `agent.say()` or `session.publish_audio()`

✅ **Continuous Conversation**: Bidirectional loop enables natural back-and-forth conversation

✅ **Real-time Transcripts**: Sent via data channels for live display in frontend

✅ **SIP Integration**: External calls routed through LiveKit SIP server into rooms

✅ **Custom Plugins**: STT, LLM, and TTS implemented as custom plugins following LiveKit patterns

---

**Remember**:
- LiveKit Agents SDK handles room connection and audio routing automatically
- VoiceAssistant class orchestrates the entire pipeline
- Custom STT/LLM/TTS plugins integrate via standard interfaces
- SIP calls are treated as regular room participants
- Data channels enable real-time transcript delivery to web clients

This architecture provides a complete, production-ready AI voice agent platform with full SIP integration, real-time transcription, and multi-modal communication capabilities.
