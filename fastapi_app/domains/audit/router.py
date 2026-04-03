import uuid
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.core.deps import get_current_active_user
from backend.fastapi_app.db.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: str | None
    ip_address: str | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
