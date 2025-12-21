# UI_REQUIREMENTS.md - Voice AI Platform UI Specifications

## Overview

This document specifies the UI components required for the Voice AI Platform frontend.

---

## 1. Call Dashboard

**Location:** `frontend/src/components/dashboard/CallDashboard.tsx`

### Features

#### Active Calls List
- Real-time updates via WebSocket
- Show: Room name, participant count, duration, status
- Click to view details
- Quick actions: Join, End call

#### Call History
- Searchable/filterable list
- Date range picker
- Filter by: Status, Duration, Participant
- Pagination

#### Per-Call Details
- Participant list with identity/SID
- Call duration (live timer for active)
- Audio/video quality metrics
- Transcript viewer (collapsible)
- Recording status indicator

#### Real-Time Statistics
```
┌─────────────────────────────────────┐
│  Total Calls    │  Avg Duration    │
│      127        │    4:32          │
├─────────────────┼──────────────────┤
│  Success Rate   │  Active Now      │
│     98.2%       │      3           │
└─────────────────┴──────────────────┘
```

#### Performance Metrics Panel
```
┌─────────────────────────────────────┐
│ STT Latency     │████████░░│ 423ms │
│ LLM Latency     │██████████│ 891ms │
│ TTS Latency     │█████░░░░░│ 267ms │
│ Total Round-Trip│██████████│1.58s  │
└─────────────────────────────────────┘
```

---

## 2. Voice Agent Interface

**Location:** `frontend/src/components/voice-agent/VoiceAgentUI.tsx`

### Main Features (Like LiveKit Cloud Playground)

#### Voice Conversation Area
- Visual audio waveform when speaking
- Speaking indicator (pulsing border)
- Transcript display (scrollable)
- Separate user/agent messages

#### Controls
```
┌─────────────────────────────────────┐
│  [🎤 Mute]  [📞 End]  [⚙️ Settings] │
└─────────────────────────────────────┘
```

- Mute/unmute microphone
- End call button
- Settings dropdown

#### Text Chat Option
- Toggle between voice and text input
- Text input field
- Send button

#### Connection Status
```
Connected | Room: meeting-123 | 2 participants
```

#### Language Selector
```
┌──────────────────────┐
│ 🌐 Language: English │
│    ├─ English        │
│    ├─ हिंदी (Hindi)   │
│    ├─ ಕನ್ನಡ (Kannada) │
│    └─ मराठी (Marathi) │
└──────────────────────┘
```

---

## 3. Entity Extraction Panel

**Location:** `frontend/src/components/voice-agent/EntityExtraction.tsx`

### Features

#### Live Entity Display
```
┌─────────────────────────────────────┐
│ 📋 Extracted Entities               │
├─────────────────────────────────────┤
│ 👤 Name:     John Smith             │
│ 📧 Email:    john@example.com       │
│ 📞 Phone:    +1-555-123-4567        │
│ 📍 Location: New York, NY           │
│ 📅 Date:     December 15, 2024      │
│ 💰 Amount:   $500.00                │
└─────────────────────────────────────┘
```

#### Categories
- Names (Person, Organization)
- Contact (Email, Phone)
- Location (Address, City)
- Date/Time
- Numbers/Amounts
- Custom entities

#### Export Option
- Copy to clipboard
- Download as JSON

---

## 4. Sentiment Analysis Panel

**Location:** `frontend/src/components/voice-agent/SentimentAnalysis.tsx`

### Features

#### Real-Time Score
```
┌─────────────────────────────────────┐
│ 😊 Sentiment: Positive (0.78)       │
│ ████████████████░░░░ 78%            │
└─────────────────────────────────────┘
```

#### Visual Indicator
- 😊 Positive (green, > 0.3)
- 😐 Neutral (gray, -0.3 to 0.3)
- 😔 Negative (red, < -0.3)

#### Trend Graph
- Line chart showing sentiment over conversation
- X-axis: Time/turns
- Y-axis: Sentiment score (-1 to 1)

---

## 5. Prompt Editor

**Location:** `frontend/src/components/voice-agent/PromptEditor.tsx`

### Features

#### System Prompt Editor
```
┌─────────────────────────────────────┐
│ System Prompt                    📝 │
├─────────────────────────────────────┤
│ You are a helpful customer service  │
│ agent. Be polite and concise.       │
│                                     │
│ Guidelines:                         │
│ - Greet the caller warmly           │
│ - Ask clarifying questions          │
│ - Provide accurate information      │
│                                     │
└─────────────────────────────────────┘
│ [Save] [Reset] [Test]               │
└─────────────────────────────────────┘
```

#### Presets
- Default greeting agent
- Customer support
- Booking assistant
- Technical support
- Custom (user-defined)

#### Test Mode
- Send test message
- See agent response
- Evaluate before saving

---

## 6. SIP Configuration Interface

**Location:** `frontend/src/components/sip/SIPConfig.tsx`

### Trunk Management

```
┌─────────────────────────────────────────────────────────┐
│ SIP Trunks                                    [+ Add]   │
├─────────────────────────────────────────────────────────┤
│ ● Main Trunk          +1-800-555-0100    ✅ Active      │
│   └─ Allowed: 0.0.0.0/0                                 │
│                                                         │
│ ○ Backup Trunk        +1-800-555-0200    ⚠️ Standby    │
│   └─ Allowed: 192.168.0.0/16                           │
└─────────────────────────────────────────────────────────┘
```

#### Create/Edit Trunk
- Trunk name
- Phone numbers (multiple)
- Allowed addresses (CIDR)
- Authentication (optional)
- Status toggle

### Dispatch Rules

```
┌─────────────────────────────────────────────────────────┐
│ Dispatch Rules                                [+ Add]   │
├─────────────────────────────────────────────────────────┤
│ 1. Main → incoming-calls (priority: 1)                  │
│ 2. Backup → overflow-room (priority: 2)                 │
└─────────────────────────────────────────────────────────┘
```

#### Create/Edit Rule
- Select trunk(s)
- Target room name
- Priority level
- Metadata (JSON)

### Call Routing Preview
- Test number input
- Show which trunk/room would handle
- Validation status

---

## 7. Common Components

### Button.tsx
```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'danger';
  size: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}
```

### Loading.tsx
```typescript
interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}
```

### Speaking Indicator CSS
```css
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

## 8. Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│ Header: Logo | Navigation | User Menu                   │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│   Sidebar    │           Main Content Area              │
│              │                                          │
│ - Dashboard  │  ┌────────────────────────────────────┐ │
│ - Voice Agent│  │                                    │ │
│ - SIP Config │  │     (Selected Component)           │ │
│ - Settings   │  │                                    │ │
│              │  └────────────────────────────────────┘ │
│              │                                          │
└──────────────┴──────────────────────────────────────────┘
```

---

## 9. State Management (Zustand)

```typescript
// stores/callStore.ts
interface CallState {
  activeCalls: Call[];
  selectedCall: Call | null;
  transcripts: TranscriptEntry[];
  entities: Entity[];
  sentiment: SentimentScore;

  // Actions
  setActiveCalls: (calls: Call[]) => void;
  addTranscript: (entry: TranscriptEntry) => void;
  updateSentiment: (score: SentimentScore) => void;
  extractEntities: (text: string) => void;
}
```

---

## 10. API Integration

```typescript
// services/api.ts
const api = {
  // Rooms
  createRoom: (name: string) => POST('/api/rooms', { name }),
  listRooms: () => GET('/api/rooms'),

  // Tokens
  getToken: (room: string, identity: string) =>
    POST('/api/tokens', { room, identity }),

  // SIP
  createTrunk: (config: TrunkConfig) => POST('/api/sip/trunks', config),
  listTrunks: () => GET('/api/sip/trunks'),
  createDispatchRule: (rule: DispatchRule) =>
    POST('/api/sip/dispatch-rules', rule),

  // Transcripts
  getTranscripts: (roomSid: string) =>
    GET(`/api/transcripts/${roomSid}`),
  logTransaction: (roomSid: string, tx: Transaction) =>
    POST(`/api/transactions/${roomSid}`, tx),
};
```

---

## Success Criteria

- [ ] Call Dashboard displays all metrics in real-time
- [ ] Voice Agent UI matches LiveKit Cloud Playground style
- [ ] Entity extraction displays live during conversation
- [ ] Sentiment analysis updates in real-time
- [ ] Prompt editor saves and applies changes
- [ ] SIP configuration allows full trunk/rule management
- [ ] Language selector works for all 4 languages
- [ ] Speaking indicator visible when participant talks
- [ ] Responsive design works on tablet/desktop