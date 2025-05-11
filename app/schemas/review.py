from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.db.database import PyObjectId

class ReviewBase(BaseModel):
    product_id: PyObjectId
    user_id: PyObjectId
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    product_id: str
    user_id: str

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewInDB(ReviewBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

class ReviewOut(ReviewBase):
    id: str = Field(alias="_id")
    product_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    user_name: Optional[str] = None 