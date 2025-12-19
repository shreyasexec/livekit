"""
WhisperLive STT Plugin for LiveKit Agents (Validated Implementation)

This module provides a custom Speech-to-Text plugin that integrates
WhisperLive real-time transcription service with LiveKit Agents.

Based on:
- WhisperLive API: https://github.com/collabora/WhisperLive
- LiveKit Agents Plugin Development patterns

Note: This implementation uses string identifiers compatible with LiveKit's
plugin system (similar to "assemblyai/universal-streaming:en").
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import websockets
from livekit.agents import stt

# Compatibility shims for older livekit.agents.stt versions
RecognitionBase = getattr(stt, "Recognition", None)
SpeechEventBase = getattr(stt, "SpeechEvent", None)
SpeechAlternative = getattr(stt, "SpeechAlternative", None)
SpeechEventType = getattr(stt, "SpeechEventType", None)

logger = logging.getLogger(__name__)


# Simple dataclass to carry STT results to the LiveKit pipeline
@dataclass
class WhisperLiveTranscript:
    text: str
    is_final: bool = True


def create_whisperlive_stt(
    host: str = "whisperlive",
    port: int = 9090,
    lang: str = "en",
    model: str = "small",
    use_vad: bool = True,
) -> "WhisperLiveSTT":
    """Factory returning a local WhisperLive STT instance."""
    return WhisperLiveSTT(
        host=host,
        port=port,
        lang=lang,
        model=model,
        use_vad=use_vad,
    )


class WhisperLiveClient:
    """
    WhisperLive WebSocket client for real-time transcription.

    This class handles the connection and communication with a WhisperLive server.
    It can be used as a standalone client or integrated into a custom STT provider.

    Based on: https://github.com/collabora/WhisperLive
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9090,
        lang: str = "en",
        model: str = "small",
        use_vad: bool = True,
        translate: bool = False,
    ):
        """
        Initialize WhisperLive client.

        Args:
            host: Server hostname
            port: Server port
            lang: Language code
            model: Whisper model size
            use_vad: Enable VAD on server side
            translate: Translate to English
        """
        self.host = host
        self.port = port
        self.lang = lang
        self.model = model
        self.use_vad = use_vad
        self.translate = translate
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id = str(uuid.uuid4())
        self.connected = False

        logger.info(
            f"WhisperLive client initialized: {host}:{port}, "
            f"model={model}, lang={lang}, vad={use_vad}"
        )

    async def connect(self):
        """Establish WebSocket connection to WhisperLive server."""
        uri = f"ws://{self.host}:{self.port}"

        try:
            self.ws = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=10,
            )

            # Send initial configuration
            config = {
                "uid": self.session_id,
                "language": self.lang,
                "task": "translate" if self.translate else "transcribe",
                "model": self.model,
                "use_vad": self.use_vad,
            }

            await self.ws.send(json.dumps(config))
            self.connected = True

            logger.info(f"Connected to WhisperLive: {uri}")
            logger.debug(f"Configuration sent: {config}")

        except Exception as e:
            logger.error(f"Failed to connect to WhisperLive: {e}")
            raise

    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to WhisperLive for transcription.

        Args:
            audio_data: Raw audio bytes (PCM int16, 16kHz, mono)
        """
        if not self.connected or not self.ws:
            raise RuntimeError("Not connected to WhisperLive server")

        try:
            await self.ws.send(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio to WhisperLive: {e}")
            raise

    async def receive_transcription(self) -> Optional[dict]:
        """
        Receive transcription from WhisperLive.

        Returns:
            Dictionary containing transcription data, or None if connection closed
        """
        if not self.connected or not self.ws:
            raise RuntimeError("Not connected to WhisperLive server")

        try:
            message = await self.ws.recv()
            data = json.loads(message)

            # WhisperLive returns segments with transcriptions
            if "segments" in data:
                return data

            # Check for end-of-transcription signal
            if data.get("eof"):
                logger.info("Received EOF from WhisperLive")
                return None

            return data

        except websockets.exceptions.ConnectionClosed:
            logger.info("WhisperLive connection closed")
            self.connected = False
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from WhisperLive: {e}")
            return None
        except Exception as e:
            logger.error(f"Error receiving from WhisperLive: {e}")
            raise

    async def close(self):
        """Close the connection to WhisperLive."""
        if self.ws:
            try:
                # Best-effort close (no EOF frame to avoid type errors on server)
                await self.ws.close()
                logger.info("WhisperLive connection closed")
            except Exception as e:
                logger.warning(f"Error closing WhisperLive connection: {e}")
        self.connected = False


class WhisperLiveSTT(stt.STT):
    """
    LiveKit STT adapter that streams audio to a local WhisperLive server.

    This implements the minimal STT interface expected by LiveKit Agents:
    - `stream(...)` yields SpeechEvent objects as transcripts arrive.
    - Audio chunks are pushed into the returned stream via `write`/`flush`.
    """

    def __init__(
        self,
        host: str = "whisperlive",
        port: int = 9090,
        lang: str = "en",
        model: str = "small",
        use_vad: bool = True,
    ):
        # Get STTCapabilities class
        Cap = getattr(stt, "STTCapabilities", None)
        if Cap is None:
            Cap = getattr(stt, "Capabilities", None)

        # Create capabilities - streaming=False so framework wraps with StreamAdapter+VAD
        if Cap:
            capabilities = Cap(
                streaming=False,  # Let framework wrap with VAD via StreamAdapter
                interim_results=False,
            )
        else:
            capabilities = type(
                "Caps",
                (),
                {"streaming": False, "interim_results": False},
            )()

        # Call parent __init__ with capabilities - this sets _label and other required attributes
        super().__init__(capabilities=capabilities)

        # Store our config
        self.host = host
        self.port = port
        self.lang = lang
        self._wl_model = model
        self.use_vad = use_vad

        logger.info(f"WhisperLiveSTT initialized: {host}:{port}, model={model}, lang={lang}")

    async def _recognize_impl(
        self,
        buffer,  # AudioBuffer from livekit.agents.utils
        *,
        language=None,
        conn_options=None,
    ):
        """
        Non-streaming recognize - called by StreamAdapter after VAD detects end of speech.
        Sends audio buffer to WhisperLive and returns transcription.
        """
        try:
            # Extract audio bytes from buffer
            if hasattr(buffer, 'data'):
                audio_bytes = bytes(buffer.data)
            elif hasattr(buffer, 'to_wav'):
                # AudioBuffer has to_wav method
                audio_bytes = buffer.to_wav()
            elif isinstance(buffer, (bytes, bytearray)):
                audio_bytes = bytes(buffer)
            else:
                # Try to get raw PCM data
                audio_bytes = bytes(buffer)

            logger.info(f"WhisperLive recognize: {len(audio_bytes)} bytes of audio")

            # Skip if audio is too short (less than 0.1 seconds at 16kHz, 16-bit)
            if len(audio_bytes) < 3200:
                logger.warning(f"Audio too short ({len(audio_bytes)} bytes), skipping")
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[],
                )

            # Connect to WhisperLive and send audio
            client = WhisperLiveClient(
                host=self.host,
                port=self.port,
                lang=self.lang,
                model=self._wl_model,
                use_vad=False,  # VAD already done by LiveKit
            )

            await client.connect()

            # Send audio in chunks (WhisperLive expects streaming chunks)
            # Chunk size: 8000 bytes = 0.25 seconds at 16kHz, 16-bit mono
            chunk_size = 8000
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                await client.send_audio(chunk)
                # Small delay between chunks to simulate streaming
                await asyncio.sleep(0.01)

            logger.debug(f"Sent {len(audio_bytes)} bytes in {(len(audio_bytes) + chunk_size - 1) // chunk_size} chunks")

            # Wait for transcription with timeout
            transcript_text = ""
            try:
                # NO artificial delay - stream audio and get response immediately
                # GPU-based WhisperLiveKit is fast enough

                # Try to get response with timeout
                for attempt in range(10):  # Max 5 seconds total
                    try:
                        data = await asyncio.wait_for(
                            client.receive_transcription(),
                            timeout=0.5
                        )

                        if data is None:
                            logger.debug("Received None from WhisperLive")
                            break

                        logger.debug(f"WhisperLive response: {data}")

                        # Handle different response formats from WhisperLive
                        if "segments" in data:
                            for seg in data.get("segments", []):
                                text = seg.get("text", "").strip()
                                if text:
                                    transcript_text = text  # Use latest segment
                                    logger.debug(f"Got segment text: '{text}'")

                        # Check for message field (some WhisperLive versions use this)
                        if "message" in data and data["message"] not in ["WAIT", "SERVER_READY"]:
                            msg = data.get("message", "").strip()
                            if msg:
                                transcript_text = msg

                        # If we have text, wait a bit more for final result
                        if transcript_text.strip() and attempt >= 3:
                            break

                    except asyncio.TimeoutError:
                        if transcript_text.strip() and attempt >= 5:
                            # We have some text, use it
                            break
                        continue

            finally:
                await client.close()

            transcript_text = transcript_text.strip()
            logger.info(f"WhisperLive transcription: '{transcript_text}'")

            # Return SpeechEvent with transcription
            SpeechData = getattr(stt, "SpeechData", None)
            if SpeechData:
                alt = SpeechData(text=transcript_text, language=self.lang)
            else:
                alt = stt.SpeechAlternative(text=transcript_text)

            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[alt] if transcript_text else [],
            )

        except Exception as e:
            logger.error(f"WhisperLive recognize error: {e}")
            # Return empty result on error
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[],
            )

    def stream(
        self,
        *args,
        **kwargs,
    ) -> AsyncIterator[stt.SpeechEvent]:
        """
        Async context manager that yields a writable SpeechStream.
        Accepts positional or keyword sample_rate/num_channels (defaults provided).
        """
        from contextlib import asynccontextmanager

        sample_rate = kwargs.pop("sample_rate", args[0] if len(args) > 0 else 16000)
        num_channels = kwargs.pop("num_channels", args[1] if len(args) > 1 else 1)
        _ = sample_rate, num_channels  # currently unused by WhisperLive

        @asynccontextmanager
        async def _cm():
            client = WhisperLiveClient(
                host=self.host,
                port=self.port,
                lang=self.lang,
                model=self._wl_model,
                use_vad=self.use_vad,
            )
            await client.connect()

            audio_q: asyncio.Queue[Optional[bytes]] = asyncio.Queue()

            async def sender():
                while True:
                    chunk = await audio_q.get()
                    if chunk is None:
                        break
                    try:
                        await client.send_audio(chunk)
                    except Exception as e:
                        logger.error(f"WhisperLive send error: {e}")
                        break

            send_task = asyncio.create_task(sender())

            class _Stream:
                async def write(self, audio: bytes):
                    await audio_q.put(audio)

                def push_frame(self, frame):
                    """
                    Adapter used by LiveKit Agents to feed raw audio frames.
                    Accepts bytes/bytearray/memoryview or objects exposing `.data`/`.pcm`.

                    NOTE: This MUST be synchronous (not async) as LiveKit calls it without await.
                    """
                    try:
                        if isinstance(frame, (bytes, bytearray, memoryview)):
                            audio = bytes(frame)
                        elif hasattr(frame, "data"):
                            audio = bytes(frame.data)
                        elif hasattr(frame, "pcm"):
                            audio = bytes(frame.pcm)
                        else:
                            logger.debug("Unknown frame type for STT; skipping")
                            return
                        # Use put_nowait since we can't await in a sync function
                        audio_q.put_nowait(audio)
                        logger.debug(f"Pushed audio frame to queue: {len(audio)} bytes")
                    except asyncio.QueueFull:
                        logger.warning("Audio queue is full, dropping frame")
                    except Exception as e:
                        logger.error(f"Failed to push frame to WhisperLive: {e}")

                async def aclose(self):
                    await audio_q.put(None)
                    await client.close()
                    send_task.cancel()

                def __aiter__(self):
                    return transcript_generator()

            stream = _Stream()

            async def transcript_generator():
                try:
                    while True:
                        try:
                            data = await client.receive_transcription()
                        except asyncio.CancelledError:
                            break
                        if data is None:
                            break

                        if "segments" in data:
                            text = " ".join(
                                seg.get("text", "") for seg in data.get("segments", [])
                            ).strip()
                        else:
                            text = data.get("text", "")

                        if not text:
                            continue

                        yield stt.SpeechEvent(
                            type=stt.SpeechEventType.FINAL,
                            alternatives=[stt.SpeechAlternative(text=text)],
                        )
                finally:
                    await stream.aclose()

            try:
                yield stream
            finally:
                await stream.aclose()

        return _cm()


# Example usage:
async def test_whisperlive():
    """Test WhisperLive connection and transcription."""
    client = WhisperLiveClient(
        host="localhost",
        port=9090,
        lang="en",
        model="small",
    )

    try:
        await client.connect()
        logger.info("WhisperLive connection test successful")

        # In a real implementation, you would send audio frames here
        # For example:
        # audio_frame = np.zeros(1600, dtype=np.int16)  # 100ms of 16kHz audio
        # await client.send_audio(audio_frame.tobytes())

        await client.close()

    except Exception as e:
        logger.error(f"WhisperLive test failed: {e}")


if __name__ == "__main__":
    # Run test
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_whisperlive())
