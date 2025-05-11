from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class OrderItemBase(BaseModel):
    product_id: str
    quantity: int
    price: float

class OrderItemOut(OrderItemBase):
    product_name:str

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemInDB(OrderItemBase):
    pass

class OrderBase(BaseModel):
    items: List[OrderItemBase]
    total_amount: float
    shipping_address: str
    contact_phone: str

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    shipping_address: Optional[str] = None
    contact_phone: Optional[str] = None

class OrderInDB(OrderBase):
    id: str = Field(alias="_id")
    user_id: str
    merchant_id: str
    status: str
    created_at: datetime
    updated_at: datetime

class Order(OrderInDB):
    items:List[OrderItemOut]
    merchant_name:str
    user_name:str