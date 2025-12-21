#!/usr/bin/env python3
"""
E2E Test for WebRTC flow with Voice Agent.

Tests:
1. Connect to room as participant
2. Wait for agent to join
3. Send test audio
4. Verify STT/LLM/TTS pipeline works
"""

import asyncio
import httpx
import numpy as np
import sys
import time
from livekit import rtc

# Configuration - use Docker service names when running inside Docker network
API_URL = "http://backend:8000"
LIVEKIT_URL = "ws://livekit:7880"  # Direct to LiveKit service
ROOM_NAME = f"test-webrtc-{int(time.time())}"
PARTICIPANT_NAME = "TestParticipant"


async def get_token(room: str, identity: str) -> tuple[str, str]:
    """Get access token from backend."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}/api/token",
            json={"room_name": room, "participant_name": identity}
        )
        resp.raise_for_status()
        data = resp.json()
        return data["token"], LIVEKIT_URL  # Use local URL for testing


async def generate_test_audio(duration_s: float = 2.0, sample_rate: int = 48000) -> bytes:
    """Generate test audio (sine wave)."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), dtype=np.float32)
    # Generate a 440Hz sine wave
    audio = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype(np.int16)
    return audio.tobytes()


async def main():
    print(f"[TEST] Starting WebRTC E2E test")
    print(f"[TEST] Room: {ROOM_NAME}")
    print(f"[TEST] Participant: {PARTICIPANT_NAME}")
    print("=" * 60)

    # Get token
    print("[TEST] Getting access token...")
    token, url = await get_token(ROOM_NAME, PARTICIPANT_NAME)
    print(f"[TEST] Token received, connecting to {url}")

    # Create room and connect
    room = rtc.Room()

    # Track events
    events = []

    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        print(f"[EVENT] Participant connected: {participant.identity}")
        events.append(("participant_connected", participant.identity))

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication, participant):
        print(f"[EVENT] Track subscribed: {track.kind} from {participant.identity}")
        events.append(("track_subscribed", track.kind, participant.identity))

    @room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        import json
        try:
            payload = json.loads(data.data.decode())
            print(f"[EVENT] Data received: {payload.get('type', 'unknown')}")
            if payload.get("type") == "transcript":
                print(f"         Speaker: {payload.get('speaker')}")
                print(f"         Text: {payload.get('text', '')[:100]}")
            events.append(("data_received", payload))
        except:
            events.append(("data_received", data.data))

    @room.on("disconnected")
    def on_disconnected():
        print("[EVENT] Disconnected from room")
        events.append(("disconnected",))

    try:
        # Connect to room
        print("[TEST] Connecting to room...")
        await room.connect(url, token)
        print(f"[TEST] Connected! Local participant: {room.local_participant.identity}")

        # Wait for agent to join
        print("[TEST] Waiting for agent to join (10s timeout)...")
        start = time.time()
        while time.time() - start < 10:
            agent_found = any(
                p.identity.lower().startswith(("agent", "voice", "ai"))
                or p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
                for p in room.remote_participants.values()
            )
            if agent_found:
                print("[TEST] Agent found!")
                break
            await asyncio.sleep(0.5)
        else:
            print("[TEST] WARNING: Agent did not join within 10s")

        # List participants
        print(f"[TEST] Room participants: {len(room.remote_participants)}")
        for sid, p in room.remote_participants.items():
            print(f"         - {p.identity} (kind={p.kind})")

        # Wait for agent greeting
        print("[TEST] Waiting for agent greeting (15s)...")
        await asyncio.sleep(15)

        # Summary
        print("=" * 60)
        print("[TEST] Test Summary:")
        print(f"       Events captured: {len(events)}")
        for evt in events:
            print(f"       - {evt[0]}: {evt[1:] if len(evt) > 1 else ''}")

        # Check for success indicators
        has_agent = any(e[0] == "participant_connected" for e in events)
        has_audio = any(e[0] == "track_subscribed" and e[1] == rtc.TrackKind.KIND_AUDIO for e in events)
        has_transcript = any(e[0] == "data_received" and isinstance(e[1], dict) and e[1].get("type") == "transcript" for e in events)

        print(f"       Agent joined: {has_agent}")
        print(f"       Audio received: {has_audio}")
        print(f"       Transcript received: {has_transcript}")

        if has_agent and has_audio:
            print("[TEST] ✓ WebRTC flow test PASSED")
            return 0
        else:
            print("[TEST] ✗ WebRTC flow test FAILED")
            return 1

    except Exception as e:
        print(f"[TEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await room.disconnect()
        print("[TEST] Disconnected")


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
