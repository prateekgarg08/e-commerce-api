from fastapi import APIRouter
from app.api.v1.products.routes import router as products_router
from app.api.v1.products.reviews import router as reviews_router

router = APIRouter()
router.include_router(products_router)
router.include_router(reviews_router)