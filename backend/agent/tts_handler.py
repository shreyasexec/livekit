"""
Piper TTS Plugin for LiveKit Agents

This module provides integration with Piper TTS service.
Since Piper doesn't have an official LiveKit plugin, we create
a custom wrapper that can be used with the agent framework.

Based on:
- Piper TTS: https://github.com/rhasspy/piper
- Custom API server implementation (see tts-service/)
"""

import logging
import os
from typing import Optional

import httpx
from livekit.agents import tts

logger = logging.getLogger(__name__)


def create_piper_tts(
    base_url: str = "http://localhost:5500",
    voice: str = "en_US-lessac-medium",
    sample_rate: int = 22050,
) -> "PiperTTS":
    """Factory returning a local Piper TTS instance."""
    return PiperTTS(base_url=base_url, voice=voice, sample_rate=sample_rate)


class PiperTTSClient:
    """
    Piper TTS client for interacting with custom Piper API server.

    This client communicates with the Piper TTS service via HTTP.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5500",
        voice: str = "en_US-lessac-medium",
        sample_rate: int = 22050,
    ):
        """
        Initialize Piper TTS client.

        Args:
            base_url: Piper service URL
            voice: Voice model name
            sample_rate: Audio sample rate
        """
        self.base_url = base_url.rstrip("/")
        self.voice = voice
        self.sample_rate = sample_rate

        logger.info(
            f"Piper TTS client initialized: {base_url}, "
            f"voice={voice}, sample_rate={sample_rate}"
        )

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize

        Returns:
            Audio data as bytes (WAV format)
        """
        import httpx

        try:
            logger.debug(f"Synthesizing text: '{text[:50]}...'")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/synthesize",
                    json={
                        "text": text,
                        "voice": self.voice,
                        "sample_rate": self.sample_rate,
                    },
                )
                response.raise_for_status()

                audio_data = response.content
                logger.debug(f"Synthesis complete: {len(audio_data)} bytes")

                return audio_data

        except httpx.HTTPError as e:
            logger.error(f"Piper TTS HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            raise

    async def list_voices(self) -> list:
        """
        List available voices from Piper service.

        Returns:
            List of voice names
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/voices")
                response.raise_for_status()

                data = response.json()
                return data.get("voices", [])

        except Exception as e:
            logger.error(f"Failed to list Piper voices: {e}")
            return []

    async def health_check(self) -> bool:
        """
        Check if Piper service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()

                data = response.json()
                return data.get("status") == "ok"

        except Exception as e:
            logger.error(f"Piper health check failed: {e}")
            return False


# Example usage and testing
async def test_piper():
    """Test Piper TTS connection and synthesis."""
    piper_url = os.getenv("PIPER_URL", "http://localhost:5500")

    client = PiperTTSClient(
        base_url=piper_url,
        voice="en_US-lessac-medium",
    )

    # Health check
    logger.info("Checking Piper TTS service health...")
    if await client.health_check():
        logger.info("Piper TTS service is healthy")

        # List voices
        voices = await client.list_voices()
        if voices:
            logger.info(f"Available voices: {voices}")

        # Test synthesis
        try:
            audio_data = await client.synthesize("Hello, this is a test.")
            logger.info(f"Synthesis successful: {len(audio_data)} bytes")
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
    else:
        logger.error("Piper TTS service is not available")


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_piper())


class PiperTTS(tts.TTS):
    """
    LiveKit TTS adapter that uses the local Piper HTTP service.
    """

    def __init__(self, base_url: str, voice: str, sample_rate: int = 22050):
        self.base_url = base_url.rstrip("/")
        self.voice = voice
        self.sample_rate = sample_rate

    async def synthesize(
        self,
        text: str,
        *,
        sample_rate: Optional[int] = None,
        voice: Optional[str] = None,
    ) -> tts.Speech:
        """
        Synthesize text via Piper HTTP API and return audio to LiveKit.
        """
        sr = sample_rate or self.sample_rate
        chosen_voice = voice or self.voice

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/synthesize",
                    json={
                        "text": text,
                        "voice": chosen_voice,
                        "sample_rate": sr,
                    },
                )
                resp.raise_for_status()
                audio_data = resp.content

            return tts.Speech(
                audio=audio_data,
                sample_rate=sr,
                num_channels=1,
                format=tts.AudioFormat.WAV,
            )
        except Exception as e:
            logger.error(f"Piper synth failed: {e}")
            raise
