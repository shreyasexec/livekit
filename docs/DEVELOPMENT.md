# DEVELOPMENT.md - Voice AI Platform Development Guide

## Voice Pipeline Architecture

```
┌─────────┐    ┌─────────┐    ┌───────────────┐    ┌────────┐    ┌───────┐    ┌─────────┐
│  Audio  │───▶│   VAD   │───▶│WhisperLiveKit │───▶│ Ollama │───▶│ Piper │───▶│ Publish │
│   In    │    │ Silero  │    │     STT       │    │  LLM   │    │  TTS  │    │  Audio  │
└─────────┘    └─────────┘    └───────────────┘    └────────┘    └───────┘    └─────────┘
     │              │                │                  │            │             │
     ▼              ▼                ▼                  ▼            ▼             ▼
  Capture       < 100ms          < 500ms           < 1000ms      < 300ms       Total
                                                                             < 2000ms
```

---

## Agent Worker Pattern

```python
# backend/agent/worker.py
from livekit.agents import Agent, AgentSession
from livekit.plugins import openai, silero
from .stt_handler import WhisperLiveKitSTT
from .tts_handler import PiperTTS

class VoiceAgent(Agent):
    """Main voice agent - entry point only, logic in handlers."""

    async def on_enter(self):
        self.stt = WhisperLiveKitSTT(url="ws://192.168.1.120:8765/")
        self.tts = PiperTTS(url="http://192.168.20.62:5500/")
        self.llm = openai.LLM.with_ollama(
            model="llama3.1:8b",
            base_url="http://192.168.1.120:11434"
        )

async def main():
    session = AgentSession(vad=silero.VAD.load())
    await session.start(agent=VoiceAgent(), room=ctx.room)
```

---

## WhisperLiveKit STT Handler

```python
# backend/agent/stt_handler.py
import asyncio
import json
import websockets

class WhisperLiveKitSTT:
    """
    WhisperLiveKit WebSocket client.
    Reference: https://github.com/collabora/WhisperLive
    """

    def __init__(self, url: str = "ws://192.168.1.120:8765/"):
        self.url = url
        self.ws = None

    async def connect(self, session_id: str, language: str = "en"):
        """Connect to WhisperLiveKit server."""
        self.ws = await websockets.connect(self.url)
        config = {
            "uid": session_id,
            "language": language,  # en, hi, kn, mr
            "model": "small",
            "use_vad": True
        }
        await self.ws.send(json.dumps(config))

    async def transcribe(self, audio_chunk: bytes) -> str:
        """
        Send audio and receive transcription.
        Audio format: 16kHz, mono, int16 PCM
        """
        if not self.ws:
            raise RuntimeError("Not connected")

        await self.ws.send(audio_chunk)
        response = await self.ws.recv()
        data = json.loads(response)

        text = ""
        for segment in data.get("segments", []):
            if segment.get("completed"):
                text += segment.get("text", "")
        return text.strip()

    async def close(self):
        if self.ws:
            await self.ws.close()
```

---

## Piper TTS Handler

```python
# backend/agent/tts_handler.py
import httpx
from typing import AsyncIterator

class PiperTTS:
    """
    Piper TTS HTTP client.
    Reference: https://github.com/rhasspy/piper
    """

    VOICES = {
        "en": "en_US-lessac-medium",
        "hi": "hi_IN-swara-medium",
        "kn": "kn_IN-wavenet",
        "mr": "mr_IN-wavenet"
    }

    def __init__(self, url: str = "http://192.168.20.62:5500/"):
        self.url = url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """Convert text to audio."""
        voice = self.VOICES.get(language, self.VOICES["en"])
        response = await self.client.post(
            f"{self.url}/api/tts",
            json={
                "text": text,
                "voice": voice,
                "output_format": "wav",
                "sample_rate": 22050
            }
        )
        response.raise_for_status()
        return response.content

    async def synthesize_stream(self, text: str, language: str = "en") -> AsyncIterator[bytes]:
        """Stream audio chunks for lower latency."""
        voice = self.VOICES.get(language, self.VOICES["en"])
        async with self.client.stream(
            "POST",
            f"{self.url}/api/tts/stream",
            json={"text": text, "voice": voice}
        ) as response:
            async for chunk in response.aiter_bytes(1024):
                yield chunk
```

---

## Ollama LLM Handler

```python
# backend/agent/llm_handler.py
import httpx
import json
from typing import AsyncIterator

class OllamaLLM:
    """
    Ollama LLM client.
    Reference: https://github.com/ollama/ollama/blob/main/docs/api.md

    NOTE: Prefer livekit-plugins-openai with_ollama() for agent integration.
    """

    def __init__(self, url: str = "http://192.168.1.120:11434", model: str = "llama3.1:8b"):
        self.url = url
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate response (non-streaming)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.post(
            f"{self.url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False}
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncIterator[str]:
        """Stream response tokens."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with self.client.stream(
            "POST",
            f"{self.url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": True}
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if content := data.get("message", {}).get("content"):
                        yield content
```

---

## Publishing Transcripts with Identity

```python
# In agent worker
@assistant.on("user_speech_committed")
def on_user_speech(msg: str, participant: rtc.Participant):
    """Publish transcript with participant identity."""
    ctx.room.local_participant.publish_data(
        payload=json.dumps({
            "type": "transcript",
            "speaker": "user",
            "participantIdentity": participant.identity,
            "participantSid": participant.sid,
            "text": msg,
            "timestamp": datetime.utcnow().isoformat(),
        }).encode("utf-8"),
        topic="transcripts",
    )
```

---

## Frontend Hooks

### useTranscript Hook
```typescript
// frontend/src/hooks/useTranscript.ts
import { useDataChannel } from '@livekit/components-react';
import { useState, useCallback } from 'react';

interface TranscriptEntry {
  type: 'transcript';
  speaker: 'user' | 'agent';
  participantIdentity: string;
  participantSid: string;
  text: string;
  timestamp: string;
}

export function useTranscript() {
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const decoder = new TextDecoder();

  const onMessage = useCallback((payload: Uint8Array) => {
    const entry = JSON.parse(decoder.decode(payload)) as TranscriptEntry;
    setTranscripts(prev => [...prev, entry]);
  }, []);

  useDataChannel('transcripts', onMessage);
  return { transcripts };
}
```

### useMetadata Hook
```typescript
// frontend/src/hooks/useMetadata.ts
import { useState, useCallback } from 'react';
import { api } from '../services/api';

interface Transaction {
  transactionId: string;
  type: 'stt' | 'llm' | 'tts' | 'call_start' | 'call_end';
  timestamp: string;
  duration?: number;
  participantSid: string;
}

export function useMetadata(roomSid: string) {
  const [metadata, setMetadata] = useState<SessionMetadata>();

  const logTransaction = useCallback(async (event: Omit<Transaction, 'transactionId' | 'timestamp'>) => {
    const transaction: Transaction = {
      transactionId: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      ...event,
    };
    setMetadata(prev => ({
      ...prev!,
      transactions: [...(prev?.transactions || []), transaction],
    }));
    await api.logTransaction(roomSid, transaction);
  }, [roomSid]);

  return { metadata, logTransaction };
}
```

---

## Speaking Indicator CSS

```css
/* frontend/src/styles/speaking.css */
.participant-tile.speaking {
  animation: speaking-pulse 1s ease-in-out infinite;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.6);
}

@keyframes speaking-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.6); }
  50% { box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.3); }
}
```

---

## Dependencies

### Backend (requirements.txt)
```
livekit-agents>=1.3.0
livekit-plugins-openai
livekit-plugins-silero
livekit
livekit-api
fastapi
uvicorn[standard]
httpx
websockets
numpy
redis
pydantic
python-dotenv
```

### Frontend (package.json)
```json
{
  "@livekit/components-react": "^2.0.0",
  "livekit-client": "^2.0.0",
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "typescript": "^5.0.0",
  "tailwindcss": "^3.4.0",
  "zustand": "^4.5.0"
}
