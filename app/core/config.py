import os
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "E-commerce API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: List[str] = ["*"]
    
    # MongoDB settings
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "ecommerce")
    CLOUDINARY_CLOUD_NAME: Optional[str] = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: Optional[str] = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: Optional[str] = os.getenv("CLOUDINARY_API_SECRET")
    RAZORPAY_KEY_ID: Optional[str] = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: Optional[str] = os.getenv("RAZORPAY_KEY_SECRET")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    LIVEKIT_API_KEY: Optional[str] = os.getenv("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET: Optional[str] = os.getenv("LIVEKIT_API_SECRET")
    LIVEKIT_URL: Optional[str] = os.getenv("LIVEKIT_URL")
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()