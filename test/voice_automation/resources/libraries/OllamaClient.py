"""
Ollama LLM Client for validating AI responses
"""
import json
import logging
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

try:
    import httpx
except ImportError:
    httpx = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import OLLAMA_URL, OLLAMA_MODEL, RESPONSE_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from Ollama LLM"""
    text: str
    model: str
    done: bool
    total_duration: int = 0
    load_duration: int = 0
    prompt_eval_count: int = 0
    eval_count: int = 0
    eval_duration: int = 0


class OllamaClient:
    """Client for Ollama LLM service"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or OLLAMA_URL).rstrip('/')
        self.model = model or OLLAMA_MODEL
        self.conversation_history: List[Dict[str, str]] = []
        self.last_response: Optional[LLMResponse] = None

    def health_check(self) -> bool:
        """Check if Ollama is healthy and model is available"""
        try:
            if httpx:
                with httpx.Client(timeout=10) as client:
                    response = client.get(f"{self.base_url}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        models = [m['name'] for m in data.get('models', [])]
                        return any(self.model in m for m in models)
            return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def generate(self, prompt: str, system: str = None, stream: bool = False) -> Optional[str]:
        """Generate response from Ollama"""
        try:
            messages = []

            if system:
                messages.append({"role": "system", "content": system})

            # Add conversation history
            messages.extend(self.conversation_history)

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "stream": stream
            }

            if httpx:
                with httpx.Client(timeout=RESPONSE_TIMEOUT * 2) as client:
                    response = client.post(
                        f"{self.base_url}/api/chat",
                        json=payload
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data.get("message", {}).get("content", "")

                        self.last_response = LLMResponse(
                            text=content,
                            model=self.model,
                            done=data.get("done", True),
                            total_duration=data.get("total_duration", 0),
                            eval_count=data.get("eval_count", 0),
                            eval_duration=data.get("eval_duration", 0)
                        )

                        # Update conversation history
                        self.conversation_history.append({"role": "user", "content": prompt})
                        self.conversation_history.append({"role": "assistant", "content": content})

                        return content
                    else:
                        logger.error(f"Ollama error: {response.status_code} - {response.text}")

            return None

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return None

    def validate_response(self, response: str, expected_keywords: List[str],
                         match_any: bool = True) -> bool:
        """Validate response contains expected keywords"""
        if not response:
            return False

        response_lower = response.lower()

        if match_any:
            return any(kw.lower() in response_lower for kw in expected_keywords)
        else:
            return all(kw.lower() in response_lower for kw in expected_keywords)

    def validate_conversation_context(self, prompt: str, context_keywords: List[str]) -> bool:
        """Validate LLM maintains conversation context"""
        # Generate response that should include context
        response = self.generate(prompt)

        if not response:
            return False

        return self.validate_response(response, context_keywords, match_any=True)

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get current conversation history"""
        return self.conversation_history.copy()

    def get_last_response_metrics(self) -> Dict[str, Any]:
        """Get metrics from last response"""
        if not self.last_response:
            return {}

        return {
            "text_length": len(self.last_response.text),
            "total_duration_ms": self.last_response.total_duration / 1_000_000,
            "eval_count": self.last_response.eval_count,
            "tokens_per_second": (
                self.last_response.eval_count / (self.last_response.eval_duration / 1_000_000_000)
                if self.last_response.eval_duration > 0 else 0
            )
        }

    # Robot Framework Keywords
    def check_ollama_health(self) -> bool:
        """Robot Framework keyword to check Ollama health"""
        result = self.health_check()
        if not result:
            raise AssertionError(f"Ollama not healthy or model {self.model} not available")
        return result

    def generate_llm_response(self, prompt: str, system_prompt: str = None) -> str:
        """Robot Framework keyword to generate LLM response"""
        response = self.generate(prompt, system=system_prompt)
        if not response:
            raise AssertionError("Failed to generate LLM response")
        return response

    def response_should_contain(self, response: str, *keywords):
        """Robot Framework keyword to validate response contains keywords"""
        keywords_list = list(keywords)
        if not self.validate_response(response, keywords_list, match_any=True):
            raise AssertionError(
                f"Response does not contain any of: {keywords_list}\nResponse: {response}"
            )
        return True

    def response_should_contain_all(self, response: str, *keywords):
        """Robot Framework keyword to validate response contains all keywords"""
        keywords_list = list(keywords)
        if not self.validate_response(response, keywords_list, match_any=False):
            raise AssertionError(
                f"Response does not contain all of: {keywords_list}\nResponse: {response}"
            )
        return True

    def clear_llm_history(self):
        """Robot Framework keyword to clear conversation history"""
        self.clear_history()

    def get_response_time(self) -> float:
        """Robot Framework keyword to get last response time in ms"""
        metrics = self.get_last_response_metrics()
        return metrics.get("total_duration_ms", 0)
