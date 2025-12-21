"""
WebRTC Handler for browser-based testing
Handles WebRTC connections, audio injection, and capture through Playwright
"""
import asyncio
import logging
import time
import tempfile
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    from playwright.async_api import Page, BrowserContext
except ImportError:
    Page = None
    BrowserContext = None

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import APP_URL, WEBRTC_TIMEOUT, HEADLESS

logger = logging.getLogger(__name__)


@dataclass
class WebRTCStats:
    """WebRTC connection statistics"""
    connection_state: str
    ice_connection_state: str
    signaling_state: str
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    audio_level: float = 0.0
    is_connected: bool = False


class WebRTCHandler:
    """Handler for WebRTC operations through browser"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="webrtc_test_")
        self.last_stats: Optional[WebRTCStats] = None

    async def setup_webrtc_permissions(self, context: 'BrowserContext'):
        """Grant microphone and camera permissions to browser context"""
        await context.grant_permissions(['microphone', 'camera'])
        logger.info("WebRTC permissions granted")

    async def wait_for_webrtc_connected(self, page: 'Page',
                                        timeout: int = None) -> bool:
        """Wait for WebRTC connection to be established"""
        timeout = timeout or WEBRTC_TIMEOUT

        # JavaScript to check WebRTC connection - check multiple indicators
        check_script = """
        () => {
            // Method 1: Check for tracked RTCPeerConnections
            const pcs = window.__rtcPeerConnections || [];
            for (const pc of pcs) {
                if (pc.connectionState === 'connected' ||
                    pc.iceConnectionState === 'connected' ||
                    pc.iceConnectionState === 'completed') {
                    return { connected: true, method: 'tracked_pc' };
                }
            }

            // Method 2: Check for any audio/video elements with streams
            const audioElements = document.querySelectorAll('audio, video');
            for (const el of audioElements) {
                if (el.srcObject && el.srcObject.getAudioTracks().length > 0) {
                    return { connected: true, method: 'audio_track' };
                }
            }

            return { connected: false, method: 'none' };
        }
        """

        # Inject RTCPeerConnection tracker for future connections
        try:
            await page.evaluate("""
            () => {
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
            }
            """)
        except Exception as e:
            logger.warning(f"Could not inject PC tracker: {e}")

        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                result = await page.evaluate(check_script)
                if result and result.get('connected'):
                    logger.info(f"WebRTC connection established (method: {result.get('method')})")
                    return True
                await asyncio.sleep(0.5)

            logger.warning(f"WebRTC connection timeout after {timeout}s")
            return False

        except Exception as e:
            logger.error(f"Error waiting for WebRTC: {e}")
            return False

    async def get_webrtc_stats(self, page: 'Page') -> WebRTCStats:
        """Get WebRTC connection statistics"""
        stats_script = """
        async () => {
            const stats = {
                connection_state: 'unknown',
                ice_connection_state: 'unknown',
                signaling_state: 'unknown',
                bytes_sent: 0,
                bytes_received: 0,
                packets_sent: 0,
                packets_received: 0,
                audio_level: 0,
                is_connected: false
            };

            // Check for tracked peer connections
            const pcs = window.__rtcPeerConnections || [];
            const audioElements = document.querySelectorAll('audio, video');
            let hasAudioTrack = false;
            for (const el of audioElements) {
                if (el.srcObject && el.srcObject.getAudioTracks().length > 0) {
                    hasAudioTrack = true;
                    break;
                }
            }

            if (pcs.length > 0) {
                const connectedPc = pcs.find(
                    (pc) => pc.connectionState === 'connected' ||
                        pc.iceConnectionState === 'connected' ||
                        pc.iceConnectionState === 'completed'
                );
                const pc = connectedPc || pcs[pcs.length - 1];
                stats.connection_state = pc.connectionState || 'unknown';
                stats.ice_connection_state = pc.iceConnectionState || 'unknown';
                stats.signaling_state = pc.signalingState || 'unknown';
                stats.is_connected = pcs.some(
                    (p) => p.connectionState === 'connected' ||
                        p.iceConnectionState === 'connected' ||
                        p.iceConnectionState === 'completed'
                );
                if (!stats.is_connected && hasAudioTrack) {
                    stats.is_connected = true;
                    if (stats.connection_state === 'new' || stats.connection_state === 'unknown') {
                        stats.connection_state = 'connected';
                    }
                }

                try {
                    const rtcStats = await pc.getStats();
                    rtcStats.forEach(report => {
                        if (report.type === 'outbound-rtp' && report.kind === 'audio') {
                            stats.bytes_sent = report.bytesSent || 0;
                            stats.packets_sent = report.packetsSent || 0;
                        }
                        if (report.type === 'inbound-rtp' && report.kind === 'audio') {
                            stats.bytes_received = report.bytesReceived || 0;
                            stats.packets_received = report.packetsReceived || 0;
                            stats.audio_level = report.audioLevel || 0;
                        }
                    });
                } catch (e) {
                    console.error('Stats error:', e);
                }
            } else {
                // Fallback: Check UI state for connection
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.textContent && btn.textContent.toLowerCase().includes('disconnect')) {
                        stats.connection_state = 'connected';
                        stats.is_connected = true;
                        break;
                    }
                }

                // Check for audio/video elements with streams
                if (hasAudioTrack) {
                    stats.connection_state = 'connected';
                    stats.is_connected = true;
                }
            }

            return stats;
        }
        """

        try:
            stats_data = await page.evaluate(stats_script)
            self.last_stats = WebRTCStats(**stats_data)
            return self.last_stats
        except Exception as e:
            logger.error(f"Failed to get WebRTC stats: {e}")
            return WebRTCStats(
                connection_state='error',
                ice_connection_state='error',
                signaling_state='error'
            )

    async def inject_audio_to_webrtc(self, page: 'Page', audio_path: str) -> bool:
        """Inject audio file into WebRTC stream"""
        try:
            # Read audio file and convert to base64
            import base64
            with open(audio_path, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode()

            # JavaScript to create audio stream from file
            inject_script = f"""
            async () => {{
                try {{
                    // Decode base64 audio
                    const audioData = atob('{audio_data}');
                    const audioArray = new Uint8Array(audioData.length);
                    for (let i = 0; i < audioData.length; i++) {{
                        audioArray[i] = audioData.charCodeAt(i);
                    }}

                    // Create audio context
                    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    if (audioContext.state === 'suspended') {{
                        await audioContext.resume();
                    }}
                    const audioBuffer = await audioContext.decodeAudioData(audioArray.buffer);

                    // Create source
                    const source = audioContext.createBufferSource();
                    source.buffer = audioBuffer;

                    // Create media stream destination
                    const destination = audioContext.createMediaStreamDestination();
                    source.connect(destination);

                    // Replace the current audio track
                    const pcs = window.__rtcPeerConnections || [];
                    for (const pc of pcs) {{
                        const senders = pc.getSenders();
                        for (const sender of senders) {{
                            if (sender.track && sender.track.kind === 'audio') {{
                                const newTrack = destination.stream.getAudioTracks()[0];
                                await sender.replaceTrack(newTrack);
                            }}
                        }}
                    }}

                    // Start playback
                    source.start();

                    return true;
                }} catch (e) {{
                    console.error('Audio injection error:', e);
                    return false;
                }}
            }}
            """

            result = await page.evaluate(inject_script)
            if result:
                logger.info(f"Audio injected: {audio_path}")
            return result

        except Exception as e:
            logger.error(f"Failed to inject audio: {e}")
            return False

    async def capture_webrtc_audio(self, page: 'Page', duration: float,
                                   output_path: str = None) -> Optional[str]:
        """Capture audio from WebRTC stream"""
        if not output_path:
            output_path = os.path.join(
                self.temp_dir,
                f"capture_{int(time.time() * 1000)}.wav"
            )

        try:
            # JavaScript to capture audio
            capture_script = f"""
            async () => {{
                return new Promise((resolve, reject) => {{
                    try {{
                        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        const chunks = [];

                        // Find audio element or stream
                        let stream = null;
                        const audioElements = document.querySelectorAll('audio, video');
                        for (const el of audioElements) {{
                            if (el.srcObject) {{
                                stream = el.srcObject;
                                break;
                            }}
                        }}

                        if (!stream) {{
                            // Try to get from peer connection
                            const pcs = window.__rtcPeerConnections || [];
                            for (const pc of pcs) {{
                                const receivers = pc.getReceivers();
                                for (const receiver of receivers) {{
                                    if (receiver.track && receiver.track.kind === 'audio') {{
                                        stream = new MediaStream([receiver.track]);
                                        break;
                                    }}
                                }}
                                if (stream) break;
                            }}
                        }}

                        if (!stream) {{
                            reject('No audio stream found');
                            return;
                        }}

                        // Create MediaRecorder
                        const recorder = new MediaRecorder(stream, {{
                            mimeType: 'audio/webm'
                        }});

                        recorder.ondataavailable = (e) => {{
                            if (e.data.size > 0) {{
                                chunks.push(e.data);
                            }}
                        }};

                        recorder.onstop = async () => {{
                            const blob = new Blob(chunks, {{ type: 'audio/webm' }});
                            const reader = new FileReader();
                            reader.onload = () => {{
                                resolve(reader.result);
                            }};
                            reader.readAsDataURL(blob);
                        }};

                        recorder.start();
                        setTimeout(() => recorder.stop(), {int(duration * 1000)});

                    }} catch (e) {{
                        reject(e.message);
                    }}
                }});
            }}
            """

            result = await page.evaluate(capture_script)

            if result and result.startswith('data:'):
                # Decode and save
                import base64
                header, data = result.split(',', 1)
                audio_bytes = base64.b64decode(data)

                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)

                logger.info(f"Audio captured: {output_path}")
                return output_path

            return None

        except Exception as e:
            logger.error(f"Failed to capture audio: {e}")
            return None

    async def get_audio_track_status(self, page: 'Page') -> Dict[str, Any]:
        """Check if audio tracks are active and flowing"""
        status_script = """
        () => {
            const status = {
                has_local_track: false,
                has_remote_track: false,
                local_enabled: false,
                remote_enabled: false,
                local_muted: true,
                remote_muted: true
            };

            const pcs = window.__rtcPeerConnections || [];
            for (const pc of pcs) {
                // Check senders (local)
                const senders = pc.getSenders();
                for (const sender of senders) {
                    if (sender.track && sender.track.kind === 'audio') {
                        status.has_local_track = true;
                        status.local_enabled = sender.track.enabled;
                        status.local_muted = sender.track.muted;
                    }
                }

                // Check receivers (remote)
                const receivers = pc.getReceivers();
                for (const receiver of receivers) {
                    if (receiver.track && receiver.track.kind === 'audio') {
                        status.has_remote_track = true;
                        status.remote_enabled = receiver.track.enabled;
                        status.remote_muted = receiver.track.muted;
                    }
                }
            }

            return status;
        }
        """

        try:
            return await page.evaluate(status_script)
        except Exception as e:
            logger.error(f"Failed to get track status: {e}")
            return {}

    async def simulate_user_speaking(self, page: 'Page', text: str,
                                     language: str = "en",
                                     tts_client=None) -> bool:
        """Simulate user speaking by synthesizing and injecting audio"""
        if not tts_client:
            from .PiperTTSClient import PiperTTSClient
            tts_client = PiperTTSClient()

        try:
            # Synthesize speech
            result = tts_client.synthesize_multilingual(text, language)
            if not result:
                logger.error("TTS synthesis failed")
                return False

            # Inject into WebRTC
            success = await self.inject_audio_to_webrtc(page, result.audio_path)
            return success

        except Exception as e:
            logger.error(f"Failed to simulate speaking: {e}")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    # Synchronous wrappers for Robot Framework
    def _run_async(self, coro):
        """Run async coroutine synchronously"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    # Robot Framework Keywords
    def webrtc_should_be_connected(self, page: 'Page'):
        """Robot Framework keyword to verify WebRTC connection"""
        start = time.time()
        while True:
            stats = self._run_async(self.get_webrtc_stats(page))
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
        return True

    def get_webrtc_connection_stats(self, page: 'Page') -> Dict[str, Any]:
        """Robot Framework keyword to get connection stats"""
        stats = self._run_async(self.get_webrtc_stats(page))
        return {
            'connection_state': stats.connection_state,
            'ice_connection_state': stats.ice_connection_state,
            'bytes_sent': stats.bytes_sent,
            'bytes_received': stats.bytes_received,
            'is_connected': stats.is_connected
        }

    def inject_audio_file(self, page: 'Page', audio_path: str) -> bool:
        """Robot Framework keyword to inject audio"""
        return self._run_async(self.inject_audio_to_webrtc(page, audio_path))

    def capture_audio(self, page: 'Page', duration: str,
                      output_path: str = None) -> str:
        """Robot Framework keyword to capture audio"""
        result = self._run_async(
            self.capture_webrtc_audio(page, float(duration), output_path)
        )
        if not result:
            raise AssertionError("Failed to capture audio")
        return result

    def audio_should_be_flowing(self, page: 'Page'):
        """Robot Framework keyword to verify audio is flowing"""
        status = self._run_async(self.get_audio_track_status(page))
        if not status.get('has_local_track') and not status.get('has_remote_track'):
            raise AssertionError("No audio tracks found")
        if status.get('local_muted') and status.get('remote_muted'):
            raise AssertionError("All audio tracks are muted")
        return True
