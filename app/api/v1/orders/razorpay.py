from fastapi import APIRouter, HTTPException, status, Body
from app.core.config import settings
import razorpay

router = APIRouter(tags=["razorpay"], prefix="/orders/razorpay")

@router.post("/order")
def create_razorpay_order(
    amount: int = Body(..., embed=True),
    currency: str = Body("INR", embed=True),
    receipt: str = Body(None, embed=True)
):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured.")
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))  # type: ignore
        options = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt or f"order_rcptid",
            "payment_capture": 1,
        }
        print("creating order")
        order = client.order.create(options)
        return {"orderId": order["id"], "order": order}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Razorpay order creation failed: {str(e)}") 