from app.api.routers.answers import router as answers_router
from app.api.routers.admin import router as admin_router
from app.api.routers.attempts import router as attempts_router
from app.api.routers.auth import router as auth_router
from app.api.routers.exams import router as exams_router
from app.api.routers.monitoring import router as monitoring_router
from app.api.routers.screenshots import router as screenshots_router
from app.api.routers.student_exams import router as student_exams_router
from app.api.routers.violations import router as violations_router

__all__ = [
    "auth_router",
    "admin_router",
    "exams_router",
    "attempts_router",
    "student_exams_router",
    "answers_router",
    "monitoring_router",
    "screenshots_router",
    "violations_router",
]
