#!/usr/bin/env python3
"""
📧 Email Notification Bot
Sends via Resend API (primary) or SMTP (fallback).
Set RESEND_API_KEY env var for best deliverability.
"""
import os
import smtplib
from email.mime.text import MIMEText


def send_alert(subject, body, to_email=None, html=False):
    """Send email via Resend API (primary) or SMTP (fallback)."""
    resend_key = os.environ.get("RESEND_API_KEY")
    to_email = to_email or os.environ.get("FROM_EMAIL", os.environ.get("SMTP_USER", ""))

    # ── Method 1: Resend API (preferred) ──
    if resend_key:
        try:
            import resend
            resend.api_key = resend_key
            params = {
                "from": os.environ.get("FROM_EMAIL", "onboarding@resend.dev"),
                "to": [to_email],
                "subject": subject,
                ( "html" if html else "text" ): body,
            }
            email = resend.Emails.send(params)
            print(f"✅ Email sent via Resend: {subject} (ID: {email['id']})")
            return True
        except Exception as e:
            print(f"❌ Resend failed: {e}")
            # Fall through to SMTP

    # ── Method 2: SMTP fallback ──
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", os.environ.get("GMAIL_APP_PASSWORD", ""))
    smtp_host = os.environ.get("SMTP_HOST", "smtp.office365.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    use_tls = os.environ.get("SMTP_TLS", "true").lower() == "true"
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        print("⚠️  No email method configured. Set RESEND_API_KEY or SMTP_USER/SMTP_PASS.")
        print(f"  Would have sent: {subject} -> {to_email}")
        return False

    msg = MIMEText(body, "html" if html else "plain")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        if use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        print(f"✅ Email sent via SMTP: {subject}")
        return True
    except Exception as e:
        print(f"❌ SMTP failed: {e}")
        return False


if __name__ == "__main__":
    if os.environ.get("RESEND_API_KEY"):
        print("✅ Resend API configured")
        send_alert(
            "🧪 Bot Active - Resend Mode",
            "Email bot started successfully using Resend API.",
            html=False,
        )
    else:
        print("⚠️  Set RESEND_API_KEY env var for best deliverability")
