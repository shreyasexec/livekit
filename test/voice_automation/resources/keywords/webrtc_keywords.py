"""
WebRTC Keywords for Robot Framework
Keywords for WebRTC UI-based testing
"""
# Apply nest_asyncio FIRST
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

import asyncio
import logging
import time
from typing import Optional, Dict, Any

from robot.api.deco import keyword, library

import sys
import os
import importlib.util

# Get the directory of this file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))
sys.path.insert(0, _BASE_DIR)

# Import browser_keywords by file path to ensure we get the same module as Robot Framework
_browser_module_path = os.path.join(_THIS_DIR, 'browser_keywords.py')
_spec = importlib.util.spec_from_file_location("browser_keywords", _browser_module_path)
_browser_module = importlib.util.module_from_spec(_spec)

# Check if already loaded in sys.modules
if "browser_keywords" in sys.modules:
    _browser_module = sys.modules["browser_keywords"]
else:
    _spec.loader.exec_module(_browser_module)
    sys.modules["browser_keywords"] = _browser_module

BrowserKeywords = _browser_module.BrowserKeywords
_BROWSER_STATE = _browser_module._BROWSER_STATE

from resources.libraries.WebRTCHandler import WebRTCHandler
from resources.libraries.PiperTTSClient import PiperTTSClient
from config import APP_URL, WEBRTC_TIMEOUT

logger = logging.getLogger(__name__)


@library(scope='GLOBAL')
class WebRTCKeywords:
    """Keywords for WebRTC testing through browser UI"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.webrtc_handler = WebRTCHandler()
        # Share browser_keywords with Robot Framework's global instance
        self.browser_keywords = BrowserKeywords()
        self.tts_client = PiperTTSClient()

    def _get_page(self):
        """Get the shared page from browser state"""
        # Access module-level state directly to ensure we get the shared page
        return _BROWSER_STATE.get('page')

    def _get_loop(self):
        """Get or create event loop from shared state"""
        loop = _BROWSER_STATE.get('loop')
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _BROWSER_STATE['loop'] = loop
        return loop

    def _run_async(self, coro):
        """Run async coroutine using shared event loop"""
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    async def _send_text_via_room(self, page, text: str) -> bool:
        """Send text input via LiveKit text stream if available"""
        return await page.evaluate(
            """
            async (text) => {
                const room = window.__lkRoom;
                if (!room || !room.localParticipant || !room.localParticipant.sendText) {
                    return false;
                }
                try {
                    if (typeof room.localParticipant.sendChatMessage === 'function') {
                        await room.localParticipant.sendChatMessage(text);
                        return true;
                    }
                    await room.localParticipant.sendText(text, { topic: 'lk.chat' });
                    return true;
                } catch (e) {
                    console.warn('sendText failed', e);
                    return false;
                }
            }
            """,
            text,
        )

    @keyword("Open App With WebRTC Permissions")
    def open_app_with_webrtc_permissions(self, headless: bool = True):
        """Open browser with WebRTC permissions and navigate to app"""
        self.browser_keywords.open_browser_with_permissions(headless)
        self.browser_keywords.navigate_to_app()
        logger.info("App opened with WebRTC permissions")
        return True

    @keyword("Join Room Via WebRTC")
    def join_room_via_webrtc(self, room_name: str, participant_name: str):
        """Join room using the web UI"""
        self.browser_keywords.enter_room_details(room_name, participant_name)
        self.browser_keywords.click_join_room_button()
        self.browser_keywords.wait_for_room_connection()
        logger.info(f"Joined room via WebRTC: {room_name}")
        return True

    @keyword("Wait For WebRTC Connection")
    def wait_for_webrtc_connection(self, timeout: str = None):
        """Wait for WebRTC connection to be established"""
        timeout = int(timeout) if timeout else WEBRTC_TIMEOUT
        page = self.browser_keywords.get_page()

        if not page:
            raise AssertionError("Browser not opened")

        connected = self._run_async(
            self.webrtc_handler.wait_for_webrtc_connected(page, timeout)
        )

        if not connected:
            raise AssertionError(f"WebRTC connection not established within {timeout}s")

        logger.info("WebRTC connection established")
        return True

    @keyword("WebRTC Should Be Connected")
    def webrtc_should_be_connected(self):
        """Verify WebRTC is connected"""
        page = self.browser_keywords.get_page()

        if not page:
            raise AssertionError("Browser not opened")

        start = time.time()
        while True:
            stats = self._run_async(self.webrtc_handler.get_webrtc_stats(page))
            if stats.is_connected:
                return True

            fallback = self._run_async(page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        if (btn.textContent && btn.textContent.toLowerCase().includes('disconnect')) {
                            return true;
                        }
                    }

                    const audioElements = document.querySelectorAll('audio, video');
                    for (const el of audioElements) {
                        if (el.srcObject && el.srcObject.getAudioTracks().length > 0) {
                            return true;
                        }
                    }

                    return false;
                }
            """))

            if fallback:
                return True

            if time.time() - start > 5:
                raise AssertionError(
                    f"WebRTC not connected. State: {stats.connection_state}"
                )
            time.sleep(0.5)

    @keyword("Inject Audio To WebRTC Stream")
    def inject_audio_to_webrtc_stream(self, audio_path: str):
        """Inject audio file into WebRTC stream"""
        page = self.browser_keywords.get_page()

        if not page:
            raise AssertionError("Browser not opened")

        success = self._run_async(
            self.webrtc_handler.inject_audio_to_webrtc(page, audio_path)
        )

        if not success:
            raise AssertionError(f"Failed to inject audio: {audio_path}")

        logger.info(f"Injected audio: {audio_path}")
        return True

    @keyword("Capture WebRTC Audio")
    def capture_webrtc_audio(self, duration: str,
                             output_path: str = None) -> str:
        """Capture audio from WebRTC stream"""
        page = self.browser_keywords.get_page()

        if not page:
            raise AssertionError("Browser not opened")

        result = self._run_async(
            self.webrtc_handler.capture_webrtc_audio(
                page, float(duration), output_path
            )
        )

        if not result:
            raise AssertionError("Failed to capture WebRTC audio")

        logger.info(f"Captured audio: {result}")
        return result

    @keyword("Speak Via WebRTC")
    def speak_via_webrtc(self, text: str, language: str = "en"):
        """Synthesize text and inject into WebRTC stream"""
        page = self.browser_keywords.get_page()

        if not page:
            raise AssertionError("Browser not opened")

        # Prefer LiveKit text stream if available (per LiveKit Agents text input)
        if self._run_async(self._send_text_via_room(page, text)):
            logger.info(f"Sent text via LiveKit text stream: {text}")
            return True

        # Synthesize speech
        result = self.tts_client.synthesize_multilingual(text, language)
        if not result:
            raise AssertionError(f"TTS synthesis failed for: {text}")

        # Inject into WebRTC
        success = self._run_async(
            self.webrtc_handler.inject_audio_to_webrtc(page, result.audio_path)
        )

        if not success:
            raise AssertionError("Failed to inject synthesized audio")

        # Wait for audio to play
        time.sleep(result.duration + 0.5)

        logger.info(f"Spoke via WebRTC: {text}")
        return True

    @keyword("Listen From WebRTC")
    def listen_from_webrtc(self, timeout: str = "10") -> str:
        """Listen for response via WebRTC and transcribe"""
        page = self.browser_keywords.get_page()

        if not page:
            raise AssertionError("Browser not opened")

        # Wait for and get transcript from UI
        response = self.browser_keywords.wait_for_agent_response(timeout)

        if not response:
            response = self._run_async(page.evaluate("""
                () => {
                    const last = window.__lkLastTranscript;
                    if (last && typeof last.text === 'string') {
                        return last.text;
                    }
                    const chat = window.__lkLastChatMessage;
                    if (chat && typeof chat.message === 'string') {
                        return chat.message;
                    }
                    return '';
                }
            """))

        if not response:
            logger.warning("No response received from WebRTC")
            return ""

        logger.info(f"Received from WebRTC: {response[:100]}...")
        return response

    @keyword("WebRTC Audio Should Be Flowing")
    def webrtc_audio_should_be_flowing(self):
        """Verify audio is flowing through WebRTC"""
        page = self.browser_keywords.get_page()

        if not page:
            raise AssertionError("Browser not opened")

        status = self._run_async(
            self.webrtc_handler.get_audio_track_status(page)
        )

        if not status.get('has_local_track') and not status.get('has_remote_track'):
            raise AssertionError("No audio tracks found in WebRTC connection")

        logger.info(f"Audio status: {status}")
        return True

    @keyword("Get WebRTC Connection Stats")
    def get_webrtc_connection_stats(self) -> Dict[str, Any]:
        """Get WebRTC connection statistics"""
        page = self.browser_keywords.get_page()

        if not page:
            return {}

        stats = self._run_async(self.webrtc_handler.get_webrtc_stats(page))

        return {
            'connection_state': stats.connection_state,
            'ice_connection_state': stats.ice_connection_state,
            'bytes_sent': stats.bytes_sent,
            'bytes_received': stats.bytes_received,
            'packets_sent': stats.packets_sent,
            'packets_received': stats.packets_received,
            'is_connected': stats.is_connected
        }

    @keyword("Run WebRTC Conversation")
    def run_webrtc_conversation(self, turns: list, language: str = "en",
                                timeout: str = "15") -> list:
        """Run multi-turn conversation via WebRTC"""
        results = []

        for i, user_input in enumerate(turns):
            # Speak
            self.speak_via_webrtc(user_input, language)

            # Wait and listen
            response = self.listen_from_webrtc(timeout)

            results.append({
                'turn': i + 1,
                'input': user_input,
                'response': response
            })

            logger.info(f"Turn {i + 1}: {user_input} -> {response[:50]}...")

        return results

    @keyword("Disconnect WebRTC")
    def disconnect_webrtc(self):
        """Disconnect from WebRTC and close browser"""
        try:
            self.browser_keywords.click_disconnect_button()
        except Exception:
            pass

        self.browser_keywords.close_browser()
        self.webrtc_handler.cleanup()
        logger.info("WebRTC disconnected")
        return True

    @keyword("Take WebRTC Screenshot")
    def take_webrtc_screenshot(self, path: str = None) -> str:
        """Take screenshot during WebRTC session"""
        return self.browser_keywords.take_screenshot(path)

    @keyword("Get Audio Track Status")
    def get_audio_track_status(self) -> Dict[str, Any]:
        """Get status of audio tracks"""
        page = self.browser_keywords.get_page()

        if not page:
            return {}

        return self._run_async(
            self.webrtc_handler.get_audio_track_status(page)
        )

    @keyword("WebRTC Should Have Sent Audio")
    def webrtc_should_have_sent_audio(self):
        """Verify audio has been sent via WebRTC"""
        stats = self.get_webrtc_connection_stats()

        if stats.get('bytes_sent', 0) == 0:
            raise AssertionError("No audio bytes sent via WebRTC")

        logger.info(f"Bytes sent: {stats['bytes_sent']}")
        return True

    @keyword("WebRTC Should Have Received Audio")
    def webrtc_should_have_received_audio(self):
        """Verify audio has been received via WebRTC"""
        stats = self.get_webrtc_connection_stats()

        if stats.get('bytes_received', 0) == 0:
            raise AssertionError("No audio bytes received via WebRTC")

        logger.info(f"Bytes received: {stats['bytes_received']}")
        return True
