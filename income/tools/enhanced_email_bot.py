#!/usr/bin/env python3
"""
Enhanced Email Bot - Multi-purpose notification system with templates.
Now supports Resend API (primary) + SMTP fallback.
"""
import os
import smtplib
import json
import logging
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

BASE_DIR = Path.home() / "income"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "email_bot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("email_bot")


class EmailBot:
    """Handles all email notifications via Resend API or SMTP."""

    def __init__(self):
        self.resend_key = os.environ.get("RESEND_API_KEY", "")
        self.from_email = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")
        self.default_to = os.environ.get("FROM_EMAIL", os.environ.get("SMTP_USER", ""))
        self.log_file = BASE_DIR / "email_log.json"
        self.load_log()

    def load_log(self):
        if self.log_file.exists():
            with open(self.log_file) as f:
                self.sent_log = json.load(f)
        else:
            self.sent_log = {"total_sent": 0, "emails": []}

    def save_log(self):
        with open(self.log_file, "w") as f:
            json.dump(self.sent_log, f, indent=2)

    def send(self, subject: str, body: str, to_email: str = None, html: bool = False) -> bool:
        """Send email via Resend API (primary) or SMTP (fallback)."""
        if to_email is None:
            to_email = self.default_to

        # ── Method 1: Resend API ──
        if self.resend_key:
            try:
                import resend
                resend.api_key = self.resend_key
                params = {
                    "from": self.from_email,
                    "to": [to_email],
                    "subject": subject,
                    ("html" if html else "text"): body,
                }
                email = resend.Emails.send(params)
                logger.info(f"✅ Email sent via Resend: {subject} (ID: {email['id']})")
                self.sent_log["total_sent"] += 1
                self.sent_log["emails"].append({
                    "to": to_email, "subject": subject,
                    "method": "resend",
                    "timestamp": datetime.now().isoformat(),
                })
                self.save_log()
                return True
            except Exception as e:
                logger.warning(f"⚠️ Resend failed, trying SMTP: {e}")

        # ── Method 2: SMTP fallback ──
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", os.environ.get("GMAIL_APP_PASSWORD", ""))
        if not smtp_user or not smtp_pass:
            logger.warning("⚠️  No email method configured. Set RESEND_API_KEY or SMTP_USER/SMTP_PASS.")
            logger.info(f"  Would have sent: {subject}")
            return False

        msg = MIMEText(body, "html" if html else "plain")
        msg["Subject"] = subject
        msg["From"] = os.environ.get("FROM_EMAIL", smtp_user)
        msg["To"] = to_email

        try:
            smtp_host = os.environ.get("SMTP_HOST", "smtp.office365.com")
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
            use_tls = os.environ.get("SMTP_TLS", "true").lower() == "true"
            if use_tls:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            logger.info(f"✅ Email sent via SMTP: {subject}")
            self.sent_log["total_sent"] += 1
            self.sent_log["emails"].append({
                "to": to_email, "subject": subject,
                "method": "smtp",
                "timestamp": datetime.now().isoformat(),
            })
            self.save_log()
            return True
        except Exception as e:
            logger.error(f"❌ Email failed: {e}")
            return False

    def send_trade_alert(self, trade_data: dict):
        side = trade_data.get("side", "UNKNOWN")
        symbol = trade_data.get("symbol", "N/A")
        pnl = trade_data.get("pnl", 0)
        balance = trade_data.get("balance_after", 0)
        reason = trade_data.get("reason", "")
        subject = f"{'🟢' if pnl >= 0 else '🔴'} Trade Alert: {side} {symbol} (${pnl:+.2f})"
        body = f"Trade Alert\nAction: {side}\nSymbol: {symbol}\nP&L: ${pnl:+.2f}\nBalance: ${balance:.2f}\nReason: {reason}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send(subject, body.strip())

    def send_daily_summary(self, stats: dict):
        subject = f"📊 Daily Summary — {datetime.now().strftime('%Y-%m-%d')}"
        body = f"""Daily Summary — {datetime.now().strftime('%Y-%m-%d')}

Trading:
  Balance: ${stats.get('balance', 0):.2f}
  Daily P&L: ${stats.get('daily_pnl', 0):+.2f}
  Total P&L: ${stats.get('total_pnl', 0):+.2f}
  Win Rate: {stats.get('win_rate', 0):.1f}%
  Trades Today: {stats.get('trades_today', 0)}

Bug Bounty:
  Programs: {stats.get('programs_monitored', 0)}
  Alerts: {stats.get('alerts_today', 0)}

System: Uptime: {stats.get('uptime', 'N/A')}"""
        return self.send(subject, body.strip())

    def send_program_alert(self, program_data: dict):
        name = program_data.get("name", "Unknown")
        platform = program_data.get("platform", "Unknown")
        url = program_data.get("url", "")
        subject = f"🆕 New Program: {name}"
        body = f"New Bug Bounty Program!\nProgram: {name}\nPlatform: {platform}\nURL: {url}\nFound: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return self.send(subject, body.strip())

    def send_weekly_report(self, weekly_stats: dict):
        subject = f"📈 Weekly Report — Week {datetime.now().isocalendar()[1]}"
        body = f"""Weekly Report

💰 Earnings: Trading ${weekly_stats.get('trading_pnl', 0):+.2f}
  Bug Bounty: ${weekly_stats.get('bug_bounty', 0):.2f}
  Freelance: ${weekly_stats.get('freelance', 0):.2f}
  Total: ${weekly_stats.get('total', 0):.2f}

📊 Win Rate: {weekly_stats.get('win_rate', 0):.1f}%
  Trades: {weekly_stats.get('trades', 0)}
  Reports: {weekly_stats.get('reports', 0)}"""
        return self.send(subject, body.strip())


def test_email():
    bot = EmailBot()
    success = bot.send(
        "🧪 Test - Email System Online",
        f"System running with Resend. Time: {datetime.now().isoformat()}",
    )
    if success:
        logger.info("✅ Email system working!")
    else:
        logger.info("⚠️ Email test completed (check config)")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_email()
    else:
        bot = EmailBot()
        if bot.resend_key:
            logger.info(f"✅ Resend API configured — sent {bot.sent_log['total_sent']} emails")
        else:
            logger.info("⚠️ Set RESEND_API_KEY env var for best deliverability")
