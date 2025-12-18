"""
LiveKit AI Voice Agent Worker - WhisperLiveKit + Piper TTS Integration

Based on official LiveKit Agents documentation:
- https://docs.livekit.io/agents/build/sessions
- https://docs.livekit.io/agents/build/nodes

Uses:
- WhisperLiveKit for STT (--pcm-input mode): https://github.com/QuentinFuxa/WhisperLiveKit
- livekit-plugins-piper-tts for TTS: https://pypi.org/project/livekit-plugins-piper-tts/
- Ollama for LLM (OpenAI-compatible API)
"""

import asyncio
import json
import logging
import os
import struct
import time
from dataclasses import dataclass

import aiohttp
import numpy as np
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    DEFAULT_API_CONNECT_OPTIONS,
    JobContext,
    WorkerOptions,
    cli,
    stt,
    tts,
    utils,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.voice import room_io
from livekit.plugins import openai, silero
# Note: Using custom PiperTTS implementation below instead of piper_tts plugin
# The plugin has issues: sync requests blocking event loop, no chunked output

# Load environment variables
load_dotenv()

# Configure logging - DEBUG level for full visibility
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce noise from external libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


@dataclass
class WhisperLiveKitOptions:
    """Options for WhisperLiveKit STT."""
    host: str
    port: int
    language: str
    sample_rate: int
    use_ssl: bool = False  # Use wss:// instead of ws://


class WhisperLiveKitSTT(stt.STT):
    """
    WhisperLiveKit Streaming STT Plugin for LiveKit Agents.

    This implements streaming STT that bridges WebRTC audio to WhisperLiveKit WebSocket.
    Uses --pcm-input mode for raw PCM audio (s16le format).

    Architecture:
    - streaming=True: LiveKit sends audio frames in real-time
    - Audio frames are converted to raw PCM s16le and sent to WhisperLiveKit
    - WhisperLiveKit returns transcription results via WebSocket

    WhisperLiveKit Protocol (PCM mode):
    1. Connect to WebSocket at ws://host:port
    2. Send raw PCM audio as s16le (16-bit signed little-endian)
    3. Receive JSON transcription messages with text

    See: https://github.com/QuentinFuxa/WhisperLiveKit
    """

    def __init__(
        self,
        host: str = "whisperlivekit",
        port: int = 8765,
        language: str = "en",
        sample_rate: int = 16000,
        use_ssl: bool = False,
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
            )
        )
        self._opts = WhisperLiveKitOptions(
            host=host,
            port=port,
            language=language,
            sample_rate=sample_rate,
            use_ssl=use_ssl,
        )
        self._session = None
        protocol = "wss" if use_ssl else "ws"
        logger.info(f"WhisperLiveKitSTT initialized: {protocol}://{host}:{port} (streaming=True, pcm-input mode)")

    def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an aiohttp session with optimized connection settings."""
        if self._session is None or self._session.closed:
            # Optimized connector: connection pooling + keep-alive
            connector = aiohttp.TCPConnector(
                limit=10,               # Max connections
                limit_per_host=5,       # Max per host
                ttl_dns_cache=300,      # DNS cache 5 min
                keepalive_timeout=30,   # Keep connections alive
            )
            self._session = aiohttp.ClientSession(connector=connector)
            logger.debug("[STT] Created new aiohttp session with connection pooling")
        return self._session

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: str | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        """Required abstract method - not used for streaming STT."""
        raise NotImplementedError(
            "WhisperLiveKit STT is streaming-only, use stream() instead"
        )

    def stream(
        self,
        *,
        language: str | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "WhisperLiveKitSpeechStream":
        """Create a streaming transcription session."""
        opts = WhisperLiveKitOptions(
            host=self._opts.host,
            port=self._opts.port,
            language=language or self._opts.language,
            sample_rate=self._opts.sample_rate,
            use_ssl=self._opts.use_ssl,
        )
        return WhisperLiveKitSpeechStream(
            stt=self,
            opts=opts,
            conn_options=conn_options,
            http_session=self._ensure_session(),
        )


class WhisperLiveKitSpeechStream(stt.SpeechStream):
    """
    WhisperLiveKit streaming speech-to-text implementation.

    Bridges WebRTC audio from LiveKit to WhisperLiveKit WebSocket.
    Uses PCM input mode (raw s16le audio) for direct audio streaming.

    Key optimization: Uses stable text timeout for force-finalization
    when interim text hasn't changed for a period.
    """

    STABLE_TEXT_TIMEOUT = 0.3  # Force finalize if text unchanged for 300ms (reduced for lower latency)

    def __init__(
        self,
        *,
        stt: WhisperLiveKitSTT,
        opts: WhisperLiveKitOptions,
        conn_options: APIConnectOptions,
        http_session: aiohttp.ClientSession,
    ):
        super().__init__(stt=stt, conn_options=conn_options, sample_rate=opts.sample_rate)
        self._opts = opts
        self._session = http_session
        self._speaking = False
        self._session_id = f"wlk-{utils.shortuuid()}"
        self._request_id = ""
        self._last_interim_text = ""
        self._last_interim_time = 0.0
        self._finalized_texts: set[str] = set()

        logger.info(f"[{self._session_id}] WhisperLiveKitSpeechStream created")

    async def _run(self) -> None:
        """Main streaming loop with WebSocket connection to WhisperLiveKit."""
        closing_ws = False
        protocol = "wss" if self._opts.use_ssl else "ws"
        ws_url = f"{protocol}://{self._opts.host}:{self._opts.port}/asr"

        logger.info(f"[{self._session_id}] Connecting to WhisperLiveKit at {ws_url}")

        @utils.log_exceptions(logger=logger)
        async def send_task(ws: aiohttp.ClientWebSocketResponse) -> None:
            """Send audio frames to WhisperLiveKit as raw PCM (s16le)."""
            nonlocal closing_ws

            # Buffer for accumulating audio samples - smaller chunks for lower latency
            samples_per_chunk = self._opts.sample_rate // 40  # 25ms chunks (reduced from 50ms)
            audio_buffer = utils.audio.AudioByteStream(
                sample_rate=self._opts.sample_rate,
                num_channels=1,
                samples_per_channel=samples_per_chunk,
            )

            chunks_sent = 0
            logged_format = False

            async for data in self._input_ch:
                if isinstance(data, rtc.AudioFrame):
                    # Log audio format once
                    if not logged_format:
                        logger.info(
                            f"[{self._session_id}] Audio format: "
                            f"sample_rate={data.sample_rate}, "
                            f"channels={data.num_channels}, "
                            f"samples={data.samples_per_channel}, "
                            f"bytes={len(data.data.tobytes())}"
                        )
                        logged_format = True

                    frames = audio_buffer.write(data.data.tobytes())

                    for frame in frames:
                        # Send raw PCM s16le directly (WhisperLiveKit --pcm-input expects this)
                        pcm_data = frame.data.tobytes()
                        await ws.send_bytes(pcm_data)
                        chunks_sent += 1

                        if chunks_sent % 100 == 0:
                            logger.debug(f"[{self._session_id}] Sent {chunks_sent} PCM chunks")

                elif isinstance(data, self._FlushSentinel):
                    frames = audio_buffer.flush()
                    for frame in frames:
                        pcm_data = frame.data.tobytes()
                        await ws.send_bytes(pcm_data)

            closing_ws = True
            logger.info(f"[{self._session_id}] Audio streaming completed, sent {chunks_sent} chunks")

        @utils.log_exceptions(logger=logger)
        async def recv_task(ws: aiohttp.ClientWebSocketResponse) -> None:
            """Receive transcription results from WhisperLiveKit."""
            nonlocal closing_ws

            async def check_stable_text() -> None:
                """Background task to force-finalize text that has stabilized."""
                while not closing_ws:
                    await asyncio.sleep(0.1)

                    if (
                        self._last_interim_text
                        and self._last_interim_time > 0
                        and self._last_interim_text not in self._finalized_texts
                    ):
                        elapsed = time.time() - self._last_interim_time
                        if elapsed >= self.STABLE_TEXT_TIMEOUT:
                            text = self._last_interim_text
                            logger.info(
                                f"[{self._session_id}] STABLE TEXT ({elapsed:.2f}s) - force finalizing: '{text}'"
                            )

                            self._request_id = utils.shortuuid()
                            speech_data = stt.SpeechData(
                                language=self._opts.language,
                                text=text,
                                confidence=1.0,
                            )
                            final_event = stt.SpeechEvent(
                                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                                request_id=self._request_id,
                                alternatives=[speech_data],
                            )
                            self._event_ch.send_nowait(final_event)

                            self._finalized_texts.add(text)

                            if self._speaking:
                                self._speaking = False
                                end_event = stt.SpeechEvent(
                                    type=stt.SpeechEventType.END_OF_SPEECH
                                )
                                self._event_ch.send_nowait(end_event)

                            self._last_interim_text = ""
                            self._last_interim_time = 0

            stable_check_task = asyncio.create_task(check_stable_text())

            try:
                while True:
                    try:
                        msg = await ws.receive()

                        if msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSING,
                        ):
                            if closing_ws:
                                return
                            raise APIConnectionError("WhisperLiveKit connection closed unexpectedly")

                        if msg.type == aiohttp.WSMsgType.ERROR:
                            raise APIConnectionError(f"WebSocket error: {ws.exception()}")

                        if msg.type != aiohttp.WSMsgType.TEXT:
                            continue

                        # Parse WhisperLiveKit response
                        try:
                            data = json.loads(msg.data)
                        except json.JSONDecodeError:
                            logger.warning(f"[{self._session_id}] Invalid JSON from WhisperLiveKit")
                            continue

                        # WhisperLiveKit response format:
                        # {
                        #   'status': 'active_transcription',
                        #   'lines': [{'speaker': -2, 'text': '...', 'start': '...', 'end': '...'}],
                        #   'buffer_transcription': '...',  # interim text
                        #   'remaining_time_transcription': X.X,
                        # }

                        text = ""
                        is_final = False

                        # WhisperLiveKit format - check lines and buffer
                        if "lines" in data or "buffer_transcription" in data:
                            # Check buffer_transcription for interim results (ongoing speech)
                            buffer_text = data.get("buffer_transcription", "").strip()

                            # Check lines for finalized segments
                            lines = data.get("lines", [])
                            new_final_text = ""
                            for line in lines:
                                line_text = line.get("text", "").strip()
                                # Only process lines we haven't seen before
                                if line_text and line_text not in self._finalized_texts:
                                    new_final_text = line_text

                            # Priority: new final text > buffer (interim)
                            if new_final_text:
                                text = new_final_text
                                is_final = True
                                logger.info(f"[{self._session_id}] WLK FINAL: '{text}'")
                            elif buffer_text and buffer_text != self._last_interim_text:
                                text = buffer_text
                                is_final = False
                                logger.debug(f"[{self._session_id}] WLK interim: '{text}'")

                        # Fallback formats
                        elif "text" in data:
                            text = data.get("text", "").strip()
                            is_final = data.get("is_final", False) or data.get("completed", False)
                        elif "segments" in data:
                            segments = data.get("segments", [])
                            for seg in segments:
                                seg_text = seg.get("text", "").strip()
                                if seg_text:
                                    text = seg_text
                                    is_final = seg.get("completed", False) or seg.get("is_final", False)

                        if not text:
                            continue

                        self._request_id = utils.shortuuid()

                        if not self._speaking:
                            self._speaking = True
                            start_event = stt.SpeechEvent(
                                type=stt.SpeechEventType.START_OF_SPEECH
                            )
                            self._event_ch.send_nowait(start_event)
                            logger.debug(f"[{self._session_id}] Speech started")

                        speech_data = stt.SpeechData(
                            language=self._opts.language,
                            text=text,
                            confidence=1.0,
                        )

                        if text in self._finalized_texts:
                            logger.debug(f"[{self._session_id}] Skipping already finalized: '{text}'")
                            continue

                        if is_final:
                            final_event = stt.SpeechEvent(
                                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                                request_id=self._request_id,
                                alternatives=[speech_data],
                            )
                            self._event_ch.send_nowait(final_event)
                            logger.info(f"[{self._session_id}] Final: '{text}'")

                            self._finalized_texts.add(text)

                            if self._speaking:
                                self._speaking = False
                                end_event = stt.SpeechEvent(
                                    type=stt.SpeechEventType.END_OF_SPEECH
                                )
                                self._event_ch.send_nowait(end_event)

                            self._last_interim_text = ""
                            self._last_interim_time = 0
                        else:
                            # Interim transcript
                            if text != self._last_interim_text:
                                self._last_interim_text = text
                                self._last_interim_time = time.time()
                                logger.debug(f"[{self._session_id}] Interim: '{text}'")

                            interim_event = stt.SpeechEvent(
                                type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                                request_id=self._request_id,
                                alternatives=[speech_data],
                            )
                            self._event_ch.send_nowait(interim_event)

                    except asyncio.CancelledError:
                        return
                    except Exception as e:
                        if not closing_ws:
                            logger.error(f"[{self._session_id}] Error in recv_task: {e}")
                            raise
                        return
            finally:
                stable_check_task.cancel()
                try:
                    await stable_check_task
                except asyncio.CancelledError:
                    pass

        # Connect to WhisperLiveKit WebSocket
        ws: aiohttp.ClientWebSocketResponse | None = None

        # For SSL connections with self-signed certs, disable verification
        import ssl
        ssl_context = None
        if self._opts.use_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.info(f"[{self._session_id}] Using SSL (certificate verification disabled for self-signed)")

        try:
            ws = await asyncio.wait_for(
                self._session.ws_connect(ws_url, ssl=ssl_context if self._opts.use_ssl else False),
                timeout=self._conn_options.timeout,
            )
            logger.info(f"[{self._session_id}] Connected to WhisperLiveKit")

            # Run send and receive tasks concurrently
            tasks = [
                asyncio.create_task(send_task(ws)),
                asyncio.create_task(recv_task(ws)),
            ]

            try:
                await asyncio.gather(*tasks)
            finally:
                await utils.aio.gracefully_cancel(*tasks)

        except asyncio.TimeoutError:
            raise APIConnectionError(f"Timeout connecting to WhisperLiveKit at {ws_url}")
        except aiohttp.ClientError as e:
            raise APIConnectionError(f"Failed to connect to WhisperLiveKit: {e}")
        finally:
            if ws is not None and not ws.closed:
                await ws.close()
            logger.info(f"[{self._session_id}] WhisperLiveKit connection closed")


# =============================================================================
# Custom Async Piper TTS Implementation
# =============================================================================
# The livekit-plugins-piper-tts has issues:
# 1. Uses sync requests.post() which blocks the event loop
# 2. Pushes all audio at once causing stuttering
# This implementation uses async httpx and chunked audio output

PIPER_SAMPLE_RATE = 22050
PIPER_NUM_CHANNELS = 1
PIPER_CHUNK_SIZE = 4096  # Send audio in smaller chunks to prevent stuttering


class AsyncPiperTTS(tts.TTS):
    """Async Piper TTS with chunked audio output for smooth playback."""

    def __init__(self, base_url: str):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),  # Non-streaming uses synthesize()
            sample_rate=PIPER_SAMPLE_RATE,
            num_channels=PIPER_NUM_CHANNELS,
        )
        # Use streaming HTTP endpoint for lower latency chunked delivery
        self._base_url = base_url.replace("/api/synthesize", "/api/synthesize/stream")
        self._session: aiohttp.ClientSession | None = None
        logger.info(f"[TTS] Initialized with endpoint: {self._base_url}")

    def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an aiohttp session with optimized connection settings."""
        if self._session is None or self._session.closed:
            # Optimized connector: connection pooling + keep-alive
            connector = aiohttp.TCPConnector(
                limit=10,               # Max connections
                limit_per_host=5,       # Max per host
                ttl_dns_cache=300,      # DNS cache 5 min
                keepalive_timeout=30,   # Keep connections alive
            )
            self._session = aiohttp.ClientSession(connector=connector)
            logger.debug("[TTS] Created new aiohttp session with connection pooling")
        return self._session

    def synthesize(self, text: str, *, conn_options=DEFAULT_API_CONNECT_OPTIONS):
        return AsyncPiperStreamingStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            base_url=self._base_url,
            http_session=self._ensure_session(),
        )


class AsyncPiperStreamingStream(tts.ChunkedStream):
    """Async streaming TTS - emits audio chunks as they arrive from Piper for lowest latency."""

    def __init__(
        self,
        *,
        tts: AsyncPiperTTS,
        input_text: str,
        conn_options,
        base_url: str,
        http_session: aiohttp.ClientSession,
    ):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._base_url = base_url
        self._session = http_session

    async def _run(self, output_emitter: tts.AudioEmitter):
        """Stream audio from Piper in real-time for lowest latency."""
        synthesis_start = time.time()
        first_chunk_time = None

        try:
            # Initialize emitter immediately
            output_emitter.initialize(
                request_id=utils.shortuuid(),
                sample_rate=PIPER_SAMPLE_RATE,
                num_channels=PIPER_NUM_CHANNELS,
                mime_type="audio/pcm",
            )

            # Async streaming HTTP request to Piper TTS
            async with self._session.post(
                self._base_url,
                headers={"Content-Type": "application/json"},
                json={"text": self.input_text},
                timeout=aiohttp.ClientTimeout(total=30, sock_read=10),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[TTS] Piper streaming error: {response.status} - {error_text}")
                    return

                # Stream PCM chunks as they arrive
                chunks_sent = 0
                total_bytes = 0

                async for chunk in response.content.iter_chunked(PIPER_CHUNK_SIZE):
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        time_to_first = first_chunk_time - synthesis_start
                        logger.info(f"[TTS] Time to first audio chunk: {time_to_first:.3f}s")

                    output_emitter.push(chunk)
                    chunks_sent += 1
                    total_bytes += len(chunk)

                    # Yield control periodically
                    if chunks_sent % 5 == 0:
                        await asyncio.sleep(0)

            output_emitter.flush()

            total_time = time.time() - synthesis_start
            logger.info(f"[TTS] Streamed {total_bytes} bytes in {chunks_sent} chunks, total: {total_time:.2f}s")

        except asyncio.TimeoutError:
            logger.error("[TTS] Piper TTS streaming timed out")
        except aiohttp.ClientError as e:
            logger.error(f"[TTS] Piper TTS streaming error: {e}")
        except Exception as e:
            logger.error(f"[TTS] Piper TTS error: {e}")


def create_voice_pipeline(
    ollama_url: str,
    ollama_model: str,
    piper_tts_url: str,
    whisperlivekit_host: str,
    whisperlivekit_port: int,
    whisperlivekit_use_ssl: bool = False,
) -> tuple:
    """
    Create the voice pipeline components.

    Returns tuple of (stt, llm, tts, vad) for use with AgentSession.

    Pipeline: Audio (WebRTC) -> STT (WhisperLiveKit) -> LLM (Ollama) -> TTS (Piper) -> Audio
    """
    # Create WhisperLiveKit STT instance
    whisper_stt = WhisperLiveKitSTT(
        host=whisperlivekit_host,
        port=whisperlivekit_port,
        use_ssl=whisperlivekit_use_ssl,
    )

    # Create Ollama LLM with OpenAI-compatible API
    llm = openai.LLM.with_ollama(
        model=ollama_model,
        base_url=f"{ollama_url}/v1",
    )

    # Create async Piper TTS with chunked output
    piper_tts = AsyncPiperTTS(f"{piper_tts_url}/api/synthesize")

    # Tune Silero VAD for faster end-of-speech detection - OPTIMIZED
    vad = silero.VAD.load(
        min_speech_duration=0.05,   # Minimum speech to trigger (keep low)
        min_silence_duration=0.15,  # Reduced from 0.25s for faster turn detection
        activation_threshold=0.5,   # Slightly higher threshold for cleaner detection
    )

    protocol = "wss" if whisperlivekit_use_ssl else "ws"
    logger.info(f"Voice pipeline created:")
    logger.info(f"  - Ollama: {ollama_url}, model: {ollama_model}")
    logger.info(f"  - WhisperLiveKit: {protocol}://{whisperlivekit_host}:{whisperlivekit_port}")
    logger.info(f"  - Piper TTS: {piper_tts_url}")

    return whisper_stt, llm, piper_tts, vad


async def entrypoint(ctx: JobContext):
    """
    Main entry point for the AI voice agent.
    """
    logger.info("=" * 80)
    logger.info(f"Agent entrypoint called for room: {ctx.room.name}")
    logger.info("=" * 80)

    # Get configuration from environment
    ollama_url = os.getenv("OLLAMA_URL", "http://192.168.1.120:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    piper_tts_url = os.getenv("PIPER_TTS_URL", "http://piper-tts:5500")
    whisperlivekit_host = os.getenv("WHISPERLIVEKIT_HOST", "whisperlivekit")
    whisperlivekit_port = int(os.getenv("WHISPERLIVEKIT_PORT", "8765"))
    whisperlivekit_use_ssl = os.getenv("WHISPERLIVEKIT_USE_SSL", "false").lower() in ("true", "1", "yes")

    protocol = "wss" if whisperlivekit_use_ssl else "ws"
    logger.info(f"Configuration:")
    logger.info(f"  - Ollama URL: {ollama_url}")
    logger.info(f"  - Ollama Model: {ollama_model}")
    logger.info(f"  - WhisperLiveKit: {protocol}://{whisperlivekit_host}:{whisperlivekit_port}")
    logger.info(f"  - Piper TTS URL: {piper_tts_url}")

    # Create the voice pipeline components
    stt, llm, tts, vad = create_voice_pipeline(
        ollama_url=ollama_url,
        ollama_model=ollama_model,
        piper_tts_url=piper_tts_url,
        whisperlivekit_host=whisperlivekit_host,
        whisperlivekit_port=whisperlivekit_port,
        whisperlivekit_use_ssl=whisperlivekit_use_ssl,
    )

    # Create the agent with just instructions
    agent = Agent(
        instructions="""You are Trinity, a helpful AI voice assistant.
You help users with their questions in a friendly, conversational manner.
Keep your responses concise and natural for voice conversation.
Speak in a warm, friendly tone. Avoid using special characters or emojis.""",
    )

    # Create session with STT, LLM, TTS, VAD components
    # Per LiveKit docs: Session needs these components, not the Agent
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
        turn_detection="vad",
        min_endpointing_delay=0.2,  # Reduced from 0.3s for faster response initiation
    )

    # Timing tracking for latency analysis
    timing_data = {
        "speech_start": 0,
        "stt_final": 0,
        "llm_start": 0,
        "llm_first_token": 0,
        "llm_complete": 0,
        "tts_start": 0,
        "tts_first_audio": 0,
    }

    # Set up event handlers for debugging and timing
    # Helper function to publish transcripts to frontend
    async def publish_transcript(speaker: str, text: str, participant_identity: str = ""):
        """Publish transcript to frontend via data channel."""
        from datetime import datetime
        try:
            transcript_data = json.dumps({
                "type": "transcript",
                "speaker": speaker,  # "user" or "assistant"
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
                "participantIdentity": participant_identity or ("Trinity AI" if speaker == "assistant" else "User"),
            }).encode("utf-8")

            await ctx.room.local_participant.publish_data(
                payload=transcript_data,
                topic="transcripts",
            )
            logger.debug(f"[TRANSCRIPT] Published {speaker}: '{text[:50]}...'")
        except Exception as e:
            logger.error(f"[TRANSCRIPT] Failed to publish: {e}")

    @session.on("user_input_transcribed")
    def on_user_transcript(ev):
        """Handle user speech transcription."""
        if ev.is_final:
            timing_data["stt_final"] = time.time()
            stt_latency = timing_data["stt_final"] - timing_data["speech_start"] if timing_data["speech_start"] > 0 else 0
            logger.info(f"[TIMING] STT Final: '{ev.transcript}' (STT latency: {stt_latency:.2f}s)")

            # Publish user transcript to frontend
            asyncio.create_task(publish_transcript("user", ev.transcript))

    @session.on("agent_speech_committed")
    def on_agent_speech(ev):
        """Handle agent speech - publish to frontend."""
        if hasattr(ev, 'content') and ev.content:
            logger.info(f"[AGENT] Speaking: '{ev.content[:50]}...'")
            asyncio.create_task(publish_transcript("assistant", ev.content))

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        """Handle agent state changes with timing."""
        now = time.time()

        if ev.new_state == "listening":
            timing_data["speech_start"] = now
            logger.info(f"[STATE] {ev.old_state} -> {ev.new_state}")
        elif ev.new_state == "thinking":
            timing_data["llm_start"] = now
            if timing_data["stt_final"] > 0:
                stt_to_llm = now - timing_data["stt_final"]
                logger.info(f"[STATE] {ev.old_state} -> {ev.new_state} (STT->LLM: {stt_to_llm:.2f}s)")
            else:
                logger.info(f"[STATE] {ev.old_state} -> {ev.new_state}")
        elif ev.new_state == "speaking":
            timing_data["tts_start"] = now
            if timing_data["llm_start"] > 0:
                llm_latency = now - timing_data["llm_start"]
                total_latency = now - timing_data["speech_start"] if timing_data["speech_start"] > 0 else 0
                logger.info(f"[STATE] {ev.old_state} -> {ev.new_state} (LLM: {llm_latency:.2f}s, Total: {total_latency:.2f}s)")
            else:
                logger.info(f"[STATE] {ev.old_state} -> {ev.new_state}")
        else:
            logger.info(f"[STATE] {ev.old_state} -> {ev.new_state}")

    @session.on("user_started_speaking")
    def on_user_started_speaking(ev):
        timing_data["speech_start"] = time.time()
        logger.info(f"[VAD] User started speaking")

    @session.on("user_stopped_speaking")
    def on_user_stopped_speaking(ev):
        if timing_data["speech_start"] > 0:
            speech_duration = time.time() - timing_data["speech_start"]
            logger.info(f"[VAD] User stopped speaking (duration: {speech_duration:.2f}s)")

    # Start the session
    logger.info("Starting AgentSession...")

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                sample_rate=16000,
                num_channels=1,
            ),
        ),
    )

    logger.info("=" * 80)
    logger.info("AGENT SESSION STARTED SUCCESSFULLY")
    logger.info(f"  Room: {ctx.room.name}")
    logger.info("  Pipeline: Audio -> WhisperLiveKit STT -> Ollama LLM -> Piper TTS -> Audio")
    logger.info("=" * 80)

    # Generate initial greeting AFTER session is started
    # This is the correct way per LiveKit docs
    logger.info("Generating initial greeting...")
    session.generate_reply(
        instructions="Greet the user warmly and briefly. Ask how you can help them today. Keep it short - one or two sentences."
    )


if __name__ == "__main__":
    logger.info("Starting LiveKit AI Agent Worker...")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL', 'not set')}")
    logger.info(f"Ollama URL: {os.getenv('OLLAMA_URL', 'http://192.168.1.120:11434')}")

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
