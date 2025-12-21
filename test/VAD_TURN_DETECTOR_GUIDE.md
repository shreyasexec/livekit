# VAD and Turn Detector Configuration Guide

## Overview

Voice Activity Detection (VAD) and Turn Detection are critical for natural conversation flow. This guide explains how they work and how to tune them for optimal performance.

---

## How It Works

### 1. Voice Activity Detection (VAD)
**Technology:** Silero VAD (open-source, runs on CPU)
**Purpose:** Detect when user is speaking vs. silence

**Flow:**
```
User Audio → Silero VAD → "Speech Detected" or "Silence Detected"
                ↓
         If "Speech Detected" → Interrupt agent if speaking
```

### 2. Turn Detector
**Technology:** LiveKit Multilingual Model
**Purpose:** Decide when user has finished their turn

**Flow:**
```
STT Interim Transcripts → Turn Detector → "Turn Complete" signal
                            ↓
                     Agent starts responding
```

---

## Critical Behaviors

### A. User Talks → Agent Stops Immediately

**What should happen:**
1. User starts speaking
2. VAD detects speech within **50-100ms**
3. Agent stops speaking **immediately** (within 100ms)
4. STT starts transcribing user speech

**Configuration:**
```python
# In worker.py
vad=silero.VAD.load()  # Default settings work well
```

**Tuning:**
- **If agent doesn't stop fast enough:**
  ```python
  vad=silero.VAD.load(
      min_speech_duration_ms=100,  # Lower = faster detection (default: 250)
      min_silence_duration_ms=300  # Lower = faster end detection (default: 500)
  )
  ```

**Test:** Manual Test Procedure 2.1 (Interrupt Test)

---

### B. User Pauses (Incomplete Sentence) → Agent Waits 2 Seconds

**What should happen:**
1. User says: "Hello, I want to..." (incomplete)
2. User stops talking (thinking pause)
3. Turn detector waits **2 seconds** for user to continue
4. After 2 seconds, agent responds

**Configuration:**
```python
# In worker.py
turn_detector=MultilingualModel(
    min_endpointing_delay=2000,  # 2 seconds = 2000ms
)
```

**Tuning:**
- **If agent interrupts thinking pauses** (responds too fast):
  ```python
  min_endpointing_delay=2500  # Increase to 2.5 seconds
  ```

- **If agent waits too long** (feels slow):
  ```python
  min_endpointing_delay=1500  # Decrease to 1.5 seconds
  ```

**Test:** Manual Test Procedure 2.2 (Silence Timeout Test)

---

### C. User Completes Sentence → Agent Responds Quickly

**What should happen:**
1. User says: "Hello, how are you?" (complete)
2. Turn detector recognizes complete sentence
3. Agent starts responding within **300-800ms**

**Configuration:**
```python
# In worker.py
turn_detector=MultilingualModel(
    min_endpointing_delay=2000,  # Max wait time
    # Turn detector uses ML to detect completion earlier than timeout
)
```

**How it works:**
- Turn detector analyzes STT transcripts
- Uses ML model to predict "turn is complete"
- Responds **before** 2-second timeout if sentence is clearly complete

**Test:** Manual Test Procedure 2.3 (Turn Completion Test)

---

## Current Configuration

### Location
File: `/home/aicalltaker/livekit/backend/agent/worker.py`

### Current Settings
```python
# VAD Configuration
vad=silero.VAD.load()
# Uses default Silero VAD settings:
# - min_speech_duration_ms: 250
# - min_silence_duration_ms: 500
# - speech_pad_ms: 30

# Turn Detector Configuration
turn_detector=MultilingualModel()
# Uses default turn detector settings:
# - min_endpointing_delay: ~2000ms (estimated from behavior)
# - Multilingual support (auto-detects language)
```

### View Full Configuration
```bash
grep -A 30 "def prewarm" /home/aicalltaker/livekit/backend/agent/worker.py
```

---

## Tuning Workflow

### Step 1: Identify the Problem

Run manual tests (see `MANUAL_TEST_PROCEDURES.md`):
- Test 2.1: Interrupt behavior
- Test 2.2: Silence timeout
- Test 2.3: Turn completion

Document what's wrong:
- [ ] Agent doesn't stop when I interrupt
- [ ] Agent interrupts my thinking pauses
- [ ] Agent waits too long to respond
- [ ] Agent responds before I finish

---

### Step 2: Adjust Parameters

Edit `/home/aicalltaker/livekit/backend/agent/worker.py`:

Find the `prewarm` function (around line 450-500):

```python
async def prewarm(proc: JobContext):
    """Prewarm function to load models before handling jobs."""

    # VAD configuration
    await proc.wait_for_participant()
    proc.add_participant_entrypoint(entrypoint)

    # Inside Agent class initialization:
    vad = silero.VAD.load(
        # TUNE THESE VALUES:
        min_speech_duration_ms=250,  # Lower = faster speech detection
        min_silence_duration_ms=500,  # Lower = faster silence detection
    )

    turn_detector = MultilingualModel(
        # TUNE THIS VALUE:
        min_endpointing_delay=2000,  # Silence timeout in milliseconds
    )
```

---

### Step 3: Apply Changes

```bash
# Restart agent worker to apply changes
docker compose restart agent-worker

# Wait for startup
sleep 5

# Check logs
docker compose logs agent-worker --tail=20
```

---

### Step 4: Re-Test

Run the same manual tests again:
- Test 2.1, 2.2, 2.3
- Document improvements/regressions

---

### Step 5: Iterate

Repeat steps 2-4 until behavior is optimal.

---

## Recommended Configurations

### Scenario 1: Customer Support (Patient, Thorough)
```python
vad = silero.VAD.load(
    min_speech_duration_ms=300,  # Less sensitive (avoid false triggers)
    min_silence_duration_ms=600,
)

turn_detector = MultilingualModel(
    min_endpointing_delay=2500,  # Longer wait (let users think)
)
```

**Characteristics:**
- Agent doesn't rush
- Allows longer thinking pauses
- Good for complex questions

---

### Scenario 2: Quick Interactions (Fast, Responsive)
```python
vad = silero.VAD.load(
    min_speech_duration_ms=150,  # Very sensitive
    min_silence_duration_ms=300,
)

turn_detector = MultilingualModel(
    min_endpointing_delay=1500,  # Shorter wait
)
```

**Characteristics:**
- Snappy responses
- Minimal wait time
- Good for simple queries

---

### Scenario 3: Current Production Settings (Balanced)
```python
vad = silero.VAD.load()  # Defaults

turn_detector = MultilingualModel()  # Defaults
# min_endpointing_delay: ~2000ms (from testing)
```

**Characteristics:**
- Balanced between speed and patience
- Works for most use cases
- **Current deployment**

---

## Advanced: Turn Detector Internals

### How Turn Detector Decides

The Multilingual Model uses:
1. **Transcript analysis:** Looks for sentence-ending patterns
2. **Timing:** Measures silence duration
3. **Language model:** Predicts if utterance is complete

### Example Decision Process

```
User says: "Hello, how are you?"

Interim transcripts received:
t=0ms:    "Hello"           → Not complete (no question answered)
t=200ms:  "Hello how"        → Not complete
t=500ms:  "Hello how are"    → Not complete
t=800ms:  "Hello how are you" → Possibly complete (valid question)
t=1100ms: "Hello how are you?" → COMPLETE (punctuation + silence)

Silence detected for 300ms after "you?"
→ Turn Detector: COMPLETE at t=1400ms
→ Agent starts responding
```

**Key Insight:** Turn detector doesn't wait full 2 seconds if sentence is clearly complete!

---

## Monitoring VAD/Turn Detector

### Real-Time Monitoring

Terminal 1:
```bash
docker compose logs -f agent-worker | grep -E "(VAD|Turn|Interrupt)"
```

Terminal 2:
```bash
docker compose logs -f agent-worker | grep PERF
```

### Metrics to Watch

From `[PERF]` logs:
```
[PERF] turn_1 | STT:400ms | LLM-TTFT:800ms | ...
```

**STT time** includes:
- User speech duration
- Turn detector decision time
- Should be **< 500ms** from speech end to final transcript

---

## Troubleshooting

### Problem: Agent doesn't stop when interrupted

**Possible Causes:**
1. VAD not detecting speech fast enough
2. Interrupt handling not enabled

**Solutions:**
```python
# Lower VAD thresholds
vad = silero.VAD.load(
    min_speech_duration_ms=100,  # Faster detection
)

# Verify interrupt is enabled (should be default)
# Check Agent initialization has interrupt behavior enabled
```

---

### Problem: Agent interrupts when I'm thinking

**Possible Cause:**
Turn detector timeout too short

**Solution:**
```python
turn_detector = MultilingualModel(
    min_endpointing_delay=2500,  # Increase to 2.5s
)
```

---

### Problem: Conversation feels sluggish

**Possible Cause:**
Turn detector timeout too long

**Solution:**
```python
turn_detector = MultilingualModel(
    min_endpointing_delay=1500,  # Decrease to 1.5s
)
```

**Warning:** Don't go below 1000ms or agent will interrupt thinking pauses!

---

## Performance Impact

### VAD Performance
- **CPU Usage:** ~5-10% of one core
- **Latency:** ~10-20ms per audio frame
- **Memory:** ~50MB

### Turn Detector Performance
- **CPU Usage:** Minimal (runs on transcript events only)
- **Latency:** ~5-10ms per transcript
- **Memory:** ~100MB (ML model loaded)

**Total Impact:** Negligible on modern hardware

---

## Testing Checklist

After tuning, verify:

- [ ] **Interrupt Test (2.1):** Agent stops within 100ms when I speak
- [ ] **Silence Timeout (2.2):** Agent waits 2s for incomplete sentences
- [ ] **Turn Completion (2.3):** Agent responds 300-800ms after complete sentences
- [ ] **Performance:** E2E latency still < 2 seconds
- [ ] **Natural Flow:** Conversation feels smooth, not robotic

---

## References

### Official Documentation
- LiveKit VAD: https://docs.livekit.io/agents/plugins/silero/
- LiveKit Turn Detection: https://docs.livekit.io/agents/overview/turn-detection/
- Silero VAD GitHub: https://github.com/snakers4/silero-vad

### Code Locations
- VAD Configuration: `/home/aicalltaker/livekit/backend/agent/worker.py` (line ~470)
- Turn Detector: `/home/aicalltaker/livekit/backend/agent/worker.py` (line ~480)
- Agent Initialization: `/home/aicalltaker/livekit/backend/agent/worker.py` (line ~500)

---

**END OF VAD AND TURN DETECTOR GUIDE**
