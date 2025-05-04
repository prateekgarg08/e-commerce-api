from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryInDB(CategoryBase):
    id: str = Field(alias="_id")
    is_active: bool
    

class Category(CategoryInDB):
    pass

class CategoryTree(Category):
    subcategories: List["CategoryTree"] = []