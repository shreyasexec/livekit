"""
LiveKit Token Generation for Testing
Generates access tokens for test participants
"""

import os
from livekit import api

class TokenGenerator:
    """Generate LiveKit access tokens for test participants"""

    ROBOT_LIBRARY_SCOPE = 'TEST'

    def __init__(self):
        # Read from environment
        self.api_key = os.getenv('LIVEKIT_API_KEY', 'devkey')
        self.api_secret = os.getenv('LIVEKIT_API_SECRET', 'secret')

    def generate_token(self, room_name: str, participant_name: str, ttl: int = 300) -> str:
        """Generate access token for LiveKit room

        Args:
            room_name: Room name to join
            participant_name: Participant identity
            ttl: Token time-to-live in seconds (default 300 = 5 minutes)

        Returns:
            JWT access token string
        """
        token = api.AccessToken(self.api_key, self.api_secret)
        token.with_identity(participant_name)
        token.with_name(participant_name)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
        from datetime import timedelta
        token.with_ttl(timedelta(seconds=ttl))

        jwt_token = token.to_jwt()
        print(f"Generated token for {participant_name} in room {room_name}")
        return jwt_token
