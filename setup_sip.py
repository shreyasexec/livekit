#!/usr/bin/env python3
"""
Setup SIP Trunk and Dispatch Rules for Linphone Integration

This script creates:
1. SIP Inbound Trunk for receiving calls
2. SIP Dispatch Rule to route calls to the AI agent room
"""

import requests
import json
import sys
import os

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
SIP_NUMBER = os.getenv("SIP_NUMBER", "+1234567890")
AGENT_ROOM = os.getenv("AGENT_ROOM", "ai-agent-room")

# For local network, use your machine's IP
# Find it with: ip addr show (Linux) or ipconfig (Windows)
LOCAL_IP = os.getenv("LOCAL_IP", "192.168.1.100")


def create_room(room_name):
    """Create a LiveKit room for the AI agent."""
    print(f"Creating room: {room_name}")

    response = requests.post(
        f"{API_URL}/api/rooms",
        json={
            "name": room_name,
            "empty_timeout": 600,  # 10 minutes
            "max_participants": 10
        }
    )

    if response.status_code == 200:
        print(f"✓ Room created: {room_name}")
        return response.json()
    else:
        print(f"✗ Failed to create room: {response.text}")
        return None


def create_sip_trunk():
    """Create SIP inbound trunk."""
    print(f"\nCreating SIP trunk for number: {SIP_NUMBER}")

    response = requests.post(
        f"{API_URL}/api/sip/trunk",
        json={
            "name": "linphone-trunk",
            "numbers": [SIP_NUMBER],
            "allowed_addresses": ["0.0.0.0/0"]  # Allow all IPs (for testing)
        }
    )

    if response.status_code == 200:
        trunk_data = response.json()
        trunk_id = trunk_data.get("trunk", {}).get("sip_trunk_id")
        print(f"✓ SIP trunk created")
        print(f"  Trunk ID: {trunk_id}")
        print(f"  Number: {SIP_NUMBER}")
        return trunk_id
    else:
        print(f"✗ Failed to create SIP trunk: {response.text}")
        return None


def create_dispatch_rule(trunk_id, room_name):
    """Create SIP dispatch rule to route calls to AI agent room."""
    print(f"\nCreating dispatch rule: {SIP_NUMBER} → {room_name}")

    response = requests.post(
        f"{API_URL}/api/sip/dispatch",
        json={
            "room_name": room_name,
            "trunk_ids": [trunk_id],
            "pin": ""  # No PIN required
        }
    )

    if response.status_code == 200:
        print(f"✓ Dispatch rule created")
        print(f"  Calls to {SIP_NUMBER} will join room: {room_name}")
        return response.json()
    else:
        print(f"✗ Failed to create dispatch rule: {response.text}")
        return None


def print_linphone_config():
    """Print Linphone configuration instructions."""
    print("\n" + "="*60)
    print("Linphone Configuration")
    print("="*60)
    print("\n1. Open Linphone")
    print("2. Go to: Settings → SIP Accounts → Add Account")
    print("3. Configure:")
    print(f"   - Username: your_username")
    print(f"   - SIP Domain: {LOCAL_IP}:5060")
    print(f"   - Password: (leave empty)")
    print(f"   - Transport: UDP")
    print("4. Save and wait for registration")
    print("\n5. To call the AI agent:")
    print(f"   Dial: {SIP_NUMBER}@{LOCAL_IP}:5060")
    print("\n6. The call will be routed to room: {AGENT_ROOM}")
    print("   AI agent will automatically join and respond!")
    print("="*60)


def main():
    print("="*60)
    print("LiveKit SIP Setup for AI Agent")
    print("="*60)
    print(f"\nAPI URL: {API_URL}")
    print(f"SIP Number: {SIP_NUMBER}")
    print(f"Agent Room: {AGENT_ROOM}")
    print(f"Local IP: {LOCAL_IP}")
    print()

    # Check if API is accessible
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code != 200:
            print("✗ Backend API is not accessible!")
            print(f"  Make sure services are running: docker compose ps")
            sys.exit(1)
        print("✓ Backend API is accessible")
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        print(f"  Make sure services are running: docker compose up -d")
        sys.exit(1)

    # Create room for AI agent
    create_room(AGENT_ROOM)

    # Create SIP trunk
    trunk_id = create_sip_trunk()
    if not trunk_id:
        print("\n✗ Failed to create SIP trunk. Exiting.")
        sys.exit(1)

    # Create dispatch rule
    if not create_dispatch_rule(trunk_id, AGENT_ROOM):
        print("\n✗ Failed to create dispatch rule. Exiting.")
        sys.exit(1)

    # Print Linphone config
    print_linphone_config()

    print("\n✓ SIP setup complete!")
    print("\nNext steps:")
    print("1. Configure Linphone with the settings above")
    print("2. Make a test call")
    print("3. Check agent logs: docker compose logs -f agent-worker")


if __name__ == "__main__":
    main()
