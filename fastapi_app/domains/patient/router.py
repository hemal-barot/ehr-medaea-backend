import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.core.deps import get_current_active_user
from backend.fastapi_app.db.models import Patient, User, UserOrganization
from .schemas import PatientCreate, PatientUpdate, PatientResponse

router = APIRouter(prefix="/patients", tags=["Patients"])


def _get_org_id(user: User, db: Session) -> Optional[str]:
    uo = db.query(UserOrganization).filter(UserOrganization.user_id == user.id).first()
    return uo.organization_id if uo else None


@router.get("", response_model=List[PatientResponse])
def list_patients(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    org_id = _get_org_id(current_user, db)
    q = db.query(Patient)
    if org_id:
        q = q.filter(Patient.organization_id == org_id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Patient.first_name.ilike(like))
            | (Patient.last_name.ilike(like))
            | (Patient.email.ilike(like))
        )
    if status:
        q = q.filter(Patient.status == status)
    return q.offset(skip).limit(limit).all()


@router.post("", response_model=PatientResponse, status_code=201)
def create_patient(
    payload: PatientCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    org_id = _get_org_id(current_user, db)
    patient = Patient(
        id=str(uuid.uuid4()),
        organization_id=payload.organization_id or org_id,
        **payload.model_dump(exclude={"organization_id"}),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/recent", response_model=List[PatientResponse])
def recent_patients(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    org_id = _get_org_id(current_user, db)
    q = db.query(Patient).order_by(Patient.created_at.desc())
    if org_id:
        q = q.filter(Patient.organization_id == org_id)
    return q.limit(limit).all()


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
