from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.libs.livekit import create_access_token
from app.core.security import get_current_user

router = APIRouter(tags=["livekit"], prefix="/livekit")

class TokenRequest(BaseModel):
    room: str
    name: str = ""

@router.post("/token")
async def get_livekit_token(
    req: TokenRequest,
    current_user = Depends(get_current_user)
):
    identity = str(current_user["_id"])
    name = req.name or current_user.get("name", identity)
    token = create_access_token(identity=identity, room=req.room, name=name)
    return {"token": token} 