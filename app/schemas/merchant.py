from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.db.database import PyObjectId


class MerchantBase(BaseModel):
    business_name: str
    business_description: Optional[str] = None
    contact_email: EmailStr
    contact_phone: Optional[str] = None

class MerchantCreate(MerchantBase):
    pass

class MerchantUpdate(BaseModel):
    business_name: Optional[str] = None
    business_description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None

class MerchantInDB(MerchantBase):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class MerchantOut(MerchantBase):
    id: str = Field(alias="_id")
    pass