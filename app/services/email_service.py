"""
Email service for SENTINEL.
Sends verification codes via SMTP if configured, otherwise logs to console.
"""

import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


def generate_verification_code() -> str:
    """Generate a random 6-digit verification code."""
    return str(random.randint(100000, 999999))


def send_verification_email(to_email: str, code: str) -> bool:
    """
    Send a verification code to the user's email.
    If SMTP is not configured, logs the code to console instead.

    Returns True if sent/logged successfully.
    """
    if settings.SMTP_HOST and settings.SMTP_USER:
        return _send_smtp(to_email, code)
    else:
        return _log_to_console(to_email, code)


def _log_to_console(to_email: str, code: str) -> bool:
    """Log verification code to console (development mode)."""
    print("=" * 60)
    print(f"  📧 VERIFICATION CODE for {to_email}")
    print(f"  🔑 CODE: {code}")
    print(f"  ⏱️  Expires in {settings.VERIFICATION_CODE_EXPIRY_MINUTES} minutes")
    print("=" * 60)
    return True


def _send_smtp(to_email: str, code: str) -> bool:
    """Send verification code via SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"SENTINEL — Your Verification Code: {code}"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email

        html_body = f"""
        <div style="font-family: 'Courier New', monospace; background: #0f172a; color: #e2e8f0; padding: 40px; max-width: 500px; margin: 0 auto;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #06b6d4; letter-spacing: 8px; font-size: 24px;">SENTINEL</h1>
                <div style="color: #64748b; font-size: 10px; letter-spacing: 4px;">BIO-DIGITAL TWIN // VERIFICATION</div>
            </div>
            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 30px; text-align: center;">
                <div style="color: #94a3b8; font-size: 11px; letter-spacing: 3px; margin-bottom: 15px;">YOUR VERIFICATION CODE</div>
                <div style="font-size: 36px; letter-spacing: 12px; color: #06b6d4; font-weight: bold; padding: 15px 0;">{code}</div>
                <div style="color: #64748b; font-size: 11px; margin-top: 15px;">This code expires in {settings.VERIFICATION_CODE_EXPIRY_MINUTES} minutes.</div>
            </div>
            <div style="text-align: center; margin-top: 25px; color: #475569; font-size: 10px; letter-spacing: 2px;">
                If you did not request this, ignore this email.
            </div>
        </div>
        """

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())

        print(f"[EMAIL] Verification code sent to {to_email}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        # Fall back to console
        return _log_to_console(to_email, code)
