# Manual Test Procedures - Voice AI Platform

## Prerequisites

1. All services running: `docker compose ps` - all should be "healthy"
2. Browser: Chrome/Edge (best WebRTC support)
3. Linphone app installed for SIP testing
4. Microphone permissions enabled

---

## Test 1: WebRTC Browser Test

### Setup
1. Open Chrome: `https://192.168.20.62:3000/`
2. Accept self-signed certificate warning (click "Advanced" → "Proceed")
3. First time: Visit `https://192.168.20.62:7880` and accept certificate there too

### Test Procedure

#### 1.1 Basic Connection Test
**Steps:**
1. Enter Room Name: `test-room-001`
2. Enter Your Name: `Test User`
3. Click "Join Room"
4. **VERIFY**: Green "Connected" status appears
5. **VERIFY**: Audio visualizer shows activity
6. **VERIFY**: No error messages in UI

**Expected Result:**
- Connection status: "Connected" (green)
- No errors in browser console (F12)
- Agent worker logs show: `Agent joined room test-room-001`

**FAIL if:**
- Red error message appears
- Console shows WebSocket errors
- Agent doesn't join

---

#### 1.2 Simple Greeting Test
**Steps:**
1. Connected to room (from 1.1)
2. Speak clearly: **"Hello"**
3. Wait for agent response

**VERIFY Performance:**
- Agent stops speaking immediately when you speak (VAD interrupt)
- Response starts within **2 seconds** of your speech ending
- No awkward silences or interruptions

**Check Logs:**
```bash
docker compose logs agent-worker --tail=50 | grep PERF
```

**Expected Log Output:**
```
[PERF] turn_1 | STT:400ms | LLM-TTFT:800ms | LLM:1200ms | TTS-TTFB:200ms | E2E:1800ms
```

**PASS Criteria:**
- E2E (end-to-end) < 2000ms
- Agent responds naturally
- Audio is clear, no distortion

**FAIL if:**
- E2E > 2000ms
- Agent doesn't respond
- Audio is garbled

---

#### 1.3 Multi-Turn Conversation Test
**Steps:**
1. Say: **"Hello, how are you?"**
2. Wait for response
3. Say: **"What can you help me with?"**
4. Wait for response
5. Say: **"Thank you, goodbye"**

**VERIFY:**
- Each turn completes successfully
- Context is maintained (agent remembers conversation)
- Performance stays < 2s per turn

**Check Transcript Panel:**
- All your speech appears in transcript
- All agent responses appear in transcript
- Timestamps are reasonable

---

## Test 2: VAD Turn Detector Testing

### Critical Test Scenarios

#### 2.1 Interrupt Test (Agent should stop when user speaks)
**Setup:**
1. Join room
2. Ask a question that will get a long response: **"Can you explain what you do in detail?"**

**Test Steps:**
1. Agent starts speaking (long response)
2. **IMMEDIATELY** interrupt by saying: **"Wait, stop"**
3. **VERIFY**: Agent stops speaking **immediately** (within 100ms)
4. **VERIFY**: Your interruption is transcribed
5. Agent responds to your interruption

**PASS Criteria:**
- Agent stops within **100ms** of your speech starting
- No audio overlap (agent voice cuts off cleanly)
- Your "Wait, stop" is recognized

**FAIL if:**
- Agent continues speaking over you
- Your speech isn't recognized
- Agent takes > 200ms to stop

---

#### 2.2 Silence Timeout Test (2-second rule)
**Setup:**
1. Join room
2. Start speaking but **don't complete the sentence**

**Test Steps:**
1. Say: **"Hello, I want to..."** (then pause, don't finish)
2. Stay silent for exactly **2 seconds**
3. **VERIFY**: Agent waits full 2 seconds
4. **VERIFY**: Agent then responds after 2s timeout

**PASS Criteria:**
- Agent waits **minimum 2 seconds** before responding
- Agent doesn't interrupt your thinking pause
- Response is natural ("Yes? How can I help?")

**FAIL if:**
- Agent responds before 2 seconds
- Agent interrupts your pause
- No response after 3+ seconds

---

#### 2.3 Turn Completion Test
**Setup:**
1. Join room

**Test Steps:**
1. Say: **"Hello, how are you today?"** (complete sentence)
2. **VERIFY**: Agent starts responding within **500ms** of your last word
3. **VERIFY**: Agent doesn't wait unnecessarily

**PASS Criteria:**
- Agent responds **300-800ms** after you finish speaking
- Feels natural (not too fast, not too slow)
- No awkward pause

**FAIL if:**
- Agent responds before you finish (< 300ms)
- Agent takes > 1 second to start response
- Conversation feels unnatural

---

## Test 3: SIP Testing via Linphone

### Setup Linphone
1. Open Linphone app
2. Add SIP account:
   - Username: `test-user`
   - Domain: `192.168.20.62:5060`
   - Transport: UDP
   - No authentication required

### Test Procedure

#### 3.1 SIP Call Connection
**Steps:**
1. In Linphone, dial: `sip:voice-agent@192.168.20.62:5060`
2. Wait for call to connect
3. **VERIFY**: Call status shows "Connected"
4. **VERIFY**: You hear agent greeting

**Expected Greeting:**
"Hello, how can I help you today?"

**PASS Criteria:**
- Call connects within 3 seconds
- Agent greeting plays clearly
- No audio dropouts

---

#### 3.2 SIP Two-Way Audio Test
**Steps:**
1. Connected call (from 3.1)
2. Say: **"Hello, can you hear me?"**
3. Wait for response
4. Say: **"What's the weather like?"**
5. Wait for response

**VERIFY:**
- Agent hears and transcribes your speech correctly
- You hear agent responses clearly
- No echo or feedback
- Performance < 2s per turn

**Check Logs:**
```bash
docker compose logs livekit-sip --tail=50
```

---

## Test 4: Performance Measurement

### Setup Performance Monitoring
```bash
# Terminal 1: Watch agent logs in real-time
docker compose logs -f agent-worker | grep PERF

# Terminal 2: Monitor system resources
docker stats --no-stream livekit-agent-worker-1 livekit-piper-tts-1
```

### Measure Latencies

#### Component Breakdown (Target < 2000ms total)
| Component | Target | Measured | Pass/Fail |
|-----------|--------|----------|-----------|
| STT | < 500ms | ______ms | ⬜ |
| LLM TTFT | < 1000ms | ______ms | ⬜ |
| TTS TTFB | < 300ms | ______ms | ⬜ |
| **E2E Total** | **< 2000ms** | ______ms | ⬜ |

#### How to Measure:
1. Join room
2. Say: **"Hello"**
3. Check logs for `[PERF]` line
4. Record values in table above
5. Repeat 5 times, use average

**Example Log:**
```
[PERF] turn_1 | STT:423ms | LLM-TTFT:856ms | LLM:1180ms | TTS-TTFB:245ms | E2E:1704ms
```

---

## Test 5: VAD Configuration Verification

### Check Current VAD Settings
```bash
docker compose exec agent-worker python -c "
from livekit.plugins import silero
vad = silero.VAD.load()
print(f'VAD Model: {vad}')
"
```

### Check Turn Detector Settings
```bash
# View agent worker code
grep -A 10 "MultilingualModel" /home/aicalltaker/livekit/backend/agent/worker.py
```

**Expected Configuration:**
- VAD: Silero VAD
- Turn Detector: Multilingual Model
- Interrupt behavior: Enabled (agent stops when user speaks)
- Min end-of-turn timeout: 2000ms (2 seconds)

---

## Test 6: Error Handling

#### 6.1 Network Interruption Test
**Steps:**
1. Join room, start conversation
2. Disconnect WiFi for 3 seconds
3. Reconnect WiFi
4. Continue conversation

**VERIFY:**
- UI shows "Reconnecting..."
- Connection recovers automatically
- Conversation resumes without restart

---

#### 6.2 Microphone Permission Revocation
**Steps:**
1. Join room
2. Browser settings → Revoke microphone permission
3. Try to speak

**VERIFY:**
- Clear error message shown
- Instructions to re-enable permission
- No browser crash

---

## Test Results Template

```
Date: ___________
Tester: ___________

## WebRTC Tests
- [ ] 1.1 Basic Connection: PASS / FAIL
- [ ] 1.2 Simple Greeting: PASS / FAIL (E2E: ____ms)
- [ ] 1.3 Multi-Turn: PASS / FAIL

## VAD Tests
- [ ] 2.1 Interrupt: PASS / FAIL
- [ ] 2.2 Silence Timeout (2s): PASS / FAIL
- [ ] 2.3 Turn Completion: PASS / FAIL

## SIP Tests
- [ ] 3.1 Connection: PASS / FAIL
- [ ] 3.2 Two-Way Audio: PASS / FAIL

## Performance
- Average E2E Latency: ____ms (Target: < 2000ms)

## Issues Found:
1. ___________
2. ___________
3. ___________
```

---

## Troubleshooting

### Issue: "SSL connection is closed" warnings in logs
**Solution:** These are harmless - asyncio warnings when connections close normally. Suppressed in latest code.

### Issue: Agent doesn't respond
**Check:**
1. `docker compose logs agent-worker --tail=50`
2. Look for errors in STT/LLM/TTS
3. Verify services healthy: `docker compose ps`

### Issue: High latency (> 2s)
**Check:**
1. Ollama server: `curl http://192.168.1.120:11434/api/tags`
2. WhisperLiveKit: `curl -k https://192.168.1.120:8765/`
3. Network latency: `ping 192.168.1.120`

### Issue: VAD not working (agent doesn't stop when interrupted)
**Check:**
1. Agent logs for VAD events
2. Verify Silero VAD is loaded
3. Check turn detector configuration

---

## Performance Tuning Guide

### If E2E > 2000ms:

**STT too slow (> 500ms):**
- Check WhisperLiveKit GPU server performance
- Reduce audio chunk size

**LLM too slow (> 1000ms TTFT):**
- Use faster Ollama model (llama3.1:8b → phi3)
- Check Ollama GPU utilization

**TTS too slow (> 300ms TTFB):**
- Verify Piper is using ONNX optimizations
- Check CPU usage of piper-tts container

---

## VAD Turn Detector Tuning

### Adjust Interrupt Sensitivity
Edit `/home/aicalltaker/livekit/backend/agent/worker.py`:

```python
turn_detector=MultilingualModel(
    # Lower = more sensitive to interrupts
    min_volume=0.3,  # Default: 0.5
)
```

### Adjust Silence Timeout
```python
turn_detector=MultilingualModel(
    # Milliseconds of silence before considering turn complete
    min_endpointing_delay=2000,  # Current: 2 seconds
)
```

### Test Changes:
```bash
docker compose restart agent-worker
# Re-run VAD tests 2.1, 2.2, 2.3
```

---

**END OF MANUAL TEST PROCEDURES**
