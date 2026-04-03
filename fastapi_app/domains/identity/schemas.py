from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
import re


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrgInfo(BaseModel):
    id: str
    name: str
    org_type: Optional[str] = None
    role: str
    department: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: str
    specialty: Optional[str] = None
    npi: Optional[str] = None
    provider_type: Optional[str] = None
    avatar_url: Optional[str] = None
    mfa_enabled: bool = False
    mfa_method: Optional[str] = None
    is_verified: bool = False
    organizations: List[OrgInfo] = []

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = "doctor"
    specialty: Optional[str] = None
    provider_type: Optional[str] = None
    npi: Optional[str] = None
    dea: Optional[str] = None
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    license_expiry: Optional[str] = None
    org_name: Optional[str] = None
    org_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    department: Optional[str] = None
    hipaa_consent: Optional[bool] = False
    ehr_consent: Optional[bool] = False
    audit_consent: Optional[bool] = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("one number")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v

    @field_validator("npi")
    @classmethod
    def npi_format(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^\d{10}$", v):
            raise ValueError("NPI must be exactly 10 digits")
        return v


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None
    provider_type: Optional[str] = None
    npi: Optional[str] = None
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("one number")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class MfaSetupRequest(BaseModel):
    method: str  # "authenticator" | "sms" | "email"
    phone: Optional[str] = None  # required for sms


class MfaFinalizeRequest(BaseModel):
    method: str
    code: str
    setup_token: Optional[str] = None  # for sms/email setup


class MfaVerifyRequest(BaseModel):
    code: str
    mfa_token: str
    method: Optional[str] = "authenticator"
