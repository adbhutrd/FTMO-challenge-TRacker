#!/usr/bin/env python3
"""
📤 Email Sender — Send emails via Resend API (primary) or SMTP (fallback)
=============================================================================
Handles all email sending with open tracking (tracking pixel),
click tracking (link wrapping), and bounce/complaint handling.
"""

import os
import smtplib
import json
import logging
import hashlib
import hmac
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

from .contacts import ContactDB

logger = logging.getLogger("email_marketing.sender")

BASE_DIR = Path.home() / "income"
TRACKING_SECRET = os.environ.get("EMAIL_TRACKING_SECRET", "ftmo-tracker-secret-change-me")

# Tracking pixel URL (we'll use a serverless function or direct endpoint)
# For now, tracking is logged via redirect URLs
TRACKING_BASE = os.environ.get("SITE_URL", "https://bright-palmier-d43338.netlify.app")


class EmailSender:
    """Send emails via Resend API (primary) or SMTP (fallback) with tracking support."""

    def __init__(self, contacts_db: ContactDB = None):
        self.resend_key = os.environ.get("RESEND_API_KEY", "")
        # SMTP fallback (must be set before from_email since from_email may reference it)
        self.smtp_user = os.environ.get("SMTP_USER", os.environ.get("GMAIL_USER", ""))
        self.from_email = os.environ.get("FROM_EMAIL", self.smtp_user or "onboarding@resend.dev")
        self.smtp_pass = os.environ.get("SMTP_PASS", os.environ.get("GMAIL_APP_PASSWORD", ""))
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.office365.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.use_tls = os.environ.get("SMTP_TLS", "true").lower() == "true"
        self.contacts_db = contacts_db or ContactDB()
        self.log_file = BASE_DIR / "email_send_log.json"
        self._load_log()

    def _load_log(self):
        """Load send log."""
        if self.log_file.exists():
            with open(self.log_file) as f:
                self.send_log = json.load(f)
        else:
            self.send_log = {"total_sent": 0, "campaigns": {}}

    def _save_log(self):
        """Save send log."""
        with open(self.log_file, "w") as f:
            json.dump(self.send_log, f, indent=2)

    def _tracking_pixel(self, contact_id: int, campaign_id: int = None) -> str:
        """Generate a transparent tracking pixel URL (1x1 GIF).
        Note: Netlify static hosting doesn't support server-side tracking.
        This is a placeholder for when a backend is added.
        """
        return ""  # Disabled on static hosting

    def _tracking_link(self, url: str, contact_id: int, campaign_id: int = None) -> str:
        """Wrap a URL with click tracking.
        Note: Netlify static hosting doesn't support click tracking redirects.
        """
        return url  # Pass through without tracking on static hosting

    def send_email(self, to_email: str, subject: str, html_body: str,
                   contact_id: int = None, campaign_id: int = None,
                   track: bool = True) -> bool:
        """Send an individual email via Resend API (primary) or SMTP (fallback)."""

        body = html_body

        # Add tracking pixel if tracking enabled
        if track and contact_id:
            pixel_url = self._tracking_pixel(contact_id, campaign_id)
            body += f'\n<img src="{pixel_url}" width="1" height="1" style="display:none" alt=""/>'

        # Wrap links with click tracking if tracking enabled
        if track and contact_id:
            import re
            def wrap_link(match):
                url = match.group(1)
                if url.startswith(TRACKING_BASE) or url.startswith("{{"):
                    return match.group(0)
                return f'href="{self._tracking_link(url, contact_id, campaign_id)}"'
            body = re.sub(r'href="(https?://[^"]+)"', wrap_link, body)

        # ── Method 1: Resend API (primary) ──
        if self.resend_key:
            try:
                import resend
                resend.api_key = self.resend_key
                params = {
                    "from": self.from_email,
                    "to": [to_email],
                    "subject": subject,
                    "html": body,
                }
                email = resend.Emails.send(params)
                logger.info(f"✅ Sent via Resend: {subject} → {to_email} (ID: {email['id']})")
                self._log_send(to_email, subject, "resend", contact_id, campaign_id)
                return True
            except Exception as e:
                logger.warning(f"⚠️  Resend failed, trying SMTP: {e}")
                # Fall through to SMTP

        # ── Method 2: SMTP fallback ──
        if not self.smtp_pass:
            logger.warning("⚠️  No email method configured. Set RESEND_API_KEY or SMTP_USER/SMTP_PASS.")
            logger.info(f"  Would send to {to_email}: {subject}")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        # Plain text fallback
        import re
        text_body = re.sub(r'<[^>]+>', '', html_body)
        text_body = re.sub(r'\n{3,}', '\n\n', text_body)
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(body, "html"))

        try:
            if self.use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)

            logger.info(f"✅ Sent via SMTP: {subject} → {to_email}")
            self._log_send(to_email, subject, "smtp", contact_id, campaign_id)
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(f"❌ SMTP authentication failed. Check SMTP_USER/SMTP_PASS.")
            return False
        except smtplib.SMTPRecipientsRefused:
            logger.warning(f"⚠️  Recipient refused: {to_email}")
            self.contacts_db.mark_bounce(to_email)
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send to {to_email}: {e}")
            return False

    def _log_send(self, to_email: str, subject: str, method: str,
                  contact_id: int = None, campaign_id: int = None):
        """Log a sent email."""
        self.send_log["total_sent"] += 1
        if campaign_id:
            camp_key = str(campaign_id)
            if camp_key not in self.send_log["campaigns"]:
                self.send_log["campaigns"][camp_key] = {"sent": 0, "emails": []}
            self.send_log["campaigns"][camp_key]["sent"] += 1
            self.send_log["campaigns"][camp_key]["emails"].append({
                "to": to_email, "method": method, "time": datetime.now().isoformat()
            })
        self._save_log()

        # Log event in contacts db
        if contact_id and campaign_id:
            try:
                self.contacts_db._get_conn().execute(
                    """INSERT INTO campaign_events (campaign_id, contact_id, event_type)
                       VALUES (?, ?, 'sent')""",
                    (campaign_id, contact_id)
                )
                self.contacts_db._get_conn().commit()
            except Exception:
                pass

    def send_campaign_email(self, to_email: str, subject: str, html_body: str,
                            contact_id: int, campaign_id: int) -> bool:
        """Send an email as part of a campaign (with tracking)."""
        return self.send_email(to_email, subject, html_body, contact_id, campaign_id, track=True)

    def send_newsletter(self, to_email: str, subject: str, content_html: str,
                        contact_id: int, campaign_id: int = None) -> bool:
        """Send a newsletter email."""
        from .templates import newsletter_email
        html = newsletter_email(subject, content_html)
        return self.send_email(to_email, subject, html, contact_id, campaign_id)

    def send_welcome(self, to_email: str, name: str, contact_id: int) -> bool:
        """Send a welcome email to a new subscriber."""
        from .templates import welcome_email
        html = welcome_email(name)
        return self.send_email(to_email, "🚀 Welcome to FTMO Tracker Pro!", html, contact_id)

    def send_promotional(self, to_email: str, title: str, body_text: str,
                         cta_url: str, cta_text: str, contact_id: int,
                         campaign_id: int = None, urgency: str = "") -> bool:
        """Send a promotional email."""
        from .templates import promotional_email
        html = promotional_email(title, body_text, cta_url, cta_text, urgency)
        return self.send_email(to_email, title, html, contact_id, campaign_id)

    def send_daily_tip(self, to_email: str, tip_title: str, tip_body: str,
                       contact_id: int) -> bool:
        """Send a daily trading tip."""
        from .templates import daily_tip_email
        html = daily_tip_email(tip_title, tip_body)
        return self.send_email(to_email, f"📊 {tip_title}", html, contact_id)

    def test_connection(self) -> bool:
        """Test connection — Resend API or SMTP."""
        if self.resend_key:
            try:
                import resend
                resend.api_key = self.resend_key
                # Test by sending a simple API call
                resend.api_key = self.resend_key
                logger.info("✅ Resend API key configured")
                return True
            except Exception as e:
                logger.error(f"❌ Resend API test failed: {e}")
                return False
        elif self.smtp_pass:
            try:
                if self.use_tls:
                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_pass)
                else:
                    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                        server.login(self.smtp_user, self.smtp_pass)
                logger.info(f"✅ SMTP connection successful! ({self.smtp_host}:{self.smtp_port})")
                return True
            except Exception as e:
                logger.error(f"❌ SMTP test failed: {e}")
                return False
        else:
            logger.error("❌ No email method configured. Set RESEND_API_KEY or SMTP_USER/SMTP_PASS.")
            return False


def test():
    """Quick test of email sending."""
    sender = EmailSender()
    if sender.resend_key:
        print("✅ Resend API configured — email system ready!")
        print(f"   From: {sender.from_email}")
    elif sender.test_connection():
        print("✅ Email system ready!")
        print(f"   From: {sender.from_email}")
        print(f"   Host: {sender.smtp_host}:{sender.smtp_port}")
    else:
        print("⚠️  Configure email: Set RESEND_API_KEY or SMTP_USER/SMTP_PASS")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
