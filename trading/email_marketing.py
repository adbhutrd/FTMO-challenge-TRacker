#!/usr/bin/env python3
"""
📧 EMAIL MARKETING — Lead Capture & Auto-Responder
====================================================
Captures emails from website visitors, sends automated sequences.
Builds email list for promotions.

Usage:
    python3 email_marketing.py --capture <email> [name]
    python3 email_marketing.py --send-welcome <email>
    python3 email_marketing.py --campaign <name>
    python3 email_marketing.py --stats
    python3 email_marketing.py --server
"""

import json
import os
import sys
import smtplib
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

HOME = Path.home()
TRADING_DIR = HOME / "trading"
INCOME_DIR = HOME / "income"
DATA_DIR = INCOME_DIR / "email_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = INCOME_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | EMAIL | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "email_marketing.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("email_mkt")

# ── Email Templates ────────────────────────────────────────────────

WELCOME_SEQUENCE = [
    {
        "subject": "Welcome to FTMO Challenge Tracker! 📊",
        "body": """Hi {name},

Welcome to FTMO Challenge Tracker! 

Here's your free challenge tracking starter pack:

1. 🌐 **Web Tracker:** https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html
   No signup needed - just open and start tracking.

2. 🤖 **Telegram Bot:** @ArdTradingBot
   Track from your phone with 11 commands.

3. 📈 **Pro Features (Free Trial):** https://gumroad.com/l/ezteprg
   Cloud sync, unlimited accounts, PDF reports.

Quick Start:
1. Set up: /setup 2step 50000
2. Add a day: /add 50200
3. Check: /status

Happy trading!
- FTMO Tracker Team""",
    },
    {
        "subject": "Tip: The #1 Rule That Fails FTMO Traders",
        "body": """Hi {name},

Quick tip: The most common reason FTMO challenges fail is **drawdown miscalculation**.

Most traders think drawdown = (current balance - starting balance) / starting balance

But FTMO calculates it as:
❌ Drawdown = (peak balance - current balance) / peak balance

This means if you hit $55,000 then drop to $52,000, your drawdown is 5.45%, not 4%.

Our tracker handles this automatically. Just enter your balance after each trading day.

👉 Track now: https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html

Best,
FTMO Tracker Team""",
    },
    {
        "subject": "Pro Features Now Available 🚀",
        "body": """Hi {name},

Great news! The FTMO Challenge Tracker Pro version is now available:

🔥 **Pro Features ($19.99/mo)**
✅ Cloud sync across all devices
✅ Unlimited accounts (track multiple challenges)
✅ PDF report export
✅ Email alerts for drawdown warnings
✅ Priority support

👉 Get Pro Access: https://gumroad.com/l/ezteprg

Special offer for early subscribers!

Best,
FTMO Tracker Team""",
    },
]


class EmailMarketing:
    """Email capture, list management, and campaign automation."""

    def __init__(self):
        self.leads_file = DATA_DIR / "leads.json"
        self.campaigns_file = DATA_DIR / "campaigns.json"
        self.load()

    def load(self):
        # Leads database
        if self.leads_file.exists():
            try:
                self.leads = json.loads(self.leads_file.read_text())
            except:
                self.leads = {}
        else:
            self.leads = {}

        # Campaigns
        if self.campaigns_file.exists():
            try:
                self.campaigns = json.loads(self.campaigns_file.read_text())
            except:
                self.campaigns = []
        else:
            self.campaigns = []

    def save(self):
        self.leads_file.write_text(json.dumps(self.leads, indent=2, default=str))
        self.campaigns_file.write_text(json.dumps(self.campaigns, indent=2, default=str))

    def capture_lead(self, email: str, name: str = "", source: str = "web") -> dict:
        """Capture a new email lead."""
        if email in self.leads:
            self.leads[email]["last_seen"] = datetime.now().isoformat()
            self.leads[email]["source"] = source
            self.save()
            return {"existing": True, "lead": self.leads[email]}

        lead = {
            "email": email,
            "name": name or email.split("@")[0],
            "source": source,
            "captured": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "emails_sent": 0,
            "sequence_step": 0,
            "converted": False,
            "conversion_date": None,
            "pro_subscriber": False,
            "tags": [],
        }
        self.leads[email] = lead
        self.save()
        logger.info(f"✅ Lead captured: {email} (source: {source})")
        return {"existing": False, "lead": lead}

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email via SMTP."""
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        from_email = os.getenv("FROM_EMAIL", "tracker@ftmo-income.com")

        if not all([smtp_host, smtp_user, smtp_pass]):
            logger.warning("⚠️ SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS")
            # Log email to file instead
            email_log = DATA_DIR / "email_queue.json"
            if email_log.exists():
                queue = json.loads(email_log.read_text())
            else:
                queue = []
            queue.append({
                "to": to_email,
                "subject": subject,
                "body": body,
                "timestamp": datetime.now().isoformat(),
            })
            email_log.write_text(json.dumps(queue, indent=2, default=str))
            logger.info(f"📧 Email queued for {to_email}: {subject}")
            return True  # Queued for later sending

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to_email], msg.as_string())

            logger.info(f"✅ Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"❌ Email send failed for {to_email}: {e}")
            return False

    def send_welcome_sequence(self, email: str) -> dict:
        """Send the welcome email sequence to a new lead."""
        if email not in self.leads:
            return {"error": "Lead not found"}

        lead = self.leads[email]
        results = []

        # Send emails based on current step
        step = lead.get("sequence_step", 0)
        emails_to_send = WELCOME_SEQUENCE[step:step+1]

        for template in emails_to_send:
            body = template["body"].format(name=lead["name"])
            success = self.send_email(email, template["subject"], body)
            results.append({
                "subject": template["subject"],
                "success": success,
            })
            if success:
                lead["emails_sent"] = lead.get("emails_sent", 0) + 1
                lead["sequence_step"] = lead.get("sequence_step", 0) + 1

        self.save()
        return {"results": results, "next_step": lead["sequence_step"]}

    def run_campaign(self, campaign_name: str) -> dict:
        """Run a campaign to all leads."""
        results = {"total": len(self.leads), "sent": 0, "errors": 0}
        campaign_leads = list(self.leads.values())

        if campaign_name == "welcome":
            for lead in campaign_leads:
                if lead["sequence_step"] < len(WELCOME_SEQUENCE):
                    result = self.send_welcome_sequence(lead["email"])
                    if result.get("results"):
                        results["sent"] += 1
                    else:
                        results["errors"] += 1
        elif campaign_name == "promo":
            promo_subject = "FTMO Challenge Tracker Pro - Limited Offer 🚀"
            promo_body = """Hi {name},

Ready to take your FTMO tracking to the next level?

Pro Features:
✅ Cloud sync across devices
✅ Unlimited accounts
✅ PDF report export
✅ Email alerts
✅ Priority support

👉 Get Pro Access: https://gumroad.com/l/ezteprg

Only $19.99/month - cancel anytime.

FTMO Tracker Team"""
            for lead in campaign_leads:
                if not lead.get("pro_subscriber"):
                    body = promo_body.format(name=lead["name"])
                    if self.send_email(lead["email"], promo_subject, body):
                        results["sent"] += 1
                    else:
                        results["errors"] += 1

        return results

    def get_stats(self) -> dict:
        """Get email marketing stats."""
        total = len(self.leads)
        converted = sum(1 for l in self.leads.values() if l.get("converted"))
        pro = sum(1 for l in self.leads.values() if l.get("pro_subscriber"))
        emails_sent = sum(l.get("emails_sent", 0) for l in self.leads.values())

        return {
            "total_leads": total,
            "converted": converted,
            "pro_subscribers": pro,
            "total_emails_sent": emails_sent,
            "conversion_rate": f"{(converted/total*100):.1f}%" if total > 0 else "0%",
        }

    def print_stats(self):
        s = self.get_stats()
        print(f"\n{'='*50}")
        print(f"  📧 EMAIL MARKETING STATS")
        print(f"{'='*50}")
        print(f"  Total Leads:     {s['total_leads']}")
        print(f"  Converted:       {s['converted']} ({s['conversion_rate']})")
        print(f"  Pro Subscribers: {s['pro_subscribers']}")
        print(f"  Emails Sent:     {s['total_emails_sent']}")
        print()

    def start_http_server(self):
        """Start a simple HTTP server to capture emails from web forms."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class EmailCaptureHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/capture"):
                    from urllib.parse import urlparse, parse_qs
                    params = parse_qs(urlparse(self.path).query)
                    email = params.get("email", [""])[0]
                    name = params.get("name", [""])[0]
                    source = params.get("source", ["web"])[0]
                    
                    if email:
                        capture_lead(email, name, source)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"status":"ok"}')
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"status":"error","message":"email required"}')
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b'<h1>Email Capture Server</h1><p>POST to /capture with email param</p>')
            
            def do_POST(self):
                if self.path == "/capture":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length)
                    try:
                        data = json.loads(body)
                        email = data.get("email", "")
                        name = data.get("name", "")
                        source = data.get("source", "api")
                        if email:
                            capture_lead(email, name, source)
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(b'{"status":"ok"}')
                        else:
                            self.send_response(400)
                            self.end_headers()
                            self.wfile.write(b'{"status":"error"}')
                    except:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"status":"error"}')
                else:
                    self.send_response(404)
                    self.end_headers()

        def handler_capture(email, name, source):
            s = EmailMarketing()
            s.capture_lead(email, name, source)
            s.send_welcome_sequence(email)

        self._handler_capture = handler_capture
        server = HTTPServer(("0.0.0.0", 8099), EmailCaptureHandler)
        print("📧 Email capture server running on port 8099...")
        server.serve_forever()


def main():
    system = EmailMarketing()

    if len(sys.argv) < 2:
        print("""📧 EMAIL MARKETING SYSTEM

Commands:
  --capture <email> [name]   Capture a new lead
  --send-welcome <email>     Send welcome sequence
  --campaign <name>          Run campaign (welcome, promo)
  --stats                    Show email stats
  --server                   Start email capture HTTP server
  --send-queue               Send queued emails
""")
        return

    cmd = sys.argv[1]

    if cmd == "--capture":
        email = sys.argv[2] if len(sys.argv) > 2 else ""
        name = sys.argv[3] if len(sys.argv) > 3 else ""
        if not email:
            print("❌ Email required")
            return
        result = system.capture_lead(email, name)
        system.send_welcome_sequence(email)
        print(f"✅ Lead captured: {email}")
        print(f"   Welcome sequence initiated")

    elif cmd == "--send-welcome":
        email = sys.argv[2] if len(sys.argv) > 2 else ""
        if not email:
            print("❌ Email required")
            return
        result = system.send_welcome_sequence(email)
        print(f"Sent: {result}")

    elif cmd == "--campaign":
        name = sys.argv[2] if len(sys.argv) > 2 else "welcome"
        result = system.run_campaign(name)
        print(f"Campaign '{name}': {result['sent']} sent, {result['errors']} errors")

    elif cmd == "--stats":
        system.print_stats()

    elif cmd == "--server":
        system.start_http_server()

    elif cmd == "--send-queue":
        queue_file = DATA_DIR / "email_queue.json"
        if queue_file.exists():
            queue = json.loads(queue_file.read_text())
            sent = 0
            for email in queue:
                if system.send_email(email["to"], email["subject"], email["body"]):
                    sent += 1
            print(f"Sent {sent}/{len(queue)} queued emails")
            # Clear queue
            queue_file.write_text("[]")
        else:
            print("No queued emails")

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
