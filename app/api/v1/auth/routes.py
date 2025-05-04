from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import verify_password, create_access_token, get_password_hash
from app.db.database import db
from app.schemas.user import Token, UserCreate, User
from app.db.models import UserRole
from datetime import datetime
from uuid import uuid4

router = APIRouter(tags=["auth"], prefix="/auth")

@router.post("/register")
async def register(user_data: UserCreate):
    # Check if user already exists
    user = await db.users.find_one({"email": user_data.email})
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "role": UserRole.USER,
        "is_active": True,
        "created_at": datetime.utcnow(),  # Add created_at
        "updated_at": datetime.utcnow(), 
        "_id":str(uuid4())
    }
    
    await db.users.insert_one(new_user)
    return {"success":True}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user["_id"]), expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}