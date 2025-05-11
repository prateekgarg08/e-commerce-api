from fastapi import APIRouter
from app.api.v1.orders.routes import router
from app.api.v1.orders.razorpay import router as razorpay_routers