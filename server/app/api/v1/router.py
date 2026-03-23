from fastapi import APIRouter

from app.api.routers import (
    admin_router,
    answers_router,
    attempts_router,
    auth_router,
    exams_router,
    monitoring_router,
    screenshots_router,
    student_exams_router,
    violations_router,
)
from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(exams_router)
api_router.include_router(attempts_router)
api_router.include_router(student_exams_router)
api_router.include_router(answers_router)
api_router.include_router(monitoring_router)
api_router.include_router(screenshots_router)
api_router.include_router(violations_router)
