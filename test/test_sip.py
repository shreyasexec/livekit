#!/usr/bin/env python3
"""
SIP End-to-End Test Suite

Tests SIP inbound call flow:
1. Verify SIP trunk exists
2. Verify dispatch rule routes to room
3. Simulate inbound call (requires SIP client)

Run from backend container:
    docker compose exec backend python3 -c "$(cat test/test_sip.py)"
"""

import asyncio
import os
from livekit import api


LIVEKIT_URL = os.getenv("LIVEKIT_URL", "http://livekit:7880")
API_KEY = os.getenv("LIVEKIT_API_KEY", "1uhwH2Iv3aGFNTCGC3bNv0OhBjsffTdgJJiGDgYfJKw=")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "vh+pYw6eg1DQaMPZH4tdS3t39fwTRvuA4XEqNF37Mf8=")


async def test_sip_configuration():
    """Verify SIP trunk and dispatch rule configuration."""
    print("\n" + "=" * 60)
    print("SIP CONFIGURATION TEST")
    print("=" * 60 + "\n")

    lk = api.LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)
    all_ok = True

    # Test 1: Check inbound trunks
    print("[1] Checking SIP Inbound Trunks...")
    try:
        trunks = await lk.sip.list_inbound_trunk(api.ListSIPInboundTrunkRequest())
        if trunks.items:
            for t in trunks.items:
                print(f"    [OK] Trunk: {t.name} (ID: {t.sip_trunk_id})")
                print(f"         Numbers: {t.numbers}")
                print(f"         Allowed: {t.allowed_addresses}")
        else:
            print("    [FAIL] No inbound trunks configured")
            all_ok = False
    except Exception as e:
        print(f"    [FAIL] Error: {e}")
        all_ok = False

    # Test 2: Check dispatch rules
    print("\n[2] Checking SIP Dispatch Rules...")
    try:
        rules = await lk.sip.list_dispatch_rule(api.ListSIPDispatchRuleRequest())
        if rules.items:
            for r in rules.items:
                print(f"    [OK] Rule: {r.sip_dispatch_rule_id}")
                print(f"         Trunk IDs: {r.trunk_ids}")
                if r.rule.dispatch_rule_direct:
                    room = r.rule.dispatch_rule_direct.room_name
                    print(f"         Routes to: {room}")
        else:
            print("    [FAIL] No dispatch rules configured")
            all_ok = False
    except Exception as e:
        print(f"    [FAIL] Error: {e}")
        all_ok = False

    # Test 3: Verify room can be created
    print("\n[3] Testing room creation for SIP calls...")
    try:
        room = await lk.room.create_room(
            api.CreateRoomRequest(name="ai-agent-room", empty_timeout=300)
        )
        print(f"    [OK] Room ready: {room.name} (sid: {room.sid})")
    except Exception as e:
        print(f"    [FAIL] Error: {e}")
        all_ok = False

    await lk.aclose()

    # Summary
    print("\n" + "=" * 60)
    print("SIP CALL INSTRUCTIONS")
    print("=" * 60)
    print("""
LINPHONE CONFIGURATION (No Registration Required):

1. Account Settings:
   - SIP Account: Create "Direct Call" account (no registration)
   - Display Name: YourName
   - Username: caller (any identifier)
   - SIP Domain: 192.168.20.62
   - Transport: UDP
   - Registration: DISABLED (important!)

2. To Call the AI Agent:
   - Open Linphone dialpad
   - Dial: sip:+1234567890@192.168.20.62
   - Or: +1234567890 (if domain is set)

3. Alternative Direct Room Call:
   - Dial: sip:ai-agent-room@192.168.20.62

The call routes to room 'ai-agent-room' where the AI agent joins.
""")
    print("=" * 60)
    print(f"RESULT: {'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}")
    print("=" * 60 + "\n")

    return all_ok


if __name__ == "__main__":
    success = asyncio.run(test_sip_configuration())
    exit(0 if success else 1)
