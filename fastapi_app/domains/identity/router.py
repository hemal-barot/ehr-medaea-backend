"""
Identity domain router — Medaea EHR
Full HIPAA/ONC-compliant authentication flow:
  • Signup → welcome email + optional verification
  • Login → check verification → MFA challenge → JWT
  • Email verification via token link
  • Resend activation email
  • Forgot / Reset password via email
  • MFA setup (TOTP + SMS via Twilio)
  • MFA verify during login
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.core.security import verify_password, hash_password, create_access_token
from backend.fastapi_app.core.deps import get_current_active_user
from backend.fastapi_app.core.config import settings
from backend.fastapi_app.db.models import User, Organization, UserOrganization
from backend.fastapi_app.shared import email_service, mfa_service
from backend.fastapi_app.shared.email_templates import (
    welcome_email, verification_email, resend_verification_email,
    password_reset_email, mfa_otp_email,
)
from .schemas import (
    AuthResponse, SignupRequest, UserResponse, OrgInfo,
    UpdateProfileRequest, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    MfaSetupRequest, MfaVerifyRequest, MfaFinalizeRequest,
    ResendVerificationRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(prefix="/users", tags=["Users"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _format_user(user: User, db: Session) -> UserResponse:
    user_orgs = (
        db.query(UserOrganization, Organization)
        .join(Organization, UserOrganization.organization_id == Organization.id)
        .filter(UserOrganization.user_id == user.id)
        .all()
    )
    orgs = [
        OrgInfo(
            id=org.id,
            name=org.name,
            org_type=org.org_type,
            role=uo.role,
            department=uo.department,
        )
        for uo, org in user_orgs
    ]
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        role=user.role,
        specialty=user.specialty,
        npi=user.npi,
        provider_type=user.provider_type,
        avatar_url=user.avatar_url,
        mfa_enabled=user.mfa_enabled,
        mfa_method=user.mfa_method,
        is_verified=user.is_verified,
        organizations=orgs,
    )


def _generate_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def _verification_url(token: str) -> str:
    return f"{settings.frontend_url}/verify-email?token={token}"


def _reset_url(token: str) -> str:
    return f"{settings.frontend_url}/reset-password?token={token}"


# ─── Signup ──────────────────────────────────────────────────────────────────

@router.post("/signup", status_code=201)
def signup(
    payload: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # Determine verification state
    needs_verification = settings.require_email_verification
    verify_token = _generate_token() if needs_verification else None
    verify_expires = (
        datetime.now(timezone.utc) + timedelta(hours=24) if needs_verification else None
    )

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        role=payload.role or "doctor",
        specialty=payload.specialty,
        provider_type=payload.provider_type,
        npi=payload.npi,
        is_active=True,
        is_verified=not needs_verification,
        email_verification_token=verify_token,
        email_verification_expires=verify_expires,
        hipaa_consent=payload.hipaa_consent or False,
        hipaa_consent_at=datetime.now(timezone.utc) if (payload.hipaa_consent or False) else None,
    )
    db.add(user)

    if payload.org_name:
        org = Organization(
            id=str(uuid.uuid4()),
            name=payload.org_name,
            org_type=payload.org_type,
            address=payload.address,
            city=payload.city,
            state=payload.state,
            zip=payload.zip,
        )
        db.add(org)
        db.flush()
        uo = UserOrganization(
            id=str(uuid.uuid4()),
            user_id=user.id,
            organization_id=org.id,
            role=payload.role or "doctor",
            department=payload.department,
        )
        db.add(uo)

    db.commit()
    db.refresh(user)

    # Send emails in background
    login_url = f"{settings.frontend_url}/login"
    if needs_verification:
        vurl = _verification_url(verify_token)
        subj, html = verification_email(user.first_name, vurl)
        background_tasks.add_task(email_service.send_email, user.email, subj, html)
    else:
        subj, html = welcome_email(user.first_name, login_url)
        background_tasks.add_task(email_service.send_email, user.email, subj, html)

    token = create_access_token({"sub": user.id})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_format_user(user, db),
    )


# ─── Login ───────────────────────────────────────────────────────────────────

@router.post("/login")
def login(
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been deactivated. Contact support.")

    # Check email verification requirement
    if settings.require_email_verification and not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="email_not_verified",
            headers={"X-Error-Code": "EMAIL_NOT_VERIFIED"},
        )

    # MFA challenge
    if user.mfa_enabled and user.mfa_method:
        mfa_token = _generate_token(32)
        method = user.mfa_method

        if method == "sms" and user.mfa_phone:
            otp = mfa_service.generate_numeric_otp()
            mfa_service.store_otp(mfa_token, otp, "sms", user.id)
            sent = mfa_service.send_sms_otp(user.mfa_phone, otp)
            if not sent:
                raise HTTPException(status_code=503, detail="Failed to send SMS. Try email MFA or contact support.")

        elif method == "email":
            otp = mfa_service.generate_numeric_otp()
            mfa_service.store_otp(mfa_token, otp, "email", user.id)
            subj, html = mfa_otp_email(user.first_name, otp, settings.mfa_token_expire_minutes)
            background_tasks.add_task(email_service.send_email, user.email, subj, html)

        elif method == "authenticator":
            mfa_service.store_otp(mfa_token, "__totp__", "authenticator", user.id)

        return {
            "mfa_required": True,
            "mfa_token": mfa_token,
            "method": method,
            "message": f"MFA code sent via {method}",
        }

    # No MFA — issue token
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token({"sub": user.id})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_format_user(user, db),
    )


# ─── MFA verify ──────────────────────────────────────────────────────────────

@router.post("/mfa/verify")
def mfa_verify(payload: MfaVerifyRequest, db: Session = Depends(get_db)):
    if payload.method == "authenticator":
        # TOTP — look up user from mfa_token store
        entry = mfa_service._otp_store.get(payload.mfa_token)
        if not entry or entry.code != "__totp__":
            raise HTTPException(status_code=401, detail="MFA session expired. Please login again.")
        if mfa_service._otp_store.get(payload.mfa_token) and \
                mfa_service._otp_store[payload.mfa_token].expires_at < __import__("time").time():
            raise HTTPException(status_code=401, detail="MFA session expired.")
        user = db.query(User).filter(User.id == entry.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        secret = mfa_service.decrypt_secret(user.mfa_secret_encrypted or "")
        if not mfa_service.verify_totp(secret, payload.code):
            raise HTTPException(status_code=401, detail="Invalid authenticator code. Please try again.")
        mfa_service._otp_store.pop(payload.mfa_token, None)
    else:
        # SMS or Email OTP
        ok, err, user_id = mfa_service.validate_otp(payload.mfa_token, payload.code)
        if not ok:
            raise HTTPException(status_code=401, detail=err)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token({"sub": user.id})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_format_user(user, db),
    )


# ─── MFA Setup ───────────────────────────────────────────────────────────────

@router.post("/mfa/setup/initiate")
def mfa_setup_initiate(
    payload: MfaSetupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    method = payload.method

    if method == "authenticator":
        secret = mfa_service.generate_totp_secret()
        # Store temporarily in pending field
        current_user.mfa_secret_encrypted = mfa_service.encrypt_secret(f"PENDING:{secret}")
        db.commit()
        qr = mfa_service.generate_totp_qr_base64(secret, current_user.email)
        return {
            "method": "authenticator",
            "qr_code": qr,
            "secret": secret,
            "issuer": "Medaea EHR",
            "message": "Scan the QR code with your authenticator app, then confirm the 6-digit code.",
        }

    elif method == "sms":
        if not payload.phone:
            raise HTTPException(status_code=422, detail="Phone number required for SMS MFA.")
        otp = mfa_service.generate_numeric_otp()
        token_key = _generate_token(24)
        mfa_service.store_otp(token_key, otp, "sms_setup", current_user.id)
        # Temporarily save phone
        current_user.mfa_phone = payload.phone
        db.commit()
        sent = mfa_service.send_sms_otp(payload.phone, otp)
        if not sent:
            raise HTTPException(status_code=503, detail="Failed to send SMS. Check your phone number.")
        return {
            "method": "sms",
            "setup_token": token_key,
            "message": f"Verification code sent to {payload.phone[-4:].rjust(len(payload.phone), '*')}",
        }

    elif method == "email":
        otp = mfa_service.generate_numeric_otp()
        token_key = _generate_token(24)
        mfa_service.store_otp(token_key, otp, "email_setup", current_user.id)
        subj, html = mfa_otp_email(current_user.first_name, otp, settings.mfa_token_expire_minutes)
        background_tasks.add_task(email_service.send_email, current_user.email, subj, html)
        return {
            "method": "email",
            "setup_token": token_key,
            "message": f"Verification code sent to {current_user.email}",
        }

    raise HTTPException(status_code=422, detail="Invalid MFA method. Choose: authenticator, sms, or email.")


@router.post("/mfa/setup/finalize")
def mfa_setup_finalize(
    payload: MfaFinalizeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    method = payload.method
    backup_codes = mfa_service.generate_backup_codes()
    backup_hashes = [__import__("hashlib").sha256(c.encode()).hexdigest() for c in backup_codes]

    if method == "authenticator":
        enc = current_user.mfa_secret_encrypted or ""
        if enc.startswith("PENDING:"):
            secret = enc[len("PENDING:"):]
        else:
            secret = mfa_service.decrypt_secret(enc)
        if not mfa_service.verify_totp(secret, payload.code):
            raise HTTPException(status_code=400, detail="Invalid authenticator code. Please try again.")
        current_user.mfa_secret_encrypted = mfa_service.encrypt_secret(secret)
        current_user.mfa_enabled = True
        current_user.mfa_method = "authenticator"
        current_user.mfa_backup_codes = backup_hashes

    elif method in ("sms", "email"):
        ok, err, _ = mfa_service.validate_otp(payload.setup_token or "", payload.code)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        current_user.mfa_enabled = True
        current_user.mfa_method = method
        current_user.mfa_backup_codes = backup_hashes

    db.commit()
    return {
        "message": f"2FA enabled via {method}. Save your backup codes — they won't be shown again.",
        "backup_codes": backup_codes,
        "user": _format_user(current_user, db),
    }


@router.post("/mfa/disable")
def mfa_disable(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    current_user.mfa_enabled = False
    current_user.mfa_method = None
    current_user.mfa_secret_encrypted = None
    current_user.mfa_backup_codes = None
    db.commit()
    return {"message": "Two-factor authentication has been disabled."}


# ─── Email verification ───────────────────────────────────────────────────────

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")
    if user.email_verification_expires and user.email_verification_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification link has expired. Please request a new one.")
    user.is_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    db.commit()
    return {"message": "Email verified successfully! You can now log in.", "verified": True}


@router.post("/resend-verification")
def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Don't reveal whether email exists (security)
        return {"message": "If that email is registered, a new activation link has been sent."}
    if user.is_verified:
        return {"message": "Your account is already verified. Please log in."}

    token = _generate_token()
    user.email_verification_token = token
    user.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()

    vurl = _verification_url(token)
    subj, html = resend_verification_email(user.first_name, vurl)
    background_tasks.add_task(email_service.send_email, user.email, subj, html)
    return {"message": "If that email is registered, a new activation link has been sent."}


# ─── Forgot / Reset password ──────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    # Always return 200 (don't reveal email existence)
    if user:
        token = _generate_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        rurl = _reset_url(token)
        subj, html = password_reset_email(user.first_name, rurl)
        background_tasks.add_task(email_service.send_email, user.email, subj, html)
    return {"message": "If that email is registered, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.password_reset_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")
    if user.password_reset_expires and user.password_reset_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")

    # Validate password strength (HIPAA minimum)
    pw = payload.new_password
    errors = []
    if len(pw) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in pw):
        errors.append("one uppercase letter")
    if not any(c.islower() for c in pw):
        errors.append("one lowercase letter")
    if not any(c.isdigit() for c in pw):
        errors.append("one number")
    if errors:
        raise HTTPException(status_code=422, detail=f"Password must contain: {', '.join(errors)}.")

    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    return {"message": "Password reset successfully. Please log in with your new password."}


# ─── User profile ─────────────────────────────────────────────────────────────

@users_router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return _format_user(current_user, db)


@users_router.put("/me", response_model=UserResponse)
@users_router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return _format_user(current_user, db)


@users_router.post("/me/password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}
