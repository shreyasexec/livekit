"""
FastAPI Backend for LiveKit AI Agent Platform

Provides REST API endpoints for:
- Token generation for room access
- Room management
- SIP trunk and dispatch rule configuration
- Health checks
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get configuration from environment
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "http://livekit:7880")
# Public URL (used in tokens/WS returned to browser)
LIVEKIT_PUBLIC_URL = os.getenv("LIVEKIT_PUBLIC_URL", LIVEKIT_URL)
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
    logger.warning("LIVEKIT_API_KEY and LIVEKIT_API_SECRET not set - using defaults")
    LIVEKIT_API_KEY = "devkey"
    LIVEKIT_API_SECRET = "secret"

# Create FastAPI app
app = FastAPI(
    title="Trinity LiveKit AI Agent API",
    description="Backend API for LiveKit-based AI voice and video platform",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class TokenRequest(BaseModel):
    """Request model for token generation."""
    room_name: str
    participant_name: str
    metadata: Optional[str] = None


class TokenResponse(BaseModel):
    """Response model for token generation."""
    token: str
    url: str


class CreateRoomRequest(BaseModel):
    """Request model for room creation."""
    name: str
    empty_timeout: int = 300
    max_participants: int = 50


class SIPTrunkRequest(BaseModel):
    """Request model for SIP trunk creation."""
    name: str
    numbers: list[str]
    allowed_addresses: list[str] = ["0.0.0.0/0"]


class SIPDispatchRuleRequest(BaseModel):
    """Request model for SIP dispatch rule creation."""
    room_name: str
    trunk_ids: list[str]
    pin: str = ""


# Health check
@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status and timestamp
    """
    return {
        "status": "ok",
        "service": "Trinity LiveKit API",
        "timestamp": datetime.utcnow().isoformat(),
        "livekit_url": LIVEKIT_URL,
    }


# Token generation
@app.post("/api/token", response_model=TokenResponse)
async def generate_token(request: TokenRequest):
    """
    Generate LiveKit access token for a participant.

    The token grants permissions to join a room and publish/subscribe tracks.

    Args:
        request: Token request with room and participant details

    Returns:
        Access token and WebSocket URL

    Raises:
        HTTPException: If token generation fails
    """
    try:
        logger.info(
            f"Generating token for {request.participant_name} "
            f"in room {request.room_name}"
        )

        token = api.AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        # Set participant identity and name
        token.with_identity(request.participant_name)
        token.with_name(request.participant_name)

        if request.metadata:
            token.with_metadata(request.metadata)

        # Grant permissions
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )

        jwt_token = token.to_jwt()

        # Generate WebSocket URL from public URL
        ws_url = LIVEKIT_PUBLIC_URL.replace("http", "ws")

        logger.info(
            f"Token generated successfully for {request.participant_name}"
        )
        logger.info(f"LIVEKIT_PUBLIC_URL: {LIVEKIT_PUBLIC_URL}")
        logger.info(f"WebSocket URL: {ws_url}")

        return TokenResponse(
            token=jwt_token,
            url=ws_url,
        )

    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Room management
@app.post("/api/rooms")
async def create_room(request: CreateRoomRequest):
    """
    Create a new LiveKit room.

    Args:
        request: Room creation request

    Returns:
        Room information

    Raises:
        HTTPException: If room creation fails
    """
    try:
        logger.info(f"Creating room: {request.name}")

        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        room = await lk_api.room.create_room(
            api.CreateRoomRequest(
                name=request.name,
                empty_timeout=request.empty_timeout,
                max_participants=request.max_participants,
            )
        )

        await lk_api.aclose()

        logger.info(f"Room created successfully: {request.name}")

        return {
            "room": {
                "sid": room.sid,
                "name": room.name,
                "empty_timeout": room.empty_timeout,
                "max_participants": room.max_participants,
                "creation_time": room.creation_time,
            }
        }

    except Exception as e:
        logger.error(f"Failed to create room: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rooms")
async def list_rooms():
    """
    List all active rooms.

    Returns:
        List of rooms with participant counts

    Raises:
        HTTPException: If listing fails
    """
    try:
        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        rooms = await lk_api.room.list_rooms(api.ListRoomsRequest())

        await lk_api.aclose()

        return {
            "rooms": [
                {
                    "sid": room.sid,
                    "name": room.name,
                    "num_participants": room.num_participants,
                    "creation_time": room.creation_time,
                }
                for room in rooms
            ]
        }

    except Exception as e:
        logger.error(f"Failed to list rooms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# SIP configuration
@app.post("/api/sip/trunk")
async def create_sip_trunk(request: SIPTrunkRequest):
    """
    Create SIP inbound trunk.

    This allows external SIP clients (like Linphone) to call into LiveKit rooms.

    Args:
        request: SIP trunk configuration

    Returns:
        Created trunk information

    Raises:
        HTTPException: If trunk creation fails
    """
    try:
        logger.info(f"Creating SIP trunk: {request.name}")

        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        trunk = await lk_api.sip.create_sip_inbound_trunk(
            api.CreateSIPInboundTrunkRequest(
                trunk=api.SIPInboundTrunkInfo(
                    name=request.name,
                    numbers=request.numbers,
                    allowed_addresses=request.allowed_addresses,
                )
            )
        )

        await lk_api.aclose()

        logger.info(f"SIP trunk created successfully: {request.name}")

        return {"trunk": trunk}

    except Exception as e:
        logger.error(f"Failed to create SIP trunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sip/dispatch")
async def create_sip_dispatch_rule(request: SIPDispatchRuleRequest):
    """
    Create SIP dispatch rule.

    Routes incoming SIP calls to specific LiveKit rooms.
    The AI agent will automatically join when a SIP call arrives.

    Args:
        request: Dispatch rule configuration

    Returns:
        Created rule information

    Raises:
        HTTPException: If rule creation fails
    """
    try:
        logger.info(
            f"Creating SIP dispatch rule for room: {request.room_name}"
        )

        lk_api = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )

        rule = await lk_api.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(
                rule=api.SIPDispatchRule(
                    dispatch_rule_direct=api.SIPDispatchRuleDirect(
                        room_name=request.room_name,
                        pin=request.pin,
                    ),
                ),
                trunk_ids=request.trunk_ids,
            )
        )

        await lk_api.aclose()

        logger.info(
            f"SIP dispatch rule created: calls → room '{request.room_name}'"
        )

        return {"rule": rule}

    except Exception as e:
        logger.error(f"Failed to create SIP dispatch rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Trinity LiveKit AI Agent API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "token": "/api/token (POST)",
            "rooms": "/api/rooms (GET, POST)",
            "sip_trunk": "/api/sip/trunk (POST)",
            "sip_dispatch": "/api/sip/dispatch (POST)",
        }
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Trinity LiveKit API server...")
    logger.info(f"LiveKit URL: {LIVEKIT_URL}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
