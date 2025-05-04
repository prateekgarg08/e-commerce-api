from fastapi import FastAPI, File, HTTPException, UploadFile,status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, users, merchants, products, categories, orders
from app.core.config import settings
from app.libs.cloudinary import upload_image 
# from app.libs.chromadb import collection
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="E-commerce API with FastAPI and MongoDB",
    version="1.0.0",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(merchants.router, prefix=settings.API_V1_STR)
app.include_router(products.router, prefix=settings.API_V1_STR)
app.include_router(categories.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)


@app.post("/upload")
async def handle_upload(image: UploadFile=File(...)):
    try:
        url = await upload_image(image)

        return {
            "data": {
                "url": url
            }
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e)

@app.get("/")
def root():
    return {"message": "Welcome to E-commerce API"}