"""
LiveKit Agent for programmatic room interactions
Uses LiveKit Python SDK for direct room communication
"""
import asyncio
import logging
import time
import uuid
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

try:
    from livekit import rtc
    from livekit import api as lk_api
except ImportError:
    rtc = None
    lk_api = None

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import (
    LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
    RESPONSE_TIMEOUT, AUDIO_SAMPLE_RATE
)

logger = logging.getLogger(__name__)


@dataclass
class Participant:
    """Participant info"""
    sid: str
    identity: str
    is_speaking: bool = False
    is_local: bool = False


@dataclass
class TranscriptMessage:
    """Transcript message from agent"""
    text: str
    speaker: str
    participant_identity: str
    timestamp: str


class LiveKitAgent:
    """Agent for LiveKit room interactions"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, url: str = None, api_key: str = None, api_secret: str = None):
        self.url = url or LIVEKIT_URL
        self.api_key = api_key or LIVEKIT_API_KEY
        self.api_secret = api_secret or LIVEKIT_API_SECRET
        self.room: Optional['rtc.Room'] = None
        self.participants: Dict[str, Participant] = {}
        self.transcripts: List[TranscriptMessage] = []
        self.is_connected = False
        self._loop = None
        self._token = None
        self.on_transcript: Optional[Callable] = None
        self.language = "en"

    def _get_loop(self):
        """Get or create event loop"""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop

    def create_token(self, room_name: str, identity: str = None) -> str:
        """Create access token for room"""
        if not lk_api:
            logger.error("livekit-api not installed")
            return ""

        try:
            identity = identity or f"test-agent-{uuid.uuid4().hex[:8]}"

            token = lk_api.AccessToken(self.api_key, self.api_secret)
            token.with_identity(identity)
            token.with_name(identity)
            token.with_grants(lk_api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            ))

            self._token = token.to_jwt()
            return self._token

        except Exception as e:
            logger.error(f"Failed to create token: {e}")
            return ""

    def connect_to_room(self, room_name: str, identity: str = None) -> bool:
        """Connect to LiveKit room"""
        if not rtc:
            logger.error("livekit SDK not installed")
            return False

        loop = self._get_loop()
        return loop.run_until_complete(
            self._connect_async(room_name, identity)
        )

    async def _connect_async(self, room_name: str, identity: str = None) -> bool:
        """Async connect to room"""
        try:
            # Create token
            token = self.create_token(room_name, identity)
            if not token:
                return False

            # Create room
            self.room = rtc.Room()

            # Set up event handlers
            @self.room.on("participant_connected")
            def on_participant_connected(participant: rtc.RemoteParticipant):
                self.participants[participant.sid] = Participant(
                    sid=participant.sid,
                    identity=participant.identity
                )
                logger.info(f"Participant connected: {participant.identity}")

            @self.room.on("participant_disconnected")
            def on_participant_disconnected(participant: rtc.RemoteParticipant):
                if participant.sid in self.participants:
                    del self.participants[participant.sid]
                logger.info(f"Participant disconnected: {participant.identity}")

            @self.room.on("data_received")
            def on_data(data: bytes, participant: rtc.RemoteParticipant,
                       kind: rtc.DataPacketKind, topic: str = None):
                self._handle_data(data, participant, topic)

            @self.room.on("track_subscribed")
            def on_track_subscribed(track: rtc.Track,
                                   publication: rtc.RemoteTrackPublication,
                                   participant: rtc.RemoteParticipant):
                logger.info(f"Track subscribed: {track.kind} from {participant.identity}")

            # Connect
            await self.room.connect(self.url, token)

            self.is_connected = True
            logger.info(f"Connected to room: {room_name}")

            # Add existing participants
            for p in self.room.remote_participants.values():
                self.participants[p.sid] = Participant(
                    sid=p.sid,
                    identity=p.identity
                )

            return True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.is_connected = False
            return False

    def _handle_data(self, data: bytes, participant, topic: str):
        """Handle incoming data messages"""
        try:
            import json
            decoded = json.loads(data.decode('utf-8'))

            if topic == 'transcripts' and 'text' in decoded:
                msg = TranscriptMessage(
                    text=decoded.get('text', ''),
                    speaker=decoded.get('speaker', 'unknown'),
                    participant_identity=decoded.get('participantIdentity', ''),
                    timestamp=decoded.get('timestamp', '')
                )
                self.transcripts.append(msg)
                logger.debug(f"Transcript: [{msg.speaker}] {msg.text}")

                if self.on_transcript:
                    self.on_transcript(msg)

        except Exception as e:
            logger.warning(f"Failed to handle data: {e}")

    def disconnect(self):
        """Disconnect from room"""
        loop = self._get_loop()
        loop.run_until_complete(self._disconnect_async())

    async def _disconnect_async(self):
        """Async disconnect"""
        if self.room:
            await self.room.disconnect()
            self.room = None
        self.is_connected = False
        self.participants.clear()
        logger.info("Disconnected from room")

    def speak(self, text: str, language: str = None) -> bool:
        """Speak text using TTS and publish to room"""
        if not self.is_connected or not self.room:
            logger.error("Not connected to room")
            return False

        language = language or self.language

        try:
            from .PiperTTSClient import PiperTTSClient

            # Synthesize
            tts = PiperTTSClient()
            result = tts.synthesize_multilingual(text, language)
            if not result:
                return False

            # Read audio and publish
            loop = self._get_loop()
            return loop.run_until_complete(
                self._publish_audio_async(result.audio_path)
            )

        except Exception as e:
            logger.error(f"Failed to speak: {e}")
            return False

    async def _publish_audio_async(self, audio_path: str) -> bool:
        """Publish audio file to room"""
        try:
            import soundfile as sf
            import numpy as np

            # Read audio
            data, sample_rate = sf.read(audio_path, dtype='float32')

            # Create audio source
            source = rtc.AudioSource(sample_rate, 1)

            # Create and publish track
            track = rtc.LocalAudioTrack.create_audio_track("audio", source)
            options = rtc.TrackPublishOptions()
            await self.room.local_participant.publish_track(track, options)

            # Send audio frames
            chunk_size = int(sample_rate * 0.02)  # 20ms chunks
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)))

                frame = rtc.AudioFrame.create(sample_rate, 1, chunk_size)
                frame_data = (chunk * 32767).astype(np.int16)
                frame.data[:] = frame_data.tobytes()
                await source.capture_frame(frame)
                await asyncio.sleep(0.02)

            # Unpublish
            await self.room.local_participant.unpublish_track(track.sid)

            return True

        except Exception as e:
            logger.error(f"Failed to publish audio: {e}")
            return False

    def listen(self, timeout: float = None) -> Optional[str]:
        """Listen for transcript from agent"""
        timeout = timeout or RESPONSE_TIMEOUT
        loop = self._get_loop()
        return loop.run_until_complete(self._listen_async(timeout))

    async def _listen_async(self, timeout: float) -> Optional[str]:
        """Async listen for transcript"""
        start_time = time.time()
        initial_count = len(self.transcripts)

        while time.time() - start_time < timeout:
            # Check for new agent transcript
            if len(self.transcripts) > initial_count:
                for t in self.transcripts[initial_count:]:
                    if t.speaker == 'assistant' or t.speaker == 'agent':
                        return t.text

            await asyncio.sleep(0.1)

        return None

    def speak_and_listen(self, text: str, timeout: float = None,
                         language: str = None) -> Optional[str]:
        """Speak and wait for response"""
        if not self.speak(text, language):
            return None
        return self.listen(timeout)

    def get_participants(self) -> List[Dict[str, Any]]:
        """Get list of participants"""
        return [
            {
                'sid': p.sid,
                'identity': p.identity,
                'is_speaking': p.is_speaking
            }
            for p in self.participants.values()
        ]

    def get_transcripts(self) -> List[Dict[str, Any]]:
        """Get all transcripts"""
        return [
            {
                'text': t.text,
                'speaker': t.speaker,
                'participant': t.participant_identity,
                'timestamp': t.timestamp
            }
            for t in self.transcripts
        ]

    def clear_transcripts(self):
        """Clear transcript history"""
        self.transcripts.clear()

    def set_language(self, language_code: str):
        """Set language for TTS"""
        self.language = language_code

    # Robot Framework Keywords
    def connect_to_livekit_room(self, room_name: str,
                                identity: str = None) -> bool:
        """Robot Framework keyword to connect to room"""
        result = self.connect_to_room(room_name, identity)
        if not result:
            raise AssertionError(f"Failed to connect to room: {room_name}")
        return result

    def disconnect_from_livekit(self):
        """Robot Framework keyword to disconnect"""
        self.disconnect()

    def livekit_should_be_connected(self):
        """Robot Framework keyword to verify connection"""
        if not self.is_connected:
            raise AssertionError("Not connected to LiveKit room")
        return True

    def speak_to_room(self, text: str, language: str = "en") -> bool:
        """Robot Framework keyword to speak"""
        result = self.speak(text, language)
        if not result:
            raise AssertionError(f"Failed to speak: {text}")
        return result

    def listen_for_response(self, timeout: str = "15") -> str:
        """Robot Framework keyword to listen"""
        result = self.listen(float(timeout))
        if not result:
            raise AssertionError("No response received")
        return result

    def speak_and_wait_for_response(self, text: str, timeout: str = "15",
                                    language: str = "en") -> str:
        """Robot Framework keyword to speak and listen"""
        result = self.speak_and_listen(text, float(timeout), language)
        if not result:
            raise AssertionError(f"No response for: {text}")
        return result

    def get_participant_count(self) -> int:
        """Robot Framework keyword to get participant count"""
        return len(self.participants) + 1  # Include self

    def room_should_have_participants(self, min_count: str = "1"):
        """Robot Framework keyword to verify participants"""
        count = len(self.participants) + 1
        if count < int(min_count):
            raise AssertionError(
                f"Expected at least {min_count} participants, got {count}"
            )
        return True
