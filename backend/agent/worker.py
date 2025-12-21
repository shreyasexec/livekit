"""
LiveKit AI Voice Agent Worker - Production Grade
Based on LiveKit Agents v1.3.8 API
With detailed per-component performance metrics

Performance optimizations:
- Streaming STT with fast finalization (150ms stable timeout)
- Streaming TTS with first-chunk latency tracking
- Fast VAD settings for quick turn detection
- Connection pooling for external services
"""

import asyncio
import json
import logging
import os
import ssl
import time
from typing import Optional

import aiohttp
import numpy as np
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    stt,
    tts,
    utils,
)
from livekit.plugins import openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("voice-agent")

# Reduce noise from libraries
for lib in ["httpx", "httpcore", "aiohttp", "websockets", "asyncio"]:
    logging.getLogger(lib).setLevel(logging.ERROR)  # Only show errors, suppress warnings

# Enable DEBUG for livekit.agents to see session activity
logging.getLogger("livekit.agents").setLevel(logging.DEBUG)


# =============================================================================
# Performance Metrics Tracker
# =============================================================================

class PerfMetrics:
    """Track per-component latencies for the voice pipeline."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.speech_start: Optional[float] = None
        self.speech_end: Optional[float] = None
        self.stt_start: Optional[float] = None
        self.stt_end: Optional[float] = None
        self.llm_start: Optional[float] = None
        self.llm_first_token: Optional[float] = None
        self.llm_end: Optional[float] = None
        self.tts_start: Optional[float] = None
        self.tts_first_chunk: Optional[float] = None
        self.tts_end: Optional[float] = None

    def log_summary(self, turn_id: str = ""):
        """Log performance summary for this turn."""
        metrics = {}

        if self.stt_start and self.stt_end:
            metrics["stt_ms"] = int((self.stt_end - self.stt_start) * 1000)

        if self.llm_start and self.llm_first_token:
            metrics["llm_ttft_ms"] = int((self.llm_first_token - self.llm_start) * 1000)

        if self.llm_start and self.llm_end:
            metrics["llm_total_ms"] = int((self.llm_end - self.llm_start) * 1000)

        if self.tts_start and self.tts_first_chunk:
            metrics["tts_ttfb_ms"] = int((self.tts_first_chunk - self.tts_start) * 1000)

        if self.speech_end and self.tts_first_chunk:
            metrics["e2e_ms"] = int((self.tts_first_chunk - self.speech_end) * 1000)

        if metrics:
            logger.info(f"[PERF] {turn_id} | STT:{metrics.get('stt_ms', '?')}ms | LLM-TTFT:{metrics.get('llm_ttft_ms', '?')}ms | LLM:{metrics.get('llm_total_ms', '?')}ms | TTS-TTFB:{metrics.get('tts_ttfb_ms', '?')}ms | E2E:{metrics.get('e2e_ms', '?')}ms")

        return metrics


# Global metrics instance
perf = PerfMetrics()


# =============================================================================
# WhisperLiveKit STT - Production Implementation with Metrics
# =============================================================================

class WhisperLiveKitSTT(stt.STT):
    """Streaming STT via WhisperLiveKit WebSocket.

    WhisperLiveKit protocol:
    - Connect to wss://<host>:<port>/ (root path)
    - Send raw PCM audio (16kHz, mono, int16)
    - Receive JSON with transcription results
    - Extract detected language for multi-language TTS
    """

    def __init__(self, host: str, port: int, use_ssl: bool = True):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=True, interim_results=True)
        )
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._session: Optional[aiohttp.ClientSession] = None
        self._detected_language = "en"  # Track detected language
        logger.info(f"[STT] WhisperLiveKit configured: {'wss' if use_ssl else 'ws'}://{host}:{port}")

    @property
    def detected_language(self) -> str:
        """Get the currently detected language code."""
        return self._detected_language

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # Use persistent connection with keep-alive
            connector = aiohttp.TCPConnector(limit=10, keepalive_timeout=30)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def _recognize_impl(self, buffer, *, language=None, conn_options=None):
        """Non-streaming recognition - not typically used with streaming STT."""
        raise NotImplementedError("Use stream() for WhisperLiveKit")

    def stream(self, *, language=None, conn_options=None) -> "WhisperLiveKitStream":
        return WhisperLiveKitStream(
            host=self._host,
            port=self._port,
            use_ssl=self._use_ssl,
            session=self._get_session(),
            conn_options=conn_options,
        )


class WhisperLiveKitStream(stt.RecognizeStream):
    """WebSocket stream to WhisperLiveKit - Production Real-time Streaming.

    IMPORTANT: Do NOT force finalization based on stable timeout!
    Let WhisperLiveKit decide when text is final via 'lines' array.
    Turn detector uses interim transcripts to predict end-of-utterance.

    Protocol:
    - Send raw PCM audio (16kHz, mono, int16)
    - Receive JSON with 'lines' (finalized) and 'buffer_transcription' (pending)
    - Only 'lines' entries are FINAL_TRANSCRIPT
    - 'buffer_transcription' entries are INTERIM_TRANSCRIPT for turn detector
    """

    # REMOVED: STABLE_TIMEOUT forced premature finalization, bypassing turn detector

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool,
        session: aiohttp.ClientSession,
        conn_options
    ):
        super().__init__(
            stt=WhisperLiveKitSTT(host, port, use_ssl),
            conn_options=conn_options,
            sample_rate=16000
        )
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._session = session
        self._last_interim = ""  # Last interim text (for deduplication)
        self._last_interim_time = 0.0  # For language-setting final
        self._language_final_emitted = False  # Track if we've set language
        self._processed_lines = 0  # Count of lines already emitted as final
        self._first_audio_time: Optional[float] = None
        # Extract language from conn_options or default to empty string
        self._detected_language = conn_options.language if conn_options and hasattr(conn_options, 'language') else ""

    async def _run(self):
        """Main streaming loop - receives audio from input channel, sends to WhisperLiveKit."""
        protocol = "wss" if self._use_ssl else "ws"
        # WhisperLiveKit uses /asr endpoint for WebSocket ASR
        url = f"{protocol}://{self._host}:{self._port}/asr"

        ssl_ctx = None
        if self._use_ssl:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        closing = False
        connect_start = time.time()

        async def send_audio(ws):
            """Send audio frames to WhisperLiveKit.

            Per official protocol: send raw PCM bytes directly.
            """
            nonlocal closing
            # Buffer for converting to consistent chunk sizes
            buffer = utils.audio.AudioByteStream(
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=400  # 25ms chunks
            )

            async for data in self._input_ch:
                if closing or ws.closed:
                    break

                if isinstance(data, rtc.AudioFrame):
                    if self._first_audio_time is None:
                        self._first_audio_time = time.time()
                        perf.stt_start = self._first_audio_time
                        logger.debug("[STT] First audio frame received")

                    for frame in buffer.write(data.data.tobytes()):
                        if closing or ws.closed:
                            break
                        try:
                            await ws.send_bytes(frame.data.tobytes())
                        except ConnectionResetError:
                            logger.warning("[STT] Connection reset - stopping send")
                            closing = True
                            return
                        except Exception as e:
                            if "closing" in str(e).lower() or "closed" in str(e).lower():
                                logger.debug("[STT] WebSocket closing - stopping send")
                                closing = True
                                return
                            logger.error(f"[STT] Send error: {e}")
                            return

                elif isinstance(data, self._FlushSentinel):
                    # Flush remaining audio and signal end
                    for frame in buffer.flush():
                        if ws.closed:
                            break
                        try:
                            await ws.send_bytes(frame.data.tobytes())
                        except Exception:
                            pass
                    # Per protocol: send empty blob to signal end
                    try:
                        if not ws.closed:
                            await ws.send_bytes(b"")
                    except Exception:
                        pass
            closing = True

        async def recv_transcripts(ws):
            """Receive and process transcripts from WhisperLiveKit in real-time.

            WhisperLiveKit streams interim transcripts via buffer_transcription.
            Finals are emitted when 'lines' array grows or when stream closes.

            IMPORTANT: We emit a "quick final" after 300ms of stable text to set
            the language in the SDK. Without this, the turn detector won't work
            because it requires language from a FINAL_TRANSCRIPT.
            """
            nonlocal closing

            # Background task to emit language-setting final
            async def check_language_final():
                """Emit a quick final to set language after short stable period.

                Per LiveKit docs, the turn detector requires language from FINAL_TRANSCRIPT.
                We emit a quick final after 150ms of stable text to set the language.
                """
                while not closing:
                    await asyncio.sleep(0.05)  # Check every 50ms for responsiveness
                    if (
                        not self._language_final_emitted
                        and self._last_interim
                        and self._last_interim_time > 0
                        and time.time() - self._last_interim_time >= 0.15  # 150ms stable
                    ):
                        self._language_final_emitted = True
                        logger.info(f"[STT] Language-setting final: '{self._last_interim}'")
                        self._emit_final(self._last_interim, is_language_setting=True)

            language_task = asyncio.create_task(check_language_final())

            try:
                while True:
                    try:
                        msg = await ws.receive()
                    except Exception as e:
                        if closing:
                            break
                        logger.error(f"[STT] Receive error: {e}")
                        break

                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                        break

                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue

                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue

                    # Handle protocol messages
                    msg_type = data.get("type", "transcription")
                    if msg_type == "config":
                        logger.debug(f"[STT] Config received: useAudioWorklet={data.get('useAudioWorklet')}")
                        continue
                    elif msg_type == "ready_to_stop":
                        logger.debug("[STT] Ready to stop received")
                        continue

                    text, is_final = self._extract_text(data)
                    if not text:
                        continue

                    if is_final:
                        self._emit_final(text)
                    else:
                        self._emit_interim(text)

            except asyncio.CancelledError:
                pass
            finally:
                language_task.cancel()
                try:
                    await language_task
                except asyncio.CancelledError:
                    pass
                # Emit final with any remaining interim text when stream closes
                if self._last_interim:
                    logger.debug(f"[STT] Final on stream close: '{self._last_interim[:40]}...'")
                    self._emit_final(self._last_interim)

        # Connect and run
        try:
            ws = await asyncio.wait_for(
                self._session.ws_connect(
                    url,
                    ssl=ssl_ctx,
                    heartbeat=30,
                    receive_timeout=None  # No timeout - server controls lifecycle
                ),
                timeout=10,
            )
            connect_time = (time.time() - connect_start) * 1000
            logger.info(f"[STT] Connected to WhisperLiveKit in {connect_time:.0f}ms")

            # Per official WhisperLiveKit protocol (github.com/QuentinFuxa/WhisperLiveKit):
            # 1. Server sends {type: "config", useAudioWorklet: true/false} first
            # 2. Client waits for config, then sends raw audio bytes
            # 3. Do NOT send config from client - server doesn't expect it
            try:
                config_msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                if config_msg.type == aiohttp.WSMsgType.TEXT:
                    config_data = json.loads(config_msg.data)
                    if config_data.get("type") == "config":
                        use_worklet = config_data.get("useAudioWorklet", False)
                        logger.info(f"[STT] Server config received: useAudioWorklet={use_worklet}")
                    else:
                        logger.debug(f"[STT] First message (non-config): {config_data}")
                else:
                    logger.debug(f"[STT] First message type: {config_msg.type}")
            except asyncio.TimeoutError:
                logger.warning("[STT] No config from server in 5s - proceeding anyway")

            # Run send and receive concurrently
            await asyncio.gather(
                send_audio(ws),
                recv_transcripts(ws),
                return_exceptions=True
            )

        except asyncio.TimeoutError:
            logger.error("[STT] Connection timeout")
        except Exception as e:
            logger.error(f"[STT] WebSocket error: {e}")

    def _extract_text(self, data: dict) -> tuple[str, bool]:
        """Extract text and language from WhisperLiveKit response.

        WhisperLiveKit format:
        - lines: finalized segments (list of {text, start, end, speaker})
        - buffer_transcription: pending unvalidated text (NOT cumulative)
        - language: detected language code (e.g., "en", "hi", "kn", "mr")

        Returns: (text, is_final)
        """
        msg_type = data.get("type", "")
        if msg_type in ("config", "ready_to_stop"):
            return "", False

        # Extract detected language if available
        # WhisperLiveKit may send language as "language" or "detected_language"
        detected_lang = data.get("language") or data.get("detected_language")
        if detected_lang and detected_lang != self._detected_language:
            self._detected_language = detected_lang
            logger.info(f"[STT] Detected language: {detected_lang}")

        # Process new finalized lines
        lines = data.get("lines", [])
        if len(lines) > self._processed_lines:
            # Collect all new finalized text
            new_texts = []
            for line in lines[self._processed_lines:]:
                text = line.get("text", "").strip() if isinstance(line, dict) else str(line).strip()
                if text:
                    new_texts.append(text)
            self._processed_lines = len(lines)
            if new_texts:
                return " ".join(new_texts), True

        # buffer_transcription is already just the pending portion
        buffer = data.get("buffer_transcription", "").strip()
        if buffer:
            return buffer, False

        return "", False

    def _emit_final(self, text: str, is_language_setting: bool = False):
        """Emit final transcript event with detected language.

        Args:
            text: The transcribed text
            is_language_setting: If True, this is a quick final just to set language
        """
        # Record STT completion time
        perf.stt_end = time.time()
        perf.speech_end = time.time()
        stt_latency = int((perf.stt_end - perf.stt_start) * 1000) if perf.stt_start else 0

        try:
            event = stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(language=self._detected_language, text=text)],
            )
            logger.info(f"[STT-EVENT] Sending FINAL event: '{text}' to event channel")
            self._event_ch.send_nowait(event)
            logger.info(f"[STT-EVENT] FINAL event sent successfully")
        except Exception as e:
            logger.error(f"[STT-EVENT] FAILED to emit final event: {e}", exc_info=True)

        # Reset interim tracking after emitting final
        self._last_interim = ""

        # If this is a real final (from lines[]), reset language flag for next turn
        if not is_language_setting:
            self._language_final_emitted = False

        display_text = f"'{text[:50]}...'" if len(text) > 50 else f"'{text}'"
        final_type = "lang-set" if is_language_setting else "real"
        logger.info(f"[STT] Final [{final_type}] ({stt_latency}ms): {display_text}")

    def _emit_interim(self, text: str):
        """Emit interim transcript event only when text changes, with detected language.

        Interim transcripts are critical for turn detector to predict EOU.
        """
        if text != self._last_interim:
            self._last_interim = text
            self._last_interim_time = time.time()

            # Log interim for debugging turn detector flow
            display_text = f"'{text[:40]}...'" if len(text) > 40 else f"'{text}'"
            logger.debug(f"[STT] Interim: {display_text}")

            try:
                event = stt.SpeechEvent(
                    type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                    alternatives=[stt.SpeechData(language=self._detected_language, text=text)],
                )
                logger.debug(f"[STT-EVENT] Sending INTERIM event: {display_text}")
                self._event_ch.send_nowait(event)
                logger.debug(f"[STT-EVENT] INTERIM event sent")
            except Exception as e:
                logger.error(f"[STT-EVENT] FAILED to emit interim event: {e}", exc_info=True)


# =============================================================================
# Piper TTS - Production Implementation with Streaming, Metrics & Multi-Language
# =============================================================================

# Voice mapping for multi-language TTS
# Per CLAUDE.md: EN, HI, KN, MR support required
VOICE_MAP = {
    "en": "en_US-lessac-medium",
    "hi": "hi_IN-swara-medium",
    "kn": "kn_IN-wavenet",
    "mr": "mr_IN-wavenet",
}
DEFAULT_VOICE = "en_US-lessac-medium"

class PiperTTS(tts.TTS):
    """Streaming TTS via Piper HTTP API with multi-language support.

    Uses the /api/synthesize/stream endpoint for lower latency.
    Audio is streamed in PCM chunks as they're generated.
    Automatically selects voice based on detected language from STT.
    """

    def __init__(self, base_url: str, stt_instance: Optional[WhisperLiveKitSTT] = None):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),  # Non-streaming synthesis per request
            sample_rate=22050,
            num_channels=1,
        )
        self._url = f"{base_url.rstrip('/')}/api/synthesize/stream"
        self._session: Optional[aiohttp.ClientSession] = None
        self._stt = stt_instance  # Reference to STT for language detection
        logger.info(f"[TTS] Piper configured: {self._url}")
        logger.info(f"[TTS] Multi-language voices: {list(VOICE_MAP.keys())}")

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10, keepalive_timeout=30)
            timeout = aiohttp.ClientTimeout(total=30, connect=5)
            self._session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self._session

    def synthesize(self, text: str, *, conn_options=None) -> "PiperChunkedStream":
        return PiperChunkedStream(
            tts=self,
            text=text,
            url=self._url,
            session=self._get_session(),
            sample_rate=self.sample_rate,
            conn_options=conn_options,
        )


class PiperChunkedStream(tts.ChunkedStream):
    """Stream audio chunks from Piper with metrics tracking.

    Performance optimizations:
    - Streaming response for lower time-to-first-byte
    - Chunk-based processing (4KB = ~90ms of audio)
    - Connection reuse
    """

    def __init__(
        self,
        tts: "PiperTTS",
        text: str,
        url: str,
        session: aiohttp.ClientSession,
        sample_rate: int,
        conn_options=None
    ):
        super().__init__(
            tts=tts,
            input_text=text,
            conn_options=conn_options,
        )
        self._url = url
        self._session = session
        self._sample_rate = sample_rate

    async def _run(self, output_emitter: tts.AudioEmitter):
        """Stream audio from Piper service with language-specific voice."""
        # Initialize emitter with PCM format (raw audio, no WAV headers)
        request_id = utils.shortuuid()
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._sample_rate,
            num_channels=1,
            mime_type="audio/pcm"  # Raw PCM from streaming endpoint
        )

        # Select voice based on detected language from STT
        detected_lang = "en"
        if hasattr(self._tts, '_stt') and self._tts._stt:
            detected_lang = self._tts._stt.detected_language

        voice = VOICE_MAP.get(detected_lang, DEFAULT_VOICE)
        logger.info(f"[TTS] Using voice '{voice}' for language '{detected_lang}'")

        perf.tts_start = time.time()
        start = time.time()
        first_chunk = True
        total_bytes = 0

        try:
            async with self._session.post(
                self._url,
                json={"text": self._input_text, "voice": voice, "sample_rate": self._sample_rate}
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"[TTS] HTTP {resp.status}: {error_text}")
                    return

                # Stream chunks as they arrive
                async for chunk in resp.content.iter_chunked(4096):
                    if first_chunk:
                        perf.tts_first_chunk = time.time()
                        ttfb = int((perf.tts_first_chunk - start) * 1000)
                        logger.info(f"[TTS] First chunk: {ttfb}ms")
                        first_chunk = False

                    total_bytes += len(chunk)
                    output_emitter.push(chunk)

            perf.tts_end = time.time()
            total_time = int((perf.tts_end - start) * 1000)
            logger.info(f"[TTS] Complete: {total_bytes} bytes in {total_time}ms")

            # Log full pipeline metrics
            perf.log_summary("turn")
            perf.reset()

        except asyncio.TimeoutError:
            logger.error("[TTS] Request timeout")
        except Exception as e:
            logger.error(f"[TTS] Error: {e}")

        output_emitter.flush()


# =============================================================================
# Main Entry Point
# =============================================================================

async def entrypoint(ctx: JobContext):
    """Voice agent entry point - called when agent joins room."""

    logger.info(f"Agent joining room: {ctx.room.name}")

    # Configuration from environment
    ollama_url = os.getenv("OLLAMA_URL", "http://192.168.1.120:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    piper_url = os.getenv("PIPER_TTS_URL", "http://piper-tts:5500")
    wlk_host = os.getenv("WHISPERLIVEKIT_HOST", "192.168.1.120")
    wlk_port = int(os.getenv("WHISPERLIVEKIT_PORT", "8765"))
    wlk_ssl = os.getenv("WHISPERLIVEKIT_USE_SSL", "true").lower() == "true"

    logger.info(f"[CONFIG] STT: {'wss' if wlk_ssl else 'ws'}://{wlk_host}:{wlk_port}")
    logger.info(f"[CONFIG] LLM: {ollama_url} ({ollama_model})")
    logger.info(f"[CONFIG] TTS: {piper_url}")

    # Create STT - WhisperLiveKit streaming with language detection
    my_stt = WhisperLiveKitSTT(
        host=wlk_host,
        port=wlk_port,
        use_ssl=wlk_ssl
    )

    # Create TTS - Piper streaming with multi-language support
    # Pass STT instance so TTS can access detected language
    my_tts = PiperTTS(base_url=piper_url, stt_instance=my_stt)

    # Create LLM - Ollama via OpenAI-compatible API
    # with_ollama() expects base URL WITH /v1 (e.g., http://host:11434/v1)
    ollama_base_url = f"{ollama_url.rstrip('/')}/v1"
    my_llm = openai.LLM.with_ollama(
        model=ollama_model,
        base_url=ollama_base_url
    )
    logger.info(f"[CONFIG] LLM base URL: {ollama_base_url}")

    # Create VAD - per official LiveKit docs (docs.livekit.io/agents/build/turns/vad/)
    # Increased min_silence_duration for multilingual (users pause longer between thoughts)
    my_vad = silero.VAD.load(
        min_speech_duration=0.1,       # 100ms speech to start (prevents short noise triggers)
        min_silence_duration=0.8,      # 800ms silence before end-of-turn (allows natural pauses)
        activation_threshold=0.5,      # Default - balanced sensitivity
        prefix_padding_duration=0.5,   # Default - 500ms context before speech
    )

    # Create agent with voice-optimized instructions ONLY
    # Per official example: LLM goes in AgentSession, NOT Agent!
    logger.info("[FLOW] Creating Agent with instructions...")
    agent = Agent(
        instructions="""You are a helpful voice assistant. Listen carefully and respond concisely.

Language:
Default to English. Switch languages only when the user clearly speaks in another language.
If user speaks Hindi, respond in Hindi. If user speaks Kannada, respond in Kannada.
When user says "switch to" a language, immediately switch and confirm briefly.

Voice output:
Plain text only. No markdown, lists, code, or special formatting.
Keep responses to one or two sentences maximum.
Wait for the user to finish speaking before responding.

Behavior:
Be helpful and direct. Answer questions concisely.
If unsure what the user said, ask them to repeat.
For medical, legal, or financial topics, suggest consulting a professional.""",
    )
    logger.info("[FLOW] Agent created")

    # Create session with ALL components (STT/LLM/TTS/VAD)
    # Per official example: ALL models go in AgentSession!
    # Per official LiveKit docs (docs.livekit.io/agents/build/turns/)
    # MultilingualModel has 99.4% accuracy for Hindi, 99.3% for English
    logger.info("[FLOW] Creating AgentSession with all components...")
    session = AgentSession(
        stt=my_stt,
        llm=my_llm,  # LLM goes in SESSION, not Agent!
        tts=my_tts,
        vad=my_vad,
        turn_detection=MultilingualModel(),  # Required for multilingual turn detection
        allow_interruptions=True,
        min_endpointing_delay=0.5,         # Official default: 500ms minimum before responding
        max_endpointing_delay=6.0,         # Official default: 6s max wait (NOT 3s)
    )
    logger.info("[FLOW] AgentSession created")

    # Register event handlers for metrics and transcript publishing
    # IMPORTANT: Must register BEFORE session.start()
    @session.on("agent_state_changed")
    def on_agent_state(ev):
        """Track agent state for latency measurement."""
        if ev.new_state == "speaking":
            perf.llm_start = time.time()
        logger.info(f"[EVENT] Agent state: {ev.old_state} -> {ev.new_state}")

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev):
        """Handle user input transcription - alternative to conversation_item_added."""
        logger.info(f"[EVENT] User transcribed: '{ev.transcript}' (final={ev.is_final})")
        if ev.is_final:
            asyncio.create_task(publish_transcript(
                ctx.room.local_participant,
                speaker="user",
                text=ev.transcript,
                participant_identity=ctx.room.remote_participants.get(list(ctx.room.remote_participants.keys())[0]).identity if ctx.room.remote_participants else "user"
            ))

    @session.on("conversation_item_added")
    def on_conversation_item(ev):
        """Handle new conversation items - publish transcripts."""
        item = ev.item
        role = getattr(item, 'role', '')
        text = getattr(item, 'text_content', '') or ''

        if not text:
            return

        display = f"'{text[:50]}...'" if len(text) > 50 else f"'{text}'"

        if role == "assistant":
            logger.info(f"[EVENT] Agent said: {display}")
            asyncio.create_task(publish_transcript(
                ctx.room.local_participant,
                speaker="assistant",
                text=text,
                participant_identity="Voice Assistant"
            ))
        elif role == "user":
            logger.info(f"[EVENT] User said: {display}")
            asyncio.create_task(publish_transcript(
                ctx.room.local_participant,
                speaker="user",
                text=text,
                participant_identity=ctx.room.remote_participants.get(list(ctx.room.remote_participants.keys())[0]).identity if ctx.room.remote_participants else "user"
            ))

    # Start the session BEFORE connecting to room (per official example)
    # This allows session to properly initialize audio pipeline
    logger.info("[FLOW] Starting session...")
    try:
        await session.start(agent=agent, room=ctx.room)
        logger.info("[FLOW] Session started successfully")
    except Exception as e:
        logger.error(f"[FLOW] Session start failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    # Connect to room AFTER session is started (per official example)
    logger.info("[FLOW] Connecting to room...")
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    logger.info("[FLOW] Connected to room")

    # List current participants for debugging
    logger.info(f"[FLOW] Room participants: {len(ctx.room.remote_participants)}")
    for sid, p in ctx.room.remote_participants.items():
        logger.info(f"[FLOW]   - {p.identity} (sid={sid}, kind={p.kind})")

    # Generate greeting in English
    logger.info("[FLOW] Generating initial greeting...")
    greeting_start = time.time()
    try:
        await session.generate_reply(
            instructions="Say a brief friendly greeting like 'Hello! How can I help you today?' Keep it short."
        )
        logger.info(f"[FLOW] Greeting generated in {(time.time()-greeting_start)*1000:.0f}ms")
    except Exception as e:
        logger.error(f"[FLOW] Greeting generation failed: {e}")

    logger.info("Agent ready - listening for speech")
    logger.info("=" * 60)
    logger.info("PERFORMANCE METRICS ENABLED")
    logger.info("  [STT] Speech-to-Text latency")
    logger.info("  [LLM] Language Model latency (TTFT + Total)")
    logger.info("  [TTS] Text-to-Speech latency (TTFB + Total)")
    logger.info("  [PERF] End-to-end pipeline summary")
    logger.info("=" * 60)


async def publish_transcript(
    local_participant: rtc.LocalParticipant,
    speaker: str,
    text: str,
    participant_identity: str,
    detected_language: str = "en"
):
    """Publish transcript to frontend via data channel."""
    try:
        import datetime
        payload = json.dumps({
            "type": "transcript",
            "speaker": speaker,
            "text": text,
            "participantIdentity": participant_identity,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "detectedLanguage": detected_language,
        }).encode("utf-8")

        await local_participant.publish_data(
            payload=payload,
            topic="transcripts",
            reliable=True,
        )
    except Exception as e:
        logger.error(f"Failed to publish transcript: {e}")


async def request_fnc(request):
    """Handle incoming job requests - accept one agent per room."""
    logger.info(f"[REQUEST] Job request for room: {request.room.name}")
    # Accept the job request
    await request.accept()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        request_fnc=request_fnc,
    ))
