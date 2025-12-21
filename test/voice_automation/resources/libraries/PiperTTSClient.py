"""
Piper TTS Client for Text-to-Speech synthesis
"""
import io
import logging
import time
import tempfile
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import numpy as np
except ImportError:
    np = None

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import PIPER_URL, AUDIO_SAMPLE_RATE, RESPONSE_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class TTSResult:
    """Result from TTS synthesis"""
    audio_path: str
    duration: float
    sample_rate: int
    text: str
    voice: str
    synthesis_time: float


class PiperTTSClient:
    """Client for Piper TTS HTTP API"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or PIPER_URL).rstrip('/')
        self.default_voice = "en_US-lessac-medium"
        self.last_result: Optional[TTSResult] = None
        self.temp_dir = tempfile.mkdtemp(prefix="voice_test_")

    def health_check(self) -> bool:
        """Check if Piper TTS is healthy"""
        try:
            if httpx:
                with httpx.Client(timeout=10) as client:
                    response = client.get(f"{self.base_url}/health")
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("status") == "ok"
            return False
        except Exception as e:
            logger.error(f"Piper TTS health check failed: {e}")
            return False

    def get_voices(self) -> Dict[str, Any]:
        """Get available voices"""
        try:
            if httpx:
                with httpx.Client(timeout=10) as client:
                    response = client.get(f"{self.base_url}/voices")
                    if response.status_code == 200:
                        return response.json()
            return {}
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return {}

    def synthesize(self, text: str, voice: str = None,
                   output_path: str = None) -> Optional[TTSResult]:
        """Synthesize text to speech"""
        try:
            voice = voice or self.default_voice
            start_time = time.time()

            if not output_path:
                output_path = os.path.join(
                    self.temp_dir,
                    f"tts_{int(time.time() * 1000)}.wav"
                )

            payload = {
                "text": text,
                "voice": voice,
                "sample_rate": AUDIO_SAMPLE_RATE
            }

            if httpx:
                with httpx.Client(timeout=RESPONSE_TIMEOUT * 2) as client:
                    # Use non-streaming endpoint (returns proper WAV format)
                    response = client.post(
                        f"{self.base_url}/api/synthesize",
                        json=payload
                    )

                    if response.status_code == 200:
                        # Write audio to file
                        with open(output_path, 'wb') as f:
                            f.write(response.content)

                        synthesis_time = time.time() - start_time

                        # Get audio duration
                        duration = 0
                        sample_rate = AUDIO_SAMPLE_RATE
                        if sf:
                            try:
                                info = sf.info(output_path)
                                duration = info.duration
                                sample_rate = info.samplerate
                            except Exception:
                                pass

                        self.last_result = TTSResult(
                            audio_path=output_path,
                            duration=duration,
                            sample_rate=sample_rate,
                            text=text,
                            voice=voice,
                            synthesis_time=synthesis_time
                        )

                        logger.info(f"TTS synthesized: {len(text)} chars -> {output_path}")
                        return self.last_result
                    else:
                        logger.error(f"TTS error: {response.status_code} - {response.text}")

            return None

        except Exception as e:
            logger.error(f"Failed to synthesize: {e}")
            return None

    def synthesize_multilingual(self, text: str, language: str = "en",
                                output_path: str = None) -> Optional[TTSResult]:
        """Synthesize text in specified language"""
        # Map language codes to voices
        voice_map = {
            "en": "en_US-lessac-medium",
            "hi": "hi_IN-default-medium",  # Hindi voice if available
            "kn": "kn_IN-default-medium",  # Kannada voice if available
            "mr": "mr_IN-default-medium",  # Marathi voice if available
        }

        voice = voice_map.get(language, self.default_voice)
        result = self.synthesize(text, voice=voice, output_path=output_path)

        # Fall back to English if specific language voice not available
        if not result and language != "en":
            logger.warning(f"Voice {voice} not available, falling back to English")
            result = self.synthesize(text, voice=self.default_voice, output_path=output_path)

        return result

    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file"""
        if sf:
            try:
                info = sf.info(audio_path)
                return info.duration
            except Exception as e:
                logger.error(f"Failed to get audio duration: {e}")
        return 0.0

    def get_synthesis_metrics(self) -> Dict[str, Any]:
        """Get metrics from last synthesis"""
        if not self.last_result:
            return {}

        return {
            "text_length": len(self.last_result.text),
            "audio_duration": self.last_result.duration,
            "synthesis_time_ms": self.last_result.synthesis_time * 1000,
            "realtime_factor": (
                self.last_result.duration / self.last_result.synthesis_time
                if self.last_result.synthesis_time > 0 else 0
            )
        }

    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    # Robot Framework Keywords
    def check_piper_health(self) -> bool:
        """Robot Framework keyword to check Piper TTS health"""
        result = self.health_check()
        if not result:
            raise AssertionError("Piper TTS not healthy")
        return result

    def synthesize_speech(self, text: str, output_path: str = None) -> str:
        """Robot Framework keyword to synthesize speech"""
        result = self.synthesize(text, output_path=output_path)
        if not result:
            raise AssertionError(f"Failed to synthesize: {text}")
        return result.audio_path

    def synthesize_in_language(self, text: str, language: str,
                               output_path: str = None) -> str:
        """Robot Framework keyword to synthesize in specific language"""
        result = self.synthesize_multilingual(text, language, output_path)
        if not result:
            raise AssertionError(f"Failed to synthesize in {language}: {text}")
        return result.audio_path

    def get_tts_synthesis_time(self) -> float:
        """Robot Framework keyword to get synthesis time in ms"""
        metrics = self.get_synthesis_metrics()
        return metrics.get("synthesis_time_ms", 0)

    def audio_duration_should_be_greater_than(self, audio_path: str, min_duration: str):
        """Robot Framework keyword to verify audio duration"""
        duration = self.get_audio_duration(audio_path)
        min_dur = float(min_duration)
        if duration < min_dur:
            raise AssertionError(
                f"Audio duration {duration}s is less than {min_dur}s"
            )
        return True
