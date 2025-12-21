#!/usr/bin/env python3
"""
Standalone Command-Line Voice Agent for LiveKit
Supports multiple languages: English, Hindi, Kannada, Marathi
"""
import argparse
import asyncio
import json
import logging
import sys
import time
import os
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import httpx

try:
    import websockets
except ImportError:
    print("Please install websockets: pip install websockets")
    sys.exit(1)

try:
    import soundfile as sf
    import numpy as np
except ImportError:
    print("Please install soundfile and numpy: pip install soundfile numpy")
    sys.exit(1)

# Configuration
PIPER_URL = os.getenv("PIPER_URL", "http://192.168.20.62:5500")
WHISPER_WS_URL = os.getenv("WHISPER_WS_URL", "ws://192.168.1.120:8765/")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.1.120:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Language configurations
LANGUAGE_CONFIG = {
    "en": {"name": "English", "voice": "en_US-lessac-medium"},
    "hi": {"name": "Hindi", "voice": "hi_IN-default-medium"},
    "kn": {"name": "Kannada", "voice": "kn_IN-default-medium"},
    "mr": {"name": "Marathi", "voice": "mr_IN-default-medium"},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VoiceAgent:
    """Command-line voice agent"""

    def __init__(self, language: str = "en"):
        self.language = language
        self.conversation_history = []
        self.audio_sample_rate = 16000

    async def synthesize_speech(self, text: str) -> Optional[bytes]:
        """Synthesize text to speech using Piper TTS"""
        try:
            voice = LANGUAGE_CONFIG.get(self.language, {}).get(
                "voice", "en_US-lessac-medium"
            )

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{PIPER_URL}/api/synthesize/stream",
                    json={
                        "text": text,
                        "voice": voice,
                        "sample_rate": self.audio_sample_rate
                    }
                )

                if response.status_code == 200:
                    logger.info(f"TTS synthesized: {len(text)} chars")
                    return response.content
                else:
                    logger.error(f"TTS error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None

    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio using WhisperLiveKit"""
        try:
            # Read audio file
            data, sample_rate = sf.read(audio_path, dtype='int16')

            # Connect to WebSocket
            async with websockets.connect(WHISPER_WS_URL, ping_timeout=10) as ws:
                # Send config
                config = {
                    "uid": f"agent-{int(time.time())}",
                    "language": self.language,
                    "model": "small",
                    "use_vad": True
                }
                await ws.send(json.dumps(config))

                # Send audio
                chunk_size = 4096
                audio_bytes = data.tobytes()
                for i in range(0, len(audio_bytes), chunk_size):
                    await ws.send(audio_bytes[i:i + chunk_size])
                    await asyncio.sleep(0.01)

                # Wait for transcription
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10)
                    result = json.loads(response)

                    if "segments" in result:
                        texts = [s.get("text", "") for s in result["segments"]]
                        return " ".join(texts).strip()
                    elif "text" in result:
                        return result["text"].strip()

                except asyncio.TimeoutError:
                    logger.warning("Transcription timeout")

            return None

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    async def generate_response(self, user_input: str) -> Optional[str]:
        """Generate response using Ollama LLM"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"You are a helpful voice assistant. Respond naturally and concisely. Current language: {LANGUAGE_CONFIG.get(self.language, {}).get('name', 'English')}"
                }
            ]

            # Add conversation history
            messages.extend(self.conversation_history)

            # Add user message
            messages.append({"role": "user", "content": user_input})

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": messages,
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("message", {}).get("content", "")

                    # Update history
                    self.conversation_history.append(
                        {"role": "user", "content": user_input}
                    )
                    self.conversation_history.append(
                        {"role": "assistant", "content": content}
                    )

                    return content
                else:
                    logger.error(f"LLM error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None

    async def speak(self, text: str) -> bool:
        """Speak text using TTS"""
        print(f"\n[Agent ({LANGUAGE_CONFIG.get(self.language, {}).get('name', 'English')})]: {text}")

        audio_data = await self.synthesize_speech(text)
        if audio_data:
            # Save to temp file
            temp_path = f"/tmp/agent_speech_{int(time.time())}.wav"
            with open(temp_path, 'wb') as f:
                f.write(audio_data)
            logger.info(f"Audio saved: {temp_path}")
            return True
        return False

    async def listen(self, audio_path: str) -> Optional[str]:
        """Listen and transcribe audio"""
        transcription = await self.transcribe_audio(audio_path)
        if transcription:
            print(f"\n[User]: {transcription}")
            return transcription
        return None

    async def converse(self, user_input: str) -> Optional[str]:
        """Have a conversation turn"""
        print(f"\n[User]: {user_input}")

        response = await self.generate_response(user_input)
        if response:
            await self.speak(response)
            return response
        return None

    async def run_interactive(self):
        """Run interactive conversation mode"""
        print(f"\n=== Voice Agent - {LANGUAGE_CONFIG.get(self.language, {}).get('name', 'English')} ===")
        print("Type your message or 'quit' to exit\n")

        while True:
            try:
                user_input = input("[You]: ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                response = await self.generate_response(user_input)
                if response:
                    print(f"[Agent]: {response}")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                break

    def set_language(self, language: str):
        """Set agent language"""
        if language in LANGUAGE_CONFIG:
            self.language = language
            logger.info(f"Language set to: {LANGUAGE_CONFIG[language]['name']}")
        else:
            logger.warning(f"Unknown language: {language}")

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")


async def main():
    parser = argparse.ArgumentParser(
        description="Voice Agent CLI - Multi-language support"
    )
    parser.add_argument(
        "--action",
        choices=["speak", "listen", "converse", "interactive"],
        default="interactive",
        help="Action to perform"
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Text to speak or process"
    )
    parser.add_argument(
        "--audio",
        type=str,
        help="Audio file to transcribe"
    )
    parser.add_argument(
        "--lang",
        choices=["en", "hi", "kn", "mr"],
        default="en",
        help="Language code (en=English, hi=Hindi, kn=Kannada, mr=Marathi)"
    )
    parser.add_argument(
        "--room",
        type=str,
        help="LiveKit room name (for future use)"
    )

    args = parser.parse_args()

    agent = VoiceAgent(language=args.lang)

    if args.action == "speak":
        if not args.text:
            print("Error: --text required for speak action")
            return
        await agent.speak(args.text)

    elif args.action == "listen":
        if not args.audio:
            print("Error: --audio required for listen action")
            return
        result = await agent.listen(args.audio)
        if result:
            print(f"Transcription: {result}")

    elif args.action == "converse":
        if not args.text:
            print("Error: --text required for converse action")
            return
        response = await agent.converse(args.text)
        if response:
            print(f"Response: {response}")

    elif args.action == "interactive":
        await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
