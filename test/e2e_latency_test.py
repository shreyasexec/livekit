#!/usr/bin/env python3
"""
E2E Latency Test for LiveKit Voice Agent
Measures end-to-end response time from speech to agent response.
"""

import asyncio
import json
import os
import time
import wave
import io
import struct

from livekit import api, rtc

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "http://livekit:7880")
API_KEY = os.getenv("LIVEKIT_API_KEY", "1uhwH2Iv3aGFNTCGC3bNv0OhBjsffTdgJJiGDgYfJKw=")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "vh+pYw6eg1DQaMPZH4tdS3t39fwTRvuA4XEqNF37Mf8=")


def generate_test_audio(text_hint: str = "Hello", duration_ms: int = 1000, sample_rate: int = 16000) -> bytes:
    """Generate simple test audio (sine wave as placeholder)."""
    import math
    samples = int(sample_rate * duration_ms / 1000)
    audio = []
    freq = 440  # A4 note
    for i in range(samples):
        sample = int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sample_rate))
        audio.append(struct.pack('<h', sample))
    return b''.join(audio)


async def run_latency_test():
    room_name = f"latency-test-{int(time.time())}"
    print(f"\n{'='*60}")
    print(f"E2E Voice Agent Latency Test")
    print(f"Room: {room_name}")
    print(f"{'='*60}\n")

    # Create room
    lk_api = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)

    try:
        await lk_api.room.create_room(api.CreateRoomRequest(name=room_name))
        print(f"[OK] Room created")
    except Exception as e:
        print(f"[INFO] Room exists: {e}")

    # Generate token with audio publish permission
    token = (
        api.AccessToken(API_KEY, API_SECRET)
        .with_identity("latency-test-user")
        .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
        .to_jwt()
    )

    # Connect to room
    room = rtc.Room()

    # Metrics
    metrics = {
        "agent_join_time": None,
        "greeting_time": None,
        "first_response_time": None,
        "responses": [],
    }

    agent_joined = asyncio.Event()
    greeting_received = asyncio.Event()
    response_received = asyncio.Event()
    speech_start_time = None

    @room.on("participant_connected")
    def on_participant(participant: rtc.RemoteParticipant):
        if "agent" in participant.identity.lower():
            print(f"[OK] Agent joined: {participant.identity}")
            agent_joined.set()

    @room.on("track_subscribed")
    def on_track(track: rtc.Track, pub: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            if not greeting_received.is_set():
                greeting_received.set()
                print(f"[OK] Greeting audio received")
            elif speech_start_time:
                latency = (time.time() - speech_start_time) * 1000
                metrics["responses"].append(latency)
                print(f"[LATENCY] Response received in {latency:.0f}ms")
                response_received.set()

    # Connect
    print(f"[...] Connecting to room...")
    start = time.time()
    await room.connect(LIVEKIT_URL.replace("http://", "ws://"), token)
    connect_time = (time.time() - start) * 1000
    print(f"[OK] Connected in {connect_time:.0f}ms")

    # Wait for agent
    print(f"[...] Waiting for agent...")
    start = time.time()
    try:
        await asyncio.wait_for(agent_joined.wait(), timeout=15.0)
        metrics["agent_join_time"] = (time.time() - start) * 1000
        print(f"[OK] Agent joined in {metrics['agent_join_time']:.0f}ms")
    except asyncio.TimeoutError:
        print(f"[FAIL] Agent did not join within 15s")
        await cleanup(room, lk_api, room_name)
        return metrics

    # Wait for greeting
    print(f"[...] Waiting for greeting...")
    start = time.time()
    try:
        await asyncio.wait_for(greeting_received.wait(), timeout=15.0)
        metrics["greeting_time"] = (time.time() - start) * 1000
        print(f"[OK] Greeting received in {metrics['greeting_time']:.0f}ms")
    except asyncio.TimeoutError:
        print(f"[WARN] No greeting within 15s")

    # Let greeting play
    await asyncio.sleep(3)

    # Publish audio to test response
    print(f"\n[...] Publishing test audio...")
    audio_source = rtc.AudioSource(sample_rate=16000, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("test-audio", audio_source)

    pub_options = rtc.TrackPublishOptions()
    pub_options.source = rtc.TrackSource.SOURCE_MICROPHONE

    await room.local_participant.publish_track(track, pub_options)
    print(f"[OK] Audio track published")

    # Send audio and measure response time
    for i in range(3):
        speech_start_time = time.time()
        response_received.clear()

        # Generate and send audio
        audio_data = generate_test_audio(duration_ms=1000)

        # Send in chunks (20ms frames)
        chunk_size = 320 * 2  # 20ms at 16kHz, 2 bytes per sample
        for j in range(0, len(audio_data), chunk_size):
            chunk = audio_data[j:j+chunk_size]
            if len(chunk) < chunk_size:
                chunk = chunk + b'\x00' * (chunk_size - len(chunk))

            # Create audio frame
            samples = [struct.unpack('<h', chunk[k:k+2])[0] for k in range(0, len(chunk), 2)]
            frame = rtc.AudioFrame.create(16000, 1, samples)
            await audio_source.capture_frame(frame)
            await asyncio.sleep(0.02)  # 20ms

        print(f"[...] Test {i+1}/3: Waiting for response...")

        try:
            await asyncio.wait_for(response_received.wait(), timeout=20.0)
        except asyncio.TimeoutError:
            print(f"[WARN] No response for test {i+1}")

        await asyncio.sleep(2)  # Wait between tests

    # Cleanup
    await cleanup(room, lk_api, room_name)

    # Print results
    print(f"\n{'='*60}")
    print(f"LATENCY TEST RESULTS")
    print(f"{'='*60}")
    print(f"  Agent join time:  {metrics['agent_join_time']:.0f}ms" if metrics['agent_join_time'] else "  Agent join time:  N/A")
    print(f"  Greeting time:    {metrics['greeting_time']:.0f}ms" if metrics['greeting_time'] else "  Greeting time:    N/A")

    if metrics["responses"]:
        avg = sum(metrics["responses"]) / len(metrics["responses"])
        print(f"  Response times:   {[f'{r:.0f}ms' for r in metrics['responses']]}")
        print(f"  Average latency:  {avg:.0f}ms")

        if avg < 2000:
            print(f"\n[PASS] Average latency under 2s target!")
        elif avg < 4000:
            print(f"\n[WARN] Average latency between 2-4s - needs improvement")
        else:
            print(f"\n[FAIL] Average latency over 4s - unacceptable for voice AI")
    else:
        print(f"  Response times:   No responses received")

    print(f"{'='*60}\n")

    return metrics


async def cleanup(room, lk_api, room_name):
    """Clean up resources."""
    try:
        await room.disconnect()
    except:
        pass

    try:
        await lk_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
        print(f"[OK] Room deleted")
    except:
        pass

    await lk_api.aclose()


if __name__ == "__main__":
    asyncio.run(run_latency_test())
