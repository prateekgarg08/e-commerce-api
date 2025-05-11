from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from bson import ObjectId

from app.core.security import get_current_user
from app.db.database import db
from app.db.models import UserRole
from app.schemas.category import CategoryOut, CategoryCreate, CategoryUpdate, CategoryTree

router = APIRouter(tags=["categories"], prefix="/categories")

@router.post("", )
async def create_category(
    category_data: CategoryCreate, 
    current_user = Depends(get_current_user)
):
    # Only admins can create categories
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If parent_id is provided, check if it exists
    if category_data.parent_id:
        parent = await db.categories.find_one({"_id": ObjectId(category_data.parent_id)})
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )
    
    # Create new category
    new_category = category_data.dict()
    if new_category.get("parent_id"):
        new_category["parent_id"] = ObjectId(new_category["parent_id"])
    new_category["is_active"] = True
    
    result = await db.categories.insert_one(new_category)
    created_category = await db.categories.find_one({"_id": result.inserted_id})
    created_category["_id"] = str(created_category["_id"])
    if created_category.get("parent_id"):
        created_category["parent_id"] = str(created_category["parent_id"])
    return created_category

@router.get("", response_model=List[CategoryOut])
async def list_categories(current_user = Depends(get_current_user)):
    categories = await db.categories.find().to_list(1000)

    for category in categories:
        if "_id" in category:
            category["_id"] = str(category["_id"])
        if category.get("parent_id"):
            category["parent_id"] = str(category["parent_id"])
    return categories

@router.get("/tree", response_model=List[CategoryTree])
async def get_category_tree():
    # Get all categories
    categories = await db.categories.find({"is_active": True}).to_list(1000)
    
    # Create a mapping of id -> category
    category_map = {str(category["_id"]): dict(category) for category in categories}
    
    # Convert ObjectId to string for parent_id
    for category in category_map.values():
        if category.get("parent_id"):
            category["parent_id"] = str(category["parent_id"])
    
    # Find root categories and build tree
    root_categories = []
    for category_id, category in category_map.items():
        if not category.get("parent_id"):
            category["subcategories"] = []
            root_categories.append(category)
        else:
            parent_id = category["parent_id"]
            if parent_id in category_map:
                if "subcategories" not in category_map[parent_id]:
                    category_map[parent_id]["subcategories"] = []
                category["subcategories"] = []
                category_map[parent_id]["subcategories"].append(category)
    
    return root_categories

@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: str):
    category = await db.categories.find_one({"_id": str(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: str,
    category_update: CategoryUpdate,
    current_user = Depends(get_current_user)
):
    # Only admins can update categories
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if category exists
    category = await db.categories.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Prepare update data
    update_data = {k: v for k, v in category_update.dict(exclude_unset=True).items()}
    if "parent_id" in update_data and update_data["parent_id"]:
        # Check if parent exists
        parent = await db.categories.find_one({"_id": ObjectId(update_data["parent_id"])})
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )
        update_data["parent_id"] = ObjectId(update_data["parent_id"])
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.categories.update_one(
            {"_id": ObjectId(category_id)},
            {"$set": update_data}
        )
    
    updated_category = await db.categories.find_one({"_id": ObjectId(category_id)})
    updated_category["_id"] = str(updated_category["_id"])
    return updated_category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    current_user = Depends(get_current_user)
):
    # Only admins can delete categories
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if category exists
    category = await db.categories.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Soft delete (set is_active to False)
    await db.categories.delete_one(
        {"_id": ObjectId(category_id)},
    )
    
    
    return None

@router.patch("/{category_id}/toggle-status", response_model=CategoryOut)
async def toggle_category_status(
    category_id: str,
    current_user = Depends(get_current_user)
):
    # Only admins can toggle category status
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if category exists
    category = await db.categories.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Toggle is_active status
    new_status = not category.get("is_active", True)
    await db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"is_active": new_status, "updated_at": datetime.utcnow()}}
    )
    
    updated_category = await db.categories.find_one({"_id": ObjectId(category_id)})
    updated_category["_id"] = str(updated_category["_id"])
    return updated_category


