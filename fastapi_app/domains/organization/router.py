from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.core.deps import get_current_active_user
from backend.fastapi_app.db.models import User, UserOrganization, Organization

router = APIRouter(prefix="/organizations", tags=["Organizations"])


class OrgResponse(BaseModel):
    id: str
    name: str
    org_type: str | None = None
    role: str
    department: str | None = None

    class Config:
        from_attributes = True


@router.get("/my-organizations", response_model=List[OrgResponse])
def my_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(UserOrganization, Organization)
        .join(Organization, UserOrganization.organization_id == Organization.id)
        .filter(UserOrganization.user_id == current_user.id)
        .all()
    )
    result = []
    for uo, org in rows:
        result.append(
            OrgResponse(
                id=org.id,
                name=org.name,
                org_type=org.org_type,
                role=uo.role,
                department=uo.department,
            )
        )
    return result
