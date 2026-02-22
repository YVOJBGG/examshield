from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health_service import get_health

router = APIRouter()


@router.get("/", response_model=dict[str, str])
def root() -> dict[str, str]:
    return {"message": "ExamShield API"}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return get_health()
