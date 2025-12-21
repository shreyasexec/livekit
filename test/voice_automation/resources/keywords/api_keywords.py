"""
API Keywords for Robot Framework
Keywords for testing STT, LLM, and TTS APIs
"""
import logging
from robot.api.deco import keyword, library

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from resources.libraries.WhisperLiveClient import WhisperLiveClient
from resources.libraries.OllamaClient import OllamaClient
from resources.libraries.PiperTTSClient import PiperTTSClient
from config import WHISPER_WS_URL, OLLAMA_URL, PIPER_URL

logger = logging.getLogger(__name__)


@library(scope='GLOBAL')
class APIKeywords:
    """Keywords for API testing"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.whisper_client = None
        self.ollama_client = None
        self.piper_client = None

    @keyword("Initialize STT Client")
    def initialize_stt_client(self, url: str = None):
        """Initialize WhisperLiveKit STT client"""
        self.whisper_client = WhisperLiveClient(url or WHISPER_WS_URL)
        return True

    @keyword("Initialize LLM Client")
    def initialize_llm_client(self, url: str = None, model: str = None):
        """Initialize Ollama LLM client"""
        self.ollama_client = OllamaClient(url or OLLAMA_URL, model)
        return True

    @keyword("Initialize TTS Client")
    def initialize_tts_client(self, url: str = None):
        """Initialize Piper TTS client"""
        self.piper_client = PiperTTSClient(url or PIPER_URL)
        return True

    @keyword("Initialize All Clients")
    def initialize_all_clients(self):
        """Initialize all API clients"""
        self.initialize_stt_client()
        self.initialize_llm_client()
        self.initialize_tts_client()
        return True

    @keyword("Check STT Service Health")
    def check_stt_health(self):
        """Check if STT service is healthy"""
        if not self.whisper_client:
            self.initialize_stt_client()
        return self.whisper_client.connect()

    @keyword("Check LLM Service Health")
    def check_llm_health(self):
        """Check if LLM service is healthy"""
        if not self.ollama_client:
            self.initialize_llm_client()
        result = self.ollama_client.health_check()
        if not result:
            raise AssertionError("Ollama LLM service is not healthy")
        return result

    @keyword("Check TTS Service Health")
    def check_tts_health(self):
        """Check if TTS service is healthy"""
        if not self.piper_client:
            self.initialize_tts_client()
        result = self.piper_client.health_check()
        if not result:
            raise AssertionError("Piper TTS service is not healthy")
        return result

    @keyword("Check All Services Health")
    def check_all_services_health(self):
        """Check health of all services"""
        results = {}
        try:
            results['llm'] = self.check_llm_health()
        except Exception as e:
            results['llm'] = False
            logger.error(f"LLM health check failed: {e}")

        try:
            results['tts'] = self.check_tts_health()
        except Exception as e:
            results['tts'] = False
            logger.error(f"TTS health check failed: {e}")

        return results

    @keyword("Transcribe Audio File")
    def transcribe_audio_file(self, audio_path: str, language: str = "en",
                             timeout: str = "15") -> str:
        """Transcribe audio file using STT"""
        if not self.whisper_client:
            self.initialize_stt_client()

        if not self.whisper_client.connect(language=language):
            raise AssertionError("Failed to connect to STT service")

        if not self.whisper_client.send_audio_file(audio_path):
            raise AssertionError(f"Failed to send audio file: {audio_path}")

        result = self.whisper_client.get_transcription(float(timeout))
        self.whisper_client.disconnect()

        if not result:
            raise AssertionError("No transcription received")
        return result

    @keyword("Generate LLM Response")
    def generate_llm_response(self, prompt: str,
                             system_prompt: str = None) -> str:
        """Generate response from LLM"""
        if not self.ollama_client:
            self.initialize_llm_client()

        response = self.ollama_client.generate(prompt, system=system_prompt)
        if not response:
            raise AssertionError("Failed to generate LLM response")
        return response

    @keyword("Validate LLM Response Contains")
    def validate_llm_response_contains(self, response: str, *keywords):
        """Validate LLM response contains any of the keywords"""
        if not self.ollama_client:
            self.initialize_llm_client()

        keywords_list = list(keywords)
        if not self.ollama_client.validate_response(response, keywords_list):
            raise AssertionError(
                f"Response does not contain any of: {keywords_list}"
            )
        return True

    @keyword("Synthesize Speech")
    def synthesize_speech(self, text: str, output_path: str = None) -> str:
        """Synthesize text to speech"""
        if not self.piper_client:
            self.initialize_tts_client()

        result = self.piper_client.synthesize(text, output_path=output_path)
        if not result:
            raise AssertionError(f"Failed to synthesize: {text}")
        return result.audio_path

    @keyword("Synthesize Speech In Language")
    def synthesize_speech_in_language(self, text: str, language: str,
                                      output_path: str = None) -> str:
        """Synthesize text in specific language"""
        if not self.piper_client:
            self.initialize_tts_client()

        result = self.piper_client.synthesize_multilingual(
            text, language, output_path
        )
        if not result:
            raise AssertionError(f"Failed to synthesize in {language}: {text}")
        return result.audio_path

    @keyword("Clear LLM Conversation History")
    def clear_llm_history(self):
        """Clear LLM conversation history"""
        if self.ollama_client:
            self.ollama_client.clear_history()
        return True

    @keyword("Get LLM Response Time")
    def get_llm_response_time(self) -> float:
        """Get response time of last LLM call in ms"""
        if not self.ollama_client:
            return 0
        metrics = self.ollama_client.get_last_response_metrics()
        return metrics.get('total_duration_ms', 0)

    @keyword("Get TTS Synthesis Time")
    def get_tts_synthesis_time(self) -> float:
        """Get synthesis time of last TTS call in ms"""
        if not self.piper_client:
            return 0
        metrics = self.piper_client.get_synthesis_metrics()
        return metrics.get('synthesis_time_ms', 0)

    @keyword("Cleanup API Clients")
    def cleanup_api_clients(self):
        """Cleanup all API clients"""
        if self.whisper_client:
            self.whisper_client.disconnect()
        if self.piper_client:
            self.piper_client.cleanup()
        return True
