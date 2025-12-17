# LiveKit AI Voice Agent - Project Context

## Project Summary
Build a **100% on-premises, open-source** LiveKit-based AI voice agent platform with voice/video calls, real-time transcription, and AI conversation capabilities. Uses SIP integration (Linphone) for telephony.

## ⚠️ Infrastructure Notice
- **NO LiveKit Cloud** - Self-hosted LiveKit Server only
- **NO external APIs** - All AI services on-prem except Ollama
- **Ollama hosted externally** at `192.168.1.120:11434` (local network server)
- All other services run in Docker on local machine

---

## 📚 Development Guidelines

### Documentation-First Approach
**ALWAYS refer to official documentation before implementing, fixing, or responding:**

| Component | Official Docs | Priority |
|-----------|---------------|----------|
| LiveKit Agents | https://docs.livekit.io/agents/ | Primary |
| LiveKit SDK | https://docs.livekit.io/reference/ | Primary |
| LiveKit SIP | https://docs.livekit.io/sip/ | Primary |
| WhisperLive | https://github.com/collabora/WhisperLive | Primary |
| Piper TTS | https://github.com/rhasspy/piper | Primary |
| Ollama API | https://github.com/ollama/ollama/blob/main/docs/api.md | Primary |
| React LiveKit | https://docs.livekit.io/reference/components/react/ | Primary |

**Dont create Any documentation file untill it i asked manually

**Before any implementation:
1. Check official docs for latest API signatures
2. Verify method names and parameters haven't changed
3. Look for official examples in GitHub repos
4. Cross-reference with changelog for breaking changes

### Use Existing LLM Endpoint
**DO NOT create new LLM services.** Use the existing Ollama endpoint:
```
Endpoint: http://192.168.1.120:11434
Model: llama3.1:8b (pre-pulled)
API: OpenAI-compatible via livekit-plugins-openai
```

---

## 🏗️ Code Organization Standards

### Project Structure (Mandatory)
```
livekit/
├── backend/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── worker.py          # Entry point only
│   │   ├── stt_handler.py     # STT logic isolated
│   │   ├── tts_handler.py     # TTS logic isolated
│   │   ├── llm_handler.py     # LLM logic isolated
│   │   └── utils.py           # Shared utilities
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── rooms.py
│   │   │   ├── tokens.py
│   │   │   ├── sip.py
│   │   │   └── transcripts.py
│   │   └── middleware/
│   ├── services/
│   │   ├── livekit_service.py
│   │   └── redis_service.py
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── config/
│   │   └── settings.py        # Centralized config
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── room/
│   │   │   │   ├── VideoConference.tsx
│   │   │   │   ├── ParticipantTile.tsx
│   │   │   │   └── ControlBar.tsx
│   │   │   ├── transcript/
│   │   │   │   ├── TranscriptPanel.tsx
│   │   │   │   └── TranscriptEntry.tsx
│   │   │   ├── chat/
│   │   │   │   └── ChatPanel.tsx
│   │   │   └── common/
│   │   │       ├── Button.tsx
│   │   │       └── Loading.tsx
│   │   ├── hooks/
│   │   │   ├── useRoom.ts
│   │   │   ├── useTranscript.ts
│   │   │   └── useMetadata.ts
│   │   ├── context/
│   │   │   └── RoomContext.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── utils/
│   │   │   └── helpers.ts
│   │   ├── App.tsx
│   │   └── index.tsx
│   └── package.json
└── docker-compose.yaml
```

### Implementation Principles
1. **Single Responsibility**: Each file/module handles ONE concern
2. **Dependency Injection**: Pass services, don't hardcode
3. **Configuration Centralization**: All env vars in `config/settings.py`
4. **Type Safety**: Use TypeScript strictly, Python type hints everywhere
5. **Error Boundaries**: Wrap components and async operations
6. **Logging**: Structured logging with correlation IDs

---

## 🚀 Production-Grade Scalability Requirements

### Architecture for Scale
```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌─────▼────┐         ┌─────▼────┐
   │ LiveKit │         │ LiveKit  │         │ LiveKit  │
   │ Node 1  │         │ Node 2   │         │ Node N   │
   └─────────┘         └──────────┘         └──────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │     Redis       │
                    │   (Clustered)   │
                    └─────────────────┘
```

### Scalability Checklist
| Requirement | Implementation |
|-------------|----------------|
| **Horizontal Scaling** | Stateless agent workers, Redis for shared state |
| **Connection Pooling** | Reuse HTTP/WebSocket connections to STT/TTS/LLM |
| **Message Queuing** | Redis pub/sub for transcript distribution |
| **Health Checks** | `/health` endpoint on all services |
| **Graceful Shutdown** | Handle SIGTERM, drain connections |
| **Resource Limits** | Docker memory/CPU limits per service |
| **Retry Logic** | Exponential backoff for external service calls |
| **Circuit Breakers** | Fail fast when dependencies unavailable |
| **Metrics Export** | Prometheus-compatible `/metrics` endpoints |
| **Distributed Tracing** | Correlation IDs across all services |

### Resource Planning
```yaml
# Production resource allocation per service
agent-worker:
  replicas: 3-5 per 100 concurrent users
  memory: 2GB per instance
  cpu: 2 cores per instance

whisperlive:
  replicas: 1 per 50 concurrent streams
  memory: 4GB (GPU) or 8GB (CPU)
  gpu: 1 per instance (recommended)

piper-tts:
  replicas: 1 per 100 concurrent requests
  memory: 1GB per instance
  cpu: 2 cores per instance
```

---

## 📊 Metadata & Transaction Capture (Integration Ready)

### Purpose
Capture specific IDs and metadata for integration with external applications (analytics, billing, CRM, monitoring).

### Required Metadata Schema
```typescript
interface SessionMetadata {
  // Unique Identifiers (MUST capture)
  sessionId: string;           // Unique per room session
  roomSid: string;             // LiveKit room SID
  roomName: string;            // Human-readable room name

  // Participant Info
  participants: {
    participantSid: string;    // Unique per participant
    participantIdentity: string;
    joinedAt: string;          // ISO timestamp
    leftAt?: string;
    isAgent: boolean;
  }[];

  // Transaction Events (for billing/analytics)
  transactions: {
    transactionId: string;     // UUID for each event
    type: 'stt' | 'llm' | 'tts' | 'call_start' | 'call_end';
    timestamp: string;
    duration?: number;         // ms
    tokenCount?: number;       // LLM tokens
    audioBytes?: number;       // STT/TTS audio size
    participantSid: string;
    metadata?: Record<string, any>;
  }[];

  // Session Summary
  startTime: string;
  endTime?: string;
  totalDuration?: number;
  transcriptCount: number;
  llmRequestCount: number;
}
```

### Frontend: Capture & Display
```typescript
// hooks/useMetadata.ts - Capture all session metadata
export function useMetadata(roomSid: string) {
  const [metadata, setMetadata] = useState<SessionMetadata>();

  const logTransaction = useCallback((event: TransactionEvent) => {
    const transaction = {
      transactionId: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      ...event,
    };

    // Store locally
    setMetadata(prev => ({
      ...prev,
      transactions: [...(prev?.transactions || []), transaction],
    }));

    // Send to backend for persistence
    api.logTransaction(roomSid, transaction);

    // Console log for debugging (optional, controlled by env)
    if (import.meta.env.VITE_DEBUG_TRANSACTIONS === 'true') {
      console.log(`[TXN] ${transaction.transactionId}`, transaction);
    }
  }, [roomSid]);

  return { metadata, logTransaction };
}
```

### UI Transaction Display (Minimal, Non-Intrusive)
```typescript
// components/common/TransactionBadge.tsx
// Show only essential IDs, not full logs
function TransactionBadge({ sessionId, roomSid }: Props) {
  return (
    <div className="transaction-badge">
      <span className="label">Session:</span>
      <code className="id">{sessionId.slice(0, 8)}</code>
      <button onClick={() => copyToClipboard(sessionId)}>📋</button>
    </div>
  );
}
```

### Backend: Transaction Logging API
```python
# api/routes/transcripts.py
@router.post("/api/transactions/{room_sid}")
async def log_transaction(room_sid: str, transaction: TransactionEvent):
    """
    Log transaction event for external integration.
    Stores in Redis with TTL, can be consumed by external systems.
    """
    key = f"transactions:{room_sid}"
    await redis.lpush(key, transaction.json())
    await redis.expire(key, 86400)  # 24h retention

    # Publish to external consumers
    await redis.publish("transaction_events", json.dumps({
        "room_sid": room_sid,
        "event": transaction.dict(),
    }))

    return {"status": "logged", "transaction_id": transaction.transaction_id}
```

### Integration Export Endpoint
```python
# api/routes/transcripts.py
@router.get("/api/sessions/{room_sid}/export")
async def export_session_metadata(room_sid: str):
    """
    Export complete session metadata for external applications.
    Returns: SessionMetadata JSON
    """
    metadata = await build_session_metadata(room_sid)
    return metadata

@router.get("/api/sessions/{room_sid}/transactions")
async def get_transactions(
    room_sid: str,
    type: Optional[str] = None,
    since: Optional[datetime] = None,
):
    """
    Query transactions for integration apps.
    Filterable by type and time range.
    """
    transactions = await get_filtered_transactions(room_sid, type, since)
    return {"transactions": transactions}
```

---

## ⚛️ React Frontend: Complete Feature Set

### Required Components Checklist
| Component | Purpose | Status |
|-----------|---------|--------|
| `App.tsx` | Main layout, room connection | Required |
| `VideoConference.tsx` | Participant grid, video tiles | Required |
| `ParticipantTile.tsx` | Individual video + speaking indicator | Required |
| `ControlBar.tsx` | Mute, camera, screenshare, leave | Required |
| `TranscriptPanel.tsx` | Real-time transcripts with names | Required |
| `TranscriptEntry.tsx` | Single transcript item | Required |
| `ChatPanel.tsx` | Text messaging | Required |
| `DeviceSelector.tsx` | Camera/mic/speaker selection | Required |
| `ScreenShare.tsx` | Screen share controls | Required |
| `ConnectionStatus.tsx` | Connection quality indicator | Required |
| `SessionInfo.tsx` | Session ID, room info display | Required |
| `TransactionBadge.tsx` | Minimal metadata display | Required |

### Required Hooks
```typescript
// All custom hooks needed
useRoom()           // Room connection state
useTranscript()     // Transcript data channel
useMetadata()       // Session/transaction capture
useDevices()        // Media device management
useSpeakingIndicator() // Per-participant speaking state
useConnectionQuality() // Network quality monitoring
```

### Required Features
1. **Room Management**: Join, leave, reconnect handling
2. **Media Controls**: Mute/unmute audio, enable/disable video
3. **Device Selection**: Choose input/output devices
4. **Screen Sharing**: Start/stop screen share
5. **Participant Display**: Grid layout, active speaker highlight
6. **Speaking Indicators**: Visual blink effect when speaking
7. **Real-time Transcripts**: Named, timestamped, scrolling
8. **Chat/Messaging**: Text communication via data channels
9. **Connection Status**: Quality indicator, reconnection UI
10. **Session Metadata**: Display session ID, export capability
11. **Error Handling**: User-friendly error messages, retry options
12. **Responsive Design**: Mobile and desktop layouts

### State Management Pattern
```typescript
// context/RoomContext.tsx
interface RoomState {
  room: Room | null;
  connectionState: ConnectionState;
  participants: Participant[];
  transcripts: TranscriptEntry[];
  metadata: SessionMetadata;
  error: Error | null;
}

// Actions
type RoomAction =
  | { type: 'CONNECTED'; room: Room }
  | { type: 'PARTICIPANT_JOINED'; participant: Participant }
  | { type: 'TRANSCRIPT_RECEIVED'; entry: TranscriptEntry }
  | { type: 'TRANSACTION_LOGGED'; transaction: Transaction }
  | { type: 'ERROR'; error: Error };
```

## Voice Pipeline Flow (Per Participant)

```
1. Audio Reception    → Agent receives audio from EACH participant independently
2. VAD (Silero)       → Detects speech segments per participant
3. STT (WhisperLive)  → Transcribes with participant identity attached
4. LLM (Ollama)       → Generates response (context includes who is speaking)
5. TTS (Piper)        → Converts response to audio
6. Publish            → Broadcasts to entire room (all participants hear)
7. Transcript Event   → Sends to frontend with participantIdentity for display
```

**Multi-User Handling:**
- Each participant's audio processed through separate VAD instance
- Transcripts tagged with `participantIdentity` and `participantSid`
- Agent can address specific users by name in responses
- All users see all transcripts with speaker names

## Key Implementation Patterns

### Agent Worker Pattern
```python
# Uses LiveKit Agents SDK v1.x with custom nodes
class TrinityAssistant(Agent):
    async def stt_node(self, audio, model_settings):
        # WhisperLive WebSocket integration

    async def tts_node(self, text, model_settings):
        # Piper HTTP API integration

session = AgentSession(
    llm=openai.LLM.with_ollama(model="llama3.1:8b", base_url=OLLAMA_URL),
    vad=silero.VAD.load(),
)
await session.start(agent=TrinityAssistant(), room=ctx.room)
```

### WhisperLive STT Integration
- **Protocol**: WebSocket (`ws://whisperlive:9090`)
- **Audio format**: 16kHz, mono, int16 PCM
- **Config message**: `{"uid": session_id, "language": "en", "model": "small", "use_vad": true}`
- **Response**: JSON with `segments[].text` and `segments[].completed`

### Piper TTS Integration
- **Protocol**: HTTP POST to `/api/synthesize`
- **Request**: `{"text": "...", "voice": "en_US-lessac-medium", "sample_rate": 22050}`
- **Response**: Streaming audio/wav (PCM int16)

### Ollama LLM Integration
- **Endpoint**: `http://192.168.1.120:11434/api/chat`
- **Use**: `openai.LLM.with_ollama()` from livekit-plugins-openai
- **Model**: `llama3.1:8b` (pre-pulled required)

### Frontend Data Channel
```typescript
// Receive transcripts from agent - includes participant identity
useDataChannel('transcripts', (payload) => {
    const entry = JSON.parse(decoder.decode(payload));
    // entry: {
    //   type: "transcript",
    //   speaker: "user" | "agent",
    //   participantIdentity: "User1",  // Participant's name
    //   participantSid: "PA_xxx",      // Unique ID
    //   text: "...",
    //   timestamp: "..."
    // }
});
```

### Speaking Indicator Pattern
```typescript
// Use LiveKit's isSpeaking from participant
import { useParticipants, useIsSpeaking } from '@livekit/components-react';

function ParticipantTile({ participant }) {
    const isSpeaking = useIsSpeaking(participant);

    return (
        <div className={`participant-tile ${isSpeaking ? 'speaking' : ''}`}>
            {/* Tile content */}
        </div>
    );
}

// CSS for speaking blink effect
/*
.participant-tile.speaking {
    animation: speaking-pulse 1s ease-in-out infinite;
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.6);
}

@keyframes speaking-pulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.6); }
    50% { box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.3); }
}
*/
```

### Multi-User Transcript Display
```typescript
// TranscriptPanel.tsx - Show participant names
{transcripts.map((entry, index) => (
    <div className={`transcript-entry ${entry.speaker}`}>
        <span className="participant-name">
            {entry.speaker === 'agent' ? '🤖 AI Agent' : `👤 ${entry.participantIdentity}`}
        </span>
        <span className="timestamp">{formatTime(entry.timestamp)}</span>
        <p className="text">{entry.text}</p>
    </div>
))}
```

### Agent Publishing Transcripts with Identity
```python
# In agent worker - include participant info when publishing transcripts
@assistant.on("user_speech_committed")
def on_user_speech(msg: str, participant: rtc.Participant):
    ctx.room.local_participant.publish_data(
        payload=json.dumps({
            "type": "transcript",
            "speaker": "user",
            "participantIdentity": participant.identity,  # User's name
            "participantSid": participant.sid,
            "text": msg,
            "timestamp": datetime.utcnow().isoformat(),
        }).encode("utf-8"),
        topic="transcripts",
    )
```

## Environment Variables (.env)

```bash
LIVEKIT_API_KEY=<generated>
LIVEKIT_API_SECRET=<generated>
LIVEKIT_URL=http://livekit:7880
LIVEKIT_PUBLIC_URL=wss://192.168.20.224:7880
LIVEKIT_NODE_IP=192.168.20.224

OLLAMA_URL=http://192.168.1.120:11434
OLLAMA_MODEL=llama3.1:8b

WHISPERLIVE_HOST=whisperlive
WHISPERLIVE_PORT=9090

PIPER_URL=http://piper-tts:5500

REDIS_URL=redis://redis:6379

VITE_LIVEKIT_URL=wss://192.168.20.224:7880
VITE_API_URL=https://192.168.20.224
```

## Docker Compose Services

| Service | Image/Build | Network | Notes |
|---------|-------------|---------|-------|
| livekit | `livekit/livekit-server:latest` | bridge | Mounts `configs/livekit.yaml` |
| livekit-sip | `livekit/sip:latest` | **host** | Required for UDP SIP |
| redis | `redis:7-alpine` | bridge | Persistence volume |
| whisperlive | `ghcr.io/collabora/whisperlive-gpu:latest` | bridge | GPU optional |
| piper-tts | Build from `tts-service/` | bridge | Downloads voice models |
| agent-worker | Build from `backend/` | bridge | Runs `python -m agent.worker` |
| backend | Build from `backend/` | bridge | Runs uvicorn |
| frontend | Build from `frontend/` | bridge | React dev/prod |

## SIP Configuration

### Trunk Creation
```bash
curl -X POST http://localhost:8000/api/sip/trunk \
  -d '{"name": "linphone-trunk", "numbers": ["+1234567890"], "allowed_addresses": ["0.0.0.0/0"]}'
```

### Dispatch Rule (routes calls to room)
```bash
curl -X POST http://localhost:8000/api/sip/dispatch \
  -d '{"room_name": "ai-agent-room", "trunk_ids": ["trunk_xxx"]}'
```

### Linphone Setup
- SIP Domain: `YOUR_SERVER_IP:5060`
- Transport: UDP
- Call: `+1234567890@YOUR_IP:5060`

## Common Issues & Fixes

| Issue | Check | Fix |
|-------|-------|-----|
| Agent not joining | `docker-compose logs agent-worker` | Restart agent-worker |
| No transcription | `docker-compose logs whisperlive` | Restart whisperlive, wait 30s |
| No TTS output | `curl localhost:5500/health` | Rebuild piper-tts |
| Ollama timeout | `curl http://192.168.1.120:11434/api/tags` | Check Ollama running, firewall |
| SIP not connecting | Check UDP 5060, 10000-20000 | Use `network_mode: host` for SIP |

## Service Health Checks

```bash
curl http://localhost:8000/health   # Backend
curl http://localhost:5500/health   # Piper TTS
curl http://localhost:7880          # LiveKit
ollama list                         # Ollama models
docker-compose exec redis redis-cli ping  # Redis
```

## Key Dependencies

### Python (backend/requirements.txt)
```
livekit-agents>=1.3.0
livekit-plugins-openai
livekit-plugins-silero
livekit
livekit-api
fastapi
uvicorn
httpx
websockets
numpy
redis
```

### Node (frontend/package.json)
```
@livekit/components-react
livekit-client
react
typescript
tailwindcss
```

## Documentation References

- LiveKit Agents: https://docs.livekit.io/agents/
- LiveKit v1.x Build: https://docs.livekit.io/agents/build/
- Custom Nodes: https://docs.livekit.io/agents/build/nodes
- LiveKit SIP: https://docs.livekit.io/sip/
- WhisperLive: https://github.com/collabora/WhisperLive
- Piper TTS: https://github.com/rhasspy/piper
- Ollama: https://ollama.com/

## Success Criteria

1. Frontend loads at `http://localhost:3000`
2. **Multiple users can join same room simultaneously**
3. Agent auto-joins and greets users
4. User speech transcribed with **participant name**: logs show `"👤 [User1] SAID: <text>"`
5. **Transcripts show each speaker's name** in UI
6. **Speaking indicator (blink effect)** appears on active speaker's tile
7. Agent responds with synthesized speech to entire room
8. All participants hear agent responses
9. No cloud dependencies - all services on-prem (except Ollama at 192.168.1.120)

```