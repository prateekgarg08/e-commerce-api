import os
from livekit import api

def create_access_token(identity: str, room: str, name: str = "") -> str:
    """
    Generate a LiveKit access token for a given user identity and room.
    Optionally, set a display name.
    """
    # Will use LIVEKIT_API_KEY and LIVEKIT_API_SECRET from env vars
    token = api.AccessToken() \
        .with_identity(identity) \
        .with_name(name if name else identity) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room,
        )).to_jwt()
    return token 