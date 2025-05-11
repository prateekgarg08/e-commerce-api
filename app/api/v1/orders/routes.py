# app/api/v1/orders/routes.py
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime

from app.core.security import get_current_user
from app.db.database import db
from app.db.models import UserRole, OrderStatus
from app.schemas.order import Order, OrderCreate, OrderUpdate
from bson import ObjectId
router = APIRouter(tags=["orders"], prefix="/orders")

@router.post("")
async def create_order(
    order_data: OrderCreate,
    current_user = Depends(get_current_user)
):
    # Validate items and calculate total
    total_amount = 0
    items = []
    merchant_ids = set()  # Track unique merchant IDs
    
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
        
        merchant_ids.add(str(product["merchant_id"]))  # Add merchant ID
        
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
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": product["price"],
            "merchant_id": str(product["merchant_id"])  # Add merchant ID to item
        })
        
        # Add to total
        total_amount += item_total
        
        # Update product stock
        await db.products.update_one(
            {"_id": ObjectId(item.product_id)},
            {"$inc": {"stock_quantity": -item.quantity}}
        )
    
    if len(merchant_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All products in an order must be from the same merchant"
        )

    # Create order
    new_order = {
        "user_id": ObjectId(current_user["_id"]),
        "merchant_id": ObjectId(list(merchant_ids)[0]),  # Set merchant ID
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
    created_order["_id"] = str(created_order["_id"])
    created_order["user_id"] = str(created_order["user_id"])
    created_order["merchant_id"] = str(created_order["merchant_id"])
    return created_order

@router.get("", response_model=List[Order])
async def list_orders(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    # Build query
    query = {}
    if status:
        query["status"] = status
    if current_user["role"] == UserRole.USER:
        query["user_id"] = ObjectId(current_user["_id"])
    elif current_user["role"] == UserRole.MERCHANT:
        merchant = await db.merchants.find_one({"user_id": ObjectId(current_user["_id"])})
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant profile not found"
            )
        query["merchant_id"] = ObjectId(merchant["_id"])
    # Admin can see all orders (no filter needed)

    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$lookup": {
            "from": "merchants",
            "localField": "merchant_id",
            "foreignField": "_id",
            "as": "merchant_info"
        }},
        {"$unwind": {"path": "$merchant_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"merchant_name": "$merchant_info.business_name", "user_name": "$user_info.full_name"}},
        {"$lookup": {
            "from": "products",
            "let": {"items": "$items"},
            "pipeline": [
                {"$match": {"$expr": {"$in": ["$_id", {"$map": {"input": "$$items", "as": "i", "in": {"$toObjectId": "$$i.product_id"}}}]}}},
                {"$project": {"_id": 1, "name": 1}}
            ],
            "as": "products_info"
        }},
        {"$addFields": {
            "items": {
                "$map": {
                    "input": "$items",
                    "as": "item",
                    "in": {
                        "$mergeObjects": [
                            "$$item",
                            {
                                "product_name": {
                                    "$ifNull": [
                                        {
                                            "$arrayElemAt": [
                                                {
                                                    "$map": {
                                                        "input": {
                                                            "$filter": {
                                                                "input": "$products_info",
                                                                "as": "prod",
                                                                "cond": {"$eq": ["$$prod._id", {"$toObjectId": "$$item.product_id"}]}
                                                            }
                                                        },
                                                        "as": "prod",
                                                        "in": "$$prod.name"
                                                    }
                                                },
                                                0
                                            ]
                                        },
                                        ""
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        }},
        {"$project": {"merchant_info": 0, "products_info": 0, "user_info": 0}}
    ]
    cursor = db.orders.aggregate(pipeline)
    orders = await cursor.to_list(length=limit)
    for order in orders:
        order["_id"] = str(order["_id"])
        order["user_id"] = str(order["user_id"])
        order["merchant_id"] = str(order["merchant_id"])
        for item in order.get("items", []):
            if "product_id" in item:
                item["product_id"] = str(item["product_id"])
    return orders

@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    current_user = Depends(get_current_user)
):
    pipeline = [
        {"$match": {"_id": ObjectId(order_id)}},
        {"$lookup": {
            "from": "merchants",
            "localField": "merchant_id",
            "foreignField": "_id",
            "as": "merchant_info"
        }},
        {"$unwind": {"path": "$merchant_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"merchant_name": "$merchant_info.business_name", "user_name": "$user_info.full_name"}},
        {"$lookup": {
            "from": "products",
            "let": {"items": "$items"},
            "pipeline": [
                {"$match": {"$expr": {"$in": ["$_id", {"$map": {"input": "$$items", "as": "i", "in": {"$toObjectId": "$$i.product_id"}}}]}}},
                {"$project": {"_id": 1, "name": 1}}
            ],
            "as": "products_info"
        }},
        {"$addFields": {
            "items": {
                "$map": {
                    "input": "$items",
                    "as": "item",
                    "in": {
                        "$mergeObjects": [
                            "$$item",
                            {
                                "product_name": {
                                    "$ifNull": [
                                        {
                                            "$arrayElemAt": [
                                                {
                                                    "$map": {
                                                        "input": {
                                                            "$filter": {
                                                                "input": "$products_info",
                                                                "as": "prod",
                                                                "cond": {"$eq": ["$$prod._id", {"$toObjectId": "$$item.product_id"}]}
                                                            }
                                                        },
                                                        "as": "prod",
                                                        "in": "$$prod.name"
                                                    }
                                                },
                                                0
                                            ]
                                        },
                                        ""
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        }},
        {"$project": {"merchant_info": 0, "products_info": 0, "user_info": 0}}
    ]
    cursor = db.orders.aggregate(pipeline)
    order = await cursor.to_list(length=1)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order = order[0]
    # Permission checks (same as before)
    if current_user["role"] != UserRole.ADMIN and ((order["user_id"])) != (current_user["_id"]):
        if current_user["role"] == UserRole.MERCHANT:
            merchant = await db.merchants.find_one({"user_id": ObjectId(current_user["_id"])})
            if merchant:
                merchant_products = await db.products.find(
                    {"merchant_id": merchant["_id"]}
                ).to_list(1000)
                merchant_product_ids = [str(p["_id"]) for p in merchant_products]
                has_merchant_items = any(
                    str(item["product_id"]) in merchant_product_ids
                    for item in order["items"]
                )
                if has_merchant_items:
                    order["_id"] = str(order["_id"])
                    order["user_id"] = str(order["user_id"])
                    order["merchant_id"] = str(order["merchant_id"])
                    for item in order.get("items", []):
                        if "product_id" in item:
                            item["product_id"] = str(item["product_id"])
                    return order
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    order["_id"] = str(order["_id"])
    order["user_id"] = str(order["user_id"])
    order["merchant_id"] = str(order["merchant_id"])
    for item in order.get("items", []):
        if "product_id" in item:
            item["product_id"] = str(item["product_id"])
    return order

@router.put("/{order_id}", response_model=Order)
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    current_user = Depends(get_current_user)
):
    # Get order
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions
    
    # Prepare update data
    update_data = {k: v for k, v in order_update.dict(exclude_unset=True).items()}
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_data}
        )
    
    pipeline = [
        {"$match": {"_id": ObjectId(order_id)}},
        {"$lookup": {
            "from": "merchants",
            "localField": "merchant_id",
            "foreignField": "_id",
            "as": "merchant_info"
        }},
        {"$unwind": {"path": "$merchant_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"merchant_name": "$merchant_info.business_name", "user_name": "$user_info.full_name"}},
        {"$lookup": {
            "from": "products",
            "let": {"items": "$items"},
            "pipeline": [
                {"$match": {"$expr": {"$in": ["$_id", {"$map": {"input": "$$items", "as": "i", "in": {"$toObjectId": "$$i.product_id"}}}]}}},
                {"$project": {"_id": 1, "name": 1}}
            ],
            "as": "products_info"
        }},
        {"$addFields": {
            "items": {
                "$map": {
                    "input": "$items",
                    "as": "item",
                    "in": {
                        "$mergeObjects": [
                            "$$item",
                            {
                                "product_name": {
                                    "$ifNull": [
                                        {
                                            "$arrayElemAt": [
                                                {
                                                    "$map": {
                                                        "input": {
                                                            "$filter": {
                                                                "input": "$products_info",
                                                                "as": "prod",
                                                                "cond": {"$eq": ["$$prod._id", {"$toObjectId": "$$item.product_id"}]}
                                                            }
                                                        },
                                                        "as": "prod",
                                                        "in": "$$prod.name"
                                                    }
                                                },
                                                0
                                            ]
                                        },
                                        ""
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        }},
        {"$project": {"merchant_info": 0, "products_info": 0, "user_info": 0}}
    ]
    cursor = db.orders.aggregate(pipeline)
    updated_order = await cursor.to_list(length=1)
    if not updated_order:
        raise HTTPException(status_code=404, detail="Order not found")
    updated_order = updated_order[0]
    updated_order["_id"] = str(updated_order["_id"])
    updated_order["user_id"] = str(updated_order["user_id"])
    updated_order["merchant_id"] = str(updated_order["merchant_id"])
    for item in updated_order.get("items", []):
        if "product_id" in item:
            item["product_id"] = str(item["product_id"])
    return updated_order

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: str,
    current_user = Depends(get_current_user)
):
    # Only admins can delete orders
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"is_active": False, "deleted_at": datetime.utcnow()}}
    )
    return None

@router.patch("/{order_id}/cancel", response_model=Order)
async def cancel_order(
    order_id: str,
    current_user = Depends(get_current_user)
):
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only the order owner can cancel
    if (order["user_id"]) != (current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this order."
        )

    # Only allow cancellation if order is in 'pending' state
    if order["status"].lower() != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order can only be cancelled if it is in 'pending' state."
        )

    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": "cancelled", "updated_at": datetime.utcnow()}}
    )
    updated_order = await db.orders.find_one({"_id": ObjectId(order_id)})
    updated_order["_id"] = str(updated_order["_id"])
    updated_order["user_id"] = str(updated_order["user_id"])
    updated_order["merchant_id"] = str(updated_order["merchant_id"])
    return updated_order