"""
LiveKit AI Voice Agent Worker - 100% Local Open-Source Implementation

Based on official LiveKit v1.x documentation with custom STT/TTS nodes:
- https://docs.livekit.io/agents/build/nodes
- https://docs.livekit.io/agents/build/sessions

This implementation uses:
- WhisperLive (local STT) via custom stt_node
- Piper TTS (local) via custom tts_node
- Ollama (local LLM) via official plugin
- Silero VAD (local)
- NO cloud services, NO API keys required
"""

import asyncio
import json
import logging
import os
from typing import AsyncIterable, Optional
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, AgentServer, ModelSettings
from livekit.agents import stt, tts
from livekit.plugins import openai, silero

# Import local service handlers
from .stt_handler import WhisperLiveSTT
from .tts_handler import PiperTTSClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrinityAssistant(Agent):
    """
    AI Assistant for Trinity Smart City Platform - 100% Local Implementation.

    This agent uses custom STT/TTS nodes to integrate with local services:
    - STT: WhisperLive (local WebSocket server)
    - TTS: Piper (local HTTP server)
    - LLM: Ollama (local inference server)
    """

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful AI assistant for the Trinity smart city platform.
You help users with information about city services, weather, transportation, and general inquiries.
Keep your responses concise and natural for voice conversation.
Speak in a friendly, conversational tone.
Avoid lengthy explanations unless specifically asked."""
        )
        logger.info("TrinityAssistant initialized with local STT/TTS/LLM")

    async def stt_node(
        self,
        audio: AsyncIterable[rtc.AudioFrame],
        model_settings: ModelSettings
    ) -> Optional[AsyncIterable[stt.SpeechEvent]]:
        """
        Custom STT node using local WhisperLive service.

        This overrides the default STT behavior to use our local WhisperLive server
        instead of cloud-based STT services.
        """
        logger.info("Using local WhisperLive STT service")

        # Create WhisperLive STT instance
        whisperlive_host = os.getenv("WHISPERLIVE_HOST", "whisperlive")
        whisperlive_port = int(os.getenv("WHISPERLIVE_PORT", "9090"))

        whisper_stt = WhisperLiveSTT(
            host=whisperlive_host,
            port=whisperlive_port,
            lang="en",
            model="small",
        )

        # Create STT stream
        stt_stream = whisper_stt.stream()

        # Start the stream processing
        async def process_audio():
            """Push audio frames to WhisperLive"""
            async for frame in audio:
                await stt_stream.push_frame(frame)
            await stt_stream.flush()

        # Run audio processing in background
        asyncio.create_task(process_audio())

        # Return the speech events stream
        return stt_stream

    async def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        """
        Custom TTS node using local Piper service.

        This overrides the default TTS behavior to use our local Piper server
        instead of cloud-based TTS services.
        """
        logger.info("Using local Piper TTS service")

        # Create Piper TTS client
        piper_url = os.getenv("PIPER_URL", "http://piper-tts:5500")
        piper_client = PiperTTSClient(
            base_url=piper_url,
            voice="en_US-lessac-medium",
        )

        # Process text chunks and synthesize audio
        async for text_chunk in text:
            if text_chunk.strip():
                logger.debug(f"Synthesizing: '{text_chunk[:50]}...'")

                try:
                    # Get audio from Piper
                    audio_data = await piper_client.synthesize(text_chunk)

                    # Convert audio bytes to AudioFrame
                    # Piper returns raw PCM audio at 22050 Hz
                    import numpy as np

                    # Convert bytes to int16 array
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)

                    # Create audio frame
                    frame = rtc.AudioFrame(
                        data=audio_array.tobytes(),
                        sample_rate=22050,
                        num_channels=1,
                        samples_per_channel=len(audio_array),
                    )

                    yield frame

                except Exception as e:
                    logger.error(f"TTS synthesis error: {e}")
                    continue


# Create agent server
server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    """
    Main entry point for the AI voice agent.

    This function is called when:
    1. A new room is created
    2. A participant joins (including SIP callers)
    3. Agent dispatch rules trigger
    """
    logger.info(f"="*80)
    logger.info(f"Agent entrypoint called for room: {ctx.room.name}")
    logger.info(f"="*80)

    try:
        # Get configuration from environment
        ollama_url = os.getenv("OLLAMA_URL", "http://192.168.1.120:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        whisperlive_host = os.getenv("WHISPERLIVE_HOST", "whisperlive")
        whisperlive_port = os.getenv("WHISPERLIVE_PORT", "9090")
        piper_url = os.getenv("PIPER_URL", "http://piper-tts:5500")

        logger.info(f"Configuration (100% Local):")
        logger.info(f"  - Ollama LLM: {ollama_url} (model: {ollama_model})")
        logger.info(f"  - WhisperLive STT: {whisperlive_host}:{whisperlive_port}")
        logger.info(f"  - Piper TTS: {piper_url}")
        logger.info(f"  - Silero VAD: local")

        # Create AgentSession with Ollama LLM
        # Note: STT and TTS are handled by custom nodes in TrinityAssistant
        session = AgentSession(
            # Use Ollama for LLM via official method
            llm=openai.LLM.with_ollama(
                model=ollama_model,
                base_url=f"{ollama_url}/v1",
            ),
            # VAD is still set here for the pipeline
            vad=silero.VAD.load(),
            # Note: We don't set stt/tts here because they're handled by custom nodes
        )

        logger.info("✓ AgentSession created with local Ollama LLM")

        # Set up room event handlers
        @ctx.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(
                f"🔵 Participant connected: {participant.identity} (SID: {participant.sid})")
            logger.info(f"   - Kind: {participant.kind}")

            # Check if this is a SIP caller
            if hasattr(participant, 'kind') and str(participant.kind) == "ParticipantKind.PARTICIPANT_KIND_SIP":
                logger.info("📞 SIP caller detected - agent will respond to their audio")

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"🔴 Participant disconnected: {participant.identity}")

        # Set up session event handlers
        @session.on("user_input_transcribed")
        def on_user_transcript(transcript):
            """Handle user speech transcription."""
            if transcript.is_final:
                text = transcript.transcript
                logger.info(f"👤 USER SAID: '{text}'")

        @session.on("conversation_item_added")
        def on_conversation_item(item):
            """Handle conversation items (user and agent messages)."""
            logger.info(f"💬 Conversation item added:")
            logger.info(f"   - Role: {item.role}")
            if hasattr(item, 'content') and item.content:
                content_preview = item.content[:100] if len(item.content) > 100 else item.content
                logger.info(f"   - Content: {content_preview}")

        @session.on("agent_state_changed")
        def on_agent_state(state):
            """Handle agent state changes."""
            logger.info(f"🤖 Agent state changed: {state}")

        @session.on("user_state_changed")
        def on_user_state(state):
            """Handle user state changes."""
            logger.info(f"👤 User state changed: {state}")

        # Create the agent instance (with custom STT/TTS nodes)
        logger.info("Creating TrinityAssistant agent with custom nodes...")
        agent = TrinityAssistant()
        logger.info("✓ TrinityAssistant agent created")

        # Start the agent session
        logger.info("Starting agent session...")
        await session.start(
            agent=agent,
            room=ctx.room
        )

        logger.info("="*80)
        logger.info("✓ AGENT SESSION STARTED SUCCESSFULLY")
        logger.info("  The agent is now listening for user input...")
        logger.info("  Pipeline: Audio → VAD → STT (WhisperLive) → LLM (Ollama) → TTS (Piper) → Audio")
        logger.info("  ALL SERVICES ARE LOCAL - NO CLOUD DEPENDENCIES")
        logger.info("="*80)

        # Generate initial greeting
        logger.info("Generating initial greeting...")
        await session.generate_reply(
            instructions="Greet the user warmly and offer your assistance."
        )
        logger.info("✓ Greeting generated")

    except Exception as e:
        logger.error("="*80)
        logger.error(f"✗ ERROR IN AGENT ENTRYPOINT: {e}")
        logger.error("="*80)
        logger.exception("Full traceback:")
        raise


if __name__ == "__main__":
    logger.info("Starting LiveKit AI Agent Worker (100% Local)...")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL', 'not set')}")
    logger.info(f"Ollama URL: {os.getenv('OLLAMA_URL', 'not set')}")
    logger.info(f"WhisperLive: {os.getenv('WHISPERLIVE_HOST', 'whisperlive')}:{os.getenv('WHISPERLIVE_PORT', '9090')}")
    logger.info(f"Piper TTS: {os.getenv('PIPER_URL', 'not set')}")

    # Run the agent with AgentServer pattern (v1.x)
    agents.cli.run_app(server)
