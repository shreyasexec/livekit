"""
LiveKit Keywords for Robot Framework
Keywords for LiveKit room and agent interactions
"""
import logging
from typing import Optional, List, Dict, Any

from robot.api.deco import keyword, library

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from resources.libraries.LiveKitAgent import LiveKitAgent
from config import LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET

logger = logging.getLogger(__name__)


@library(scope='GLOBAL')
class LiveKitKeywords:
    """Keywords for LiveKit room interactions"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.agent: Optional[LiveKitAgent] = None
        self.connected_room: str = ""

    @keyword("Initialize LiveKit Agent")
    def initialize_livekit_agent(self, url: str = None,
                                 api_key: str = None,
                                 api_secret: str = None):
        """Initialize LiveKit agent with credentials"""
        self.agent = LiveKitAgent(
            url=url or LIVEKIT_URL,
            api_key=api_key or LIVEKIT_API_KEY,
            api_secret=api_secret or LIVEKIT_API_SECRET
        )
        logger.info("LiveKit agent initialized")
        return True

    @keyword("Connect To Room")
    def connect_to_room(self, room_name: str, identity: str = None):
        """Connect to a LiveKit room"""
        if not self.agent:
            self.initialize_livekit_agent()

        if not self.agent.connect_to_room(room_name, identity):
            raise AssertionError(f"Failed to connect to room: {room_name}")

        self.connected_room = room_name
        logger.info(f"Connected to room: {room_name}")
        return True

    @keyword("Disconnect From Room")
    def disconnect_from_room(self):
        """Disconnect from current room"""
        if self.agent:
            self.agent.disconnect()
            self.connected_room = ""
            logger.info("Disconnected from room")
        return True

    @keyword("Room Should Be Connected")
    def room_should_be_connected(self):
        """Verify agent is connected to room"""
        if not self.agent or not self.agent.is_connected:
            raise AssertionError("Not connected to any room")
        return True

    @keyword("Speak Text")
    def speak_text(self, text: str, language: str = "en"):
        """Speak text in the room"""
        if not self.agent:
            raise AssertionError("Agent not initialized")

        if not self.agent.speak(text, language):
            raise AssertionError(f"Failed to speak: {text}")

        logger.info(f"Spoke: {text}")
        return True

    @keyword("Listen For Response")
    def listen_for_response(self, timeout: str = "15") -> str:
        """Listen for agent response"""
        if not self.agent:
            raise AssertionError("Agent not initialized")

        response = self.agent.listen(float(timeout))
        if not response:
            raise AssertionError("No response received within timeout")

        logger.info(f"Received: {response}")
        return response

    @keyword("Speak And Listen")
    def speak_and_listen(self, text: str, timeout: str = "15",
                         language: str = "en") -> str:
        """Speak text and wait for response"""
        if not self.agent:
            raise AssertionError("Agent not initialized")

        response = self.agent.speak_and_listen(text, float(timeout), language)
        if not response:
            raise AssertionError(f"No response for: {text}")

        logger.info(f"Said: {text} -> Got: {response}")
        return response

    @keyword("Get Participant Count")
    def get_participant_count(self) -> int:
        """Get number of participants in room"""
        if not self.agent:
            return 0
        return len(self.agent.get_participants()) + 1

    @keyword("Room Should Have At Least Participants")
    def room_should_have_at_least_participants(self, count: str):
        """Verify room has at least specified participants"""
        actual = self.get_participant_count()
        expected = int(count)
        if actual < expected:
            raise AssertionError(
                f"Expected at least {expected} participants, got {actual}"
            )
        return True

    @keyword("Get All Transcripts")
    def get_all_transcripts(self) -> List[Dict[str, Any]]:
        """Get all transcripts from conversation"""
        if not self.agent:
            return []
        return self.agent.get_transcripts()

    @keyword("Clear Transcripts")
    def clear_transcripts(self):
        """Clear transcript history"""
        if self.agent:
            self.agent.clear_transcripts()
        return True

    @keyword("Set Agent Language")
    def set_agent_language(self, language_code: str):
        """Set language for TTS"""
        if not self.agent:
            raise AssertionError("Agent not initialized")
        self.agent.set_language(language_code)
        logger.info(f"Language set to: {language_code}")
        return True

    @keyword("Run Multi-Turn Conversation")
    def run_multi_turn_conversation(self, turns: List[str],
                                    language: str = "en",
                                    timeout: str = "15") -> List[Dict[str, str]]:
        """Run a multi-turn conversation and return responses"""
        if not self.agent:
            raise AssertionError("Agent not initialized")

        results = []
        for i, user_input in enumerate(turns):
            response = self.agent.speak_and_listen(
                user_input, float(timeout), language
            )
            results.append({
                "turn": i + 1,
                "input": user_input,
                "response": response or ""
            })

            if not response:
                logger.warning(f"No response for turn {i + 1}: {user_input}")

        return results

    @keyword("Transcript Should Contain")
    def transcript_should_contain(self, text: str):
        """Verify transcript contains specified text"""
        transcripts = self.get_all_transcripts()
        all_text = ' '.join([t['text'] for t in transcripts])

        if text.lower() not in all_text.lower():
            raise AssertionError(
                f"Transcript does not contain: {text}\n"
                f"Transcripts: {all_text}"
            )
        return True

    @keyword("Get Last Transcript")
    def get_last_transcript(self) -> str:
        """Get the last transcript message"""
        transcripts = self.get_all_transcripts()
        if not transcripts:
            return ""
        return transcripts[-1].get('text', '')

    @keyword("Agent Should Have Responded")
    def agent_should_have_responded(self):
        """Verify agent has sent at least one response"""
        transcripts = self.get_all_transcripts()
        agent_responses = [
            t for t in transcripts
            if t.get('speaker') in ['assistant', 'agent']
        ]
        if not agent_responses:
            raise AssertionError("Agent has not responded")
        return True

    @keyword("Wait For Agent To Join")
    def wait_for_agent_to_join(self, timeout: str = "30"):
        """Wait for AI agent to join the room"""
        import time
        start = time.time()

        while time.time() - start < float(timeout):
            participants = self.agent.get_participants() if self.agent else []
            for p in participants:
                if 'agent' in p.get('identity', '').lower():
                    logger.info(f"Agent joined: {p['identity']}")
                    return True
            time.sleep(0.5)

        raise AssertionError(f"Agent did not join within {timeout}s")
