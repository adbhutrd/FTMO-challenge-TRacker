#!/usr/bin/env python3
"""
⚡ COMMAND CENTER — Unified Control & Monitoring System
========================================================
Single server that monitors and controls all bots, services, and systems.
Serves the command center dashboard and provides REST API for live data.
Also serves static files from deploy_assets/ so the dashboard can link
to other pages (index.html, tracker_dashboard.html, etc.).

Usage:
    python3 command_center.py [port]

Endpoints:
    GET  /                    - Command center dashboard (HTML)
    GET  /api/status          - All system statuses (JSON)
    GET  /api/logs?name=X     - Tail log file
    GET  /api/logs/list       - List available log files
    POST /api/action          - Trigger an action (restart, run, check)
    GET  /api/metrics         - Earnings and performance metrics
    GET  /api/processes       - Running processes
    GET  /*                   - Static files from deploy_assets/
"""

import http.server
import json
import os
import subprocess
import sys
import time
import re
import glob
import socket
import sqlite3
from datetime import datetime
from pathlib import Path

# Find an available port starting from the requested one
def find_available_port(preferred, max_attempts=20):
    for port in range(preferred, preferred + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", port))
            sock.close()
            return port
        except OSError:
            continue
    return preferred  # Give up, let it fail with a clear error

REQUESTED_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
PORT = find_available_port(REQUESTED_PORT)

HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME, "income", "logs")
TRADING_DIR = os.path.join(HOME, "trading")
DEPLOY_DIR = os.path.join(HOME, "deploy_assets")
MEME_DIR = os.path.join(HOME, "meme-coin-bot")
INCOME_DIR = os.path.join(HOME, "income")


def run_cmd(cmd, timeout=5):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout[:2000], "stderr": result.stderr[:500], "code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out", "code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "code": -1}


def get_running_processes():
    """Get all our running processes."""
    result = run_cmd("ps aux | grep -v grep | grep -E 'python3|node.*server' | head -30")
    processes = []
    for line in result["stdout"].split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 11:
            continue
        try:
            proc = {
                "pid": parts[1],
                "cpu": parts[2],
                "mem": parts[3],
                "cmd": " ".join(parts[10:]),
            }
            cmd_lower = proc["cmd"].lower()
            if "ftmo_telegram_bot" in cmd_lower:
                proc["name"] = "FTMO Telegram Bot"; proc["icon"] = "📊"
            elif "ceo_processor" in cmd_lower:
                proc["name"] = "CEO AI Processor"; proc["icon"] = "🤖"
            elif "command_center" in cmd_lower:
                proc["name"] = "Command Center"; proc["icon"] = "⚡"
            elif "mayadice" in cmd_lower:
                proc["name"] = "MayaDice"; proc["icon"] = "🎲"
            elif "server.py" in cmd_lower:
                proc["name"] = "HTTP Server"; proc["icon"] = "🌐"
            elif "recon" in cmd_lower and "app.py" in cmd_lower:
                proc["name"] = "Recon Service"; proc["icon"] = "🔍"
            elif "guardian" in cmd_lower:
                proc["name"] = "24/7 Guardian"; proc["icon"] = "🛡️"
            elif "freebuff" in cmd_lower or "next" in cmd_lower:
                proc["name"] = "Freebuff (Next.js)"; proc["icon"] = "⚛️"
            elif "hermes" in cmd_lower and "gateway" in cmd_lower:
                proc["name"] = "Hermes Gateway"; proc["icon"] = "🧠"
            elif "screen" in cmd_lower:
                continue
            else:
                proc["name"] = proc["cmd"][:40]; proc["icon"] = "⚙️"
            processes.append(proc)
        except (IndexError, ValueError):
            continue
    return processes


def check_cron_jobs():
    """Parse crontab and check job status."""
    result = run_cmd("crontab -l 2>/dev/null")
    jobs = []
    for line in result["stdout"].split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        schedule = " ".join(parts[:5])
        command = parts[5]

        name = command; icon = "⏰"
        if "meme" in command.lower():
            name = "Meme-Coin Bot"; icon = "📈"
        elif "program" in command.lower() or "bounty" in command.lower():
            name = "Bug Bounty Monitor"; icon = "🔍"
        elif "social" in command.lower():
            name = "Social Content"; icon = "📱"
        elif "orchestrator" in command.lower():
            name = "Income Orchestrator"; icon = "🔄"
        elif "email" in command.lower():
            name = "Email Marketing"; icon = "📧"
        elif "daily" in command.lower():
            name = "Daily Summary"; icon = "📋"
        elif "guardian" in command.lower():
            name = "24/7 Guardian"; icon = "🛡️"
        elif "content" in command.lower():
            name = "Content Generator"; icon = "✍️"

        readable = schedule
        if len(parts) >= 5:
            try:
                mins = parts[0]; hours = parts[1]
                if mins == "*/15": readable = "Every 15 min"
                elif hours == "*/6": readable = "Every 6 hours"
                elif mins == "0" and hours == "*": readable = "Every hour"
                elif mins == "0" and hours in ("8,18", "8,18,1", "8,18,0"): readable = "8AM & 6PM"
                elif mins == "0" and hours == "21": readable = "9PM daily"
                elif mins == "*/2": readable = "Every 2 min"
            except: pass

        log_name = ""
        if "meme" in command.lower(): log_name = "cron_meme_bot.log"
        elif "program" in command.lower(): log_name = "cron_programs.log"
        elif "social" in command.lower(): log_name = "cron_social.log"
        elif "orchestrator" in command.lower(): log_name = "cron_orchestrator.log"
        elif "email" in command.lower(): log_name = "cron_email_marketing.log"
        elif "daily" in command.lower(): log_name = "cron_daily.log"
        elif "guardian" in command.lower(): log_name = "guardian.log"
        elif "content" in command.lower(): log_name = "cron_content.log"

        log_path = os.path.join(LOG_DIR, log_name)
        status = "unknown"
        if os.path.exists(log_path):
            age_mins = int((time.time() - os.path.getmtime(log_path)) / 60)
            if age_mins < 10: status = "running"
            elif age_mins < 60: status = "recent"
            elif age_mins < 360: status = "stale"
            else: status = "dead"
        else:
            status = "never"

        jobs.append({
            "name": name, "icon": icon, "schedule": readable,
            "command": command[:60], "status": status,
            "log": log_name, "log_path": str(log_path),
        })
    return jobs


def check_logs():
    """Get list of all log files with basic info."""
    log_files = []
    if not os.path.exists(LOG_DIR):
        return log_files
    for f in sorted(os.listdir(LOG_DIR)):
        if f.endswith(".log"):
            path = os.path.join(LOG_DIR, f)
            try:
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
                age_mins = int((time.time() - mtime) / 60)
                last_lines = ""
                try:
                    with open(path, "r") as lf:
                        lines = lf.readlines()
                        last_lines = lines[-3:] if len(lines) >= 3 else lines[-len(lines):]
                        last_lines = "".join(last_lines)[:200]
                except: pass

                mini_status = "ok" if age_mins < 60 else "stale"
                if any(w in last_lines.lower() for w in ["error", "failed", "❌", "broken", "timeout"]):
                    mini_status = "error"
                elif any(w in last_lines.lower() for w in ["⚠️", "warn", "not set", "skipping"]):
                    mini_status = "warning"

                log_files.append({
                    "name": f, "size": size, "size_hr": f"{size/1024:.1f}K",
                    "age_mins": age_mins,
                    "age_hr": f"{age_mins}m" if age_mins < 60 else f"{age_mins//60}h{age_mins%60}m",
                    "status": mini_status, "last_lines": last_lines.strip(),
                })
            except: continue
    return log_files


def get_log_content(name, lines=30):
    """Get tail of a specific log file."""
    log_path = os.path.join(LOG_DIR, name)
    if not os.path.exists(log_path):
        for f in glob.glob(os.path.join(LOG_DIR, f"*{name}*.log")):
            log_path = f; break
        else:
            return {"error": f"Log file '{name}' not found"}
    try:
        result = run_cmd(f'tail -{lines} "{log_path}"')
        age_mins = int((time.time() - os.path.getmtime(log_path)) / 60)
        return {
            "name": os.path.basename(log_path), "age_mins": age_mins,
            "age_hr": f"{age_mins}m" if age_mins < 60 else f"{age_mins//60}h{age_mins%60}m",
            "size": os.path.getsize(log_path), "content": result["stdout"],
            "path": log_path,
        }
    except Exception as e:
        return {"error": str(e)}


def get_system_health():
    """Get overall system health metrics."""
    cpu = run_cmd("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
    mem = run_cmd("free -m | grep Mem")
    disk = run_cmd("df -h / | tail -1")
    uptime = run_cmd("uptime")
    cpu_pct = cpu["stdout"].strip() or "?%"
    mem_parts = mem["stdout"].split()
    mem_used = mem_parts[2] if len(mem_parts) > 2 else "?"
    mem_total = mem_parts[1] if len(mem_parts) > 1 else "?"
    return {
        "cpu": cpu_pct, "memory": f"{mem_used}/{mem_total} MB",
        "disk": disk["stdout"].strip(), "uptime": uptime["stdout"].strip(),
    }


def get_earnings_metrics():
    """Get earnings and performance metrics from available data."""
    metrics = {
        "revenue": {"total": 0, "monthly": 0, "currency": "USD"},
        "bots": {}, "projects": [],
    }
    # Meme-coin
    meme_log = os.path.join(LOG_DIR, "cron_meme_bot.log")
    if os.path.exists(meme_log):
        try:
            with open(meme_log, "r") as f:
                content = f.read()
            bal = re.search(r'Balance:\s*\$?([0-9.]+)', content)
            pnl = re.search(r'P&L:\s*\$?([+-]?[0-9.]+)', content)
            opn = re.search(r'Open:\s*(\d+)', content)
            metrics["bots"]["meme_coin"] = {
                "balance": float(bal.group(1)) if bal else 100.0,
                "open_positions": int(opn.group(1)) if opn else 0,
                "pnl": float(pnl.group(1)) if pnl else 0.0,
            }
        except: pass
    # Bug bounty
    prog_log = os.path.join(LOG_DIR, "cron_programs.log")
    pf = 0
    if os.path.exists(prog_log):
        try:
            with open(prog_log, "r") as f:
                m = re.search(r'(\d+)\s+programs?', f.read())
                if m: pf = int(m.group(1))
        except: pass
    metrics["bots"]["bug_bounty"] = {"programs_tracked": pf or 4}
    # SEO
    seo_dir = os.path.join(TRADING_DIR, "seo_content")
    sc = len(glob.glob(os.path.join(seo_dir, "*.html"))) if os.path.exists(seo_dir) else 0
    metrics["bots"]["seo"] = {"pages_generated": sc}
    # Content
    cd = os.path.join(INCOME_DIR, "content")
    cc = len(glob.glob(os.path.join(cd, "*.md"))) if os.path.exists(cd) else 0
    metrics["bots"]["content"] = {"articles_generated": cc}
    # Social
    sl = os.path.join(LOG_DIR, "cron_social.log")
    sp = 0
    if os.path.exists(sl):
        try:
            with open(sl, "r") as f: sp = f.read().count("Generated")
        except: pass
    metrics["bots"]["social"] = {"posts_generated": sp}
    # Projects
    metrics["projects"] = [
        {"name": "FTMO Tracker Pro", "type": "SaaS", "status": "live", "price": "$19.99/mo"},
        {"name": "Bug Bounty Portfolio", "type": "Service", "status": "active"},
        {"name": "SEO Content", "type": "Marketing", "status": "active", "pages": sc},
    ]
    return metrics


def perform_action(action_data):
    """Execute a management action."""
    action = action_data.get("action", "")
    target = action_data.get("target", "")

    def safe_kill(pattern):
        pid = run_cmd(f"pgrep -f '{pattern}' | head -1")["stdout"].strip()
        if pid:
            run_cmd(f"kill {pid} 2>/dev/null; sleep 1")

    if action == "restart":
        if target == "ftmo-bot":
            safe_kill("python3.*ftmo_telegram_bot")
            run_cmd(f"cd {TRADING_DIR} && screen -dmS ftmo-bot python3 ftmo_telegram_bot.py")
            return {"status": "ok", "message": "FTMO Bot restart initiated"}
        elif target == "ceo":
            safe_kill("python3.*ceo_processor")
            run_cmd(f"cd {TRADING_DIR} && screen -dmS ceo-ai python3 ceo_processor.py --watch")
            return {"status": "ok", "message": "CEO AI restart initiated"}
        elif target == "server":
            run_cmd(f"cd {DEPLOY_DIR} && nohup python3 server.py 3000 > /tmp/server_restart.log 2>&1 &")
            return {"status": "ok", "message": "HTTP Server restart initiated"}
        elif target == "guardian":
            run_cmd(f"cd {HOME} && bash 24x7_guardian.sh &")
            return {"status": "ok", "message": "Guardian check triggered"}
    elif action == "run":
        if target == "meme-bot":
            run_cmd(f"cd {MEME_DIR} && {HOME}/agentic-aama/.venv/bin/python3 bot/main.py --once >> {LOG_DIR}/cron_meme_bot.log 2>&1 &")
            return {"status": "ok", "message": "Meme bot cycle triggered"}
        elif target == "program-monitor":
            run_cmd(f"cd {INCOME_DIR} && {HOME}/agentic-aama/.venv/bin/python3 tools/enhanced_program_bot.py --once >> {LOG_DIR}/cron_programs.log 2>&1 &")
            return {"status": "ok", "message": "Bug bounty scan triggered"}
        elif target == "social":
            run_cmd(f"cd {INCOME_DIR} && {HOME}/agentic-aama/.venv/bin/python3 tools/enhanced_social_bot.py --batch 3 >> {LOG_DIR}/cron_social.log 2>&1 &")
            return {"status": "ok", "message": "Social content generation triggered"}
        elif target == "guardian":
            run_cmd(f"cd {HOME} && bash 24x7_guardian.sh")
            return {"status": "ok", "message": "Guardian check completed"}
    elif action == "check-env":
        env_checks = {}
        for var in ["GMAIL_APP_PASSWORD", "TELEGRAM_BOT_TOKEN", "CEO_CHAT_ID", "OPENROUTER_API_KEY", "STRIPE_API_KEY", "GEMINI_API_KEY"]:
            env_checks[var] = False
        env_files = [
            os.path.join(HOME, "freebuff", ".env.local"),
            os.path.join(HOME, ".hermes", ".env"),
        ]
        for ef in env_files:
            if os.path.exists(ef):
                try:
                    with open(ef) as f:
                        for line in f:
                            line = line.strip()
                            if "=" in line and not line.startswith("#"):
                                k = line.split("=")[0].strip()
                                v = line.split("=", 1)[1].strip().strip("'\"")
                                if k in env_checks and v:
                                    env_checks[k] = True
                except: pass
        return {"status": "ok", "env": env_checks}
    return {"status": "error", "message": f"Unknown action: {action}/{target}"}


def get_full_status():
    """Get complete system status."""
    return {
        "timestamp": datetime.now().isoformat(),
        "system": get_system_health(),
        "processes": get_running_processes(),
        "cron_jobs": check_cron_jobs(),
        "logs": check_logs(),
        "metrics": get_earnings_metrics(),
    }


# ════════════════════════════════════════════════════════════════
#  Email Marketing / Waitlist API
# ════════════════════════════════════════════════════════════════

EMAIL_DB_PATH = os.path.join(HOME, "income", "email_marketing.db")


def handle_waitlist(body):
    """Handle waitlist signup - add to email database."""
    email = body.get("email", "").strip().lower()
    name = body.get("name", "").strip()
    source = body.get("source", "waitlist")

    if not email or "@" not in email:
        return {"status": "error", "message": "Valid email required"}

    try:
        sys.path.insert(0, INCOME_DIR)
        from tools.email_marketing.contacts import ContactDB
        from tools.email_marketing.campaigns import CampaignManager

        db = ContactDB(EMAIL_DB_PATH)
        contact_id = db.add_contact(email, name, source, tags=["waitlist", "ftmo-pro"])

        if contact_id:
            # Enroll in welcome sequence
            try:
                manager = CampaignManager()
                manager.db = db
                manager.setup_welcome_sequence()
                conn = db._get_conn()
                seq = conn.execute(
                    "SELECT id FROM sequences WHERE name = 'Welcome Sequence' LIMIT 1"
                ).fetchone()
                if seq:
                    db.enroll_in_sequence(contact_id, seq["id"])
            except Exception as seq_err:
                # Sequence enrollment is non-critical, but log it for debugging
                print(f'  ⚠️ Sequence enrollment failed: {seq_err}')

            return {
                "status": "ok",
                "message": "Added to waitlist",
                "contact_id": contact_id,
                "total": db.get_subscriber_count()["active"]
            }
        else:
            # Already exists - just update source
            db.update_contact(email, {"source": source})
            return {
                "status": "ok",
                "message": "Already on waitlist",
                "total": db.get_subscriber_count()["active"]
            }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {e}"}


def handle_campaign_action(body):
    """Handle campaign management actions."""
    action = body.get("action", "")
    try:
        sys.path.insert(0, INCOME_DIR)
        from tools.email_marketing.campaigns import CampaignManager
        manager = CampaignManager()

        if action == "create-welcome":
            seq_id = manager.setup_welcome_sequence()
            return {"status": "ok", "message": f"Welcome sequence ready (ID: {seq_id})"}
        elif action == "send-campaign":
            campaign_id = body.get("campaign_id")
            if not campaign_id:
                return {"status": "error", "message": "campaign_id required"}
            result = manager.send_campaign(campaign_id)
            return {"status": "ok", "result": result}
        elif action == "run-pipeline":
            result = manager.run_pipeline()
            return {"status": "ok", "result": result}
        elif action == "create-promo":
            title = body.get("title", "Special Offer")
            cid = manager.create_promo_campaign(
                title=title,
                body_text=body.get("body", ""),
                cta_url=body.get("cta_url", "https://gumroad.com/l/ezteprg"),
                cta_text=body.get("cta_text", "Get Pro Access →"),
                target_tag=body.get("target_tag", "ftmo-pro"),
                urgency=body.get("urgency", ""),
            )
            return {"status": "ok", "campaign_id": cid}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_email_stats():
    """Get email marketing statistics."""
    try:
        sys.path.insert(0, INCOME_DIR)
        from tools.email_marketing.contacts import ContactDB
        db = ContactDB(EMAIL_DB_PATH)
        return {"status": "ok", "stats": db.get_stats(), "resend_key_set": bool(os.environ.get("RESEND_API_KEY", ""))}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ════════════════════════════════════════════════════════════════
#  Sigma Cloud Sync API
# ════════════════════════════════════════════════════════════════

SIGMA_DB_PATH = os.path.join(HOME, "income", "sigma_sync.db")

# Free tier limits
SIGMA_FREE_MAX_TRADES = 20
SIGMA_PRO_MAX_TRADES = 999999


def _init_sigma_db():
    """Initialize Sigma sync database."""
    conn = sqlite3.connect(SIGMA_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sigma_users (
            email TEXT PRIMARY KEY,
            sync_key TEXT NOT NULL UNIQUE,
            tier TEXT DEFAULT 'free',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sync TIMESTAMP,
            trade_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sigma_trade_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email)
        );
    """)
    conn.commit()
    return conn


def _generate_sync_key():
    """Generate a random sync key."""
    import hashlib
    raw = f"{time.time()}{os.urandom(16).hex()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _verify_sigma_user(email, sync_key):
    """Verify user exists and key matches."""
    conn = _init_sigma_db()
    row = conn.execute(
        "SELECT * FROM sigma_users WHERE email = ? AND sync_key = ?",
        (email.strip().lower(), sync_key)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def handle_sigma_register(body):
    """Register a user for Sigma cloud sync."""
    email = body.get("email", "").strip().lower()
    if not email or "@" not in email:
        return {"status": "error", "message": "Valid email required"}

    conn = _init_sigma_db()
    try:
        # Check if already registered
        existing = conn.execute("SELECT * FROM sigma_users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            return {
                "status": "ok",
                "message": "Already registered",
                "tier": existing["tier"],
                "sync_key": existing["sync_key"],
                "trade_count": existing["trade_count"],
                "last_sync": existing["last_sync"],
            }

        sync_key = _generate_sync_key()
        conn.execute(
            "INSERT INTO sigma_users (email, sync_key, tier) VALUES (?, ?, 'free')",
            (email, sync_key)
        )
        conn.commit()
        conn.close()

        return {
            "status": "ok",
            "message": "Registered successfully",
            "sync_key": sync_key,
            "tier": "free",
            "trade_count": 0,
            "max_trades": SIGMA_FREE_MAX_TRADES,
        }
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


def handle_sigma_upload(body):
    """Upload trade data to cloud."""
    email = body.get("email", "").strip().lower()
    sync_key = body.get("sync_key", "")
    trade_data = body.get("data", "")  # JSON string of trades

    if not email or not sync_key or not trade_data:
        return {"status": "error", "message": "email, sync_key, and data required"}

    user = _verify_sigma_user(email, sync_key)
    if not user:
        return {"status": "error", "message": "Invalid credentials. Register first."}

    # Parse trades to count them
    try:
        parsed = json.loads(trade_data)
        trades = parsed if isinstance(parsed, list) else parsed.get("trades", [])
        trade_count = len(trades)
    except:
        return {"status": "error", "message": "Invalid trade data format"}

    # Check tier limits
    max_trades = SIGMA_PRO_MAX_TRADES if user["tier"] == "pro" else SIGMA_FREE_MAX_TRADES
    if trade_count > max_trades:
        return {
            "status": "error",
            "message": f"Tier limit exceeded. Free: {SIGMA_FREE_MAX_TRADES} trades. Upgrade to Pro for unlimited.",
            "tier": user["tier"],
            "max_trades": max_trades,
            "your_count": trade_count,
        }

    conn = _init_sigma_db()
    try:
        conn.execute(
            """INSERT INTO sigma_trade_data (user_email, data, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(user_email)
               DO UPDATE SET data = excluded.data, updated_at = datetime('now')""",
            (email, json.dumps({"trades": trades}))
        )
        conn.execute(
            "UPDATE sigma_users SET last_sync = datetime('now'), trade_count = ? WHERE email = ?",
            (trade_count, email)
        )
        conn.commit()
        conn.close()

        return {
            "status": "ok",
            "message": "Synced successfully",
            "trade_count": trade_count,
            "tier": user["tier"],
        }
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


def handle_sigma_download(email, sync_key):
    """Download trade data from cloud."""
    if not email or not sync_key:
        return {"status": "error", "message": "email and sync_key required"}

    user = _verify_sigma_user(email, sync_key)
    if not user:
        return {"status": "error", "message": "Invalid credentials. Register first."}

    conn = _init_sigma_db()
    row = conn.execute(
        "SELECT * FROM sigma_trade_data WHERE user_email = ?", (email,)
    ).fetchone()
    conn.close()

    if row:
        data = json.loads(row["data"])
        return {
            "status": "ok",
            "data": data,
            "tier": user["tier"],
            "last_sync": row["updated_at"],
            "trade_count": user["trade_count"],
        }
    else:
        return {
            "status": "ok",
            "data": {"trades": []},
            "tier": user["tier"],
            "trade_count": 0,
            "message": "No data in cloud yet",
        }


def handle_sigma_status(email, sync_key):
    """Check sync status and limits."""
    if not email or not sync_key:
        return {"status": "error", "message": "email and sync_key required"}

    user = _verify_sigma_user(email, sync_key)
    if not user:
        return {"status": "error", "message": "Invalid credentials"}

    max_trades = SIGMA_PRO_MAX_TRADES if user["tier"] == "pro" else SIGMA_FREE_MAX_TRADES

    return {
        "status": "ok",
        "tier": user["tier"],
        "trade_count": user["trade_count"],
        "max_trades": max_trades,
        "last_sync": user["last_sync"],
        "registered_at": user["registered_at"],
    }


def handle_sigma_upgrade(body):
    """Upgrade a user to Pro tier (admin, triggered manually after payment verification)."""
    email = body.get("email", "").strip().lower()
    admin_key = body.get("admin_key", "")

    # Simple admin auth - matches env var or a hardcoded key
    if admin_key != os.environ.get("SIGMA_ADMIN_KEY", "sigma-pro-admin-2026"):
        return {"status": "error", "message": "Unauthorized"}

    conn = _init_sigma_db()
    try:
        conn.execute("UPDATE sigma_users SET tier = 'pro' WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        return {"status": "ok", "message": f"{email} upgraded to Pro"}
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}


# ════════════════════════════════════════════════════════════════
#  HTTP Request Handler
# ════════════════════════════════════════════════════════════════

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".xml": "application/xml",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".ipynb": "application/json",
}


class CommandCenterHandler(http.server.BaseHTTPRequestHandler):

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return self.rfile.read(length).decode()
        return "{}"

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        query = {}
        if "?" in self.path:
            for part in self.path.split("?", 1)[1].split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    query[k] = v

        try:
            if path == "/api/status":
                self._send_json(get_full_status())
            elif path == "/api/processes":
                self._send_json({"processes": get_running_processes()})
            elif path == "/api/cron":
                self._send_json({"cron_jobs": check_cron_jobs()})
            elif path == "/api/logs":
                name = query.get("name", "")
                lines = int(query.get("lines", 50))
                self._send_json(get_log_content(name, lines))
            elif path == "/api/logs/list":
                self._send_json({"logs": check_logs()})
            elif path == "/api/metrics":
                self._send_json(get_earnings_metrics())
            elif path == "/api/system":
                self._send_json(get_system_health())
            elif path == "/api/health":
                self._send_json({"status": "ok", "time": datetime.now().isoformat()})
            elif path == "/api/email/stats":
                self._send_json(get_email_stats())
            elif path == "/api/sigma/download":
                self._send_json(handle_sigma_download(query.get("email",""), query.get("key","")))
            elif path == "/api/sigma/status":
                self._send_json(handle_sigma_status(query.get("email",""), query.get("key","")))
            elif path == "/" or not path:
                self._send_html(get_dashboard_html())
            else:
                self._serve_static(path)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _serve_static(self, path):
        """Serve static files from DEPLOY_DIR."""
        safe_path = path.lstrip("/")
        if ".." in safe_path or safe_path.startswith("/"):
            self._send_json({"error": "Forbidden"}, 403)
            return
        filepath = os.path.normpath(os.path.join(DEPLOY_DIR, safe_path))
        # Ensure we don't escape DEPLOY_DIR
        if not filepath.startswith(os.path.normpath(DEPLOY_DIR)):
            self._send_json({"error": "Forbidden"}, 403)
            return
        if os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1].lower()
            content_type = MIME_TYPES.get(ext, "application/octet-stream")
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "max-age=30")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            # Try index.html in subdirectory
            dir_path = filepath
            idx = os.path.join(dir_path, "index.html")
            if os.path.isdir(dir_path) and os.path.isfile(idx):
                self._serve_static("/" + os.path.relpath(idx, DEPLOY_DIR))
            else:
                self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = json.loads(self._read_body())
        except: body = {}
        try:
            if path == "/api/action":
                self._send_json(perform_action(body))
            elif path == "/api/waitlist":
                result = handle_waitlist(body)
                self._send_json(result)
            elif path == "/api/email/campaign":
                result = handle_campaign_action(body)
                self._send_json(result)
            elif path == "/api/sigma/register":
                self._send_json(handle_sigma_register(body))
            elif path == "/api/sigma/upload":
                self._send_json(handle_sigma_upload(body))
            elif path == "/api/sigma/upgrade":
                self._send_json(handle_sigma_upgrade(body))
            else:
                self._send_json({"error": "Not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def log_message(self, format, *args):
        pass  # Suppress default logging


def get_dashboard_html():
    """Return the command center HTML from deploy_assets."""
    path = os.path.join(DEPLOY_DIR, "command_center.html")
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return "<html><body><h1>Command Center</h1><p>command_center.html not found in deploy_assets/</p></body></html>"


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    server_address = ("", PORT)
    print(f"""
⚡ COMMAND CENTER — ONLINE
═══════════════════════════════
  Dashboard : http://localhost:{PORT}
  API       : http://localhost:{PORT}/api/status
═══════════════════════════════
""")
    httpd = http.server.HTTPServer(server_address, CommandCenterHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down command center...")
        httpd.shutdown()
