import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.core.deps import get_current_active_user
from backend.fastapi_app.db.models import Encounter, User

router = APIRouter(prefix="/encounters", tags=["Encounters"])


class EncounterCreate(BaseModel):
    patient_id: str
    appointment_id: Optional[str] = None
    encounter_type: Optional[str] = None
    chief_complaint: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None


class EncounterResponse(BaseModel):
    id: str
    patient_id: str
    provider_id: Optional[str] = None
    appointment_id: Optional[str] = None
    encounter_type: Optional[str] = None
    chief_complaint: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[str] = None
    encounter_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/patient/{patient_id}", response_model=List[EncounterResponse])
def patient_encounters(
    patient_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.query(Encounter).filter(Encounter.patient_id == patient_id).all()


@router.post("", response_model=EncounterResponse, status_code=201)
def create_encounter(
    payload: EncounterCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    enc = Encounter(
        id=str(uuid.uuid4()),
        provider_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(enc)
    db.commit()
    db.refresh(enc)
    return enc


@router.patch("/{enc_id}")
def update_encounter(
    enc_id: str,
    payload: EncounterCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    enc = db.query(Encounter).filter(Encounter.id == enc_id).first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(enc, field, value)
    db.commit()
    db.refresh(enc)
    return enc
