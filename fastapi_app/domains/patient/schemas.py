from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = "active"


class PatientCreate(PatientBase):
    organization_id: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None


class PatientResponse(PatientBase):
    id: str
    organization_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
