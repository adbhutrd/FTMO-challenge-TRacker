#!/usr/bin/env python3
"""
📱 SMS Gateway — Open-Source SMS Service
==========================================
Self-hosted SMS gateway using an Android phone + open-source software.
Acts as a middleware between your apps and the phone's SMS gateway app.

Architecture:
  Android Phone (sms-gate.app)  ←HTTP→  This Server (sms_gateway.py)  ←API→  Your Apps
                                          ↕
                                     SQLite Queue (persistent, retries on failure)

Setup:
  1. Install sms-gate.app on a spare Android phone with SIM card
  2. Install Tailscale on phone and server
  3. Configure .env.sms with your phone's Tailscale IP and API key
  4. Run: python3 sms_gateway.py

Features:
  - REST API for sending SMS
  - Webhook endpoint for receiving SMS
  - Persistent message queue (retries on phone offline)
  - Rate limiting
  - Integration hooks for FTMO tracker, trading bots, alerts
"""

import os
import sys
import json
import time
import hashlib
import logging
import asyncio
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Callable

import requests

# Try to load Twilio
try:
    from twilio.rest import Client as TwilioClient
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False

# Try to load optional deps gracefully
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# ── Paths ──────────────────────────────────────────────────────────────
HOME = Path.home()
BASE_DIR = HOME / "sms_gateway"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "sms_queue.db"
LOG_PATH = BASE_DIR / "sms_gateway.log"
ENV_PATH = HOME / ".env.sms"

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | SMS-GW | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("sms_gateway")


# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

class Config:
    """Load configuration from .env.sms file."""

    def __init__(self):
        # Provider: 'twilio' or 'android'
        self.provider: str = "twilio"
        
        # Twilio settings
        self.twilio_sid: str = ""
        self.twilio_token: str = ""
        self.twilio_phone: str = ""
        
        # Android phone gateway settings
        self.phone_ip: str = ""
        self.phone_port: int = 8080
        self.api_key: str = ""
        
        # Server settings
        self.server_port: int = 8765
        self.webhook_url: str = ""
        self.max_retries: int = 3
        self.retry_delay: int = 60
        self.rate_limit_per_min: int = 20
        self.default_phone: str = ""
        self._load()

    def _load(self):
        """Load from .env.sms file with defaults."""
        env_vars = {
            "SMS_PROVIDER": ("provider", str),
            "TWILIO_ACCOUNT_SID": ("twilio_sid", str),
            "TWILIO_AUTH_TOKEN": ("twilio_token", str),
            "TWILIO_PHONE_NUMBER": ("twilio_phone", str),
            "SMS_PHONE_IP": ("phone_ip", str),
            "SMS_PHONE_PORT": ("phone_port", int),
            "SMS_API_KEY": ("api_key", str),
            "SMS_SERVER_PORT": ("server_port", int),
            "SMS_WEBHOOK_URL": ("webhook_url", str),
            "SMS_MAX_RETRIES": ("max_retries", int),
            "SMS_RETRY_DELAY": ("retry_delay", int),
            "SMS_RATE_LIMIT": ("rate_limit_per_min", int),
            "SMS_DEFAULT_PHONE": ("default_phone", str),
        }

        # Load from env file
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

        # Apply env vars
        for env_key, (attr, typ) in env_vars.items():
            val = os.getenv(env_key)
            if val:
                try:
                    setattr(self, attr, typ(val))
                except (ValueError, TypeError):
                    pass

    def validate(self) -> list[str]:
        """Return list of missing required settings."""
        missing = []
        if self.provider == "twilio":
            if not self.twilio_sid:
                missing.append("TWILIO_ACCOUNT_SID")
            if not self.twilio_token:
                missing.append("TWILIO_AUTH_TOKEN")
            if not self.twilio_phone:
                missing.append("TWILIO_PHONE_NUMBER")
        else:
            if not self.phone_ip:
                missing.append("SMS_PHONE_IP (Tailscale IP of your Android phone)")
            if not self.api_key:
                missing.append("SMS_API_KEY (from sms-gate.app settings)")
        return missing

    def provider_label(self) -> str:
        return "Twilio" if self.provider == "twilio" else "Android Phone"

    def save_template(self):
        """Write a template .env.sms file."""
        if not ENV_PATH.exists():
            template = """# 📱 SMS Gateway Configuration
# ==================================
# Provider: 'twilio' or 'android'
SMS_PROVIDER=twilio

# ── Twilio (permanent number) ──
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# ── Android Phone (open source) ──
# SMS_PHONE_IP=100.x.x.x
# SMS_PHONE_PORT=8080
# SMS_API_KEY=your_key

# ── Server ──
SMS_SERVER_PORT=8765
SMS_RATE_LIMIT=20
SMS_DEFAULT_PHONE=
"""
            ENV_PATH.write_text(template)
            logger.info(f"📝 Template written to {ENV_PATH}")
            return True
        return False


config = Config()


# ═══════════════════════════════════════════════════════════════════════
#  DATABASE — Persistent Message Queue
# ═══════════════════════════════════════════════════════════════════════

class MessageDB:
    """SQLite-backed persistent queue for SMS messages."""

    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    direction   TEXT NOT NULL CHECK (direction IN ('outgoing', 'incoming')),
                    phone       TEXT NOT NULL,
                    message     TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'sent', 'failed', 'delivered')),
                    retries     INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    webhook_url TEXT DEFAULT '',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at     TIMESTAMP,
                    carrier_ref TEXT DEFAULT ''
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    window_start TIMESTAMP,
                    count        INTEGER DEFAULT 0
                )
            """)
            self.conn.commit()

    def enqueue(self, phone: str, message: str, webhook_url: str = "") -> int:
        """Add an outgoing SMS to the queue. Returns message ID."""
        with self.lock:
            cur = self.conn.execute(
                "INSERT INTO messages (direction, phone, message, status, max_retries, webhook_url) "
                "VALUES ('outgoing', ?, ?, 'pending', ?, ?)",
                (phone, message, config.max_retries, webhook_url),
            )
            self.conn.commit()
            msg_id = cur.lastrowid
            logger.info(f"📤 Queued SMS #{msg_id} to {phone}: {message[:50]}...")
            return msg_id

    def get_pending(self, limit: int = 5) -> list[dict]:
        """Get pending outgoing messages."""
        with self.lock:
            rows = self.conn.execute(
                "SELECT id, phone, message, retries, max_retries FROM messages "
                "WHERE direction='outgoing' AND status='pending' "
                "ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "id": r[0], "phone": r[1], "message": r[2],
                    "retries": r[3], "max_retries": r[4],
                }
                for r in rows
            ]

    def mark_sent(self, msg_id: int, carrier_ref: str = ""):
        with self.lock:
            self.conn.execute(
                "UPDATE messages SET status='sent', sent_at=CURRENT_TIMESTAMP, carrier_ref=? WHERE id=?",
                (carrier_ref, msg_id),
            )
            self.conn.commit()

    def mark_failed(self, msg_id: int, reason: str = ""):
        with self.lock:
            self.conn.execute(
                "UPDATE messages SET status='failed', retries=retries+1 WHERE id=?",
                (msg_id,),
            )
            self.conn.commit()
            logger.warning(f"❌ SMS #{msg_id} failed: {reason}")

    def retry_later(self, msg_id: int):
        """Increment retry count but keep as pending."""
        with self.lock:
            row = self.conn.execute(
                "SELECT retries, max_retries FROM messages WHERE id=?",
                (msg_id,),
            ).fetchone()
            if row and row[0] < row[1]:
                self.conn.execute(
                    "UPDATE messages SET retries=retries+1, status='pending' WHERE id=?",
                    (msg_id,),
                )
                self.conn.commit()
                return True
            else:
                self.mark_failed(msg_id, "max_retries_exceeded")
                return False

    def record_incoming(self, phone: str, message: str, carrier_ref: str = ""):
        """Log an incoming SMS."""
        with self.lock:
            self.conn.execute(
                "INSERT INTO messages (direction, phone, message, status, carrier_ref) "
                "VALUES ('incoming', ?, ?, 'delivered', ?)",
                (phone, message, carrier_ref),
            )
            self.conn.commit()

    def get_recent(self, limit: int = 20) -> list[dict]:
        """Get recent messages."""
        with self.lock:
            rows = self.conn.execute(
                "SELECT id, direction, phone, message, status, created_at FROM messages "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {"id": r[0], "direction": r[1], "phone": r[2],
                 "message": r[3][:100], "status": r[4], "time": r[5]}
                for r in rows
            ]

    def can_send(self) -> bool:
        """Check rate limit."""
        with self.lock:
            # Clean old entries
            self.conn.execute(
                "DELETE FROM rate_limits WHERE window_start < datetime('now', '-1 minute')"
            )
            row = self.conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM rate_limits "
                "WHERE window_start >= datetime('now', '-1 minute')"
            ).fetchone()
            current = row[0] if row else 0
            if current >= config.rate_limit_per_min:
                return False
            # Increment
            self.conn.execute(
                "INSERT INTO rate_limits (window_start, count) VALUES (CURRENT_TIMESTAMP, 1)"
            )
            self.conn.commit()
            return True

    def stats(self) -> dict:
        with self.lock:
            total = self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            sent = self.conn.execute("SELECT COUNT(*) FROM messages WHERE status='sent'").fetchone()[0]
            failed = self.conn.execute("SELECT COUNT(*) FROM messages WHERE status='failed'").fetchone()[0]
            pending = self.conn.execute(
                "SELECT COUNT(*) FROM messages WHERE direction='outgoing' AND status='pending'"
            ).fetchone()[0]
            incoming = self.conn.execute(
                "SELECT COUNT(*) FROM messages WHERE direction='incoming'"
            ).fetchone()[0]
            return {
                "total": total, "sent": sent, "failed": failed,
                "pending": pending, "incoming": incoming,
            }


db = MessageDB()


# ═══════════════════════════════════════════════════════════════════════
#  PROVIDER: Twilio
# ═══════════════════════════════════════════════════════════════════════

class TwilioProvider:
    """SMS via Twilio API — permanent, reliable, instant."""

    def __init__(self):
        self.client = None
        self.from_number = ""
        if config.twilio_sid and config.twilio_token:
            self.client = TwilioClient(config.twilio_sid, config.twilio_token)
            self.from_number = config.twilio_phone

    def send_sms(self, to_phone: str, message: str) -> tuple[bool, str]:
        """Send SMS via Twilio. Returns (success, message_sid_or_error)."""
        if not self.client:
            return False, "twilio_not_configured"
        if not self.from_number:
            return False, "no_twilio_phone_number"

        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_phone,
            )
            logger.info(f"✅ Twilio SMS sent to {to_phone}: SID={msg.sid}")
            return True, msg.sid
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ Twilio error for {to_phone}: {error_str[:150]}")
            return False, error_str[:100]

    def check_health(self) -> dict:
        """Check Twilio account status."""
        if not self.client:
            return {"status": "not_configured"}
        try:
            account = self.client.api.accounts(config.twilio_sid).fetch()
            balance = "trial" if account.type == "Trial" else "active"
            return {
                "status": "ok",
                "account": account.friendly_name,
                "type": account.type,
                "from_number": self.from_number,
                "balance_status": balance,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)[:100]}


# ═══════════════════════════════════════════════════════════════════════
#  PROVIDER: Android Phone (sms-gate.app)
# ═══════════════════════════════════════════════════════════════════════

class AndroidProvider:
    """HTTP client for the Android sms-gate.app."""

    def __init__(self):
        self.base_url = f"http://{config.phone_ip}:{config.phone_port}" if config.phone_ip else ""
        self.headers = {"X-Auth-Token": config.api_key}
        self.session = requests.Session()
        self.session.timeout = 10

    def send_sms(self, phone: str, message: str) -> tuple[bool, str]:
        """Send SMS via the Android gateway."""
        if not self.base_url:
            return False, "android_not_configured"
        url = f"{self.base_url}/message"
        payload = {"phone": phone, "message": message}

        try:
            resp = self.session.post(url, json=payload, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"📱 Android SMS sent to {phone}: {data}")
                return True, data.get("id", "ok")
            else:
                logger.warning(f"⚠️ Android gateway returned {resp.status_code}: {resp.text[:200]}")
                return False, f"HTTP {resp.status_code}"
        except requests.ConnectionError:
            logger.warning("⚠️ Android gateway unreachable (phone offline?)")
            return False, "phone_offline"
        except requests.Timeout:
            logger.warning("⚠️ Android gateway timeout")
            return False, "timeout"
        except Exception as e:
            logger.error(f"❌ Android gateway error: {e}")
            return False, str(e)[:100]

    def check_health(self) -> dict:
        """Check if the phone gateway is reachable."""
        if not self.base_url:
            return {"status": "not_configured"}
        try:
            resp = self.session.get(f"{self.base_url}/health", headers=self.headers, timeout=5)
            if resp.status_code == 200:
                return {"status": "ok", "data": resp.json()}
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)[:100]}


# ═══════════════════════════════════════════════════════════════════════
#  PROVIDER SELECTOR
# ═══════════════════════════════════════════════════════════════════════

class SMSProvider:
    """Selects the right SMS provider based on config."""

    def __init__(self):
        self.twilio = TwilioProvider()
        self.android = AndroidProvider()

    @property
    def _active(self):
        if config.provider == "twilio" and config.twilio_sid:
            return self.twilio
        return self.android

    def send_sms(self, phone: str, message: str) -> tuple[bool, str]:
        return self._active.send_sms(phone, message)

    def check_health(self) -> dict:
        active = self._active
        result = active.check_health()
        result["provider"] = config.provider_label()
        result["from_number"] = config.twilio_phone if config.provider == "twilio" else config.phone_ip
        return result


phone = SMSProvider()


# ═══════════════════════════════════════════════════════════════════════
#  QUEUE PROCESSOR — Background worker that drains the queue
# ═══════════════════════════════════════════════════════════════════════

class QueueProcessor:
    """Background thread that processes the outgoing SMS queue."""

    def __init__(self):
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("🔄 Queue processor started")

    def stop(self):
        self.running = False
        logger.info("⏹ Queue processor stopped")

    def _run(self):
        while self.running:
            try:
                self._process_batch()
            except Exception as e:
                logger.error(f"❌ Queue processor error: {e}")
            time.sleep(5)  # Check every 5 seconds

    def _process_batch(self):
        pending = db.get_pending(limit=5)
        for msg in pending:
            if not self.running:
                break

            if not db.can_send():
                logger.info("⏳ Rate limited, waiting...")
                time.sleep(5)
                break

            success, result = phone.send_sms(msg["phone"], msg["message"])
            if success:
                db.mark_sent(msg["id"], str(result))
                logger.info(f"✅ SMS #{msg['id']} sent to {msg['phone']}")
            else:
                if result in ("phone_offline", "timeout"):
                    # Phone might be offline — retry later
                    retried = db.retry_later(msg["id"])
                    if retried:
                        logger.info(f"⏳ SMS #{msg['id']} queued for retry")
                    else:
                        logger.warning(f"❌ SMS #{msg['id']} max retries reached")
                else:
                    db.mark_failed(msg["id"], result)


# ═══════════════════════════════════════════════════════════════════════
#  WEBHOOK HANDLER — Process incoming SMS from the phone
# ═══════════════════════════════════════════════════════════════════════

# Callback registry for incoming SMS
_incoming_handlers: list[Callable] = []


def on_incoming_sms(func: Callable):
    """Decorator to register a handler for incoming SMS."""
    _incoming_handlers.append(func)
    return func


def handle_incoming_sms(phone_number: str, message: str, carrier_ref: str = ""):
    """Process an incoming SMS through all registered handlers."""
    logger.info(f"📩 Incoming SMS from {phone_number}: {message[:80]}...")
    db.record_incoming(phone_number, message, carrier_ref)

    for handler in _incoming_handlers:
        try:
            handler(phone_number, message)
        except Exception as e:
            logger.error(f"❌ Handler {handler.__name__} error: {e}")


# ═══════════════════════════════════════════════════════════════════════
#  BUILT-IN HANDLERS — Integrate with project services
# ═══════════════════════════════════════════════════════════════════════

# ── Bot command handler (reply via SMS to simple commands) ─────────
SMS_COMMANDS = {
    "status": "📊 Send /status to the Telegram bot for full challenge status",
    "help": "Commands: /status, /balance, /add <amount>",
}

@on_incoming_sms
def handle_sms_commands(phone: str, message: str):
    """Handle simple SMS commands."""
    msg = message.strip().lower()

    if msg == "status":
        send_sms(phone, "📊 Check the Telegram bot @ArdTradingBot for full status")
    elif msg.startswith("help"):
        send_sms(phone, "Commands: STATUS, BALANCE, ADD <amount>")
    elif msg.startswith("add "):
        send_sms(phone, "✅ Use @ArdTradingBot on Telegram to add trades")
    elif msg == "balance":
        send_sms(phone, "💰 Check your balance via @ArdTradingBot on Telegram")


# ── Alert handler for system notifications ─────────────────────────
def send_alert(message: str, phone: str = ""):
    """Send a system alert via SMS."""
    target = phone or config.default_phone
    if not target:
        logger.warning("⚠️ No default phone configured for alerts")
        return False
    return send_sms(target, f"🔔 {message}")


# ═══════════════════════════════════════════════════════════════════════
#  PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def send_sms(phone: str, message: str, webhook_url: str = "") -> dict:
    """
    Public API to send an SMS.
    Queues the message and returns immediately.
    
    Args:
        phone: Recipient phone number (E.164 format, e.g., +1234567890)
        message: Text message to send
        webhook_url: Optional URL to notify on delivery
        
    Returns:
        dict with message_id and status
    """
    if not phone or not message:
        return {"error": "phone and message required", "status": "error"}

    msg_id = db.enqueue(phone, message, webhook_url)
    return {"message_id": msg_id, "status": "queued"}


def send_sms_sync(phone: str, message: str) -> dict:
    """
    Send SMS immediately (blocking). Use for urgent messages.
    Falls back to queue if phone is offline.
    """
    if not db.can_send():
        return send_sms(phone, message)  # Queue it

    success, result = phone.send_sms(phone, message)
    if success:
        msg_id = db.enqueue(phone, message)
        db.mark_sent(msg_id, str(result))
        return {"message_id": msg_id, "status": "sent"}
    else:
        return send_sms(phone, message)  # Fall back to queue


def get_stats() -> dict:
    """Get gateway statistics."""
    return {
        "database": db.stats(),
        "phone": phone.check_health(),
        "config": {
            "phone_ip": config.phone_ip,
            "server_port": config.server_port,
            "rate_limit": config.rate_limit_per_min,
            "default_phone": "***" + config.default_phone[-4:] if config.default_phone else None,
        },
    }


# ═══════════════════════════════════════════════════════════════════════
#  FASTAPI SERVER
# ═══════════════════════════════════════════════════════════════════════

if HAS_FASTAPI:

    app = FastAPI(
        title="SMS Gateway",
        description="Self-hosted SMS gateway — send/receive SMS via Android phone",
        version="1.0.0",
    )
    processor = QueueProcessor()

    @app.on_event("startup")
    async def startup():
        processor.start()
        logger.info("🚀 SMS Gateway started")

    @app.on_event("shutdown")
    async def shutdown():
        processor.stop()
        logger.info("👋 SMS Gateway stopped")

    # ── API Endpoints ──

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        phone_status = phone.check_health()
        return {
            "status": "ok",
            "phone": phone_status["status"],
            "queue_pending": db.stats()["pending"],
            "uptime": "running",
        }

    @app.post("/send")
    async def api_send(request: Request):
        """
        Send an SMS.
        
        Body:
            { "phone": "+1234567890", "message": "Hello!", "webhook_url": "..." }
        """
        body = await request.json()
        phone_num = body.get("phone", "").strip()
        message = body.get("message", "").strip()
        webhook = body.get("webhook_url", "").strip()
        immediate = body.get("immediate", False)

        if not phone_num or not message:
            raise HTTPException(status_code=400, detail="phone and message required")

        if immediate:
            result = send_sms_sync(phone_num, message)
        else:
            result = send_sms(phone_num, message, webhook)

        return result

    @app.post("/webhook/incoming")
    async def webhook_incoming(request: Request):
        """
        Webhook endpoint for the Android phone to forward incoming SMS.
        
        Expected body (from sms-gate.app):
            { "phone": "+1234567890", "message": "Hello back!", "id": "..." }
        """
        try:
            body = await request.json()
            phone_num = body.get("phone", body.get("from", ""))
            message = body.get("message", body.get("text", ""))
            carrier_ref = body.get("id", body.get("message_id", ""))

            handle_incoming_sms(phone_num, message, carrier_ref)
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
            return {"status": "error", "detail": str(e)}

    @app.get("/messages")
    async def list_messages(limit: int = 20):
        """List recent messages."""
        return {"messages": db.get_recent(limit)}

    @app.get("/stats")
    async def api_stats():
        """Get system statistics."""
        return get_stats()

    @app.post("/alert")
    async def api_alert(request: Request):
        """
        Send a system alert SMS.
        
        Body:
            { "message": "Server CPU > 90%", "phone": "+1234567890" }
        """
        body = await request.json()
        msg = body.get("message", "")
        phone_num = body.get("phone", "")
        result = send_alert(msg, phone_num)
        return {"sent": result, "status": "queued" if result else "no_phone"}


# ═══════════════════════════════════════════════════════════════════════
#  CLI — Command-line interface
# ═══════════════════════════════════════════════════════════════════════

def cli():
    """Command-line interface."""
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "setup":
        """Generate template .env.sms file."""
        if config.save_template():
            print(f"✅ Template written to {ENV_PATH}")
            print(f"   Edit it with: nano {ENV_PATH}")
        else:
            print(f"ℹ️  {ENV_PATH} already exists")

    elif cmd == "check":
        """Check configuration and phone connectivity."""
        missing = config.validate()
        if missing:
            print("❌ Missing configuration:")
            for m in missing:
                print(f"   • {m}")
            print(f"\n   Run: python3 sms_gateway.py setup")
        else:
            print("✅ Configuration OK")
            print(f"   Phone: {config.phone_ip}:{config.phone_port}")
            print(f"   Server: port {config.server_port}")
            health = phone.check_health()
            print(f"   Phone reachable: {'✅' if health['status'] == 'ok' else '❌ ' + str(health)}")

    elif cmd == "send":
        """Send an SMS: python3 sms_gateway.py send +1234567890 \"Hello!\" """
        if len(args) < 3:
            print("Usage: sms_gateway.py send <phone> <message>")
            return
        phone_num = args[1]
        message = " ".join(args[2:])
        result = send_sms_sync(phone_num, message)
        print(json.dumps(result, indent=2))

    elif cmd == "stats":
        """Show gateway statistics."""
        stats = get_stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "serve":
        """Start the HTTP server."""
        if not HAS_FASTAPI:
            print("❌ FastAPI required. Install: pip3 install fastapi uvicorn")
            sys.exit(1)

        missing = config.validate()
        if missing:
            print("❌ Missing configuration:")
            for m in missing:
                print(f"   • {m}")
            print(f"\n   Run: python3 sms_gateway.py setup")
            sys.exit(1)

        print(f"\n{'='*50}")
        print(f"  📱 SMS Gateway Server")
        print(f"  Phone: {config.phone_ip}:{config.phone_port}")
        print(f"  Server: http://0.0.0.0:{config.server_port}")
        print(f"  Queue: {DB_PATH}")
        print(f"  Logs: {LOG_PATH}")
        print(f"{'='*50}\n")

        uvicorn.run(app, host="0.0.0.0", port=config.server_port, log_level="info")

    elif cmd == "test":
        """Test sending an SMS to yourself."""
        phone_num = args[1] if len(args) > 1 else config.default_phone
        if not phone_num:
            print("❌ No phone number. Usage: sms_gateway.py test +1234567890")
            return
        message = "🧪 Test message from SMS Gateway! Sent at " + datetime.now().strftime("%H:%M:%S")
        result = send_sms_sync(phone_num, message)
        print(json.dumps(result, indent=2))
        if result.get("status") == "sent":
            print("✅ SMS sent! Check your phone.")
        else:
            print(f"ℹ️  Queued (ID: {result.get('message_id')})")

    elif cmd == "alerts":
        """Show recent alerts/messages."""
        msgs = db.get_recent(10)
        print(f"\n📋 Recent Messages ({len(msgs)}):")
        print(f"{'ID':>4} {'Dir':8s} {'Phone':16s} {'Message':50s} {'Status':10s} {'Time':20s}")
        print("-" * 110)
        for m in msgs:
            print(f"{m['id']:>4} {m['direction']:8s} {m['phone']:16s} {m['message'][:50]:50s} {m['status']:10s} {m['time'][:19]:20s}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    cli()
