from fastapi import APIRouter

from app.api.routers import admin_router, auth_router
from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
