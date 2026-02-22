from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
def admin_ping(_: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok", "message": "admin pong"}
