from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.db.database import PyObjectId
# from bson import ObjectId
class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    category_id: PyObjectId
    stock_quantity: int = 0
    images: List[str] = []

class ProductCreate(ProductBase):
    category_id: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[str] = None
    stock_quantity: Optional[int] = None
    images: Optional[List[str]] = None
    is_active: Optional[bool] = None

class ProductInDB(ProductBase):
    id: PyObjectId = Field(alias="_id")
    merchant_id: PyObjectId
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ProductOut(ProductBase):
    id: str = Field(alias="_id")
    category_id: str
    merchant_id: str
    average_rating: Optional[float] = None
    review_count: Optional[int] = None
