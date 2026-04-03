"""HTML email templates for Medaea EHR transactional emails."""

BRAND_COLOR = "#0d9488"
BRAND_NAME = "Medaea EHR"


def _base_layout(title: str, body_content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f4f7f6;font-family:Inter,-apple-system,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7f6;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:{BRAND_COLOR};padding:28px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-0.3px;">{BRAND_NAME}</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">HIPAA-Compliant Electronic Health Records</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            {body_content}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;padding:20px 40px;border-top:1px solid #e5e7eb;">
            <p style="margin:0;font-size:12px;color:#6b7280;text-align:center;">
              {BRAND_NAME} &bull; HIPAA &amp; ONC Certified Platform<br>
              This email contains protected health information. Do not forward.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _btn(url: str, label: str, color: str = BRAND_COLOR) -> str:
    return f"""<div style="text-align:center;margin:28px 0;">
  <a href="{url}" style="background:{color};color:#ffffff;text-decoration:none;
     padding:14px 32px;border-radius:8px;font-size:15px;font-weight:600;
     display:inline-block;letter-spacing:0.2px;">{label}</a>
</div>"""


def _notice(text: str) -> str:
    return f"""<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;
     padding:14px 18px;margin:20px 0;font-size:13px;color:#92400e;">
  ⚠️ {text}
</div>"""


# ─── Welcome email (no verification required) ────────────────────────────────

def welcome_email(first_name: str, login_url: str) -> tuple[str, str]:
    subject = f"Welcome to {BRAND_NAME} — Your account is active"
    body = f"""
<h2 style="margin:0 0 8px;color:#111827;font-size:22px;">Welcome, Dr. {first_name}!</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 24px;">Your {BRAND_NAME} provider account has been created and is ready to use.</p>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px;margin-bottom:24px;">
  <tr>
    <td style="padding:20px;">
      <p style="margin:0 0 10px;font-size:14px;color:#0f766e;font-weight:600;">Your account is configured for:</p>
      <ul style="margin:0;padding-left:20px;color:#374151;font-size:14px;line-height:2;">
        <li>HIPAA-compliant patient management</li>
        <li>ONC-certified clinical documentation</li>
        <li>Secure scheduling &amp; calendar</li>
        <li>Multi-factor authentication (2FA)</li>
      </ul>
    </td>
  </tr>
</table>

{_btn(login_url, "Access Your Portal")}

{_notice("For security, please enable Two-Factor Authentication (2FA) in Settings after your first login.")}

<p style="font-size:13px;color:#6b7280;margin-top:24px;">
  If you did not create this account, please contact support immediately at
  <a href="mailto:security@medaea.com" style="color:{BRAND_COLOR};">security@medaea.com</a>.
</p>"""
    return subject, _base_layout(subject, body)


# ─── Verification email ───────────────────────────────────────────────────────

def verification_email(first_name: str, verify_url: str) -> tuple[str, str]:
    subject = f"Verify your {BRAND_NAME} email address"
    body = f"""
<h2 style="margin:0 0 8px;color:#111827;font-size:22px;">Verify your email, {first_name}</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 20px;">
  To activate your {BRAND_NAME} account and access patient records, please verify your email address.
</p>

{_btn(verify_url, "Activate My Account")}

<p style="font-size:13px;color:#6b7280;text-align:center;">
  This link expires in <strong>24 hours</strong>. Copy and paste if the button doesn't work:<br>
  <a href="{verify_url}" style="color:{BRAND_COLOR};word-break:break-all;">{verify_url}</a>
</p>

{_notice("This link is single-use and expires in 24 hours. Do not share it.")}"""
    return subject, _base_layout(subject, body)


# ─── Account not yet activated — resend prompt ───────────────────────────────

def resend_verification_email(first_name: str, verify_url: str) -> tuple[str, str]:
    subject = f"Your {BRAND_NAME} activation link"
    body = f"""
<h2 style="margin:0 0 8px;color:#111827;font-size:22px;">Resend: Activate your account</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 20px;">
  Hi {first_name}, here is a new activation link for your {BRAND_NAME} provider account.
</p>

{_btn(verify_url, "Activate My Account")}

<p style="font-size:13px;color:#6b7280;text-align:center;">
  Link expires in <strong>24 hours</strong>.<br>
  <a href="{verify_url}" style="color:{BRAND_COLOR};word-break:break-all;">{verify_url}</a>
</p>

{_notice("If you didn't request this, you can safely ignore it.")}"""
    return subject, _base_layout(subject, body)


# ─── Password reset ───────────────────────────────────────────────────────────

def password_reset_email(first_name: str, reset_url: str) -> tuple[str, str]:
    subject = f"{BRAND_NAME} — Password Reset Request"
    body = f"""
<h2 style="margin:0 0 8px;color:#111827;font-size:22px;">Password Reset</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 20px;">
  Hi {first_name}, we received a request to reset your {BRAND_NAME} password.
  Click the button below to create a new password.
</p>

{_btn(reset_url, "Reset My Password", "#dc2626")}

<p style="font-size:13px;color:#6b7280;text-align:center;">
  This link expires in <strong>1 hour</strong>.
</p>

{_notice("If you did not request a password reset, your account may be at risk. Contact support immediately.")}

<p style="font-size:12px;color:#9ca3af;margin-top:20px;">
  For HIPAA compliance, all password reset requests are logged and monitored.
</p>"""
    return subject, _base_layout(subject, body)


# ─── MFA OTP email ────────────────────────────────────────────────────────────

def mfa_otp_email(first_name: str, otp_code: str, expires_minutes: int = 5) -> tuple[str, str]:
    subject = f"{BRAND_NAME} — Your Authentication Code"
    body = f"""
<h2 style="margin:0 0 8px;color:#111827;font-size:22px;">Authentication Code</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 24px;">
  Hi {first_name}, use the following code to complete your login.
</p>

<div style="text-align:center;margin:28px 0;">
  <div style="display:inline-block;background:#f0fdfa;border:2px solid {BRAND_COLOR};
       border-radius:12px;padding:20px 40px;">
    <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:{BRAND_COLOR};
          font-family:monospace;">{otp_code}</span>
  </div>
  <p style="margin:12px 0 0;font-size:13px;color:#6b7280;">Expires in {expires_minutes} minutes</p>
</div>

{_notice("Never share this code. Medaea EHR staff will never ask for it.")}"""
    return subject, _base_layout(subject, body)
