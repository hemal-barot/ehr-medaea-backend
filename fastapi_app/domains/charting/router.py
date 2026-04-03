import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.core.deps import get_current_active_user
from backend.fastapi_app.db.models import Allergy, Medication, Problem, Immunization, User

router = APIRouter(tags=["Clinical Charting"])

# ─── Allergies ────────────────────────────────────────────────────────────────

class AllergyBase(BaseModel):
    allergen: str
    reaction: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = "active"

class AllergyResponse(AllergyBase):
    id: str
    patient_id: str
    class Config:
        from_attributes = True

@router.get("/patients/{patient_id}/allergies", response_model=List[AllergyResponse])
def get_allergies(patient_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return db.query(Allergy).filter(Allergy.patient_id == patient_id).all()

@router.post("/patients/{patient_id}/allergies", response_model=AllergyResponse, status_code=201)
def add_allergy(patient_id: str, payload: AllergyBase, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    obj = Allergy(id=str(uuid.uuid4()), patient_id=patient_id, **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.delete("/patients/{patient_id}/allergies/{allergy_id}", status_code=204)
def delete_allergy(patient_id: str, allergy_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    obj = db.query(Allergy).filter(Allergy.id == allergy_id).first()
    if not obj: raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj); db.commit()

# ─── Medications ──────────────────────────────────────────────────────────────

class MedicationBase(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    status: Optional[str] = "active"
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class MedicationResponse(MedicationBase):
    id: str
    patient_id: str
    class Config:
        from_attributes = True

@router.get("/patients/{patient_id}/medications", response_model=List[MedicationResponse])
def get_medications(patient_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return db.query(Medication).filter(Medication.patient_id == patient_id).all()

@router.post("/patients/{patient_id}/medications", response_model=MedicationResponse, status_code=201)
def add_medication(patient_id: str, payload: MedicationBase, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    obj = Medication(id=str(uuid.uuid4()), patient_id=patient_id, prescribing_provider_id=current_user.id, **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

# ─── Problems ─────────────────────────────────────────────────────────────────

class ProblemBase(BaseModel):
    description: str
    icd_code: Optional[str] = None
    status: Optional[str] = "active"
    onset_date: Optional[str] = None

class ProblemResponse(ProblemBase):
    id: str
    patient_id: str
    class Config:
        from_attributes = True

@router.get("/patients/{patient_id}/problems", response_model=List[ProblemResponse])
def get_problems(patient_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return db.query(Problem).filter(Problem.patient_id == patient_id).all()

@router.post("/patients/{patient_id}/problems", response_model=ProblemResponse, status_code=201)
def add_problem(patient_id: str, payload: ProblemBase, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    obj = Problem(id=str(uuid.uuid4()), patient_id=patient_id, **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

# ─── Immunizations ────────────────────────────────────────────────────────────

class ImmunizationBase(BaseModel):
    vaccine_name: str
    date_administered: Optional[str] = None
    dose_number: Optional[int] = None
    lot_number: Optional[str] = None
    site: Optional[str] = None
    route: Optional[str] = None

class ImmunizationResponse(ImmunizationBase):
    id: str
    patient_id: str
    class Config:
        from_attributes = True

@router.get("/patients/{patient_id}/immunizations", response_model=List[ImmunizationResponse])
def get_immunizations(patient_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return db.query(Immunization).filter(Immunization.patient_id == patient_id).all()

@router.post("/patients/{patient_id}/immunizations", response_model=ImmunizationResponse, status_code=201)
def add_immunization(patient_id: str, payload: ImmunizationBase, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    obj = Immunization(id=str(uuid.uuid4()), patient_id=patient_id, **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj
