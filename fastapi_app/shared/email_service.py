"""
Async SMTP email service for Medaea EHR.
Uses aiosmtplib with Gmail on port 587 (STARTTLS).

Design: send_email is an async function so FastAPI BackgroundTasks
can properly await it on the event loop — no thread-pool issues.
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import aiosmtplib

from backend.fastapi_app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Send an email via Gmail SMTP with STARTTLS (port 587).
    Must be async — called by FastAPI BackgroundTasks on the event loop.
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((settings.emails_from_name, settings.emails_from_email))
    msg["To"] = to_email
    msg["Subject"] = subject

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            # Port 587 = STARTTLS. start_tls=True tells aiosmtplib to upgrade
            # the plain connection with STARTTLS (not implicit TLS / port 465).
            start_tls=True,
        )
        logger.info("Email sent → %s | %s", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Email FAILED → %s | %s | Error: %s", to_email, subject, exc)
        return False


# Alias for backward-compat
send_email_async = send_email
