"""
LiveKit AI Voice Agent Worker (Fixed Implementation)

This implementation follows LiveKit Agents 1.x patterns from:
- https://docs.livekit.io/agents/start/voice-ai
- https://github.com/livekit-examples/python-agents-examples/tree/main/basics

Key fixes:
1. Correct event handler names: user_input_transcribed, conversation_item_added
2. Proper Agent initialization with custom STT/LLM/TTS plugins
3. Comprehensive logging at each pipeline stage
4. Correct session lifecycle management
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import silero

# Import custom handlers
from .stt_handler import create_whisperlive_stt
from .llm_handler import create_ollama_llm
from .tts_handler import create_piper_tts

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
    AI Assistant for Trinity Smart City Platform.

    This agent handles voice conversations through the LiveKit Agents pipeline:
    VAD → STT (WhisperLive) → LLM (Ollama) → TTS (Piper)
    """

    def __init__(self, stt, llm, tts, vad) -> None:
        """Initialize the Trinity assistant with custom plugins."""
        super().__init__(
            instructions="""You are a helpful AI assistant for the Trinity smart city platform.
            You help users with information about city services, weather, transportation, and general inquiries.
            Keep your responses concise and natural for voice conversation.
            Speak in a friendly, conversational tone.
            Avoid lengthy explanations unless specifically asked.""",
            stt=stt,
            llm=llm,
            tts=tts,
            vad=vad,
        )
        logger.info("TrinityAssistant initialized with custom STT/LLM/TTS plugins")

    async def on_enter(self):
        """Called when the agent becomes active in a session."""
        logger.info("Agent entered session - generating greeting")
        try:
            await self.session.generate_reply(
                instructions="Greet the user warmly and offer your assistance."
            )
            logger.info("Greeting generated successfully")
        except Exception as e:
            logger.error(f"Error generating greeting: {e}", exc_info=True)


async def entrypoint(ctx: JobContext):
    """
    Main entry point for the AI voice agent.

    This function is called when:
    1. A new room is created
    2. A participant joins (including SIP callers)
    3. Agent dispatch rules trigger

    Args:
        ctx: JobContext containing room information and connection details
    """
    logger.info(f"="*80)
    logger.info(f"Agent entrypoint called for room: {ctx.room.name}")
    logger.info(f"="*80)

    try:
        # Initialize custom plugins
        logger.info("Initializing AI pipeline components...")

        # Get configuration from environment
        whisperlive_host = os.getenv("WHISPERLIVE_HOST", "whisperlive")
        whisperlive_port = int(os.getenv("WHISPERLIVE_PORT", "9090"))
        ollama_url = os.getenv("OLLAMA_URL", "http://192.168.1.120:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
        piper_url = os.getenv("PIPER_URL", "http://piper-tts:5500")

        logger.info(f"Configuration:")
        logger.info(f"  - WhisperLive: {whisperlive_host}:{whisperlive_port}")
        logger.info(f"  - Ollama: {ollama_url} (model: {ollama_model})")
        logger.info(f"  - Piper TTS: {piper_url}")

        # Create STT plugin (WhisperLive)
        logger.info("Creating WhisperLive STT plugin...")
        stt_provider = create_whisperlive_stt(
            host=whisperlive_host,
            port=whisperlive_port,
            lang="en",
            model="small",
            use_vad=True,
        )
        logger.info("✓ WhisperLive STT plugin created")

        # Create LLM plugin (Ollama via OpenAI-compatible API)
        logger.info("Creating Ollama LLM plugin...")
        llm = create_ollama_llm(
            model=ollama_model,
            base_url=ollama_url,
        )
        logger.info("✓ Ollama LLM plugin created")

        # Create TTS plugin (Piper)
        logger.info("Creating Piper TTS plugin...")
        tts = create_piper_tts(
            base_url=piper_url,
            voice="en_US-lessac-medium",
        )
        logger.info("✓ Piper TTS plugin created")

        # Create VAD
        logger.info("Loading Silero VAD...")
        vad = silero.VAD.load()
        logger.info("✓ Silero VAD loaded")

        # Create the agent session
        logger.info("Creating AgentSession...")
        session = AgentSession()
        logger.info("✓ AgentSession created")

        # Set up room event handlers
        @ctx.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"🔵 Participant connected: {participant.identity} (SID: {participant.sid})")
            logger.info(f"   - Kind: {participant.kind}")
            logger.info(f"   - Tracks: {len(participant.track_publications)}")

            # Check if this is a SIP caller
            if hasattr(participant, 'kind') and str(participant.kind) == "ParticipantKind.PARTICIPANT_KIND_SIP":
                logger.info("📞 SIP caller detected - agent will respond to their audio")

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"🔴 Participant disconnected: {participant.identity}")

        # Set up session event handlers with correct names
        @session.on("user_input_transcribed")
        def on_user_transcript(transcript):
            """Handle user speech transcription."""
            if transcript.is_final:
                text = transcript.transcript
                logger.info(f"👤 USER SAID: '{text}'")
                logger.info(f"   - Is final: {transcript.is_final}")

                # Publish transcript to room via data channel
                try:
                    transcript_data = json.dumps({
                        "type": "transcript",
                        "speaker": "user",
                        "text": text,
                        "timestamp": datetime.utcnow().isoformat(),
                        "is_final": transcript.is_final
                    })

                    ctx.room.local_participant.publish_data(
                        payload=transcript_data.encode("utf-8"),
                        topic="transcripts",
                    )
                    logger.debug("✓ User transcript published to room")
                except Exception as e:
                    logger.error(f"✗ Failed to publish user transcript: {e}")

        @session.on("conversation_item_added")
        def on_conversation_item(item):
            """Handle conversation items (user and agent messages)."""
            logger.info(f"💬 Conversation item added:")
            logger.info(f"   - Role: {item.role}")
            logger.info(f"   - Content: {item.content[:100] if len(item.content) > 100 else item.content}")

            # If this is an agent response, publish it
            if item.role == "assistant":
                try:
                    transcript_data = json.dumps({
                        "type": "transcript",
                        "speaker": "agent",
                        "text": item.content,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                    ctx.room.local_participant.publish_data(
                        payload=transcript_data.encode("utf-8"),
                        topic="transcripts",
                    )
                    logger.debug("✓ Agent transcript published to room")
                except Exception as e:
                    logger.error(f"✗ Failed to publish agent transcript: {e}")

        @session.on("agent_state_changed")
        def on_agent_state(state):
            """Handle agent state changes."""
            logger.info(f"🤖 Agent state changed: {state}")

        @session.on("user_state_changed")
        def on_user_state(state):
            """Handle user state changes."""
            logger.info(f"👤 User state changed: {state}")

        # Create and start the agent
        logger.info("Creating TrinityAssistant agent...")
        agent = TrinityAssistant(
            stt=stt_provider,
            llm=llm,
            tts=tts,
            vad=vad,
        )
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
        logger.info("="*80)

    except Exception as e:
        logger.error("="*80)
        logger.error(f"✗ ERROR IN AGENT ENTRYPOINT: {e}")
        logger.error("="*80)
        logger.exception("Full traceback:")
        raise


if __name__ == "__main__":
    logger.info("Starting LiveKit AI Agent Worker...")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL', 'not set')}")
    logger.info(f"Ollama URL: {os.getenv('OLLAMA_URL', 'not set')}")
    logger.info(f"WhisperLive: {os.getenv('WHISPERLIVE_HOST', 'whisperlive')}:{os.getenv('WHISPERLIVE_PORT', '9090')}")
    logger.info(f"Piper TTS: {os.getenv('PIPER_URL', 'not set')}")

    # Run the agent with WorkerOptions pattern
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
