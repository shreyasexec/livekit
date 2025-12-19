#!/usr/bin/env python3
"""Quick test for voice agent - verifies connection and greeting."""

import asyncio
import os
import time

from livekit import api, rtc

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "http://localhost:7880")
API_KEY = os.getenv("LIVEKIT_API_KEY", "1uhwH2Iv3aGFNTCGC3bNv0OhBjsffTdgJJiGDgYfJKw=")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "vh+pYw6eg1DQaMPZH4tdS3t39fwTRvuA4XEqNF37Mf8=")


async def main():
    room_name = f"quick-test-{int(time.time())}"
    print(f"\n{'='*60}")
    print(f"Quick Voice Agent Test")
    print(f"Room: {room_name}")
    print(f"{'='*60}\n")

    # Create room with agent dispatch
    lk_api = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)

    try:
        await lk_api.room.create_room(api.CreateRoomRequest(name=room_name))
        print(f"[OK] Room created: {room_name}")
    except Exception as e:
        print(f"[INFO] Room may exist: {e}")

    # Generate token
    token = (
        api.AccessToken(API_KEY, API_SECRET)
        .with_identity("test-user")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )
    print(f"[OK] Token generated")

    # Connect to room
    room = rtc.Room()

    agent_joined = asyncio.Event()
    greeting_received = asyncio.Event()
    greeting_text = []

    @room.on("participant_connected")
    def on_participant(participant: rtc.RemoteParticipant):
        if "agent" in participant.identity.lower() or participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            print(f"[OK] Agent joined: {participant.identity}")
            agent_joined.set()

    @room.on("track_subscribed")
    def on_track(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print(f"[OK] Audio track subscribed from: {participant.identity}")
            if not greeting_received.is_set():
                # Agent is speaking - greeting!
                asyncio.get_event_loop().call_later(2.0, greeting_received.set)

    @room.on("data_received")
    def on_data(data: bytes, participant: rtc.RemoteParticipant, kind, topic):
        if topic == "transcripts":
            import json
            try:
                msg = json.loads(data.decode())
                print(f"[TRANSCRIPT] {msg.get('speaker', 'unknown')}: {msg.get('text', '')[:80]}")
                greeting_text.append(msg.get('text', ''))
            except:
                pass

    # Connect
    print(f"\n[...] Connecting to room...")
    start = time.time()
    await room.connect(LIVEKIT_URL.replace("http://", "ws://"), token)
    connect_time = (time.time() - start) * 1000
    print(f"[OK] Connected in {connect_time:.0f}ms")

    # Wait for agent
    print(f"[...] Waiting for agent to join...")
    start = time.time()
    try:
        await asyncio.wait_for(agent_joined.wait(), timeout=15.0)
        agent_join_time = (time.time() - start) * 1000
        print(f"[OK] Agent joined in {agent_join_time:.0f}ms")
    except asyncio.TimeoutError:
        print(f"[FAIL] Agent did not join within 15s")
        await room.disconnect()
        await lk_api.aclose()
        return

    # Wait for greeting
    print(f"[...] Waiting for greeting...")
    start = time.time()
    try:
        await asyncio.wait_for(greeting_received.wait(), timeout=10.0)
        greeting_time = (time.time() - start) * 1000
        print(f"[OK] Greeting received in {greeting_time:.0f}ms")
    except asyncio.TimeoutError:
        print(f"[WARN] No greeting audio detected within 10s")

    # Wait a bit more for any transcripts
    await asyncio.sleep(3)

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST RESULTS:")
    print(f"  - Room connection: {connect_time:.0f}ms")
    print(f"  - Agent join time: {agent_join_time:.0f}ms" if 'agent_join_time' in dir() else "  - Agent: NOT JOINED")
    print(f"  - Greeting time: {greeting_time:.0f}ms" if 'greeting_time' in dir() else "  - Greeting: NOT RECEIVED")
    if greeting_text:
        print(f"  - Transcripts received: {len(greeting_text)}")
    print(f"{'='*60}\n")

    # Cleanup
    await room.disconnect()

    try:
        await lk_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
        print(f"[OK] Room deleted")
    except:
        pass

    await lk_api.aclose()


if __name__ == "__main__":
    asyncio.run(main())
