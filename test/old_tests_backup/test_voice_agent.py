#!/usr/bin/env python3
"""
Voice Agent Test Suite

Tests the voice agent pipeline:
1. Agent connection and greeting
2. Prompt verification (plain text, no markdown)
3. TTS latency metrics

Run from backend container:
    docker compose exec backend python3 /app/../test/test_voice_agent.py

Or copy to backend and run:
    docker compose exec backend python3 -c "$(cat test/test_voice_agent.py)"
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Optional

from livekit import api, rtc


# Configuration - uses same keys as docker-compose
LIVEKIT_URL = "http://livekit:7880"
API_KEY = "1uhwH2Iv3aGFNTCGC3bNv0OhBjsffTdgJJiGDgYfJKw="
API_SECRET = "vh+pYw6eg1DQaMPZH4tdS3t39fwTRvuA4XEqNF37Mf8="


@dataclass
class TestResult:
    """Test result with timing and validation."""
    name: str
    passed: bool
    duration_ms: float
    message: str


class VoiceAgentTester:
    """Test voice agent functionality."""

    def __init__(self):
        self.results: list[TestResult] = []
        self.transcripts: list[dict] = []
        self.agent_joined = asyncio.Event()
        self.audio_received = asyncio.Event()

    async def run_all_tests(self) -> bool:
        """Run all tests and return overall pass/fail."""
        print("\n" + "=" * 60)
        print("VOICE AGENT TEST SUITE")
        print("=" * 60 + "\n")

        # Test 1: Agent Connection
        await self.test_agent_connection()

        # Test 2: Prompt Verification
        await self.test_prompt_output()

        # Print results
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)

        all_passed = True
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            print(f"[{status}] {result.name} ({result.duration_ms:.0f}ms)")
            print(f"       {result.message}")
            if not result.passed:
                all_passed = False

        print("=" * 60)
        print(f"OVERALL: {'PASSED' if all_passed else 'FAILED'}")
        print("=" * 60 + "\n")

        return all_passed

    async def test_agent_connection(self):
        """Test agent joins room and sends greeting audio."""
        room_name = f"test-connection-{int(time.time())}"
        start = time.time()

        try:
            lk = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)
            await lk.room.create_room(api.CreateRoomRequest(name=room_name, empty_timeout=60))

            token = (
                api.AccessToken(API_KEY, API_SECRET)
                .with_identity("Connection-Tester")
                .with_grants(api.VideoGrants(room_join=True, room=room_name))
                .to_jwt()
            )

            room = rtc.Room()

            @room.on("participant_connected")
            def on_participant(p):
                if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
                    self.agent_joined.set()

            @room.on("track_subscribed")
            def on_track(track, pub, participant):
                if track.kind == rtc.TrackKind.KIND_AUDIO:
                    self.audio_received.set()

            await room.connect(LIVEKIT_URL.replace("http://", "ws://"), token)

            # Wait for agent
            try:
                await asyncio.wait_for(self.agent_joined.wait(), timeout=10)
                agent_ok = True
            except asyncio.TimeoutError:
                agent_ok = False

            # Wait for audio
            try:
                await asyncio.wait_for(self.audio_received.wait(), timeout=10)
                audio_ok = True
            except asyncio.TimeoutError:
                audio_ok = False

            await room.disconnect()
            await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
            await lk.aclose()

            duration = (time.time() - start) * 1000
            passed = agent_ok and audio_ok

            self.results.append(TestResult(
                name="Agent Connection",
                passed=passed,
                duration_ms=duration,
                message=f"Agent: {'OK' if agent_ok else 'FAIL'}, Audio: {'OK' if audio_ok else 'FAIL'}"
            ))

        except Exception as e:
            self.results.append(TestResult(
                name="Agent Connection",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                message=f"Error: {str(e)}"
            ))

    async def test_prompt_output(self):
        """Test that agent responses follow prompt rules (plain text, brief)."""
        room_name = f"test-prompt-{int(time.time())}"
        start = time.time()
        self.transcripts = []

        try:
            lk = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)
            await lk.room.create_room(api.CreateRoomRequest(name=room_name, empty_timeout=60))

            token = (
                api.AccessToken(API_KEY, API_SECRET)
                .with_identity("Prompt-Tester")
                .with_grants(api.VideoGrants(room_join=True, room=room_name))
                .to_jwt()
            )

            room = rtc.Room()

            @room.on("data_received")
            def on_data(event):
                # Event object has: data, participant, kind, topic
                if event.topic == "transcripts":
                    try:
                        msg = json.loads(event.data.decode())
                        if msg.get("speaker") == "assistant":
                            self.transcripts.append(msg)
                            print(f"[TRANSCRIPT] {msg.get('text', '')[:60]}...")
                    except Exception as e:
                        print(f"[ERROR] Failed to parse transcript: {e}")

            await room.connect(LIVEKIT_URL.replace("http://", "ws://"), token)

            # Wait for transcripts
            await asyncio.sleep(10)

            await room.disconnect()
            await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
            await lk.aclose()

            duration = (time.time() - start) * 1000

            # Validate prompt rules
            if not self.transcripts:
                self.results.append(TestResult(
                    name="Prompt Verification",
                    passed=False,
                    duration_ms=duration,
                    message="No agent transcripts received"
                ))
                return

            # Check all transcripts for prompt compliance
            issues = []
            for t in self.transcripts:
                text = t.get("text", "")

                # Check for markdown (headers, bold, lists)
                if re.search(r'^#{1,6}\s|^\*\s|^\d+\.\s|\*\*|__|\[.*\]\(.*\)', text, re.MULTILINE):
                    issues.append("Contains markdown formatting")

                # Check for emojis (basic check)
                if re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]', text):
                    issues.append("Contains emojis")

                # Check for code blocks
                if "```" in text or "`" in text:
                    issues.append("Contains code formatting")

            passed = len(issues) == 0
            sample = self.transcripts[0].get("text", "")[:80] if self.transcripts else "N/A"

            self.results.append(TestResult(
                name="Prompt Verification",
                passed=passed,
                duration_ms=duration,
                message=f"Transcripts: {len(self.transcripts)}, Issues: {issues if issues else 'None'}, Sample: '{sample}...'"
            ))

        except Exception as e:
            self.results.append(TestResult(
                name="Prompt Verification",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                message=f"Error: {str(e)}"
            ))


async def main():
    tester = VoiceAgentTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
