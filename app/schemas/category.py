from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.db.database import PyObjectId
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: bool


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryInDB(CategoryBase):
    id: PyObjectId = Field(alias="_id")
    

class CategoryOut(CategoryBase):
    id: str = Field(alias="_id")
    pass

class CategoryTree(CategoryOut):
    subcategories: List["CategoryTree"] = []