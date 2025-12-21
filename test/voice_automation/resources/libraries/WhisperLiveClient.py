"""
WhisperLiveKit WebSocket Client for Speech-to-Text
Connects to WhisperLiveKit server for real-time transcription
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field

try:
    import websockets
except ImportError:
    websockets = None

try:
    import numpy as np
except ImportError:
    np = None

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import WHISPER_WS_URL, AUDIO_SAMPLE_RATE, RESPONSE_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Transcription result from WhisperLiveKit"""
    text: str
    is_final: bool
    language: str = "en"
    confidence: float = 1.0
    start_time: float = 0.0
    end_time: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)


class WhisperLiveClient:
    """Client for WhisperLiveKit WebSocket STT service"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, ws_url: str = None):
        self.ws_url = ws_url or WHISPER_WS_URL
        self.websocket = None
        self.session_id = None
        self.is_connected = False
        self.transcriptions: List[TranscriptionResult] = []
        self.on_transcription: Optional[Callable] = None
        self._receive_task = None
        self._loop = None

    def _get_loop(self):
        """Get or create event loop"""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop

    def connect(self, language: str = "en", model: str = "small") -> bool:
        """Connect to WhisperLiveKit WebSocket server"""
        if websockets is None:
            logger.error("websockets module not installed")
            return False

        loop = self._get_loop()
        return loop.run_until_complete(self._connect_async(language, model))

    async def _connect_async(self, language: str = "en", model: str = "small") -> bool:
        """Async connect to WebSocket"""
        try:
            self.session_id = str(uuid.uuid4())

            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            )

            # Send configuration message
            config = {
                "uid": self.session_id,
                "language": language,
                "model": model,
                "use_vad": True,
                "task": "transcribe"
            }
            await self.websocket.send(json.dumps(config))

            self.is_connected = True
            logger.info(f"Connected to WhisperLiveKit: {self.ws_url}")

            # Start receive task
            self._receive_task = asyncio.create_task(self._receive_loop())

            return True

        except Exception as e:
            logger.error(f"Failed to connect to WhisperLiveKit: {e}")
            self.is_connected = False
            return False

    async def _receive_loop(self):
        """Background task to receive transcriptions"""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=RESPONSE_TIMEOUT
                    )
                    await self._handle_message(message)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
        finally:
            self.is_connected = False

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)

            # Parse transcription
            if "segments" in data:
                for segment in data["segments"]:
                    result = TranscriptionResult(
                        text=segment.get("text", "").strip(),
                        is_final=segment.get("completed", False),
                        language=data.get("language", "en"),
                        start_time=segment.get("start", 0),
                        end_time=segment.get("end", 0)
                    )

                    if result.text:
                        self.transcriptions.append(result)
                        logger.debug(f"Transcription: {result.text} (final={result.is_final})")

                        if self.on_transcription:
                            self.on_transcription(result)

            elif "text" in data:
                result = TranscriptionResult(
                    text=data.get("text", "").strip(),
                    is_final=data.get("is_final", True),
                    language=data.get("language", "en")
                )

                if result.text:
                    self.transcriptions.append(result)
                    logger.debug(f"Transcription: {result.text}")

                    if self.on_transcription:
                        self.on_transcription(result)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse message: {e}")

    def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data to WhisperLiveKit"""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to WhisperLiveKit")
            return False

        loop = self._get_loop()
        return loop.run_until_complete(self._send_audio_async(audio_data))

    async def _send_audio_async(self, audio_data: bytes) -> bool:
        """Async send audio data"""
        try:
            await self.websocket.send(audio_data)
            return True
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            return False

    def send_audio_file(self, file_path: str, chunk_size: int = 4096) -> bool:
        """Send audio file to WhisperLiveKit"""
        try:
            import soundfile as sf

            # Read audio file
            data, sample_rate = sf.read(file_path, dtype='int16')

            # Resample if needed
            if sample_rate != AUDIO_SAMPLE_RATE:
                from scipy import signal
                samples = int(len(data) * AUDIO_SAMPLE_RATE / sample_rate)
                data = signal.resample(data, samples)
                data = data.astype(np.int16)

            # Convert to bytes
            audio_bytes = data.tobytes()

            # Send in chunks
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                if not self.send_audio(chunk):
                    return False
                time.sleep(0.01)  # Small delay between chunks

            return True

        except Exception as e:
            logger.error(f"Failed to send audio file: {e}")
            return False

    def get_transcription(self, timeout: float = None) -> Optional[str]:
        """Wait for and return transcription"""
        timeout = timeout or RESPONSE_TIMEOUT
        loop = self._get_loop()
        return loop.run_until_complete(self._get_transcription_async(timeout))

    async def _get_transcription_async(self, timeout: float) -> Optional[str]:
        """Async wait for transcription"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check for final transcription
            for t in reversed(self.transcriptions):
                if t.is_final:
                    return t.text

            await asyncio.sleep(0.1)

        # Return last transcription if any
        if self.transcriptions:
            return self.transcriptions[-1].text

        return None

    def get_all_transcriptions(self) -> List[str]:
        """Get all transcriptions"""
        return [t.text for t in self.transcriptions if t.text]

    def clear_transcriptions(self):
        """Clear stored transcriptions"""
        self.transcriptions.clear()

    def disconnect(self):
        """Disconnect from WhisperLiveKit"""
        loop = self._get_loop()
        loop.run_until_complete(self._disconnect_async())

    async def _disconnect_async(self):
        """Async disconnect"""
        self.is_connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
            self.websocket = None

        logger.info("Disconnected from WhisperLiveKit")

    def is_connected_status(self) -> bool:
        """Check if connected"""
        return self.is_connected

    # Robot Framework Keywords
    def connect_to_whisper(self, language: str = "en") -> bool:
        """Robot Framework keyword to connect to WhisperLiveKit"""
        return self.connect(language=language)

    def disconnect_from_whisper(self):
        """Robot Framework keyword to disconnect"""
        self.disconnect()

    def send_audio_to_whisper(self, audio_path: str) -> bool:
        """Robot Framework keyword to send audio file"""
        return self.send_audio_file(audio_path)

    def wait_for_transcription(self, timeout: str = "10") -> str:
        """Robot Framework keyword to wait for transcription"""
        result = self.get_transcription(float(timeout))
        return result if result else ""

    def whisper_should_be_connected(self):
        """Robot Framework keyword to verify connection"""
        if not self.is_connected:
            raise AssertionError("Not connected to WhisperLiveKit")
        return True
