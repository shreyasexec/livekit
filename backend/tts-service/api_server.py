"""
Piper TTS API Server

Provides HTTP API endpoints for Piper text-to-speech synthesis.

Performance Optimization:
- Uses native piper-tts Python library for in-memory model (no subprocess)
- Model is cached after first load (~200-400ms faster per request)
- Falls back to subprocess if native loading fails
"""

import asyncio
import io
import logging
import struct
import time
import wave
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Piper TTS API",
    description="HTTP API for Piper text-to-speech synthesis (optimized)",
    version="1.1.0"
)

# Voice models directory
VOICES_DIR = Path("/app/voices")

# =============================================================================
# NATIVE PIPER-TTS SUPPORT - Performance Optimization
# =============================================================================
# Load voice model into memory using piper-tts Python library.
# This avoids subprocess spawning overhead (~200-400ms per request).
# =============================================================================

# Cache for loaded voice models
_voice_cache: Dict[str, Any] = {}
_voice_lock = threading.Lock()
_use_native = True  # Try native first, fallback to subprocess


def _try_load_native():
    """Try to import piper-tts and mark if available."""
    global _use_native
    try:
        from piper import PiperVoice
        logger.info("[TTS] Native piper-tts library available")
        return True
    except ImportError:
        logger.warning("[TTS] Native piper-tts not available, using subprocess")
        _use_native = False
        return False


# Check native support at startup
_try_load_native()


async def get_voice(voice_name: str):
    """
    Get a cached voice model, loading if needed.

    This keeps the model in memory for faster synthesis.
    """
    global _voice_cache, _use_native

    if not _use_native:
        return None

    if voice_name in _voice_cache:
        return _voice_cache[voice_name]

    voice_path = VOICES_DIR / f"{voice_name}.onnx"
    config_path = VOICES_DIR / f"{voice_name}.onnx.json"

    if not voice_path.exists():
        return None

    try:
        from piper import PiperVoice

        # Load voice model (blocks, but only once per voice)
        def load_voice():
            logger.info(f"[TTS] Loading voice model: {voice_name}")
            start = time.time()
            voice = PiperVoice.load(str(voice_path), str(config_path) if config_path.exists() else None)
            elapsed = time.time() - start
            logger.info(f"[TTS] Voice model loaded in {elapsed:.2f}s")
            return voice

        # Run in thread to not block event loop
        loop = asyncio.get_event_loop()
        voice = await loop.run_in_executor(None, load_voice)

        with _voice_lock:
            _voice_cache[voice_name] = voice

        return voice

    except Exception as e:
        logger.error(f"[TTS] Failed to load native voice: {e}")
        _use_native = False
        return None


class SynthesizeRequest(BaseModel):
    """Request model for synthesis endpoint."""
    text: str
    voice: str = "en_US-lessac-medium"
    sample_rate: int = 22050


class VoiceInfo(BaseModel):
    """Voice model information."""
    name: str
    path: str


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Status information
    """
    return {
        "status": "ok",
        "service": "Piper TTS API",
        "voices_available": len(list(VOICES_DIR.glob("*.onnx")))
    }


@app.get("/voices")
async def list_voices():
    """
    List available voice models.

    Returns:
        List of available voices
    """
    try:
        voices = [
            {
                "name": voice.stem,
                "path": str(voice)
            }
            for voice in VOICES_DIR.glob("*.onnx")
        ]

        return {"voices": [v["name"] for v in voices]}

    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_wav_from_raw_pcm(raw_pcm: bytes, sample_rate: int = 22050, channels: int = 1, sample_width: int = 2) -> bytes:
    """
    Create a proper WAV file from raw PCM data.

    Args:
        raw_pcm: Raw PCM audio data (16-bit signed little-endian)
        sample_rate: Audio sample rate in Hz
        channels: Number of audio channels (1 for mono)
        sample_width: Bytes per sample (2 for 16-bit)

    Returns:
        Complete WAV file as bytes with proper RIFF headers
    """
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_pcm)

    wav_buffer.seek(0)
    return wav_buffer.read()


@app.post("/api/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthesize text to speech using Piper.

    Args:
        request: Synthesis request containing text and voice

    Returns:
        WAV audio response with proper RIFF headers
    """
    try:
        # Validate voice model exists
        voice_path = VOICES_DIR / f"{request.voice}.onnx"

        if not voice_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Voice model not found: {request.voice}"
            )

        logger.info(f"Synthesizing: '{request.text[:50]}...' with voice {request.voice}")

        # Run Piper TTS with raw output
        # Command: echo "text" | piper --model voice.onnx --output_raw
        process = await asyncio.create_subprocess_exec(
            "piper",
            "--model", str(voice_path),
            "--output_raw",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Send text to stdin
        stdout, stderr = await process.communicate(input=request.text.encode())

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Piper synthesis failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"TTS synthesis failed: {error_msg}"
            )

        logger.info(f"Raw PCM output: {len(stdout)} bytes")

        # Convert raw PCM to proper WAV format with headers
        # Piper outputs 16-bit signed little-endian PCM at 22050Hz mono by default
        wav_data = create_wav_from_raw_pcm(
            raw_pcm=stdout,
            sample_rate=request.sample_rate,
            channels=1,
            sample_width=2  # 16-bit = 2 bytes
        )

        logger.info(f"WAV output: {len(wav_data)} bytes (with headers)")

        # Return as complete response (not streaming) for proper WAV handling
        return Response(
            content=wav_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav",
                "Content-Length": str(len(wav_data)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/synthesize/stream")
async def synthesize_stream(request: SynthesizeRequest):
    """
    Synthesize text to speech using Piper with streaming output.

    Performance: Uses native piper-tts library when available (saves ~200-400ms).
    Falls back to subprocess if native not available.

    Returns raw PCM chunks as they are generated for lower latency.
    """
    try:
        voice_path = VOICES_DIR / f"{request.voice}.onnx"

        if not voice_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Voice model not found: {request.voice}"
            )

        # Try native synthesis first (much faster - model in memory)
        voice = await get_voice(request.voice)

        if voice is not None:
            logger.info(f"[TTS-NATIVE] Streaming: '{request.text[:50]}...'")
            return StreamingResponse(
                stream_native(request.text, voice),
                media_type="audio/pcm",
                headers={
                    "X-Sample-Rate": str(request.sample_rate),
                    "X-Channels": "1",
                    "X-Sample-Width": "2",
                    "X-Method": "native",
                },
            )

        # Fallback to subprocess
        logger.info(f"[TTS-SUBPROCESS] Streaming: '{request.text[:50]}...'")

        async def generate_audio():
            """Generator that yields PCM chunks as they're produced."""
            process = await asyncio.create_subprocess_exec(
                "piper",
                "--model", str(voice_path),
                "--output_raw",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Write text to stdin and close it
            process.stdin.write(request.text.encode())
            await process.stdin.drain()
            process.stdin.close()

            # Stream stdout in chunks (4KB = ~90ms of audio at 22050Hz 16-bit mono)
            chunk_size = 4096
            total_bytes = 0

            while True:
                chunk = await process.stdout.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                yield chunk

            await process.wait()
            logger.info(f"[TTS-SUBPROCESS] Streamed {total_bytes} bytes")

        return StreamingResponse(
            generate_audio(),
            media_type="audio/pcm",
            headers={
                "X-Sample-Rate": str(request.sample_rate),
                "X-Channels": "1",
                "X-Sample-Width": "2",
                "X-Method": "subprocess",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_native(text: str, voice):
    """
    Stream audio using native piper-tts synthesize().

    Uses threading to run synthesis in background while yielding chunks.
    """
    import queue

    start = time.time()
    first_chunk = True
    total_bytes = 0
    chunk_queue = queue.Queue()
    error_holder = [None]
    done = threading.Event()

    def producer():
        """Run synthesis in thread, push chunks to queue."""
        try:
            for audio_chunk in voice.synthesize(text):
                pcm_bytes = audio_chunk.audio_int16_bytes
                if pcm_bytes:
                    chunk_queue.put(pcm_bytes)
        except Exception as e:
            error_holder[0] = e
            logger.error(f"[TTS-NATIVE] Producer error: {e}")
        finally:
            done.set()

    # Start producer thread
    thread = threading.Thread(target=producer, daemon=True)
    thread.start()

    # Yield chunks as they arrive
    while True:
        try:
            chunk = chunk_queue.get(timeout=0.05)
            if first_chunk:
                elapsed = time.time() - start
                logger.info(f"[TTS-NATIVE] First chunk: {elapsed:.3f}s")
                first_chunk = False
            total_bytes += len(chunk)
            yield chunk
        except queue.Empty:
            if done.is_set() and chunk_queue.empty():
                break
            await asyncio.sleep(0.01)

    thread.join(timeout=2.0)

    if error_holder[0]:
        logger.error(f"[TTS-NATIVE] Error: {error_holder[0]}")

    elapsed = time.time() - start
    logger.info(f"[TTS-NATIVE] Complete: {total_bytes} bytes in {elapsed:.2f}s")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Piper TTS API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "voices": "/voices",
            "synthesize": "/api/synthesize (POST)"
        }
    }


@app.on_event("startup")
async def startup_warmup():
    """Pre-load voice model on startup for faster first request."""
    logger.info("[STARTUP] Pre-warming TTS model...")
    try:
        voice = await get_voice("en_US-lessac-medium")
        if voice:
            logger.info("[STARTUP] TTS model loaded and ready!")
        else:
            logger.warning("[STARTUP] Native TTS not available, using subprocess")
    except Exception as e:
        logger.error(f"[STARTUP] Warmup failed: {e}")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Piper TTS API server...")
    logger.info(f"Voices directory: {VOICES_DIR}")
    logger.info(f"Available voices: {len(list(VOICES_DIR.glob('*.onnx')))}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5500,
        log_level="info"
    )
