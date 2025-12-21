"""
Browser Keywords for Robot Framework
Keywords for Playwright browser automation using async API
"""
import asyncio
import logging
import time
import os
from typing import Optional

from robot.api.deco import keyword, library

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import APP_URL, HEADLESS, CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)

# Module-level shared state - this is truly global across all imports
_BROWSER_STATE = {
    'playwright': None,
    'browser': None,
    'context': None,
    'page': None,
    'loop': None
}

# Import Playwright async API
PLAYWRIGHT_AVAILABLE = True
try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None
    PLAYWRIGHT_AVAILABLE = False


def run_async(coro):
    """Run async coroutine in a new event loop"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        return result
    finally:
        try:
            loop.close()
        except Exception:
            pass


@library(scope='GLOBAL')
class BrowserKeywords:
    """Keywords for browser automation using async Playwright"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        # Use module-level shared state via _BROWSER_STATE dict
        pass

    @property
    def _playwright(self):
        return _BROWSER_STATE['playwright']

    @_playwright.setter
    def _playwright(self, value):
        _BROWSER_STATE['playwright'] = value

    @property
    def _browser(self):
        return _BROWSER_STATE['browser']

    @_browser.setter
    def _browser(self, value):
        _BROWSER_STATE['browser'] = value

    @property
    def _context(self):
        return _BROWSER_STATE['context']

    @_context.setter
    def _context(self, value):
        _BROWSER_STATE['context'] = value

    @property
    def _page(self):
        return _BROWSER_STATE['page']

    @_page.setter
    def _page(self, value):
        _BROWSER_STATE['page'] = value

    @property
    def _loop(self):
        return _BROWSER_STATE['loop']

    @_loop.setter
    def _loop(self, value):
        _BROWSER_STATE['loop'] = value

    def _get_loop(self):
        """Get or create event loop"""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def _run_async(self, coro):
        """Run coroutine synchronously"""
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    @keyword("Open Browser With Permissions")
    def open_browser_with_permissions(self, headless: bool = None):
        """Open browser with microphone/camera permissions granted"""
        if not PLAYWRIGHT_AVAILABLE:
            raise AssertionError("Playwright not installed")
        return self._run_async(self._open_browser_async(headless))

    async def _open_browser_async(self, headless: bool = None):
        """Async open browser"""
        headless = headless if headless is not None else HEADLESS

        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=[
                '--use-fake-ui-for-media-stream',
                '--use-fake-device-for-media-stream',
                '--autoplay-policy=no-user-gesture-required',
                '--allow-file-access-from-files',
                '--disable-web-security',
                '--ignore-certificate-errors',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-dev-shm-usage'
            ]
        )

        self._context = await self._browser.new_context(
            permissions=['microphone', 'camera'],
            ignore_https_errors=True,
            viewport={'width': 1280, 'height': 720}
        )

        self._page = await self._context.new_page()

        # Track RTCPeerConnections before app scripts run
        await self._page.add_init_script("""
            (() => {
                if (!window.__rtcPeerConnections) {
                    window.__rtcPeerConnections = [];
                    const origPC = window.RTCPeerConnection;
                    window.RTCPeerConnection = function(...args) {
                        const pc = new origPC(...args);
                        window.__rtcPeerConnections.push(pc);
                        return pc;
                    };
                    window.RTCPeerConnection.prototype = origPC.prototype;
                }
            })();
        """)

        # Set up console logging
        self._page.on('console', lambda msg: logger.debug(f"[Browser] {msg.text}"))

        logger.info(f"Browser opened (headless={headless})")
        return True

    @keyword("Navigate To App")
    def navigate_to_app(self, url: str = None):
        """Navigate to the voice AI app"""
        return self._run_async(self._navigate_async(url))

    async def _navigate_async(self, url: str = None):
        """Async navigate"""
        url = url or APP_URL

        if not self._page:
            raise AssertionError("Browser not opened")

        await self._page.goto(url, wait_until='networkidle', timeout=CONNECTION_TIMEOUT * 1000)
        logger.info(f"Navigated to: {url}")
        return True

    @keyword("Wait For Element")
    def wait_for_element(self, selector: str, timeout: str = "10"):
        """Wait for element to be visible"""
        return self._run_async(self._wait_element_async(selector, float(timeout)))

    async def _wait_element_async(self, selector: str, timeout: float):
        """Async wait for element"""
        if not self._page:
            raise AssertionError("Browser not opened")
        await self._page.wait_for_selector(selector, timeout=timeout * 1000)
        return True

    @keyword("Click Element")
    def click_element(self, selector: str):
        """Click on element"""
        return self._run_async(self._click_async(selector))

    async def _click_async(self, selector: str):
        """Async click"""
        if not self._page:
            raise AssertionError("Browser not opened")
        await self._page.click(selector)
        logger.debug(f"Clicked: {selector}")
        return True

    @keyword("Fill Input")
    def fill_input(self, selector: str, value: str):
        """Fill input field with value"""
        return self._run_async(self._fill_async(selector, value))

    async def _fill_async(self, selector: str, value: str):
        """Async fill"""
        if not self._page:
            raise AssertionError("Browser not opened")
        await self._page.fill(selector, value)
        logger.debug(f"Filled {selector} with: {value}")
        return True

    @keyword("Enter Room Details")
    def enter_room_details(self, room_name: str, participant_name: str):
        """Enter room name and participant name"""
        return self._run_async(self._enter_room_async(room_name, participant_name))

    async def _enter_room_async(self, room_name: str, participant_name: str):
        """Async enter room details"""
        if not self._page:
            raise AssertionError("Browser not opened")

        # Use specific selectors to avoid ambiguity
        # Room input: "Enter room name (e.g., ai-agent-room)"
        await self._page.wait_for_selector('input[placeholder*="room name"]', timeout=10000)
        room_input = self._page.locator('input[placeholder*="room name"]')
        await room_input.fill(room_name)

        # Participant name input: "Enter your name"
        name_input = self._page.locator('input[placeholder="Enter your name"]')
        await name_input.fill(participant_name)

        logger.info(f"Entered room: {room_name}, participant: {participant_name}")
        return True

    @keyword("Click Join Room Button")
    def click_join_room_button(self):
        """Click the join room button"""
        return self._run_async(self._click_join_async())

    async def _click_join_async(self):
        """Async click join"""
        if not self._page:
            raise AssertionError("Browser not opened")

        join_button = self._page.locator('button:has-text("Join")')
        await join_button.click()

        logger.info("Clicked Join Room button")
        return True

    @keyword("Wait For Room Connection")
    def wait_for_room_connection(self, timeout: str = "30"):
        """Wait for room to be connected"""
        return self._run_async(self._wait_connection_async(float(timeout)))

    async def _wait_connection_async(self, timeout: float):
        """Async wait for connection"""
        if not self._page:
            raise AssertionError("Browser not opened")

        timeout_ms = int(timeout * 1000)

        try:
            await self._page.wait_for_selector('button:has-text("Disconnect")', timeout=timeout_ms)
            logger.info("Room connected - Disconnect button visible")
            return True
        except Exception:
            pass

        try:
            await self._page.wait_for_selector('[class*="voice"], [class*="agent"]', timeout=timeout_ms)
            logger.info("Room connected - Voice UI visible")
            return True
        except Exception:
            raise AssertionError(f"Room connection timeout after {timeout}s")

    @keyword("Click Disconnect Button")
    def click_disconnect_button(self):
        """Click the disconnect button"""
        return self._run_async(self._click_disconnect_async())

    async def _click_disconnect_async(self):
        """Async click disconnect"""
        if not self._page:
            return False

        disconnect_button = self._page.locator('button:has-text("Disconnect")')
        if await disconnect_button.is_visible():
            await disconnect_button.click()
            logger.info("Clicked Disconnect button")
            return True
        return False

    @keyword("Get Transcript Text")
    def get_transcript_text(self) -> str:
        """Get transcript text from the UI"""
        return self._run_async(self._get_transcript_async())

    async def _get_transcript_async(self) -> str:
        """Async get transcript from Voice Agent UI.

        Per LiveKit React Components docs, the transcript panel uses
        a scrollable container with individual message entries.
        """
        if not self._page:
            return ""

        # Selectors that match the VoiceAgent.tsx transcript UI
        selectors = [
            # Match individual transcript entries (agent=blue, user=green)
            '.bg-blue-900\\/30, .bg-green-900\\/30',
            # Match the transcript container by its unique content structure
            'div.overflow-y-auto.space-y-3 > div',
            # Match entries containing Trinity AI (agent name)
            'div:has-text("Trinity AI")',
            # Fallback: any div with transcript-like structure
            '[class*="transcript"]',
        ]

        for selector in selectors:
            try:
                elements = self._page.locator(selector)
                if await elements.count() > 0:
                    texts = []
                    for i in range(await elements.count()):
                        text = await elements.nth(i).inner_text()
                        if text.strip():
                            texts.append(text.strip())
                    if texts:
                        return '\n'.join(texts)
            except Exception:
                continue

        return ""

    @keyword("Wait For Agent Response")
    def wait_for_agent_response(self, timeout: str = "15") -> str:
        """Wait for agent to respond in UI"""
        return self._run_async(self._wait_response_async(float(timeout)))

    async def _wait_response_async(self, timeout: float) -> str:
        """Async wait for agent response in transcript.

        Per VoiceAgent.tsx, agent responses appear as:
        - 'Trinity AI' as speaker name
        - 'assistant' as speaker type
        """
        if not self._page:
            return ""

        start_time = time.time()
        initial_transcript = await self._get_transcript_async() or ""

        while time.time() - start_time < timeout:
            current = await self._get_transcript_async()

            # Check if transcript changed (placeholder can be longer than first message)
            if current and current != initial_transcript:
                # Check for agent response markers (per VoiceAgent.tsx)
                if ('Trinity AI' in current or
                    'Trinity' in current or
                    'Agent' in current or
                    'assistant' in current.lower()):
                    # Return only the new content
                    return current

            await asyncio.sleep(0.5)

        return ""

    @keyword("Get Page")
    def get_page(self):
        """Get the current page object"""
        return self._page

    @keyword("Get Browser Context")
    def get_browser_context(self):
        """Get the browser context"""
        return self._context

    @keyword("Take Screenshot")
    def take_screenshot(self, path: str = None) -> str:
        """Take screenshot of current page"""
        return self._run_async(self._screenshot_async(path))

    async def _screenshot_async(self, path: str = None) -> str:
        """Async take screenshot"""
        if not self._page:
            raise AssertionError("Browser not opened")

        if not path:
            path = f"screenshot_{int(time.time())}.png"

        await self._page.screenshot(path=path)
        logger.info(f"Screenshot saved: {path}")
        return path

    @keyword("Close Browser")
    def close_browser(self):
        """Close the browser"""
        return self._run_async(self._close_async())

    async def _close_async(self):
        """Async close browser"""
        if self._page:
            await self._page.close()
            self._page = None

        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Browser closed")
        return True

    @keyword("Page Should Contain Text")
    def page_should_contain_text(self, text: str):
        """Verify page contains text"""
        return self._run_async(self._contain_text_async(text))

    async def _contain_text_async(self, text: str):
        """Async check text"""
        if not self._page:
            raise AssertionError("Browser not opened")

        content = await self._page.content()
        if text.lower() not in content.lower():
            raise AssertionError(f"Page does not contain: {text}")
        return True

    @keyword("Element Should Be Visible")
    def element_should_be_visible(self, selector: str):
        """Verify element is visible"""
        return self._run_async(self._visible_async(selector))

    async def _visible_async(self, selector: str):
        """Async check visibility"""
        if not self._page:
            raise AssertionError("Browser not opened")

        element = self._page.locator(selector)
        if not await element.is_visible():
            raise AssertionError(f"Element not visible: {selector}")
        return True
