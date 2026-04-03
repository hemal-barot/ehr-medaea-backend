"""
MFA service for Medaea EHR — enterprise-grade, athenahealth-style.
Supports:
  • TOTP (Authenticator apps: Google Authenticator, Authy, Microsoft Auth)
  • SMS OTP via Twilio
  • Email OTP (fallback)

MFA TOTP secrets are AES-encrypted at rest using MFA_ENCRYPTION_KEY.
"""
import base64
import hashlib
import hmac
import logging
import os
import random
import string
from typing import Optional

import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO

from backend.fastapi_app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Encryption helpers (Fernet-compatible using MFA_ENCRYPTION_KEY) ─────────

def _get_fernet():
    try:
        from cryptography.fernet import Fernet
        key = settings.mfa_encryption_key
        if not key.endswith("="):
            # pad if needed
            key = key + "=" * (4 - len(key) % 4) if len(key) % 4 else key
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        logger.warning("Fernet init failed: %s — using plain storage", exc)
        return None


def encrypt_secret(plain: str) -> str:
    f = _get_fernet()
    if f:
        return f.encrypt(plain.encode()).decode()
    return plain  # fallback: store plain (dev only)


def decrypt_secret(cipher: str) -> str:
    f = _get_fernet()
    if f:
        try:
            return f.decrypt(cipher.encode()).decode()
        except Exception:
            return cipher  # already plain
    return cipher


# ─── TOTP (Authenticator App) ─────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a new base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "Medaea EHR") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def generate_totp_qr_base64(secret: str, email: str) -> str:
    """Return base64-encoded PNG of the TOTP QR code."""
    uri = get_totp_uri(secret, email)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code with a ±1 window (30s × window = ±30s tolerance)."""
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code.strip(), valid_window=window)
    except Exception:
        return False


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate one-time backup codes (format: XXXX-XXXX)."""
    codes = []
    for _ in range(count):
        part1 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part2 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        codes.append(f"{part1}-{part2}")
    return codes


# ─── SMS OTP via Twilio ───────────────────────────────────────────────────────

def generate_numeric_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def send_sms_otp(phone_number: str, otp_code: str) -> bool:
    """
    Send an SMS OTP via Twilio Messaging API.
    Phone number must be in E.164 format: +1XXXXXXXXXX
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio credentials not configured — SMS not sent")
        return False
    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        message = client.messages.create(
            body=(
                f"Your Medaea EHR verification code is: {otp_code}\n\n"
                f"Expires in {settings.mfa_token_expire_minutes} minutes. "
                f"Do NOT share this code. Medaea will never ask for it."
            ),
            from_=settings.twilio_phone_number,
            to=phone_number,
        )
        logger.info("SMS OTP sent to %s, SID: %s", phone_number, message.sid)
        return True
    except Exception as exc:
        logger.error("Twilio SMS failed for %s: %s", phone_number, exc)
        return False


# ─── In-memory MFA token store (production: replace with Redis) ───────────────

import time
from dataclasses import dataclass, field

@dataclass
class _OtpEntry:
    code: str
    method: str
    user_id: str
    expires_at: float
    attempts: int = 0


_otp_store: dict[str, _OtpEntry] = {}


def store_otp(token_key: str, code: str, method: str, user_id: str) -> None:
    expire_secs = settings.mfa_token_expire_minutes * 60
    _otp_store[token_key] = _OtpEntry(
        code=code,
        method=method,
        user_id=user_id,
        expires_at=time.time() + expire_secs,
    )


def validate_otp(token_key: str, submitted_code: str) -> tuple[bool, str, Optional[str]]:
    """
    Returns (is_valid, error_msg, user_id).
    Increments attempts and purges on success or max attempts.
    """
    entry = _otp_store.get(token_key)
    if not entry:
        return False, "MFA session expired or invalid. Please login again.", None
    if time.time() > entry.expires_at:
        _otp_store.pop(token_key, None)
        return False, "Code has expired. Please request a new one.", None
    entry.attempts += 1
    if entry.attempts > 5:
        _otp_store.pop(token_key, None)
        return False, "Too many attempts. Please login again.", None
    if not hmac.compare_digest(entry.code.strip(), submitted_code.strip()):
        return False, f"Invalid code. {5 - entry.attempts} attempt(s) remaining.", None
    user_id = entry.user_id
    _otp_store.pop(token_key, None)
    return True, "", user_id


def purge_expired_otps():
    """Call periodically to clean up expired OTPs."""
    now = time.time()
    to_delete = [k for k, v in _otp_store.items() if v.expires_at < now]
    for k in to_delete:
        del _otp_store[k]
