"""
Ollama LLM Plugin for LiveKit Agents (OpenAI-Compatible)

This module provides integration with Ollama using OpenAI-compatible API.
Ollama supports the OpenAI API format, allowing us to use LiveKit's
OpenAI plugin with a custom base URL.

Based on:
- https://docs.livekit.io/agents/plugins/overview/
- Ollama OpenAI compatibility: https://ollama.com/blog/openai-compatibility
"""

import logging
import os

from livekit.plugins import openai

logger = logging.getLogger(__name__)


def create_ollama_llm(
    model: str = "llama3.1:8b",
    base_url: str = "http://192.168.1.120:11434",
    temperature: float = 0.7,
    **kwargs,
) -> openai.LLM:
    """
    Create Ollama LLM using OpenAI-compatible API.

    Ollama provides an OpenAI-compatible API endpoint at /v1.
    We can use LiveKit's OpenAI plugin by simply overriding the base URL.

    Args:
        model: Ollama model name (e.g., "llama3.1", "mistral", "mixtral")
               Note: The model must be pulled first: `ollama pull <model>`
        base_url: Ollama server URL (without /v1 suffix)
        temperature: Sampling temperature (0.0 to 1.0)
        **kwargs: Additional arguments passed to openai.LLM

    Returns:
        OpenAI LLM instance configured for Ollama

    Example:
        >>> llm = create_ollama_llm(
        ...     model="llama3.1",
        ...     base_url="http://192.168.1.120:11434"
        ... )

    Note:
        Make sure Ollama is running and the model is pulled:
        ```
        ollama serve
        ollama pull llama3.1
        ```
    """
    # Ollama's OpenAI-compatible endpoint is at /v1
    ollama_api_url = f"{base_url.rstrip('/')}/v1"

    logger.info(f"Creating Ollama LLM: model={model}, url={ollama_api_url}")

    try:
        # Create OpenAI LLM with Ollama endpoint
        llm = openai.LLM(
            model=model,
            base_url=ollama_api_url,
            api_key="ollama",  # Ollama doesn't require a real API key
            temperature=temperature,
            **kwargs,
        )

        logger.info(f"Ollama LLM created successfully: {model}")
        return llm

    except Exception as e:
        logger.error(f"Failed to create Ollama LLM: {e}")
        raise


def validate_ollama_connection(base_url: str = "http://localhost:11434") -> bool:
    """
    Validate connection to Ollama server.

    Args:
        base_url: Ollama server URL

    Returns:
        True if connection is successful, False otherwise
    """
    import httpx

    try:
        # Check if Ollama is running
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        response.raise_for_status()

        models = response.json().get("models", [])
        logger.info(
            f"Ollama server connected. Available models: {len(models)}")

        for model in models:
            logger.info(f"  - {model['name']}")

        return True

    except Exception as e:
        logger.error(f"Failed to connect to Ollama: {e}")
        return False


def list_ollama_models(base_url: str = "http://localhost:11434") -> list:
    """
    List available Ollama models.

    Args:
        base_url: Ollama server URL

    Returns:
        List of model names
    """
    import httpx

    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        response.raise_for_status()

        models = response.json().get("models", [])
        return [model["name"] for model in models]

    except Exception as e:
        logger.error(f"Failed to list Ollama models: {e}")
        return []


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Get Ollama URL from environment or use default
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # Validate connection
    logger.info(f"Validating Ollama connection: {ollama_url}")
    if validate_ollama_connection(ollama_url):
        logger.info("Ollama connection successful")

        # List available models
        models = list_ollama_models(ollama_url)
        if models:
            logger.info(f"Available models: {models}")

            # Create LLM instance
            try:
                llm = create_ollama_llm(
                    model=models[0],  # Use first available model
                    base_url=ollama_url,
                )
                logger.info("Ollama LLM created successfully")
            except Exception as e:
                logger.error(f"Failed to create LLM: {e}")
        else:
            logger.warning("No Ollama models found. Pull a model first:")
            logger.warning("  ollama pull llama3.1")
    else:
        logger.error("Ollama connection failed. Make sure Ollama is running:")
        logger.error("  ollama serve")
