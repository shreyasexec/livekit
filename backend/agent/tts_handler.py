"""
Piper TTS Plugin for LiveKit Agents

This module provides integration with Piper TTS service.
Since Piper doesn't have an official LiveKit plugin, we create
a custom wrapper that follows the LiveKit Agents TTS plugin pattern.

Based on:
- Piper TTS: https://github.com/rhasspy/piper
- Custom API server implementation (see tts-service/)
- LiveKit Agents TTS API: https://docs.livekit.io/agents/api/
"""

import logging
import os
from typing import Optional
from dataclasses import dataclass

import httpx
from livekit.agents import (
    tts,
    utils,
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

logger = logging.getLogger(__name__)


def create_piper_tts(
    *,
    base_url: str = "http://localhost:5500",
    voice: str = "en_US-lessac-medium",
    sample_rate: int = 22050,
) -> "PiperTTS":
    """
    Factory function to create a Piper TTS instance.

    Args:
        base_url: URL of the Piper TTS service
        voice: Voice model name
        sample_rate: Audio sample rate

    Returns:
        Configured PiperTTS instance
    """
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


@dataclass
class _TTSOptions:
    """Configuration options for Piper TTS"""
    base_url: str
    voice: str


class PiperTTS(tts.TTS):
    """
    LiveKit TTS plugin that uses the Piper TTS HTTP service.

    Piper provides high-quality neural text-to-speech synthesis.
    This implementation follows the LiveKit Agents TTS plugin pattern.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:5500",
        voice: str = "en_US-lessac-medium",
        sample_rate: int = 22050,
    ):
        """
        Initialize Piper TTS plugin.

        Args:
            base_url: URL of the Piper TTS service
            voice: Voice model name (must be available on the server)
            sample_rate: Audio sample rate (default 22050 Hz)
        """
        # Initialize parent TTS class with capabilities
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )

        self._opts = _TTSOptions(
            base_url=base_url.rstrip("/"),
            voice=voice,
        )

        logger.info(
            f"Piper TTS initialized: {base_url}, voice={voice}, "
            f"sample_rate={sample_rate}"
        )

    @property
    def model(self) -> str:
        """Return the voice model name"""
        return self._opts.voice

    @property
    def provider(self) -> str:
        """Return the provider name"""
        return "Piper"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "PiperChunkedStream":
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize
            conn_options: API connection options

        Returns:
            PiperChunkedStream for audio output
        """
        return PiperChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )


class PiperChunkedStream(tts.ChunkedStream):
    """
    Chunked stream implementation for Piper TTS.

    Handles the actual synthesis by communicating with the Piper HTTP service.
    """

    def __init__(
        self,
        *,
        tts: PiperTTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ):
        super().__init__(
            tts=tts,
            input_text=input_text,
            conn_options=conn_options,
        )
        self._tts: PiperTTS = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        """
        Run the synthesis task.

        Args:
            output_emitter: AudioEmitter to push audio data to
        """
        request_id = utils.shortuuid()

        try:
            logger.debug(f"Synthesizing text: '{self._input_text[:50]}...'")

            # Make HTTP request to Piper service
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._tts._opts.base_url}/api/synthesize",
                    json={
                        "text": self._input_text,
                        "voice": self._tts._opts.voice,
                        "sample_rate": self._tts.sample_rate,
                    },
                    timeout=self._conn_options.timeout,
                )
                resp.raise_for_status()
                audio_data = resp.content

            # Initialize the output emitter with audio format info
            output_emitter.initialize(
                request_id=request_id,
                sample_rate=self._tts.sample_rate,
                num_channels=self._tts.num_channels,
                mime_type="audio/wav",  # Piper returns WAV format
            )

            # Push the audio data
            output_emitter.push(audio_data)

            # Flush to signal completion
            output_emitter.flush()

            logger.debug(
                f"Synthesis complete: {len(audio_data)} bytes, "
                f"request_id={request_id}"
            )

        except httpx.TimeoutException:
            logger.error("Piper TTS request timed out")
            raise APITimeoutError() from None

        except httpx.HTTPStatusError as e:
            logger.error(f"Piper TTS HTTP error: {e.response.status_code}")
            raise APIStatusError(
                message=f"Piper TTS error: {e.response.text}",
                status_code=e.response.status_code,
                request_id=request_id,
                body=e.response.text,
            ) from None

        except httpx.HTTPError as e:
            logger.error(f"Piper TTS connection error: {e}")
            raise APIConnectionError() from e

        except Exception as e:
            logger.error(f"Piper TTS unexpected error: {e}")
            raise APIConnectionError() from e
