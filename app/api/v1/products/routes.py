# app/api/v1/products/routes.py (continued)
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, Query
from datetime import datetime
from bson import ObjectId

from app.core.security import get_current_user
from app.db.database import db
from app.db.models import UserRole
from app.schemas.product import Product, ProductCreate, ProductUpdate
import json
from fastapi.encoders import jsonable_encoder
router = APIRouter(tags=["products"], prefix="/products")
from fastapi.responses import ORJSONResponse
from app.libs.chromadb import add_image,search_image, embedding_function
import numpy as np
from PIL import Image
import io
import requests
from fastapi.logger import logger

@router.post("", response_model=Product)
async def create_product(
    product_data: ProductCreate,
    current_user = Depends(get_current_user)
):
    # Check if user is a merchant
    if current_user["role"] != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only merchants can create products"
        )
    
    # Get merchant profile
    merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant profile not found"
        )
    
    # Check if category exists
    category = await db.categories.find_one({"_id": ObjectId(product_data.category_id)})
    if not category:
        raise HTTPException(    
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Create new product
    new_product = product_data.dict()
    new_product["merchant_id"] = merchant["_id"]
    new_product["category_id"] = str(new_product["category_id"])
    new_product["is_active"] = True

    
    
    result = await db.products.insert_one(new_product)
    created_product = await db.products.find_one({"_id": result.inserted_id})

    image = product_data.images[0]
    metadata = {
        "category_id":product_data.category_id,
        "price":product_data.price,
        "_id":str(result.inserted_id)
    }
    add_image(str(result.inserted_id),image,metadata)
    return created_product

@router.get("", response_model=List)
async def list_products(
    category_id: Optional[str] = None,
    merchant_id: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    # Build query
    query = {"is_active": True}
    
    if category_id:
        query["category_id"] = str(category_id)
    
    if merchant_id:
        query["merchant_id"] = str(merchant_id)
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    # Price filter
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price
        if price_query:
            query["price"] = price_query
    
    # Execute query
    cursor = db.products.find(query).skip(skip).limit(limit)
    products = await cursor.to_list(length=limit)
    for product in products:
        if "_id" in product:
            product["_id"] = str(product["_id"])
        if "category_id" in product:
            product["category_id"] = str(product["category_id"])
        if "merchant_id" in product:
            product["merchant_id"] = str(product["merchant_id"])

    print("got ressults")
    return ORJSONResponse(products) 

@router.get("/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    image = io.BytesIO(requests.get(product["images"][0]).content)
    image_array = np.array(Image.open(image))
    related_products_ids = search_image(image_array,5)
    related_products = [await db.products.find_one({"_id":ObjectId(_id)}) for _id in related_products_ids]
       

    for sku in related_products:
        sku["_id"] = str(sku["_id"])
        sku["merchant_id"] = str(sku["merchant_id"])
        sku["category_id"] = str(sku["category_id"])
    product["related_products"] = related_products[1:5]


    if "_id" in product:
        product["_id"] = str(product["_id"])
    if "category_id" in product:
        product["category_id"] = str(product["category_id"])
    if "merchant_id" in product:
        product["merchant_id"] = str(product["merchant_id"])

    return product

@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user = Depends(get_current_user)
):
    # Get product
    product = await db.products.find_one({"_id": str(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user is the product owner or admin
    if current_user["role"] != UserRole.ADMIN:
        merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
        if not merchant or str(merchant["_id"]) != str(product["merchant_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    # Prepare update data
    update_data = {k: v for k, v in product_update.dict(exclude_unset=True).items()}
    if "category_id" in update_data:
        # Check if category exists
        category = await db.categories.find_one({"_id": str(update_data["category_id"])})
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        update_data["category_id"] = str(update_data["category_id"])
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.products.update_one(
            {"_id": str(product_id)},
            {"$set": update_data}
        )
    
    updated_product = await db.products.find_one({"_id": str(product_id)})
    return updated_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user = Depends(get_current_user)
):
    # Get product
    product = await db.products.find_one({"_id": str(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user is the product owner or admin
    if current_user["role"] != UserRole.ADMIN:
        merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
        if not merchant or str(merchant["_id"]) != str(product["merchant_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    # Soft delete (set is_active to False)
    await db.products.update_one(
        {"_id": str(product_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    return None

@router.get("/merchant/inventory",)
async def get_merchant_inventory(
    current_user = Depends(get_current_user)
):
    # Check if user is a merchant
    if current_user["role"] != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only merchants can access inventory"
        )
    
    # Get merchant profile
    merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant profile not found"
        )
    
    # Get merchant products
    products = await db.products.find({"merchant_id": merchant["_id"]},).to_list(1000)
    for product in products:
        product["_id"] = str(product["_id"])
        product["merchant_id"] = str(product["merchant_id"])
    return products

@router.post("/search/image")
async def get_search_by_image(image: UploadFile):
    # Read the image file
    image_data = await image.read()
    pil_image = Image.open(io.BytesIO(image_data))
    image_np = np.array(pil_image)

    # 1. Compute image embedding
    image_emb = embedding_function([image_np] )[0]

    # 2. Fetch all categories and compute their text embeddings
    categories = await db.categories.find({"is_active": True}).to_list(1000)
    category_texts = [cat["name"] for cat in categories]
    category_ids = [str(cat["_id"]) for cat in categories]
    cat_embs = embedding_function(category_texts)

    # 3. Find closest category (cosine similarity)
    def cosine_sim(a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    sims = [cosine_sim(image_emb, cat_emb) for cat_emb in cat_embs]
    print("Sims",sims)
    best_idx = int(np.argmax(sims))
    best_category_id = category_ids[best_idx]

    # 4. Return all products in that category
    products = await db.products.find({"category_id": str(best_category_id), "is_active": True}).to_list(1000)
    for product in products:
        if "_id" in product:
            product["_id"] = str(product["_id"])
        if "category_id" in product:
            product["category_id"] = str(product["category_id"])
        if "merchant_id" in product:
            product["merchant_id"] = str(product["merchant_id"])
    return {"category_id": best_category_id, "products": products}