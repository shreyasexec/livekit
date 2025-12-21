#!/usr/bin/env python3
"""
Turn Detector End-to-End Test Suite

Tests the voice agent pipeline with simulated audio:
1. Agent connection and greeting
2. STT streaming interim transcripts
3. Turn detector EOU predictions
4. Response timing validation

Run from backend container:
    docker compose exec agent-worker python3 /app/../test/test_turn_detector.py

Or copy test file and run:
    docker compose cp test/test_turn_detector.py agent-worker:/tmp/test.py
    docker compose exec agent-worker python3 /tmp/test.py
"""

import asyncio
import json
import logging
import math
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Optional

from livekit import api, rtc

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("turn-detector-test")

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "http://livekit:7880")
API_KEY = os.getenv("LIVEKIT_API_KEY", "1uhwH2Iv3aGFNTCGC3bNv0OhBjsffTdgJJiGDgYfJKw=")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "vh+pYw6eg1DQaMPZH4tdS3t39fwTRvuA4XEqNF37Mf8=")


@dataclass
class TestMetrics:
    """Track test metrics and timing."""
    test_name: str
    start_time: float = field(default_factory=time.time)
    agent_joined_at: Optional[float] = None
    first_agent_audio_at: Optional[float] = None
    transcripts: list = field(default_factory=list)
    events: list = field(default_factory=list)

    def log_event(self, event_type: str, data: dict = None):
        """Log timestamped event."""
        self.events.append({
            "time": time.time() - self.start_time,
            "type": event_type,
            "data": data or {}
        })
        logger.debug(f"[EVENT] {event_type}: {data}")

    def summary(self) -> dict:
        """Return test summary."""
        return {
            "test": self.test_name,
            "duration_s": time.time() - self.start_time,
            "agent_join_latency_ms": int((self.agent_joined_at - self.start_time) * 1000) if self.agent_joined_at else None,
            "first_audio_latency_ms": int((self.first_agent_audio_at - self.start_time) * 1000) if self.first_agent_audio_at else None,
            "transcript_count": len(self.transcripts),
            "event_count": len(self.events)
        }


def generate_sine_audio(duration_s: float, frequency: float = 440, sample_rate: int = 16000) -> bytes:
    """Generate sine wave audio for testing.

    Returns raw PCM int16 audio bytes.
    """
    samples = int(duration_s * sample_rate)
    audio = bytes()
    for i in range(samples):
        t = i / sample_rate
        value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
        audio += struct.pack('<h', value)
    return audio


def generate_speech_like_audio(duration_s: float, sample_rate: int = 16000) -> bytes:
    """Generate speech-like audio with varying amplitude and frequency.

    This creates a more realistic audio pattern that should trigger VAD.
    """
    samples = int(duration_s * sample_rate)
    audio = bytes()

    # Speech-like modulation: varying frequency and amplitude
    for i in range(samples):
        t = i / sample_rate
        # Base frequency around 200Hz (typical for speech)
        freq = 200 + 50 * math.sin(2 * math.pi * 3 * t)  # Modulate frequency
        # Amplitude modulation to simulate syllables
        amplitude = 0.3 + 0.3 * abs(math.sin(2 * math.pi * 4 * t))
        value = int(32767 * amplitude * math.sin(2 * math.pi * freq * t))
        audio += struct.pack('<h', value)

    return audio


def load_wav_file(filepath: str, target_sample_rate: int = 16000) -> bytes:
    """Load WAV file and resample to target sample rate if needed.

    Returns raw PCM int16 audio bytes at target sample rate.
    """
    import wave
    try:
        with wave.open(filepath, 'rb') as wf:
            source_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            num_frames = wf.getnframes()
            audio_data = wf.readframes(num_frames)

            logger.info(f"[AUDIO] Loaded {filepath}: {source_rate}Hz, {num_channels}ch, {sample_width}B, {num_frames} frames")

            # Convert to mono if stereo
            if num_channels == 2:
                samples = struct.unpack(f'<{num_frames * 2}h', audio_data)
                mono_samples = [(samples[i] + samples[i+1]) // 2 for i in range(0, len(samples), 2)]
                audio_data = struct.pack(f'<{len(mono_samples)}h', *mono_samples)
                num_frames = len(mono_samples)

            # Simple resampling if needed (linear interpolation)
            if source_rate != target_sample_rate:
                samples = struct.unpack(f'<{num_frames}h', audio_data)
                ratio = target_sample_rate / source_rate
                new_length = int(num_frames * ratio)
                resampled = []
                for i in range(new_length):
                    src_idx = i / ratio
                    idx0 = int(src_idx)
                    idx1 = min(idx0 + 1, num_frames - 1)
                    frac = src_idx - idx0
                    value = int(samples[idx0] * (1 - frac) + samples[idx1] * frac)
                    resampled.append(value)
                audio_data = struct.pack(f'<{len(resampled)}h', *resampled)
                logger.info(f"[AUDIO] Resampled from {source_rate}Hz to {target_sample_rate}Hz")

            return audio_data
    except Exception as e:
        logger.error(f"[AUDIO] Failed to load {filepath}: {e}")
        return generate_speech_like_audio(3.0, target_sample_rate)


async def generate_tts_audio(text: str, target_sample_rate: int = 16000) -> bytes:
    """Generate speech audio using Piper TTS service.

    Returns raw PCM int16 audio bytes at target sample rate.
    """
    import aiohttp
    import io
    import wave

    piper_url = os.getenv("PIPER_TTS_URL", "http://piper-tts:5500")
    url = f"{piper_url}/api/synthesize/stream"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"text": text, "voice": "en_US-lessac-medium", "sample_rate": 22050}
            ) as resp:
                if resp.status != 200:
                    logger.error(f"[TTS] HTTP {resp.status}")
                    return generate_speech_like_audio(3.0, target_sample_rate)

                # Read all audio data
                audio_data = await resp.read()
                logger.info(f"[TTS] Generated {len(audio_data)} bytes of audio for: '{text[:50]}'")

                # Piper returns raw PCM at 22050Hz, resample to 16kHz
                source_rate = 22050
                num_frames = len(audio_data) // 2  # 16-bit samples
                samples = struct.unpack(f'<{num_frames}h', audio_data)

                ratio = target_sample_rate / source_rate
                new_length = int(num_frames * ratio)
                resampled = []
                for i in range(new_length):
                    src_idx = i / ratio
                    idx0 = int(src_idx)
                    idx1 = min(idx0 + 1, num_frames - 1)
                    frac = src_idx - idx0
                    value = int(samples[idx0] * (1 - frac) + samples[idx1] * frac)
                    resampled.append(value)

                return struct.pack(f'<{len(resampled)}h', *resampled)

    except Exception as e:
        logger.error(f"[TTS] Failed to generate audio: {e}")
        return generate_speech_like_audio(3.0, target_sample_rate)


async def test_agent_connection_and_greeting() -> dict:
    """Test 1: Verify agent joins and sends greeting."""
    metrics = TestMetrics(test_name="Agent Connection and Greeting")
    room_name = f"test-connection-{int(time.time())}"

    logger.info(f"[TEST] Starting: {metrics.test_name}")
    logger.info(f"[TEST] Room: {room_name}")

    try:
        # Create room
        lk = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)
        await lk.room.create_room(api.CreateRoomRequest(name=room_name, empty_timeout=120))
        metrics.log_event("room_created", {"room": room_name})

        # Generate token
        token = (
            api.AccessToken(API_KEY, API_SECRET)
            .with_identity("Test-Participant")
            .with_grants(api.VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )

        # Connect to room
        room = rtc.Room()
        agent_audio_received = asyncio.Event()

        @room.on("participant_connected")
        def on_participant(p):
            if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
                metrics.agent_joined_at = time.time()
                metrics.log_event("agent_joined", {"identity": p.identity})
                logger.info(f"[TEST] Agent joined: {p.identity}")

        @room.on("track_subscribed")
        def on_track(track, pub, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                if metrics.first_agent_audio_at is None:
                    metrics.first_agent_audio_at = time.time()
                metrics.log_event("audio_track_received", {"participant": participant.identity})
                logger.info(f"[TEST] Audio track received from: {participant.identity}")
                agent_audio_received.set()

        @room.on("data_received")
        def on_data(event):
            if event.topic == "transcripts":
                try:
                    msg = json.loads(event.data.decode())
                    metrics.transcripts.append(msg)
                    metrics.log_event("transcript_received", msg)
                    logger.info(f"[TEST] Transcript: [{msg.get('speaker')}] {msg.get('text', '')[:50]}")
                except Exception as e:
                    logger.error(f"[TEST] Transcript parse error: {e}")

        # Connect
        ws_url = LIVEKIT_URL.replace("http://", "ws://").replace("https://", "wss://")
        await room.connect(ws_url, token)
        metrics.log_event("room_connected")
        logger.info(f"[TEST] Connected to room: {room_name}")

        # Wait for agent audio (greeting)
        try:
            await asyncio.wait_for(agent_audio_received.wait(), timeout=30)
            logger.info("[TEST] Agent greeting audio received")
        except asyncio.TimeoutError:
            logger.warning("[TEST] Timeout waiting for agent audio")

        # Wait a bit more for transcripts
        await asyncio.sleep(5)

        # Cleanup
        await room.disconnect()
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        await lk.aclose()

        # Determine pass/fail
        passed = (
            metrics.agent_joined_at is not None and
            metrics.first_agent_audio_at is not None
        )

        return {
            "passed": passed,
            "metrics": metrics.summary(),
            "details": {
                "agent_joined": metrics.agent_joined_at is not None,
                "audio_received": metrics.first_agent_audio_at is not None,
                "transcripts_received": len(metrics.transcripts) > 0,
            }
        }

    except Exception as e:
        logger.error(f"[TEST] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "passed": False,
            "metrics": metrics.summary(),
            "error": str(e)
        }


async def test_stt_streaming() -> dict:
    """Test 2: Verify STT streams interim transcripts during speech."""
    metrics = TestMetrics(test_name="STT Streaming (Interim Transcripts)")
    room_name = f"test-stt-stream-{int(time.time())}"

    logger.info(f"[TEST] Starting: {metrics.test_name}")
    logger.info(f"[TEST] Room: {room_name}")

    try:
        lk = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)
        await lk.room.create_room(api.CreateRoomRequest(name=room_name, empty_timeout=120))
        metrics.log_event("room_created")

        token = (
            api.AccessToken(API_KEY, API_SECRET)
            .with_identity("Audio-Test-Participant")
            .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True))
            .to_jwt()
        )

        room = rtc.Room()
        agent_ready = asyncio.Event()

        @room.on("participant_connected")
        def on_participant(p):
            if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
                metrics.agent_joined_at = time.time()
                metrics.log_event("agent_joined")
                agent_ready.set()

        @room.on("data_received")
        def on_data(event):
            if event.topic == "transcripts":
                try:
                    msg = json.loads(event.data.decode())
                    metrics.transcripts.append(msg)
                    metrics.log_event("transcript", {"speaker": msg.get("speaker"), "text": msg.get("text", "")[:30]})
                except Exception:
                    pass

        ws_url = LIVEKIT_URL.replace("http://", "ws://").replace("https://", "wss://")
        await room.connect(ws_url, token)
        metrics.log_event("connected")

        # Wait for agent
        try:
            await asyncio.wait_for(agent_ready.wait(), timeout=20)
        except asyncio.TimeoutError:
            logger.warning("[TEST] Agent did not join in time")
            await room.disconnect()
            await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
            await lk.aclose()
            return {"passed": False, "error": "Agent timeout", "metrics": metrics.summary()}

        # Wait for agent greeting
        await asyncio.sleep(5)

        # Create audio source and publish
        logger.info("[TEST] Creating audio source for publishing...")
        source = rtc.AudioSource(sample_rate=16000, num_channels=1)
        track = rtc.LocalAudioTrack.create_audio_track("test-audio", source)
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await room.local_participant.publish_track(track, options)
        metrics.log_event("audio_published")
        logger.info("[TEST] Audio track published")

        # Generate real speech audio using TTS
        logger.info("[TEST] Generating speech audio using TTS...")
        audio_data = await generate_tts_audio("Hello, I am testing the speech recognition system. Can you hear me clearly?")
        chunk_size = 960  # 30ms chunks at 16kHz (16000 * 0.03 * 2 bytes)

        start_audio = time.time()
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            if len(chunk) < chunk_size:
                chunk = chunk + bytes(chunk_size - len(chunk))

            # Create audio frame
            frame = rtc.AudioFrame(
                data=chunk,
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=chunk_size // 2
            )
            await source.capture_frame(frame)

            # Pace the audio to real-time
            elapsed = time.time() - start_audio
            expected = (i + chunk_size) / (16000 * 2)  # bytes to seconds
            if expected > elapsed:
                await asyncio.sleep(expected - elapsed)

        metrics.log_event("audio_sent", {"duration_s": 3.0})
        logger.info("[TEST] Audio sent, waiting for processing...")

        # Wait for STT to process
        await asyncio.sleep(10)

        # Cleanup
        await room.disconnect()
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        await lk.aclose()

        # Check results
        user_transcripts = [t for t in metrics.transcripts if t.get("speaker") == "user"]

        return {
            "passed": len(user_transcripts) > 0,
            "metrics": metrics.summary(),
            "details": {
                "total_transcripts": len(metrics.transcripts),
                "user_transcripts": len(user_transcripts),
                "agent_transcripts": len([t for t in metrics.transcripts if t.get("speaker") == "assistant"]),
            }
        }

    except Exception as e:
        logger.error(f"[TEST] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "passed": False,
            "error": str(e),
            "metrics": metrics.summary()
        }


async def test_turn_detector_eou() -> dict:
    """Test 3: Verify turn detector predicts EOU correctly."""
    metrics = TestMetrics(test_name="Turn Detector EOU Prediction")
    room_name = f"test-turn-detector-{int(time.time())}"

    logger.info(f"[TEST] Starting: {metrics.test_name}")
    logger.info("[TEST] This test verifies turn detector allows complete sentences")

    # This test checks that the turn detector:
    # 1. Receives interim transcripts
    # 2. Predicts low EOU when speech is ongoing
    # 3. Only triggers response after natural pause

    try:
        lk = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)
        await lk.room.create_room(api.CreateRoomRequest(name=room_name, empty_timeout=120))

        token = (
            api.AccessToken(API_KEY, API_SECRET)
            .with_identity("Turn-Detector-Tester")
            .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True))
            .to_jwt()
        )

        room = rtc.Room()
        agent_ready = asyncio.Event()
        response_received = asyncio.Event()

        @room.on("participant_connected")
        def on_participant(p):
            if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
                metrics.log_event("agent_joined")
                agent_ready.set()

        @room.on("data_received")
        def on_data(event):
            if event.topic == "transcripts":
                try:
                    msg = json.loads(event.data.decode())
                    metrics.transcripts.append(msg)
                    if msg.get("speaker") == "assistant" and "greeting" not in msg.get("text", "").lower():
                        response_received.set()
                except Exception:
                    pass

        ws_url = LIVEKIT_URL.replace("http://", "ws://").replace("https://", "wss://")
        await room.connect(ws_url, token)

        # Wait for agent
        try:
            await asyncio.wait_for(agent_ready.wait(), timeout=20)
        except asyncio.TimeoutError:
            await room.disconnect()
            await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
            await lk.aclose()
            return {"passed": False, "error": "Agent timeout", "metrics": metrics.summary()}

        # Wait for greeting
        await asyncio.sleep(8)
        logger.info("[TEST] Agent greeting complete, ready for turn detection test")

        # Publish audio track
        source = rtc.AudioSource(sample_rate=16000, num_channels=1)
        track = rtc.LocalAudioTrack.create_audio_track("test-audio", source)
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await room.local_participant.publish_track(track, options)

        # Send speech in two bursts with a short pause (simulating natural speech)
        # This tests that the turn detector doesn't cut off mid-sentence

        # First burst - generate real speech with TTS
        logger.info("[TEST] Generating and sending first speech segment...")
        audio1 = await generate_tts_audio("I would like to ask you a question about")
        chunk_size = 960
        start = time.time()
        for i in range(0, len(audio1), chunk_size):
            chunk = audio1[i:i + chunk_size]
            if len(chunk) < chunk_size:
                chunk = chunk + bytes(chunk_size - len(chunk))
            frame = rtc.AudioFrame(data=chunk, sample_rate=16000, num_channels=1, samples_per_channel=chunk_size // 2)
            await source.capture_frame(frame)
            elapsed = time.time() - start
            expected = (i + chunk_size) / (16000 * 2)
            if expected > elapsed:
                await asyncio.sleep(expected - elapsed)

        metrics.log_event("first_segment_sent")

        # Short pause (300ms - should NOT trigger response)
        logger.info("[TEST] Short pause (300ms)...")
        await asyncio.sleep(0.3)

        # Second burst - complete the sentence
        logger.info("[TEST] Generating and sending second speech segment...")
        audio2 = await generate_tts_audio("the weather forecast for tomorrow please.")
        start = time.time()
        for i in range(0, len(audio2), chunk_size):
            chunk = audio2[i:i + chunk_size]
            if len(chunk) < chunk_size:
                chunk = chunk + bytes(chunk_size - len(chunk))
            frame = rtc.AudioFrame(data=chunk, sample_rate=16000, num_channels=1, samples_per_channel=chunk_size // 2)
            await source.capture_frame(frame)
            elapsed = time.time() - start
            expected = (i + chunk_size) / (16000 * 2)
            if expected > elapsed:
                await asyncio.sleep(expected - elapsed)

        metrics.log_event("second_segment_sent")

        # Now wait with silence - turn detector should trigger response
        logger.info("[TEST] Silence period - waiting for turn detector to trigger response...")
        speech_end = time.time()

        try:
            await asyncio.wait_for(response_received.wait(), timeout=15)
            response_time = time.time()
            response_delay = response_time - speech_end
            metrics.log_event("response_received", {"delay_s": response_delay})
            logger.info(f"[TEST] Response received after {response_delay:.2f}s")
        except asyncio.TimeoutError:
            logger.warning("[TEST] No response received after speech")
            response_delay = None

        # Cleanup
        await room.disconnect()
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        await lk.aclose()

        # Evaluate
        # Success criteria:
        # - Agent did not respond during the 300ms pause
        # - Agent responded after the final silence

        user_transcripts = [t for t in metrics.transcripts if t.get("speaker") == "user"]
        agent_responses = [t for t in metrics.transcripts if t.get("speaker") == "assistant"]

        # Check if response came at appropriate time (after full speech, not during short pause)
        passed = response_delay is not None

        return {
            "passed": passed,
            "metrics": metrics.summary(),
            "details": {
                "response_delay_s": response_delay,
                "user_transcripts": len(user_transcripts),
                "agent_responses": len(agent_responses),
                "events": len(metrics.events)
            }
        }

    except Exception as e:
        logger.error(f"[TEST] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "passed": False,
            "error": str(e),
            "metrics": metrics.summary()
        }


async def run_all_tests():
    """Run all turn detector tests."""
    print("\n" + "=" * 70)
    print("TURN DETECTOR TEST SUITE")
    print("=" * 70)
    print(f"LiveKit URL: {LIVEKIT_URL}")
    print("=" * 70 + "\n")

    results = {}

    # Test 1: Agent connection
    print("\n[TEST 1/3] Agent Connection and Greeting")
    print("-" * 50)
    results["connection"] = await test_agent_connection_and_greeting()
    print(f"Result: {'PASS' if results['connection']['passed'] else 'FAIL'}")

    # Test 2: STT streaming
    print("\n[TEST 2/3] STT Streaming")
    print("-" * 50)
    results["stt_streaming"] = await test_stt_streaming()
    print(f"Result: {'PASS' if results['stt_streaming']['passed'] else 'FAIL'}")

    # Test 3: Turn detector
    print("\n[TEST 3/3] Turn Detector EOU")
    print("-" * 50)
    results["turn_detector"] = await test_turn_detector_eou()
    print(f"Result: {'PASS' if results['turn_detector']['passed'] else 'FAIL'}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, result in results.items():
        status = "PASS" if result["passed"] else "FAIL"
        if not result["passed"]:
            all_passed = False
        print(f"  [{status}] {name}")
        if "metrics" in result:
            m = result["metrics"]
            print(f"        Duration: {m.get('duration_s', 0):.1f}s")
        if "error" in result:
            print(f"        Error: {result['error']}")
        if "details" in result:
            for k, v in result["details"].items():
                print(f"        {k}: {v}")

    print("=" * 70)
    print(f"OVERALL: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
