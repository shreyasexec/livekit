"""
LiveKit Testing Library for Robot Framework
Connects to LiveKit rooms, sends/receives audio, measures performance
"""

import os

# Disable SSL verification for self-signed certificates - MUST be before imports
os.environ['PYTHONHTTPSVERIFY'] = '0'
# Set to /dev/null to effectively disable cert verification
if hasattr(os, 'devnull'):
    os.environ['CURL_CA_BUNDLE'] = os.devnull
    os.environ['REQUESTS_CA_BUNDLE'] = os.devnull

import asyncio
import time
import wave
import json
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from livekit import api, rtc

@dataclass
class PerformanceMetrics:
    """Track performance metrics for voice pipeline"""
    speech_sent_time: Optional[float] = None
    agent_response_start_time: Optional[float] = None
    agent_response_end_time: Optional[float] = None
    transcript_received_time: Optional[float] = None

    user_transcript: str = ""
    agent_transcript: str = ""

    def get_response_latency_ms(self) -> Optional[int]:
        """Get latency from speech sent to agent response start (ms)"""
        if self.speech_sent_time and self.agent_response_start_time:
            return int((self.agent_response_start_time - self.speech_sent_time) * 1000)
        return None

    def get_total_latency_ms(self) -> Optional[int]:
        """Get total latency from speech sent to response complete (ms)"""
        if self.speech_sent_time and self.agent_response_end_time:
            return int((self.agent_response_end_time - self.speech_sent_time) * 1000)
        return None

@dataclass
class VADEvent:
    """Track VAD events for testing turn detector"""
    event_type: str  # "user_start", "user_end", "agent_start", "agent_end"
    timestamp: float

class LiveKitTester:
    """LiveKit connection and testing library for Robot Framework"""

    ROBOT_LIBRARY_SCOPE = 'TEST'

    def __init__(self):
        self.room: Optional[rtc.Room] = None
        self.audio_source: Optional[rtc.AudioSource] = None
        self.metrics: PerformanceMetrics = PerformanceMetrics()
        self.vad_events: List[VADEvent] = []
        self.agent_speaking: bool = False
        self.received_audio_frames: List[rtc.AudioFrame] = []
        self.transcripts: List[Dict] = []
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._expecting_response: bool = False  # Flag to track if we're waiting for agent response

    def _get_loop(self):
        """Get or create event loop"""
        if self._event_loop is None or self._event_loop.is_closed():
            try:
                self._event_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    def connect_to_room(self, url: str, token: str, timeout: int = 10):
        """Connect to LiveKit room

        Args:
            url: LiveKit server URL (ws://...)
            token: Access token for room
            timeout: Connection timeout in seconds
        """
        loop = self._get_loop()
        loop.run_until_complete(self._connect_to_room_async(url, token, timeout))

    async def _connect_to_room_async(self, url: str, token: str, timeout: int):
        """Async implementation of room connection"""
        self.room = rtc.Room()

        # Register event handlers
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            print(f"Participant connected: {participant.identity}")

        @self.room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.TrackPublication,
            participant: rtc.RemoteParticipant
        ):
            print(f"Track subscribed: {track.kind} from {participant.identity}")

            if track.kind == rtc.TrackKind.KIND_AUDIO:
                audio_stream = rtc.AudioStream(track)
                asyncio.create_task(self._receive_audio(audio_stream))

        @self.room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            """Handle transcript data from agent"""
            participant = data.participant if hasattr(data, 'participant') else None
            print(f"[DEBUG] Data received from {participant.identity if participant else 'unknown'}: {len(data.data)} bytes")
            try:
                payload = json.loads(data.data.decode('utf-8'))
                print(f"[DEBUG] Parsed payload: {payload}")
                if payload.get('type') == 'transcript':
                    self.transcripts.append(payload)

                    speaker = payload.get('speaker', '')
                    text = payload.get('text', '')

                    if speaker == 'assistant':
                        self.metrics.agent_transcript = text
                        if not self.metrics.agent_response_start_time:
                            self.metrics.agent_response_start_time = time.time()
                        print(f"[AGENT TRANSCRIPT] {text}")
                    elif speaker == 'user':
                        self.metrics.user_transcript = text
                        self.metrics.transcript_received_time = time.time()
                        print(f"[USER TRANSCRIPT] {text}")

                    print(f"Transcript [{speaker}]: {text}")
                else:
                    print(f"[DEBUG] Non-transcript data type: {payload.get('type')}")
            except Exception as e:
                print(f"Error parsing data: {e}")
                print(f"[DEBUG] Raw data: {data[:200]}")

        # Connect to room
        try:
            await asyncio.wait_for(
                self.room.connect(url, token),
                timeout=timeout
            )
            print(f"Connected to room: {self.room.name}")
        except asyncio.TimeoutError:
            raise Exception(f"Failed to connect to room within {timeout} seconds")

    async def _receive_audio(self, audio_stream: rtc.AudioStream):
        """Receive and process audio frames from agent"""
        async for event in audio_stream:
            frame = event.frame
            self.received_audio_frames.append(frame)

            # Detect agent speaking
            if not self.agent_speaking:
                self.agent_speaking = True
                self.vad_events.append(VADEvent("agent_start", time.time()))
                # Only set response start time if we're expecting a response (after sending user audio)
                if self._expecting_response and not self.metrics.agent_response_start_time:
                    self.metrics.agent_response_start_time = time.time()
                    print(f"[DEBUG] Agent response start time set from audio frame (after user speech)")
                elif not self._expecting_response:
                    print(f"[DEBUG] Agent speaking but not expecting response yet (greeting)")
                print("Agent started speaking")

    def send_audio_file(self, audio_file_path: str, wait_after: float = 0.5):
        """Send audio file to room

        Args:
            audio_file_path: Path to WAV file (16kHz mono)
            wait_after: Seconds to wait after sending
        """
        loop = self._get_loop()
        loop.run_until_complete(self._send_audio_file_async(audio_file_path, wait_after))

    async def _send_audio_file_async(self, audio_file_path: str, wait_after: float):
        """Async implementation of audio sending"""
        if not self.room:
            raise Exception("Not connected to room")

        # Create audio source if not exists
        if not self.audio_source:
            self.audio_source = rtc.AudioSource(16000, 1)  # 16kHz mono
            track = rtc.LocalAudioTrack.create_audio_track("test-audio", self.audio_source)
            # Publish with SOURCE_MICROPHONE so agent accepts it
            options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
            await self.room.local_participant.publish_track(track, options)
            print("Published audio track (source=MICROPHONE)")
            await asyncio.sleep(0.5)  # Wait for track to be ready

        # Read WAV file
        with wave.open(audio_file_path, 'rb') as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            audio_data = wf.readframes(wf.getnframes())
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Convert to 16kHz mono if needed
        if sample_rate != 16000 or num_channels != 1:
            raise Exception(f"Audio must be 16kHz mono, got {sample_rate}Hz {num_channels}ch")

        # Mark VAD start and set expecting response flag
        self.vad_events.append(VADEvent("user_start", time.time()))
        self._expecting_response = True  # NOW we expect agent to respond
        print(f"[DEBUG] Starting to send audio, total samples: {len(audio_array)}")
        print(f"[DEBUG] Now expecting agent response")

        # Send audio in chunks (10ms = 160 samples at 16kHz)
        chunk_size = 160
        chunks_sent = 0
        for i in range(0, len(audio_array), chunk_size):
            chunk = audio_array[i:i+chunk_size]
            if len(chunk) < chunk_size:
                # Pad last chunk
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))

            frame = rtc.AudioFrame(
                data=chunk.tobytes(),
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=chunk_size
            )
            await self.audio_source.capture_frame(frame)
            await asyncio.sleep(0.01)  # 10ms per chunk
            chunks_sent += 1

        # Mark speech end time - THIS is when we start measuring latency
        self.vad_events.append(VADEvent("user_end", time.time()))
        self.metrics.speech_sent_time = time.time()  # Set AFTER audio is sent
        duration_ms = len(audio_array) / 16  # 16 samples per ms at 16kHz
        print(f"[DEBUG] Sent {chunks_sent} audio chunks ({duration_ms:.0f}ms of audio)")
        print(f"Sent audio file: {audio_file_path}")

        # Keep sending silence frames to keep stream alive
        if wait_after > 0:
            print(f"[DEBUG] Sending silence frames for {wait_after}s to keep stream alive")
            silence_chunk = np.zeros(chunk_size, dtype=np.int16)
            silence_chunks = int((wait_after * 1000) / 10)  # Number of 10ms chunks
            for _ in range(silence_chunks):
                frame = rtc.AudioFrame(
                    data=silence_chunk.tobytes(),
                    sample_rate=16000,
                    num_channels=1,
                    samples_per_channel=chunk_size
                )
                await self.audio_source.capture_frame(frame)
                await asyncio.sleep(0.01)
            print(f"[DEBUG] Finished sending silence frames")

    def wait_for_agent_response(self, timeout: float = 5.0):
        """Wait for agent to respond

        Args:
            timeout: Maximum wait time in seconds
        """
        loop = self._get_loop()
        loop.run_until_complete(self._wait_for_agent_response_async(timeout))

    async def _wait_for_agent_response_async(self, timeout: float):
        """Async wait for agent response"""
        start_time = time.time()
        print(f"[DEBUG] Waiting for agent response (timeout={timeout}s)")

        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            if self.metrics.agent_response_start_time:
                print(f"[DEBUG] Agent response detected at {elapsed:.1f}s")
                # Wait a bit more for complete response
                await asyncio.sleep(1.0)
                self.metrics.agent_response_end_time = time.time()

                # Mark agent speech end
                if self.agent_speaking:
                    self.agent_speaking = False
                    self.vad_events.append(VADEvent("agent_end", time.time()))

                print(f"[DEBUG] Agent transcript: '{self.metrics.agent_transcript}'")
                return
            await asyncio.sleep(0.1)

        print(f"[DEBUG] Timeout reached. Agent response start time: {self.metrics.agent_response_start_time}")
        print(f"[DEBUG] Agent transcript: '{self.metrics.agent_transcript}'")
        print(f"[DEBUG] Total transcripts received: {len(self.transcripts)}")
        raise Exception(f"Agent did not respond within {timeout} seconds")

    def get_response_latency(self) -> int:
        """Get response latency in milliseconds"""
        latency = self.metrics.get_response_latency_ms()
        if latency is None:
            return -1
        return latency

    def get_total_latency(self) -> int:
        """Get total latency in milliseconds"""
        latency = self.metrics.get_total_latency_ms()
        if latency is None:
            return -1
        return latency

    def verify_agent_responded(self):
        """Verify that agent provided a response"""
        if not self.metrics.agent_response_start_time:
            raise AssertionError("Agent did not respond")
        if not self.metrics.agent_transcript:
            raise AssertionError("Agent transcript is empty")
        print(f"Agent response: {self.metrics.agent_transcript}")

    def verify_latency_under(self, max_latency_ms: int):
        """Verify response latency is under threshold

        Args:
            max_latency_ms: Maximum acceptable latency in milliseconds
        """
        latency = self.get_response_latency()
        if latency < 0:
            raise AssertionError("No latency data available")

        if latency > max_latency_ms:
            raise AssertionError(
                f"Latency {latency}ms exceeds maximum {max_latency_ms}ms"
            )
        print(f"Latency {latency}ms is under {max_latency_ms}ms threshold")

    def verify_vad_interrupt(self, max_interrupt_ms: int = 200):
        """Verify agent stopped when user started speaking (interrupt test)

        Args:
            max_interrupt_ms: Maximum allowed interrupt time in milliseconds
        """
        # Find last agent_start and next user_start
        agent_starts = [e for e in self.vad_events if e.event_type == "agent_start"]
        user_starts = [e for e in self.vad_events if e.event_type == "user_start"]

        if not agent_starts or not user_starts:
            raise AssertionError("No VAD events recorded")

        # Check if there's an agent_end after the last user_start
        last_user_start = user_starts[-1]
        agent_ends_after = [
            e for e in self.vad_events
            if e.event_type == "agent_end" and e.timestamp > last_user_start.timestamp
        ]

        if not agent_ends_after:
            raise AssertionError("Agent did not stop when user started speaking")

        # Calculate interrupt latency
        agent_end = agent_ends_after[0]
        interrupt_latency_ms = int((agent_end.timestamp - last_user_start.timestamp) * 1000)

        if interrupt_latency_ms > max_interrupt_ms:
            raise AssertionError(
                f"Interrupt latency {interrupt_latency_ms}ms exceeds {max_interrupt_ms}ms"
            )
        print(f"Agent stopped in {interrupt_latency_ms}ms (interrupt working)")

    def disconnect(self):
        """Disconnect from room"""
        if self.room:
            loop = self._get_loop()
            loop.run_until_complete(self.room.disconnect())
            self.room = None
            print("Disconnected from room")

    def reset_metrics(self):
        """Reset performance metrics for next test"""
        print(f"[DEBUG] Resetting metrics. Current state:")
        print(f"  - agent_speaking: {self.agent_speaking}")
        print(f"  - agent_response_start_time: {self.metrics.agent_response_start_time}")
        print(f"  - agent_transcript: '{self.metrics.agent_transcript}'")
        print(f"  - received_audio_frames: {len(self.received_audio_frames)}")
        print(f"  - transcripts: {len(self.transcripts)}")

        self.metrics = PerformanceMetrics()
        self.vad_events = []
        self.agent_speaking = False
        self.received_audio_frames = []
        self.transcripts = []
        self._expecting_response = False
        print(f"[DEBUG] Metrics reset complete, not expecting response")
