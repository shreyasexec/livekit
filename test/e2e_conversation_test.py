#!/usr/bin/env python3
"""
E2E Conversation Test - Simulates Real User Interaction

This test:
1. Joins LiveKit room like React UI does (username + room)
2. Sends synthetic audio (no mic needed - runs on headless Ubuntu)
3. Listens for agent responses
4. Measures component latencies for each conversation turn
5. Runs for configurable duration (default 1 minute)

Run from project root:
  docker-compose exec backend python /app/test/e2e_conversation_test.py

Or standalone with env vars:
  python test/e2e_conversation_test.py
"""

import asyncio
import time
import json
import wave
import io
import os
import sys
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from collections import defaultdict

# Install dependencies
subprocess.run([sys.executable, "-m", "pip", "install", "livekit", "livekit-api", "aiohttp", "numpy", "-q"], capture_output=True)

from livekit import rtc, api
import aiohttp
import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================
CONFIG = {
    # LiveKit
    "LIVEKIT_URL": os.getenv("LIVEKIT_URL", "ws://livekit:7880"),
    "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY", "devkey"),
    "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET", "secret"),

    # Services
    "PIPER_URL": os.getenv("PIPER_URL", "http://piper-tts:5500"),

    # Test parameters
    "TEST_DURATION_SECONDS": int(os.getenv("TEST_DURATION", "60")),  # 1 minute default
    "ROOM_NAME": f"e2e-test-{int(time.time())}",
    "USER_NAME": "E2E-Tester",
}

# Test phrases to simulate user speaking (varied lengths for realistic testing)
TEST_PHRASES = [
    "Hello, how are you today?",
    "What can you help me with?",
    "Tell me about yourself.",
    "What is the weather like?",
    "Can you explain artificial intelligence?",
    "What time is it?",
    "Thank you for your help.",
    "That's interesting, tell me more.",
    "How does voice recognition work?",
    "What are your capabilities?",
]


@dataclass
class TurnMetrics:
    """Metrics for a single conversation turn."""
    turn_number: int
    user_text: str
    agent_text: str = ""

    # Timestamps (ms from test start)
    audio_send_start: float = 0
    audio_send_end: float = 0
    transcript_received: float = 0
    agent_started_speaking: float = 0
    agent_stopped_speaking: float = 0

    # Calculated latencies (ms)
    stt_latency: float = 0  # audio_send_end -> transcript_received
    total_latency: float = 0  # audio_send_end -> agent_started_speaking
    agent_speech_duration: float = 0


@dataclass
class TestResults:
    """Aggregated test results."""
    total_turns: int = 0
    successful_turns: int = 0
    failed_turns: int = 0

    turns: List[TurnMetrics] = field(default_factory=list)

    # Aggregate latencies (ms)
    avg_stt_latency: float = 0
    avg_total_latency: float = 0
    min_total_latency: float = float('inf')
    max_total_latency: float = 0

    # Component breakdown from agent logs
    component_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    errors: List[str] = field(default_factory=list)


class ConversationTester:
    """Simulates a user having a conversation with the AI agent."""

    def __init__(self):
        self.test_start_time = 0
        self.results = TestResults()
        self.current_turn: Optional[TurnMetrics] = None
        self.room: Optional[rtc.Room] = None
        self.audio_source: Optional[rtc.AudioSource] = None

        # Event tracking
        self.agent_speaking = asyncio.Event()
        self.agent_stopped = asyncio.Event()
        self.transcript_received = asyncio.Event()
        self.received_transcript = ""
        self.received_agent_text = ""

    def log(self, msg: str, level: str = "INFO"):
        """Log with timestamp from test start."""
        elapsed = (time.time() - self.test_start_time) * 1000 if self.test_start_time else 0
        print(f"[{elapsed:>8.0f}ms] [{level}] {msg}")

    async def generate_speech_audio(self, text: str) -> tuple[np.ndarray, float]:
        """Generate speech audio using Piper TTS (simulates user speaking)."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CONFIG['PIPER_URL']}/api/synthesize",
                json={"text": text, "voice": "en_US-lessac-medium"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                wav_data = await resp.read()

        # Parse WAV
        with wave.open(io.BytesIO(wav_data), 'rb') as w:
            pcm = w.readframes(w.getnframes())
            rate = w.getframerate()
            channels = w.getnchannels()

        samples = np.frombuffer(pcm, dtype=np.int16)
        if channels == 2:
            samples = samples[::2]

        # Resample to 48kHz for LiveKit
        target_rate = 48000
        if rate != target_rate:
            target_len = int(len(samples) * target_rate / rate)
            samples = np.interp(
                np.linspace(0, len(samples), target_len),
                np.arange(len(samples)),
                samples.astype(np.float32)
            ).astype(np.int16)

        duration_ms = len(samples) / target_rate * 1000
        return samples, duration_ms

    async def send_audio(self, samples: np.ndarray):
        """Send audio samples through LiveKit (simulates mic input)."""
        # Send in 10ms frames (480 samples at 48kHz)
        frame_size = 480

        for i in range(0, len(samples), frame_size):
            chunk = samples[i:i+frame_size]
            if len(chunk) < frame_size:
                chunk = np.pad(chunk, (0, frame_size - len(chunk)))

            frame = rtc.AudioFrame.create(48000, 1, frame_size)
            np.copyto(np.frombuffer(frame.data, dtype=np.int16), chunk)
            await self.audio_source.capture_frame(frame)
            await asyncio.sleep(0.008)  # ~8ms between frames (slightly faster than realtime)

    def setup_event_handlers(self):
        """Setup LiveKit room event handlers."""

        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            self.log(f"Participant joined: {participant.identity}")
            if "agent" in participant.identity.lower():
                self.log("✓ Agent has joined the room", "SUCCESS")

        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            self.log(f"Participant left: {participant.identity}")

        @self.room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication,
                                participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                self.log(f"Subscribed to audio from: {participant.identity}")

        @self.room.on("active_speakers_changed")
        def on_active_speakers(speakers: list[rtc.Participant]):
            for speaker in speakers:
                if "agent" in speaker.identity.lower():
                    if self.current_turn and self.current_turn.agent_started_speaking == 0:
                        self.current_turn.agent_started_speaking = (time.time() - self.test_start_time) * 1000
                        self.log(f"Agent started speaking (turn {self.current_turn.turn_number})")
                    self.agent_speaking.set()

            # Check if agent stopped speaking
            agent_speaking = any("agent" in s.identity.lower() for s in speakers)
            if not agent_speaking and self.agent_speaking.is_set():
                if self.current_turn and self.current_turn.agent_stopped_speaking == 0:
                    self.current_turn.agent_stopped_speaking = (time.time() - self.test_start_time) * 1000
                    self.log(f"Agent stopped speaking")
                self.agent_stopped.set()

        @self.room.on("data_received")
        def on_data_received(data_packet: rtc.DataPacket):
            try:
                # Handle different data packet formats
                if hasattr(data_packet, 'data'):
                    raw_data = data_packet.data
                else:
                    raw_data = data_packet

                if isinstance(raw_data, bytes):
                    msg = json.loads(raw_data.decode('utf-8'))
                else:
                    msg = json.loads(str(raw_data))

                msg_type = msg.get("type", "")

                if msg_type == "transcript":
                    speaker = msg.get("speaker", "unknown")
                    text = msg.get("text", "")

                    if speaker == "user":
                        self.received_transcript = text
                        if self.current_turn:
                            self.current_turn.transcript_received = (time.time() - self.test_start_time) * 1000
                        self.log(f"📝 User transcript: '{text[:60]}...' " if len(text) > 60 else f"📝 User transcript: '{text}'")
                        self.transcript_received.set()

                    elif speaker in ["assistant", "agent"]:
                        self.received_agent_text = text
                        if self.current_turn:
                            self.current_turn.agent_text = text
                        self.log(f"🤖 Agent response: '{text[:60]}...' " if len(text) > 60 else f"🤖 Agent response: '{text}'")

                elif msg_type == "agent_status":
                    status = msg.get("status", "")
                    self.log(f"Agent status: {status}")

            except Exception as e:
                pass  # Ignore malformed data

    async def run_conversation_turn(self, turn_number: int, text: str) -> TurnMetrics:
        """Run a single conversation turn."""
        self.current_turn = TurnMetrics(turn_number=turn_number, user_text=text)

        # Reset events
        self.agent_speaking.clear()
        self.agent_stopped.clear()
        self.transcript_received.clear()
        self.received_transcript = ""
        self.received_agent_text = ""

        self.log(f"\n{'='*60}")
        self.log(f"TURN {turn_number}: '{text}'")
        self.log(f"{'='*60}")

        # Generate audio
        self.log("Generating speech audio...")
        gen_start = time.time()
        samples, audio_duration = await self.generate_speech_audio(text)
        gen_time = (time.time() - gen_start) * 1000
        self.log(f"Audio generated: {audio_duration:.0f}ms duration (took {gen_time:.0f}ms)")

        # Send audio
        self.current_turn.audio_send_start = (time.time() - self.test_start_time) * 1000
        self.log("Sending audio to room...")

        await self.send_audio(samples)

        self.current_turn.audio_send_end = (time.time() - self.test_start_time) * 1000
        send_time = self.current_turn.audio_send_end - self.current_turn.audio_send_start
        self.log(f"Audio sent in {send_time:.0f}ms")

        # Wait for agent response (with timeout)
        self.log("Waiting for agent response...")

        try:
            # Wait for transcript first
            await asyncio.wait_for(self.transcript_received.wait(), timeout=15.0)

            # Calculate STT latency
            if self.current_turn.transcript_received > 0:
                self.current_turn.stt_latency = self.current_turn.transcript_received - self.current_turn.audio_send_end
                self.log(f"STT latency: {self.current_turn.stt_latency:.0f}ms")

            # Wait for agent to start speaking
            await asyncio.wait_for(self.agent_speaking.wait(), timeout=20.0)

            # Calculate total latency (audio sent -> agent speaking)
            if self.current_turn.agent_started_speaking > 0:
                self.current_turn.total_latency = self.current_turn.agent_started_speaking - self.current_turn.audio_send_end
                self.log(f"Total latency: {self.current_turn.total_latency:.0f}ms")

            # Wait for agent to finish speaking
            await asyncio.wait_for(self.agent_stopped.wait(), timeout=30.0)

            if self.current_turn.agent_stopped_speaking > 0:
                self.current_turn.agent_speech_duration = (
                    self.current_turn.agent_stopped_speaking - self.current_turn.agent_started_speaking
                )
                self.log(f"Agent spoke for: {self.current_turn.agent_speech_duration:.0f}ms")

            self.results.successful_turns += 1

        except asyncio.TimeoutError:
            self.log("Timeout waiting for agent response", "ERROR")
            self.results.failed_turns += 1
            self.results.errors.append(f"Turn {turn_number}: Timeout")

        # Small pause between turns
        await asyncio.sleep(1.0)

        return self.current_turn

    async def run_test(self, duration_seconds: int = 60):
        """Run the full conversation test."""
        self.test_start_time = time.time()
        self.results = TestResults()

        print("\n" + "=" * 70)
        print("E2E CONVERSATION TEST - LiveKit Voice Agent")
        print(f"Started at: {datetime.now().isoformat()}")
        print(f"Duration: {duration_seconds} seconds")
        print(f"Room: {CONFIG['ROOM_NAME']}")
        print("=" * 70)

        # Create room and token
        self.log("Creating access token...")
        token = api.AccessToken(CONFIG["LIVEKIT_API_KEY"], CONFIG["LIVEKIT_API_SECRET"])
        token.with_identity(CONFIG["USER_NAME"])
        token.with_name(CONFIG["USER_NAME"])
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=CONFIG["ROOM_NAME"],
            can_publish=True,
            can_subscribe=True,
        ))

        # Connect to room
        self.log(f"Connecting to: {CONFIG['LIVEKIT_URL']}")
        self.room = rtc.Room()
        self.setup_event_handlers()

        try:
            await self.room.connect(CONFIG["LIVEKIT_URL"], token.to_jwt())
            self.log("✓ Connected to room", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to connect: {e}", "ERROR")
            return self.results

        # Wait for agent to join
        self.log("Waiting for agent to join...")
        await asyncio.sleep(3)

        # Check if agent is present
        agent_present = any("agent" in p.identity.lower() for p in self.room.remote_participants.values())
        if not agent_present:
            self.log("⚠ Agent not detected. Waiting longer...", "WARNING")
            await asyncio.sleep(5)
            agent_present = any("agent" in p.identity.lower() for p in self.room.remote_participants.values())

        if not agent_present:
            self.log("Agent did not join. Test cannot proceed.", "ERROR")
            self.results.errors.append("Agent never joined the room")
            await self.room.disconnect()
            return self.results

        # Publish audio track (simulates mic)
        self.log("Publishing audio track (simulated mic)...")
        self.audio_source = rtc.AudioSource(48000, 1)
        track = rtc.LocalAudioTrack.create_audio_track("microphone", self.audio_source)
        opts = rtc.TrackPublishOptions()
        opts.source = rtc.TrackSource.SOURCE_MICROPHONE
        await self.room.local_participant.publish_track(track, opts)
        self.log("✓ Audio track published", "SUCCESS")

        await asyncio.sleep(1)

        # Run conversation turns until duration expires
        test_end_time = time.time() + duration_seconds
        turn_number = 0
        phrase_index = 0

        while time.time() < test_end_time:
            turn_number += 1
            phrase = TEST_PHRASES[phrase_index % len(TEST_PHRASES)]
            phrase_index += 1

            turn_metrics = await self.run_conversation_turn(turn_number, phrase)
            self.results.turns.append(turn_metrics)
            self.results.total_turns += 1

            # Check if we should continue
            remaining = test_end_time - time.time()
            if remaining < 10:
                self.log(f"Test duration almost complete ({remaining:.0f}s remaining)")
                break

        # Disconnect
        self.log("\nDisconnecting from room...")
        await self.room.disconnect()
        self.log("✓ Disconnected", "SUCCESS")

        # Calculate aggregate metrics
        self._calculate_aggregates()

        return self.results

    def _calculate_aggregates(self):
        """Calculate aggregate metrics from all turns."""
        successful_turns = [t for t in self.results.turns if t.total_latency > 0]

        if successful_turns:
            stt_latencies = [t.stt_latency for t in successful_turns if t.stt_latency > 0]
            total_latencies = [t.total_latency for t in successful_turns]

            if stt_latencies:
                self.results.avg_stt_latency = sum(stt_latencies) / len(stt_latencies)

            if total_latencies:
                self.results.avg_total_latency = sum(total_latencies) / len(total_latencies)
                self.results.min_total_latency = min(total_latencies)
                self.results.max_total_latency = max(total_latencies)

    def print_results(self):
        """Print detailed test results."""
        r = self.results

        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)

        print(f"\n📊 CONVERSATION STATISTICS:")
        print(f"  Total turns:      {r.total_turns}")
        print(f"  Successful turns: {r.successful_turns}")
        print(f"  Failed turns:     {r.failed_turns}")

        if r.successful_turns > 0:
            print(f"\n⏱️ LATENCY METRICS (measured from test client):")
            print(f"  Average STT latency:   {r.avg_stt_latency:>8.0f}ms")
            print(f"  Average total latency: {r.avg_total_latency:>8.0f}ms")
            print(f"  Min total latency:     {r.min_total_latency:>8.0f}ms")
            print(f"  Max total latency:     {r.max_total_latency:>8.0f}ms")

            # Per-turn breakdown
            print(f"\n📋 PER-TURN BREAKDOWN:")
            print(f"  {'Turn':<6} {'User Text':<30} {'STT(ms)':<10} {'Total(ms)':<10} {'Agent(ms)':<10}")
            print(f"  {'-'*6} {'-'*30} {'-'*10} {'-'*10} {'-'*10}")

            for turn in r.turns:
                user_text = turn.user_text[:27] + "..." if len(turn.user_text) > 30 else turn.user_text
                stt = f"{turn.stt_latency:.0f}" if turn.stt_latency > 0 else "N/A"
                total = f"{turn.total_latency:.0f}" if turn.total_latency > 0 else "N/A"
                agent = f"{turn.agent_speech_duration:.0f}" if turn.agent_speech_duration > 0 else "N/A"
                print(f"  {turn.turn_number:<6} {user_text:<30} {stt:<10} {total:<10} {agent:<10}")

        if r.errors:
            print(f"\n❌ ERRORS:")
            for err in r.errors:
                print(f"  - {err}")

        # Bottleneck analysis
        print(f"\n🎯 BOTTLENECK ANALYSIS:")
        if r.avg_total_latency > 0:
            if r.avg_stt_latency > r.avg_total_latency * 0.5:
                print(f"  ⚠️  STT is the primary bottleneck ({r.avg_stt_latency:.0f}ms = {r.avg_stt_latency/r.avg_total_latency*100:.0f}% of total)")
                print(f"      → Consider GPU acceleration for WhisperLive")
                print(f"      → Or use smaller Whisper model (tiny/base)")
            else:
                llm_tts_latency = r.avg_total_latency - r.avg_stt_latency
                print(f"  STT latency:     {r.avg_stt_latency:.0f}ms ({r.avg_stt_latency/r.avg_total_latency*100:.0f}%)")
                print(f"  LLM+TTS latency: {llm_tts_latency:.0f}ms ({llm_tts_latency/r.avg_total_latency*100:.0f}%)")

        print(f"\n💡 NOTE: For detailed component breakdown (VAD, STT, LLM, TTS separately),")
        print(f"   check the agent-worker logs: docker-compose logs agent-worker")
        print(f"   Look for [TIMING] and [STATE] log entries.")

        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)


async def main():
    """Main entry point."""
    duration = CONFIG["TEST_DURATION_SECONDS"]

    # Allow override from command line
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            pass

    tester = ConversationTester()
    results = await tester.run_test(duration_seconds=duration)
    tester.print_results()

    return results


if __name__ == "__main__":
    asyncio.run(main())
