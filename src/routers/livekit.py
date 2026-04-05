"""
LiveKit Router for FastAPI
Provides token generation and room management endpoints
"""
import json
import os
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from livekit import api

# Load environment variables
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://")

router = APIRouter(prefix="/api/livekit", tags=["LiveKit"])


# Request/Response Models
class TokenRequest(BaseModel):
    """Request model for token generation"""
    participant_name: Optional[str] = "user"
    room_name: Optional[str] = None
    agent_name: Optional[str] = None
    fields: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class TokenResponse(BaseModel):
    """Response model for token generation"""
    token: str
    url: str
    room_name: str
    participant_name: str


class RoomInfo(BaseModel):
    """Room information"""
    sid: str
    name: str
    num_participants: int
    creation_time: int
    metadata: str


@router.post("/token", response_model=TokenResponse)
async def generate_token(request: TokenRequest = Body(...)):
    """
    Generate LiveKit access token for a participant
    
    This endpoint creates a JWT token that allows a participant to join a LiveKit room.
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured"
        )
    
    try:
        # Generate unique identifiers if not provided
        import random
        room_name = request.room_name or f"room_{random.randint(1000, 9999)}"
        participant_identity = f"user_{random.randint(1000, 9999)}"
        
        # Create token
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(participant_identity)
        token.with_name(request.participant_name)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        ))
        
        # Add room configuration for agent dispatch
        if request.agent_name or request.fields:
            room_config = {}
            
            if request.agent_name:
                room_config["agents"] = [{"agentName": request.agent_name}]
            
            # Add metadata with fields for data collection
            metadata = request.metadata or {}
            if request.fields:
                metadata["fields"] = request.fields
            
            if metadata:
                token.with_metadata(json.dumps(metadata))
        
        # Generate JWT
        jwt_token = token.to_jwt()
        
        return TokenResponse(
            token=jwt_token,
            url=LIVEKIT_URL.replace("https://", "wss://"),
            room_name=room_name,
            participant_name=request.participant_name
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")


@router.get("/rooms", response_model=List[RoomInfo])
async def list_rooms():
    """
    List all active LiveKit rooms
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured"
        )
    
    try:
        room_service = api.RoomService(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        rooms = await room_service.list_rooms()
        
        return [
            RoomInfo(
                sid=room.sid,
                name=room.name,
                num_participants=room.num_participants,
                creation_time=room.creation_time,
                metadata=room.metadata
            )
            for room in rooms
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list rooms: {str(e)}")


@router.get("/rooms/{room_name}", response_model=RoomInfo)
async def get_room(room_name: str):
    """
    Get information about a specific room
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured"
        )
    
    try:
        room_service = api.RoomService(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        rooms = await room_service.list_rooms([room_name])
        
        if not rooms:
            raise HTTPException(status_code=404, detail="Room not found")
        
        room = rooms[0]
        return RoomInfo(
            sid=room.sid,
            name=room.name,
            num_participants=room.num_participants,
            creation_time=room.creation_time,
            metadata=room.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get room: {str(e)}")


@router.delete("/rooms/{room_name}")
async def delete_room(room_name: str):
    """
    Delete/close a room
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured"
        )
    
    try:
        room_service = api.RoomService(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        await room_service.delete_room(room_name)
        
        return {"message": f"Room {room_name} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete room: {str(e)}")


@router.post("/rooms/{room_name}/metadata")
async def update_room_metadata(
    room_name: str,
    metadata: Dict[str, Any] = Body(...)
):
    """
    Update room metadata (e.g., add data collection fields)
    """
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials not configured"
        )
    
    try:
        room_service = api.RoomService(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        await room_service.update_room_metadata(room_name, json.dumps(metadata))
        
        return {"message": "Metadata updated successfully", "metadata": metadata}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")
