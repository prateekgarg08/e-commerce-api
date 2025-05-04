from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import datetime

from app.core.security import get_current_user
from app.db.database import db
from app.db.models import UserRole
from app.schemas.merchant import Merchant, MerchantCreate, MerchantUpdate

router = APIRouter(tags=["merchants"], prefix="/merchants")

@router.post("", response_model=Merchant)
async def create_merchant(
    merchant_data: MerchantCreate, 
    current_user = Depends(get_current_user)
):
    # Check if user already has a merchant account
    existing = await db.merchants.find_one({"user_id": str(current_user["_id"])})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a merchant account"
        )
    
    # Create new merchant
    new_merchant = merchant_data.dict()
    new_merchant["user_id"] = str(current_user["_id"])
    new_merchant["is_verified"] = False
    
    result = await db.merchants.insert_one(new_merchant)
    
    # Update user role to merchant
    await db.users.update_one(
        {"_id": str(current_user["_id"])},
        {"$set": {"role": UserRole.MERCHANT}}
    )
    
    created_merchant = await db.merchants.find_one({"_id": result.inserted_id})
    return created_merchant

@router.get("/me", response_model=Merchant)
async def get_merchant_profile(current_user = Depends(get_current_user)):
    if current_user["role"] != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a merchant account"
        )
    
    merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")
    
    return merchant

@router.put("/me", response_model=Merchant)
async def update_merchant_profile(
    merchant_update: MerchantUpdate,
    current_user = Depends(get_current_user)
):
    if current_user["role"] != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a merchant account"
        )
    
    merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")
    
    update_data = {k: v for k, v in merchant_update.dict(exclude_unset=True).items()}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.merchants.update_one(
            {"_id": merchant["_id"]},
            {"$set": update_data}
        )
    
    updated_merchant = await db.merchants.find_one({"_id": merchant["_id"]})
    return updated_merchant

@router.get("", response_model=List[Merchant])
async def list_merchants():
    merchants = await db.merchants.find({"is_verified": True}).to_list(1000)
    return merchants

@router.get("/{merchant_id}", response_model=Merchant)
async def get_merchant(merchant_id: str):
    merchant = await db.merchants.find_one({"_id": ObjectId(merchant_id)})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant