# app/api/v1/orders/routes.py
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from bson import ObjectId

from app.core.security import get_current_user
from app.db.database import db
from app.db.models import UserRole, OrderStatus
from app.schemas.order import Order, OrderCreate, OrderUpdate

router = APIRouter(tags=["orders"], prefix="/orders")

@router.post("")
async def create_order(
    order_data: OrderCreate,
    current_user = Depends(get_current_user)
):
    # Validate items and calculate total
    total_amount = 0
    items = []
    
    for item in order_data.items:
        # Check if product exists and is active
        product = await db.products.find_one({
            "_id": ObjectId(item.product_id),
            "is_active": True
        })
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item.product_id} not found or inactive"
            )
        
        # Check if enough stock
        if product["stock_quantity"] < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for product {product['name']}"
            )
        
        # Calculate item total
        item_total = product["price"] * item.quantity
        
        # Add to items list
        items.append({
            "product_id": str(item.product_id),
            "quantity": item.quantity,
            "price": product["price"]
        })
        
        # Add to total
        total_amount += item_total
        
        # Update product stock
        await db.products.update_one(
            {"_id": str(item.product_id)},
            {"$inc": {"stock_quantity": -item.quantity}}
        )
    
    # Create order
    new_order = {
        "_id":str(uuid4()),
        "user_id": str(current_user["_id"]),
        "items": items,
        "total_amount": total_amount,
        "status": OrderStatus.PENDING,
        "shipping_address": order_data.shipping_address,
        "contact_phone": order_data.contact_phone,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.orders.insert_one(new_order)
    created_order = await db.orders.find_one({"_id": result.inserted_id})

   

    return created_order

@router.get("", response_model=List[Order])
async def list_orders(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    # Build query
    query = {"user_id": str(current_user["_id"])}
    
    if status:
        query["status"] = status
    
    # Execute query
    cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)
    return orders

@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    current_user = Depends(get_current_user)
):
    order = await db.orders.find_one({"_id": str(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if user is the order owner or admin
    if current_user["role"] != UserRole.ADMIN and str(order["user_id"]) != str(current_user["_id"]):
        # Check if user is a merchant and has products in the order
        if current_user["role"] == UserRole.MERCHANT:
            merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
            if merchant:
                # Get merchant products
                merchant_products = await db.products.find(
                    {"merchant_id": merchant["_id"]}
                ).to_list(1000)
                merchant_product_ids = [str(p["_id"]) for p in merchant_products]
                
                # Check if any order item is from this merchant
                has_merchant_items = any(
                    str(item["product_id"]) in merchant_product_ids
                    for item in order["items"]
                )
                
                if has_merchant_items:
                    return order
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return order

@router.put("/{order_id}", response_model=Order)
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    current_user = Depends(get_current_user)
):
    # Get order
    order = await db.orders.find_one({"_id": str(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions
    is_admin = current_user["role"] == UserRole.ADMIN
    is_order_owner = str(order["user_id"]) == str(current_user["_id"])
    
    # Only admins can update status
    if "status" in order_update.dict(exclude_unset=True) and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update order status"
        )
    
    # Only order owner can update shipping address and contact phone
    if not is_admin and not is_order_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Prepare update data
    update_data = {k: v for k, v in order_update.dict(exclude_unset=True).items()}
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.orders.update_one(
            {"_id": str(order_id)},
            {"$set": update_data}
        )
    
    updated_order = await db.orders.find_one({"_id": str(order_id)})
    return updated_order

@router.get("/merchant/orders", response_model=List[Order])
async def get_merchant_orders(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    # Check if user is a merchant
    if current_user["role"] != UserRole.MERCHANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only merchants can access this endpoint"
        )
    
    # Get merchant profile
    merchant = await db.merchants.find_one({"user_id": str(current_user["_id"])})
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant profile not found"
        )
    
    # Get merchant products
    merchant_products = await db.products.find(
        {"merchant_id": ObjectId(merchant["_id"])}
    ).to_list(1000)
    merchant_product_ids = [p["_id"] for p in merchant_products]
    
    # Build query for orders that contain merchant products
    query = {
        "items.product_id": {"$in": merchant_product_ids}
    }
    
    if status:
        query["status"] = status
    
    # Execute query
    cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)
    return orders