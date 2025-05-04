from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.security import get_current_user, get_password_hash
from app.db.database import db
from app.schemas.user import User, UserUpdate

router = APIRouter(tags=["users"], prefix="/users")

@router.get("/me", response_model=User)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=User)
async def update_user_me(user_update: UserUpdate, current_user = Depends(get_current_user)):
    user_data = {k: v for k, v in user_update.dict(exclude_unset=True).items()}
    
    if "password" in user_data:
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
    
    if user_data:
        user_data["updated_at"] = datetime.utcnow()
        await db.users.update_one(
            {"_id": str(current_user["_id"])},
            {"$set": user_data}
        )
    
    updated_user = await db.users.find_one({"_id": str(current_user["_id"])})
    return updated_user

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, current_user = Depends(get_current_user)):
    if current_user["role"] != UserRole.ADMIN and str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = await db.users.find_one({"_id": str(user_id)})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user