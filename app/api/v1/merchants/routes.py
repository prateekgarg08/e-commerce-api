from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from app.core.security import get_current_user
from app.db.database import db
from app.db.models import UserRole
from app.schemas.merchant import MerchantOut, MerchantCreate, MerchantUpdate
from bson import ObjectId
router = APIRouter(tags=["merchants"], prefix="/merchants")

def to_str_id(merchant):
    if merchant is None:
        return None
    merchant = dict(merchant)
    if "_id" in merchant:
        merchant["_id"] = str(merchant["_id"])
    if "user_id" in merchant:
        merchant["user_id"] = str(merchant["user_id"])
    return merchant

@router.post("")
async def create_merchant(
    merchant_data: MerchantCreate, 
    current_user = Depends(get_current_user)
):
    # Check if user already has a merchant account
    existing = await db.merchants.find_one({"user_id": ObjectId(current_user["_id"])})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a merchant account"
        )
    
    # Create new merchant
    new_merchant = merchant_data.dict()
    new_merchant["user_id"] = ObjectId(current_user["_id"])
    new_merchant["is_verified"] = False
    
    result = await db.merchants.insert_one(new_merchant)
    
    # Update user role to merchant
    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": {"role": UserRole.MERCHANT}}
    )
    
    created_merchant = await db.merchants.find_one({"_id": result.inserted_id})
    return to_str_id(created_merchant)

@router.get("/me")
async def get_merchant_profile(current_user = Depends(get_current_user)):
    if current_user["role"] != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a merchant account"
        )
    
    merchant = await db.merchants.find_one({"user_id": ObjectId(current_user["_id"])})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")
    
    return to_str_id(merchant)

@router.put("/me")
async def update_merchant_profile(
    merchant_update: MerchantUpdate,
    current_user = Depends(get_current_user)
):
    if current_user["role"] != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a merchant account"
        )
    
    merchant = await db.merchants.find_one({"user_id": ObjectId(current_user["_id"])})
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
    return to_str_id(updated_merchant)

@router.get("")
async def list_merchants():
    merchants = await db.merchants.find({}).to_list(1000)
    return [to_str_id(m) for m in merchants]

@router.get("/{merchant_id}")
async def get_merchant(merchant_id: str):
    merchant = await db.merchants.find_one({"_id": ObjectId(merchant_id)})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return to_str_id(merchant)

@router.put("/{merchant_id}/verify")
async def verify_merchant(
    merchant_id: str,
    current_user = Depends(get_current_user)
):
    # Only admins can verify merchants
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can verify merchants"
        )
    
    merchant = await db.merchants.find_one({"_id": ObjectId(merchant_id)})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    await db.merchants.update_one(
        {"_id": ObjectId(merchant_id)},
        {"$set": {"is_verified": True, "verified_at": datetime.utcnow()}}
    )
    
    updated_merchant = await db.merchants.find_one({"_id": ObjectId(merchant_id)})
    return to_str_id(updated_merchant)

@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant(
    merchant_id: str,
    current_user = Depends(get_current_user)
):
    # Only admins can delete merchants
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    merchant = await db.merchants.find_one({"_id": ObjectId(merchant_id)})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    await db.merchants.update_one(
        {"_id": ObjectId(merchant_id)},
        {"$set": {"is_verified": False, "deleted_at": datetime.utcnow()}}
    )
    return None