import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, String, Text, Integer, JSON
)
from sqlalchemy.orm import relationship

from backend.fastapi_app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    org_type = Column(String)
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    zip = Column(String)
    npi = Column(String)
    tax_id = Column(String)
    phone = Column(String)
    website = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    users = relationship("UserOrganization", back_populates="organization")
    patients = relationship("Patient", back_populates="organization")
    appointments = relationship("Appointment", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    phone = Column(String)
    role = Column(String, default="doctor")
    specialty = Column(String)
    npi = Column(String)
    dea = Column(String)
    license_number = Column(String)
    license_state = Column(String)
    license_expiry = Column(String)
    provider_type = Column(String)
    avatar_url = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Email verification
    email_verification_token = Column(String, nullable=True, index=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # MFA
    mfa_enabled = Column(Boolean, default=False)
    mfa_method = Column(String, nullable=True)  # "authenticator" | "sms" | "email"
    mfa_secret_encrypted = Column(String, nullable=True)  # encrypted TOTP secret
    mfa_phone = Column(String, nullable=True)  # E.164 phone for SMS MFA
    mfa_backup_codes = Column(JSON, nullable=True)  # list of backup code hashes

    # Consents (HIPAA)
    hipaa_consent = Column(Boolean, default=False)
    hipaa_consent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    organizations = relationship("UserOrganization", back_populates="user")
    appointments = relationship("Appointment", back_populates="provider", foreign_keys="[Appointment.provider_id]")


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    role = Column(String, default="doctor")
    department = Column(String)
    permissions = Column(JSON, nullable=True)

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="users")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=_uuid)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    date_of_birth = Column(String)
    gender = Column(String)
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    zip = Column(String)
    race = Column(String)
    ethnicity = Column(String)
    preferred_language = Column(String)
    marital_status = Column(String)
    ssn_last4 = Column(String)
    mrn = Column(String)  # Medical Record Number
    status = Column(String, default="active")
    organization_id = Column(String, ForeignKey("organizations.id"))
    primary_provider_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    organization = relationship("Organization", back_populates="patients")
    appointments = relationship("Appointment", back_populates="patient")
    encounters = relationship("Encounter", back_populates="patient")
    allergies = relationship("Allergy", back_populates="patient")
    medications = relationship("Medication", back_populates="patient")
    problems = relationship("Problem", back_populates="patient")
    immunizations = relationship("Immunization", back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=_uuid)
    patient_id = Column(String, ForeignKey("patients.id"))
    provider_id = Column(String, ForeignKey("users.id"))
    patient_first_name = Column(String, nullable=False)
    patient_last_name = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer, default=30)
    visit_type = Column(String)
    room = Column(String)
    condition_type = Column(String)
    reason = Column(Text)
    status = Column(String, default="scheduled")
    location = Column(String)
    location_type = Column(String)
    notes = Column(Text)
    organization_id = Column(String, ForeignKey("organizations.id"))
    created_at = Column(DateTime(timezone=True), default=_now)

    patient = relationship("Patient", back_populates="appointments")
    provider = relationship("User", back_populates="appointments", foreign_keys=[provider_id])
    organization = relationship("Organization", back_populates="appointments")


class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(String, primary_key=True, default=_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    provider_id = Column(String, ForeignKey("users.id"))
    appointment_id = Column(String, ForeignKey("appointments.id"))
    encounter_type = Column(String)
    chief_complaint = Column(Text)
    subjective = Column(Text)
    objective = Column(Text)
    assessment = Column(Text)
    plan = Column(Text)
    status = Column(String, default="open")
    encounter_date = Column(DateTime(timezone=True), default=_now)
    created_at = Column(DateTime(timezone=True), default=_now)

    patient = relationship("Patient", back_populates="encounters")


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(String, primary_key=True, default=_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    allergen = Column(String, nullable=False)
    allergen_type = Column(String)  # drug, food, environmental, latex
    reaction = Column(String)
    severity = Column(String)  # mild, moderate, severe, life-threatening
    status = Column(String, default="active")
    onset_date = Column(String)
    snomed_code = Column(String)
    created_at = Column(DateTime(timezone=True), default=_now)

    patient = relationship("Patient", back_populates="allergies")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(String, primary_key=True, default=_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    name = Column(String, nullable=False)
    ndc_code = Column(String)
    rxnorm_code = Column(String)
    dosage = Column(String)
    frequency = Column(String)
    route = Column(String)
    status = Column(String, default="active")
    prescribing_provider_id = Column(String, ForeignKey("users.id"))
    start_date = Column(String)
    end_date = Column(String)
    refills = Column(Integer, default=0)
    instructions = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    patient = relationship("Patient", back_populates="medications")


class Problem(Base):
    __tablename__ = "problems"

    id = Column(String, primary_key=True, default=_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    description = Column(String, nullable=False)
    icd10_code = Column(String)
    snomed_code = Column(String)
    status = Column(String, default="active")
    onset_date = Column(String)
    resolved_date = Column(String)
    chronic = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    patient = relationship("Patient", back_populates="problems")


class Immunization(Base):
    __tablename__ = "immunizations"

    id = Column(String, primary_key=True, default=_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    vaccine_name = Column(String, nullable=False)
    cvx_code = Column(String)  # CDC CVX vaccine code
    date_administered = Column(String)
    dose_number = Column(Integer)
    lot_number = Column(String)
    site = Column(String)
    route = Column(String)
    administered_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    vis_published_date = Column(String)
    created_at = Column(DateTime(timezone=True), default=_now)

    patient = relationship("Patient", back_populates="immunizations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String)
    resource_id = Column(String)
    details = Column(Text)
    ip_address = Column(String)
    user_agent = Column(String)
    phi_accessed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    patient_id = Column(String, ForeignKey("patients.id"))
    appointment_id = Column(String, ForeignKey("appointments.id"))
    uploaded_by = Column(String, ForeignKey("users.id"))
    file_name = Column(String)
    file_url = Column(String)
    document_type = Column(String)
    loinc_code = Column(String)
    created_at = Column(DateTime(timezone=True), default=_now)


# ─── Calendar / Scheduling tables ────────────────────────────────────────────

class PtoRequest(Base):
    """PTO, sick leave, conference, and blocked time requests per provider."""
    __tablename__ = "pto_requests"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    type = Column(String, nullable=False)        # PTO | Sick | Conference | Blocked
    status = Column(String, default="pending")  # pending | approved | denied
    date_from = Column(String, nullable=False)  # ISO date string  e.g. "2026-04-01"
    date_to = Column(String, nullable=False)
    duration = Column(String)                   # human label e.g. "5 days"
    coverage_provider = Column(String)          # free-text name of covering provider
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", foreign_keys=[user_id])


class AvailabilityRule(Base):
    """Automated scheduling rules and constraints for a clinic."""
    __tablename__ = "availability_rules"

    id = Column(String, primary_key=True, default=_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)       # Buffer | Break | Conflict | Double Booking | Advance
    priority = Column(Integer, default=1)
    description = Column(Text)
    applies_to = Column(String, default="All Providers")
    conditions = Column(Text)
    enabled = Column(Boolean, default=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


class ScheduleTemplate(Base):
    """Reusable weekly schedule templates that can be applied to providers or departments."""
    __tablename__ = "schedule_templates"

    id = Column(String, primary_key=True, default=_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    badge = Column(String, default="Provider")  # Provider | Department | Clinic
    status = Column(String, default="active")   # active | inactive
    description = Column(Text)
    days = Column(String)           # human label e.g. "Monday – Friday"
    hours = Column(String)          # human label e.g. "8:00 AM – 5:00 PM"
    types = Column(String)          # comma-separated visit types
    applied_to = Column(String)     # free-text scope
    usage_count = Column(Integer, default=0)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


class Room(Base):
    """Physical exam/procedure rooms and resources in a clinic."""
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String)           # General | Procedure | Specialty | Consult | Diagnostic
    icon = Column(String, default="fa-door-open")
    status = Column(String, default="available")  # available | occupied | reserved | maintenance
    created_at = Column(DateTime(timezone=True), default=_now)

    bookings = relationship("RoomBooking", back_populates="room")


class RoomBooking(Base):
    """A time-slot booking of a room tied (optionally) to an appointment."""
    __tablename__ = "room_bookings"

    id = Column(String, primary_key=True, default=_uuid)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False, index=True)
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=True)
    patient_name = Column(String)
    doctor_name = Column(String)
    booking_date = Column(DateTime(timezone=True), default=_now)
    start_hour = Column(Integer, nullable=False)   # 0-23
    start_min = Column(Integer, default=0)         # 0 or 30
    duration_min = Column(Integer, default=30)
    created_at = Column(DateTime(timezone=True), default=_now)

    room = relationship("Room", back_populates="bookings")


class StaffSchedule(Base):
    """Weekly shift schedule for a provider within an organization."""
    __tablename__ = "staff_schedules"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    mon = Column(String)   # shift label e.g. "8:00 AM - 5:00 PM" or "Off"
    tue = Column(String)
    wed = Column(String)
    thu = Column(String)
    fri = Column(String)
    sat = Column(String, default="Off")
    sun = Column(String, default="Off")
    status = Column(String, default="active")  # active | pto
    effective_from = Column(String)            # ISO date
    created_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", foreign_keys=[user_id])


class OnCallAssignment(Base):
    """On-call period assignment for a provider."""
    __tablename__ = "on_call_assignments"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    backup_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    period_label = Column(String)               # human label e.g. "Tonight 6 PM – 6 AM"
    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))
    status = Column(String, default="upcoming")  # active | upcoming
    total_calls = Column(Integer, default=0)
    emergencies = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", foreign_keys=[user_id])
    backup_user = relationship("User", foreign_keys=[backup_user_id])
