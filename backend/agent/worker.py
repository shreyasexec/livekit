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
            instructions="""You are Trinity, a friendly and conversational AI voice assistant.

## Your Personality:
- Warm, enthusiastic, and personable - like talking to a helpful friend
- Natural and casual in speech - use contractions, conversational phrases
- Genuinely curious about the user's needs and eager to help
- Keep responses SHORT and conversational (1-3 sentences max)
- Speak like a real person, not a formal assistant

## How to Respond:
- Start with natural acknowledgments: "Sure!", "Got it!", "Absolutely!", "Of course!"
- Use casual language: "Hey", "Yeah", "Cool", "Awesome", instead of formal phrases
- Ask follow-up questions to keep the conversation flowing
- Mirror the user's energy and tone
- If you don't know something, be honest: "Hmm, I'm not sure about that one"

## What to Avoid:
- NO long-winded explanations or lists unless specifically asked
- NO formal language like "I would be happy to assist you"
- NO robotic phrases like "As an AI assistant"
- Don't apologize unless truly necessary
- Keep it natural and brief!

## Examples of Good Responses:
User: "What's the weather?"
You: "Let me check that for you! What city are you in?"

User: "Tell me about city services"
You: "Sure thing! We've got lots of services available. What are you looking for specifically - transportation, utilities, or something else?"

Remember: You're having a CONVERSATION, not giving a presentation. Keep it short, natural, and engaging!"""
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
        Custom TTS node using local Piper service with sentence buffering.

        This buffers text chunks into complete sentences before synthesizing,
        which dramatically reduces latency and creates more natural speech flow.
        """
        logger.info("Using local Piper TTS service")

        # Create Piper TTS client
        piper_url = os.getenv("PIPER_URL", "http://piper-tts:5500")
        piper_client = PiperTTSClient(
            base_url=piper_url,
            voice="en_US-lessac-medium",
        )

        import numpy as np
        import re

        # Sentence delimiters
        sentence_endings = re.compile(r'[.!?]\s*')

        # Buffer for accumulating text
        buffer = ""

        # Process text chunks and buffer into sentences
        async for text_chunk in text:
            if not text_chunk.strip():
                continue

            buffer += text_chunk

            # Check if we have complete sentences
            sentences = sentence_endings.split(buffer)

            # If we have complete sentences (more than one part after split)
            if len(sentences) > 1:
                # Process all complete sentences
                for sentence in sentences[:-1]:
                    sentence = sentence.strip()
                    if sentence:
                        logger.debug(f"Synthesizing sentence: '{sentence[:50]}...'")

                        try:
                            # Get audio from Piper for the full sentence
                            audio_data = await piper_client.synthesize(sentence + ".")

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

                # Keep the incomplete sentence in buffer
                buffer = sentences[-1]

            # If buffer gets too long (> 200 chars), flush it anyway to avoid delays
            elif len(buffer) > 200:
                logger.debug(f"Flushing long buffer: '{buffer[:50]}...'")
                try:
                    audio_data = await piper_client.synthesize(buffer)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    frame = rtc.AudioFrame(
                        data=audio_array.tobytes(),
                        sample_rate=22050,
                        num_channels=1,
                        samples_per_channel=len(audio_array),
                    )
                    yield frame
                    buffer = ""
                except Exception as e:
                    logger.error(f"TTS synthesis error: {e}")
                    buffer = ""

        # Flush any remaining text in buffer
        if buffer.strip():
            logger.debug(f"Flushing final buffer: '{buffer[:50]}...'")
            try:
                audio_data = await piper_client.synthesize(buffer)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                frame = rtc.AudioFrame(
                    data=audio_array.tobytes(),
                    sample_rate=22050,
                    num_channels=1,
                    samples_per_channel=len(audio_array),
                )
                yield frame
            except Exception as e:
                logger.error(f"TTS synthesis error: {e}")


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
            """Handle user speech transcription and send to UI."""
            if transcript.is_final:
                text = transcript.transcript
                logger.info(f"👤 USER SAID: '{text}'")

                # Send transcript to frontend via data channel
                import json
                from datetime import datetime
                try:
                    transcript_data = json.dumps({
                        "type": "transcript",
                        "speaker": "user",
                        "text": text,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    ctx.room.local_participant.publish_data(
                        payload=transcript_data.encode("utf-8"),
                        topic="transcripts",
                    )
                    logger.debug(f"✓ Sent user transcript to UI: '{text[:50]}...'")
                except Exception as e:
                    logger.error(f"Failed to send user transcript: {e}")

        @session.on("conversation_item_added")
        def on_conversation_item(item):
            """Handle conversation items and send agent responses to UI."""
            logger.info(f"💬 Conversation item added:")
            logger.info(f"   - Role: {item.role}")
            if hasattr(item, 'content') and item.content:
                content_preview = item.content[:100] if len(item.content) > 100 else item.content
                logger.info(f"   - Content: {content_preview}")

                # If this is an agent response, send it to the UI
                if item.role == "assistant" and item.content:
                    import json
                    from datetime import datetime
                    try:
                        transcript_data = json.dumps({
                            "type": "transcript",
                            "speaker": "assistant",
                            "text": item.content,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        ctx.room.local_participant.publish_data(
                            payload=transcript_data.encode("utf-8"),
                            topic="transcripts",
                        )
                        logger.debug(f"✓ Sent agent transcript to UI: '{item.content[:50]}...'")
                    except Exception as e:
                        logger.error(f"Failed to send agent transcript: {e}")

        @session.on("agent_state_changed")
        def on_agent_state(state):
            """Handle agent state changes and send to UI."""
            logger.info(f"🤖 Agent state changed: {state}")

            # Send state change to UI
            import json
            try:
                state_data = json.dumps({
                    "type": "agent_state",
                    "state": str(state),
                })
                ctx.room.local_participant.publish_data(
                    payload=state_data.encode("utf-8"),
                    topic="agent_status",
                )
            except Exception as e:
                logger.error(f"Failed to send agent state: {e}")

        @session.on("user_state_changed")
        def on_user_state(state):
            """Handle user state changes and send to UI."""
            logger.info(f"👤 User state changed: {state}")

            # Send state change to UI
            import json
            try:
                state_data = json.dumps({
                    "type": "user_state",
                    "state": str(state),
                })
                ctx.room.local_participant.publish_data(
                    payload=state_data.encode("utf-8"),
                    topic="user_status",
                )
            except Exception as e:
                logger.error(f"Failed to send user state: {e}")

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
