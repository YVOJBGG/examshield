import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.core.security import verify_token
from app.db.session import get_db
from app.models import User
from app.schemas.monitoring import MonitoringEventOut, MonitoringStatusIn
from app.services.ws_manager import admin_monitoring_manager

router = APIRouter(tags=["monitoring"])


def _resolve_user_from_token(token: str, db: Session) -> User | None:
    payload = verify_token(token)
    user_id = uuid.UUID(payload["sub"])
    return db.scalar(select(User).where(User.id == user_id))


@router.post("/monitoring/status", response_model=MonitoringEventOut)
async def post_monitoring_status(
    payload: MonitoringStatusIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> MonitoringEventOut:
    event = MonitoringEventOut(
        event_type=payload.event_type,
        timestamp=payload.timestamp,
        user_id=current_user.id,
        username=current_user.username,
        exam_id=payload.exam_id,
        attempt_id=payload.attempt_id,
        status=payload.status,
        message=payload.message,
    )
    await admin_monitoring_manager.broadcast_event(event)
    return event


@router.websocket("/ws/admin/monitor")
async def ws_admin_monitor(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> None:
    try:
        user = _resolve_user_from_token(token, db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    if user is None or user.role != "admin":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Admin access required")
        return

    await admin_monitoring_manager.connect_admin(websocket)
    try:
        while True:
            # Keep the connection alive and absorb optional client-side pings/messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await admin_monitoring_manager.disconnect_admin(websocket)
    except Exception:
        await admin_monitoring_manager.disconnect_admin(websocket)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Monitoring socket error")
