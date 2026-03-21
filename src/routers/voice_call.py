"""
Voice Call Router
-----------------
FastAPI endpoints for managing LiveKit voice call rooms.
- POST /voice-call/create   — create a room and return a join token
- GET  /voice-call/token     — get a participant token for an existing room
"""
import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/voice-call", tags=["Voice Call"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateRoomRequest(BaseModel):
    """Request body for creating a new voice call room."""
    room_name: str | None = None
    fields: list[str] | None = None  # fields to collect, e.g. ["Họ và tên", "Số điện thoại"]
    participant_name: str = "customer"


class CreateRoomResponse(BaseModel):
    room_name: str
    participant_token: str
    livekit_url: str


class TokenRequest(BaseModel):
    room_name: str
    participant_name: str = "customer"


class TokenResponse(BaseModel):
    participant_token: str
    livekit_url: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create", response_model=CreateRoomResponse)
async def create_voice_call(payload: CreateRoomRequest):
    """
    Create a LiveKit room for a voice call with the AI agent.

    The room metadata includes the fields to collect, which the LiveKit
    agent server reads when the session starts.

    Returns a participant token that the frontend uses to join the room.
    """
    try:
        from livekit.api import LiveKitAPI

        livekit_url = os.getenv("LIVEKIT_URL", "")
        api_key = os.getenv("LIVEKIT_API_KEY", "")
        api_secret = os.getenv("LIVEKIT_API_SECRET", "")

        if not all([livekit_url, api_key, api_secret]):
            raise HTTPException(
                status_code=500,
                detail="LiveKit credentials not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env",
            )

        # Generate room name
        import uuid
        room_name = payload.room_name or f"voice-call-{uuid.uuid4().hex[:8]}"

        # Room metadata: tells the agent which fields to collect
        metadata = json.dumps(
            {"fields": payload.fields},
            ensure_ascii=False,
        ) if payload.fields else ""

        # Create room + dispatch agent via LiveKit API
        async with LiveKitAPI(
            url=livekit_url,
            api_key=api_key,
            api_secret=api_secret,
        ) as api:
            from livekit.api import (
                CreateRoomRequest as LKCreateRoomRequest,
                CreateAgentDispatchRequest,
            )

            # 1. Create the room
            await api.room.create_room(
                LKCreateRoomRequest(
                    name=room_name,
                    metadata=metadata,
                    empty_timeout=300,  # 5 min timeout
                )
            )

            # 2. Explicitly dispatch the agent to the room
            #    (required because agent_name is set, which disables auto dispatch)
            await api.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(
                    agent_name="data-collection-agent",
                    room=room_name,
                    metadata=metadata,  # pass fields as job metadata
                )
            )

        # Generate participant token
        from livekit.api import AccessToken, VideoGrants
        token = (
            AccessToken(api_key=api_key, api_secret=api_secret)
            .with_identity(payload.participant_name)
            .with_name(payload.participant_name)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                )
            )
        )

        return CreateRoomResponse(
            room_name=room_name,
            participant_token=token.to_jwt(),
            livekit_url=livekit_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/token", response_model=TokenResponse)
async def get_participant_token(payload: TokenRequest):
    """
    Generate a participant token for an existing room.
    Use this when the frontend needs a fresh token to (re)join a room.
    """
    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")
    livekit_url = os.getenv("LIVEKIT_URL", "")

    if not all([api_key, api_secret, livekit_url]):
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured.",
        )

    try:
        from livekit.api import AccessToken, VideoGrants
        token = (
            AccessToken(api_key=api_key, api_secret=api_secret)
            .with_identity(payload.participant_name)
            .with_name(payload.participant_name)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=payload.room_name,
                )
            )
        )

        return TokenResponse(
            participant_token=token.to_jwt(),
            livekit_url=livekit_url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
