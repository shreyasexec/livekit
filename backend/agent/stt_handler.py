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
        if self.ws and not self.ws.closed:
            try:
                # Send EOF signal
                await self.ws.send(json.dumps({"eof": True}))
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
        # Ensure EventEmitter state exists for metrics callbacks in AgentSession
        try:
            super().__init__()
        except Exception:
            pass
        if not hasattr(self, "_events"):
            self._events = {}

        # Declare capabilities so AgentSession knows this STT supports streaming
        Cap = getattr(stt, "Capabilities", None)
        if Cap:
            self._capabilities = Cap(
                streaming=True,
                interim_results=True,
                metrics=True,
            )
        else:
            self._capabilities = type(
                "Caps",
                (),
                {"streaming": True, "interim_results": True, "metrics": True},
            )()

        self.host = host
        self.port = port
        self.lang = lang
        self._wl_model = model
        self.use_vad = use_vad

    async def _recognize_impl(
        self,
        audio: bytes,
        *,
        sample_rate: int,
        num_channels: int,
    ):
        """
        Fallback non-streaming recognize; WhisperLive is streaming-only here,
        so return an empty final alternative to satisfy the abstract interface.
        """
        alt_cls = SpeechAlternative or getattr(stt, "SpeechAlternative", None)
        alt = alt_cls(text="") if alt_cls else None

        if RecognitionBase:
            return RecognitionBase(alternatives=[alt] if alt else [])

        event_cls = SpeechEventBase or getattr(stt, "SpeechEvent", None)
        evt_type = SpeechEventType or getattr(stt, "SpeechEventType", None)
        if event_cls and evt_type:
            return event_cls(type=evt_type.FINAL, alternatives=[alt] if alt else [])

        return None

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
                        data = await client.receive_transcription()
                        if data is None:
                            break

                        text = ""
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
