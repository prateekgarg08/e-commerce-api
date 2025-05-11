from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from bson import ObjectId
from app.db.database import db
from app.db.models import UserRole
from app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate
from app.core.security import get_current_user
from fastapi.encoders import jsonable_encoder
from datetime import datetime

router = APIRouter(tags=["reviews"], prefix="/products/{product_id}/reviews")

@router.post("", response_model=ReviewOut)
async def create_review(
    product_id: str,
    review: ReviewCreate,
    current_user=Depends(get_current_user)
):
    # Only users can create reviews
    if current_user["role"] != UserRole.USER:
        raise HTTPException(status_code=403, detail="Only users can create reviews.")
    # Check if product exists
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    # Prevent duplicate reviews by the same user
    existing = await db.reviews.find_one({"product_id": ObjectId(product_id), "user_id": ObjectId(current_user["_id"])})
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product.")
    review_data = review.dict()
    review_data["product_id"] = ObjectId(product_id)
    review_data["user_id"] = ObjectId(current_user["_id"])
    review_data["created_at"] = datetime.utcnow()
    review_data["updated_at"] = datetime.utcnow()
    result = await db.reviews.insert_one(review_data)
    created = await db.reviews.find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    created["product_id"] = str(created["product_id"])
    created["user_id"] = str(created["user_id"])
    # Fetch user_name
    user = await db.users.find_one({"_id": ObjectId(created["user_id"])})
    created["user_name"] = user["full_name"] if user and "full_name" in user else None
    return created

@router.get("", response_model=List[ReviewOut])
async def list_reviews(product_id: str):
    pipeline = [
        {"$match": {"product_id": ObjectId(product_id)}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"user_name": "$user_info.full_name"}},
        {"$project": {
            "_id": 1,
            "product_id": 1,
            "user_id": 1,
            "rating": 1,
            "comment": 1,
            "created_at": 1,
            "updated_at": 1,
            "user_name": 1
        }}
    ]
    cursor = db.reviews.aggregate(pipeline)
    reviews = await cursor.to_list(length=100)
    for review in reviews:
        review["_id"] = str(review["_id"])
        review["product_id"] = str(review["product_id"])
        review["user_id"] = str(review["user_id"])
    return reviews

@router.put("/{review_id}", response_model=ReviewOut)
async def update_review(
    product_id: str,
    review_id: str,
    review_update: ReviewUpdate,
    current_user=Depends(get_current_user)
):
    review = await db.reviews.find_one({"_id": ObjectId(review_id), "product_id": ObjectId(product_id)})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    if str(review["user_id"]) != str(current_user["_id"]) and current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions.")
    update_data = {k: v for k, v in review_update.dict(exclude_unset=True).items()}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.reviews.update_one({"_id": ObjectId(review_id)}, {"$set": update_data})
    updated = await db.reviews.find_one({"_id": ObjectId(review_id)})
    updated["_id"] = str(updated["_id"])
    updated["product_id"] = str(updated["product_id"])
    updated["user_id"] = str(updated["user_id"])
    # Fetch user_name
    user = await db.users.find_one({"_id": ObjectId(updated["user_id"])})
    updated["user_name"] = user["full_name"] if user and "full_name" in user else None
    return updated

@router.delete("/{review_id}", status_code=204)
async def delete_review(
    product_id: str,
    review_id: str,
    current_user=Depends(get_current_user)
):
    review = await db.reviews.find_one({"_id": ObjectId(review_id), "product_id": ObjectId(product_id)})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    if str(review["user_id"]) != str(current_user["_id"]) and current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions.")
    await db.reviews.delete_one({"_id": ObjectId(review_id)})
    return None 