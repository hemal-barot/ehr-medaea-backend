from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    patient_id: Optional[str] = None
    patient_first_name: str
    patient_last_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    condition_type: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = "scheduled"
    location: Optional[str] = None
    location_type: Optional[str] = None
    notes: Optional[str] = None
    organization_id: Optional[str] = None


class AppointmentUpdate(BaseModel):
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    condition_type: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    location_type: Optional[str] = None
    notes: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    status: str


class AppointmentResponse(BaseModel):
    id: str
    patient_id: Optional[str] = None
    provider_id: Optional[str] = None
    patient_first_name: str
    patient_last_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    condition_type: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    location_type: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
