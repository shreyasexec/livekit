"""
Piper TTS API Server

Provides HTTP API endpoints for Piper text-to-speech synthesis.
This server wraps the Piper TTS command-line tool with a REST API.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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
    description="HTTP API for Piper text-to-speech synthesis",
    version="1.0.0"
)

# Voice models directory
VOICES_DIR = Path("/app/voices")


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


@app.post("/api/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthesize text to speech using Piper.

    Args:
        request: Synthesis request containing text and voice

    Returns:
        Streaming audio response (WAV format)
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

        # Run Piper TTS
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

        logger.info(f"Synthesis complete: {len(stdout)} bytes")

        # Return audio as streaming response
        async def audio_stream():
            yield stdout

        return StreamingResponse(
            audio_stream(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
