from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.webhooks import router as webhook_router
from app.api.v1.admin import router as admin_router
from app.api.v1.mobile import MOBILE_ROUTERS

api_router = APIRouter()

api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(webhook_router, tags=["webhook"])
for _mobile in MOBILE_ROUTERS:
    api_router.include_router(_mobile, tags=["mobile"])
api_router.include_router(admin_router)
