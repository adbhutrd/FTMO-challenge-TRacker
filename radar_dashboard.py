#!/usr/bin/env python3
"""
📊 Industry Research Radar — Web Dashboard Server
===================================================
Serves a dashboard at http://localhost:8766 showing all tracked jobs,
scan history, and allowing you to mark jobs as applied.

Usage:
  python3 radar_dashboard.py              # Start server on port 8766
  python3 radar_dashboard.py --port 8080  # Custom port
  python3 radar_dashboard.py --open       # Start and open browser
"""

import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | DASHBOARD | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("radar_dashboard")

# ── Config ──────────────────────────────────────────────────────────

DATA_DIR = Path.home() / "radar_data"
DB_PATH = DATA_DIR / "radar.db"
DASHBOARD_HTML_PATH = Path(__file__).parent / "radar_dashboard.html"
PORT = 8766
SCAN_SCRIPT = Path(__file__).parent / "radar.py"

# ── Scan State with Per-Company Progress ───────────────────────────

COMPANY_LIST = [
    "ASML", "Philips", "ING", "Booking.com", "Adyen",
    "Elastic", "Mollie", "KPN", "TomTom", "ABN AMRO", "NCSC",
]

COMPANY_ICONS = {
    "ASML": "🔬",
    "Philips": "💡",
    "ING": "🏦",
    "Booking.com": "🏨",
    "Adyen": "💳",
    "Elastic": "🔎",
    "Mollie": "💸",
    "KPN": "📡",
    "TomTom": "🗺️",
    "ABN AMRO": "🏛️",
    "NCSC": "🛡️",
}

_scan_state = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "status": "idle",  # "idle", "running", "completed", "failed"
    "message": "",
    # Per-company progress
    "total_companies": len(COMPANY_LIST),
    "completed_companies": 0,
    "current_company": None,
    "company_statuses": {c: "pending" for c in COMPANY_LIST},  # pending/running/completed/failed
}
_scan_lock = threading.Lock()


def run_scan_background():
    """Run the radar scanner company-by-company with per-company progress tracking."""
    global _scan_state
    with _scan_lock:
        _scan_state["running"] = True
        _scan_state["started_at"] = datetime.now(timezone.utc).isoformat()
        _scan_state["status"] = "running"
        _scan_state["message"] = "Scan in progress..."
        _scan_state["completed_companies"] = 0
        _scan_state["current_company"] = None
        _scan_state["company_statuses"] = {c: "pending" for c in COMPANY_LIST}
    
    try:
        for idx, company in enumerate(COMPANY_LIST):
            # Mark current company as running
            with _scan_lock:
                _scan_state["current_company"] = company
                _scan_state["company_statuses"][company] = "running"
            
            # Run radar.py for this single company (no --dry-run for real scan with SMS)
            try:
                result = subprocess.run(
                    [sys.executable, str(SCAN_SCRIPT), company],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(Path.home()),
                )
                with _scan_lock:
                    if result.returncode == 0:
                        _scan_state["company_statuses"][company] = "completed"
                    else:
                        _scan_state["company_statuses"][company] = "failed"
                        _scan_state["message"] = f"{company} failed (code {result.returncode})"
            except subprocess.TimeoutExpired:
                with _scan_lock:
                    _scan_state["company_statuses"][company] = "failed"
                    _scan_state["message"] = f"{company} timed out"
            except Exception as e:
                with _scan_lock:
                    _scan_state["company_statuses"][company] = "failed"
                    _scan_state["message"] = f"{company} error: {str(e)[:80]}"
            
            # Update completion count
            with _scan_lock:
                _scan_state["completed_companies"] = idx + 1
        
        # All done — determine overall status
        with _scan_lock:
            failed_count = sum(1 for s in _scan_state["company_statuses"].values() if s == "failed")
            if failed_count == 0:
                _scan_state["status"] = "completed"
                _scan_state["message"] = "All companies scanned successfully"
            elif failed_count < len(COMPANY_LIST):
                _scan_state["status"] = "completed"
                _scan_state["message"] = f"{len(COMPANY_LIST) - failed_count}/{len(COMPANY_LIST)} companies completed, {failed_count} failed"
            else:
                _scan_state["status"] = "failed"
                _scan_state["message"] = "All companies failed to scan"
        
        # Log a summary ALL scan entry so send_telegram_alerts() can find it
        try:
            conn = get_conn()
            if conn:
                total_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE active = 1").fetchone()[0]
                total_new = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE first_seen >= ?",
                    (_scan_state["started_at"],)
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO scan_log (scan_time, company, jobs_found, new_matches, alerts_sent) "
                    "VALUES (?, 'ALL', ?, ?, 0)",
                    (datetime.now(timezone.utc).isoformat(), total_jobs, total_new),
                )
                conn.commit()
                conn.close()
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to log summary scan: {e}")
        
        # Send Telegram alerts to subscribers if scan completed with new jobs
        if _scan_state["status"] == "completed":
            try:
                send_telegram_alerts()
            except Exception as e:
                logger.warning(f"  ⚠️ Telegram alerts error: {e}")
    except Exception as e:
        with _scan_lock:
            _scan_state["status"] = "failed"
            _scan_state["message"] = f"Scan engine error: {str(e)[:100]}"
    finally:
        with _scan_lock:
            _scan_state["running"] = False
            _scan_state["finished_at"] = datetime.now(timezone.utc).isoformat()


def get_scan_status() -> dict:
    """Get the current scan status with per-company progress."""
    with _scan_lock:
        return dict(_scan_state)


def trigger_scan() -> bool:
    """Trigger a scan if one isn't already running."""
    with _scan_lock:
        if _scan_state["running"]:
            return False
    
    thread = threading.Thread(target=run_scan_background, daemon=True)
    thread.start()
    return True


# ── Telegram Alerts ─────────────────────────────────────────────────

SUBSCRIBERS_PATH = DATA_DIR / "telegram_subscribers.json"

# Cached Telegram bot info (lazy-loaded)
_telegram_bot_info = None

def get_telegram_bot_info() -> dict:
    """Get Telegram bot information via the Bot API getMe.
    
    Returns dict with: configured, bot_username, first_name, subscriber_count
    """
    global _telegram_bot_info
    if _telegram_bot_info is not None:
        return _telegram_bot_info
    
    token = os.environ.get("RADAR_TELEGRAM_BOT_TOKEN", "")
    if not token:
        _telegram_bot_info = {
            "configured": False,
            "bot_username": "",
            "first_name": "",
            "subscriber_count": 0,
        }
        return _telegram_bot_info
    
    # Get bot username from Telegram API
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            bot_user = data.get("result", {})
            _telegram_bot_info = {
                "configured": True,
                "bot_username": bot_user.get("username", ""),
                "first_name": bot_user.get("first_name", ""),
            }
    except Exception as e:
        logger.warning(f"  ⚠️ Failed to get Telegram bot info: {e}")
        _telegram_bot_info = {
            "configured": True,
            "bot_username": "",
            "first_name": "",
        }
    
    # Add subscriber count
    try:
        if SUBSCRIBERS_PATH.exists():
            subs = json.loads(SUBSCRIBERS_PATH.read_text())
            _telegram_bot_info["subscriber_count"] = sum(
                1 for d in subs.values() if d.get("enabled", False)
            )
        else:
            _telegram_bot_info["subscriber_count"] = 0
    except (json.JSONDecodeError, OSError):
        _telegram_bot_info["subscriber_count"] = 0
    
    return _telegram_bot_info


def check_bot_process() -> dict:
    """Check if the Telegram bot process is running.
    
    Returns dict with:
      - bot_running: True if a radar_bot.py process is found
      - last_activity: ISO timestamp of the last log line (if bot is running)
    """
    bot_running = False
    last_activity = None
    
    # Check for bot process via pgrep
    try:
        result = subprocess.run(
            ["pgrep", "-f", "radar_bot.py"],
            capture_output=True, text=True, timeout=5,
        )
        # pgrep returns 0 if matching processes found
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(p) for p in result.stdout.strip().split() if p.strip()]
            # Filter out our own pgrep command and the dashbaord server
            alive = []
            for pid in pids:
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = f.read().decode().replace("\x00", " ")
                        if "radar_bot.py" in cmd and "pgrep" not in cmd:
                            alive.append(pid)
                except (FileNotFoundError, ProcessLookupError, OSError):
                    pass
            if alive:
                bot_running = True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    
    # Check bot log file for last activity
    if bot_running:
        bot_log = DATA_DIR / "bot.log"
        if bot_log.exists():
            try:
                mtime = datetime.fromtimestamp(bot_log.stat().st_mtime, tz=timezone.utc)
                last_activity = mtime.isoformat()
            except OSError:
                pass
    
    return {"bot_running": bot_running, "last_activity": last_activity}


def invalidate_telegram_bot_info():
    """Clear cached bot info so it's re-fetched on next request."""
    global _telegram_bot_info
    _telegram_bot_info = None


def send_telegram_alerts():
    """Send scan results to all Telegram subscribers via Bot API.
    
    Reads subscribers from telegram_subscribers.json (created by radar_bot.py),
    queries the DB for the latest scan's new jobs, and sends a message
    to each subscriber via the Telegram HTTP API.
    """
    token = os.environ.get("RADAR_TELEGRAM_BOT_TOKEN", "")
    if not token:
        return  # Bot not configured — nothing to send
    
    # Load subscribers
    if not SUBSCRIBERS_PATH.exists():
        return  # No subscribers yet
    try:
        subscribers = json.loads(SUBSCRIBERS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return
    
    active_chats = [int(cid) for cid, data in subscribers.items()
                    if data.get("enabled", False)]
    if not active_chats:
        return
    
    # Get latest scan stats
    conn = get_conn()
    if not conn:
        return
    
    last_scan = conn.execute(
        "SELECT scan_time, jobs_found, new_matches FROM scan_log "
        "WHERE company IS NULL OR company = 'ALL' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    
    # Get new jobs found in this scan (filtered by scan start time)
    scan_start = _scan_state.get("started_at") or "1970-01-01"
    new_jobs = conn.execute(
        "SELECT company, title, url FROM jobs "
        "WHERE first_seen >= ? AND applied = 0 "
        "ORDER BY first_seen DESC LIMIT 5",
        (scan_start,),
    ).fetchall()
    conn.close()
    
    if not last_scan:
        return
    
    # Only send alerts if new jobs were found
    new_count = last_scan["new_matches"]
    if not new_count or new_count == 0:
        return
    
    # Build the message
    scan_time = last_scan["scan_time"][:19] if last_scan["scan_time"] else "just now"
    total_found = last_scan["jobs_found"]
    
    lines = [
        "✅ *Radar found new matching jobs!*\n",
        f"📋 {total_found} total matching jobs",
        f"🆕 {new_count} new\n",
    ]
    
    if new_jobs:
        lines.append("*Recent New:*")
        for job in new_jobs:
            icon = COMPANY_ICONS.get(job["company"], "🏢")
            title = job["title"][:55]
            lines.append(f"  {icon} {title}")
        lines.append("")
    
    lines.append("🔍 Dashboard: http://localhost:8766")
    lines.append("🤖 /status in the Telegram bot for full stats")
    
    message_text = "\n".join(lines)
    
    # Send to each subscriber via Telegram HTTP API
    for chat_id in active_chats:
        try:
            payload = json.dumps({
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "Markdown",
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10):
                logger.info(f"  📨 Telegram alert sent to chat {chat_id}")
        except urllib.error.HTTPError as e:
            if e.code == 403:
                # Bot was blocked by user — remove them from subscribers
                logger.warning(f"  ⚠️ Chat {chat_id} blocked the bot, removing from subscribers")
                subscribers.pop(str(chat_id), None)
                SUBSCRIBERS_PATH.write_text(json.dumps(subscribers, indent=2))
                invalidate_telegram_bot_info()  # Refresh cached subscriber count
            else:
                logger.warning(f"  ⚠️ Telegram send to {chat_id} failed: {e.code} {e.reason[:80]}")
        except Exception as e:
            logger.warning(f"  ⚠️ Telegram send to {chat_id} failed: {str(e)[:80]}")


# ── Database ─────────────────────────────────────────────────────────

def get_conn():
    """Get a database connection with the applied column if needed."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # Ensure the applied column exists (added in Phase 2)
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN applied INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists or table doesn't exist yet
    
    return conn


def get_all_jobs(company: str = None, status: str = None, search: str = None) -> list:
    """Get all jobs with optional filters."""
    conn = get_conn()
    if not conn:
        return []
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    
    if company and company != "all":
        query += " AND company = ?"
        params.append(company)
    
    if status == "applied":
        query += " AND applied = 1"
    elif status == "new":
        query += " AND applied = 0"
    
    if search:
        query += " AND (title LIKE ? OR company LIKE ? OR url LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    query += " ORDER BY first_seen DESC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Get dashboard statistics."""
    conn = get_conn()
    if not conn:
        return {"total_jobs": 0, "applied_jobs": 0, "new_jobs": 0, "active_jobs": 0,
                "total_scans": 0, "last_scan": "Never", "by_company": []}
    
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied = 1").fetchone()[0]
    new_this = total - applied
    active = conn.execute("SELECT COUNT(*) FROM jobs WHERE active = 1").fetchone()[0]
    
    by_company = conn.execute(
        "SELECT company, COUNT(*) as count, COALESCE(SUM(applied), 0) as applied_count "
        "FROM jobs GROUP BY company ORDER BY count DESC"
    ).fetchall()
    
    last_scan = conn.execute(
        "SELECT scan_time FROM scan_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    
    total_scans = conn.execute("SELECT COUNT(*) FROM scan_log").fetchone()[0]
    
    conn.close()
    
    return {
        "total_jobs": total,
        "applied_jobs": applied,
        "new_jobs": new_this,
        "active_jobs": active,
        "total_scans": total_scans,
        "last_scan": last_scan[0] if last_scan else "Never",
        "by_company": [dict(r) for r in by_company],
    }


def get_scan_history(limit: int = 50) -> list:
    """Get recent scan history."""
    conn = get_conn()
    if not conn:
        return []
    rows = conn.execute(
        "SELECT * FROM scan_log ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_job_applied(job_id: str, applied: bool = True) -> bool:
    """Mark a job as applied (or unmark)."""
    conn = get_conn()
    if not conn:
        return False
    conn.execute(
        "UPDATE jobs SET applied = ? WHERE id = ?",
        (1 if applied else 0, job_id)
    )
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


# ── HTTP Server ──────────────────────────────────────────────────────

class RadarDashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the radar dashboard."""
    
    def _send_json(self, data, status=200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
    def _send_html(self, html, status=200):
        """Send an HTML response."""
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def _send_404(self):
        """Send a 404 response."""
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not found")
    
    def _read_body(self) -> str:
        """Read the request body."""
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return self.rfile.read(length).decode()
        return ""
    
    def _get_route(self) -> tuple:
        """Parse the URL and return (path, query_params)."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)
        return path, params
    
    def do_GET(self):
        """Handle GET requests."""
        path, params = self._get_route()
        
        if path == "/" or path == "":
            self._serve_dashboard()
        elif path == "/api/jobs":
            company = params.get("company", [None])[0]
            status = params.get("status", [None])[0]
            search = params.get("search", [None])[0]
            jobs = get_all_jobs(company=company, status=status, search=search)
            self._send_json({"jobs": jobs, "count": len(jobs)})
        elif path == "/api/stats":
            stats = get_stats()
            self._send_json(stats)
        elif path == "/api/scans":
            limit = int(params.get("limit", [50])[0])
            scans = get_scan_history(limit=limit)
            self._send_json({"scans": scans, "count": len(scans)})
        elif path == "/api/scan/status":
            status = get_scan_status()
            self._send_json(status)
        elif path == "/api/telegram/status":
            # Merge cached config with real-time process health
            info = get_telegram_bot_info()
            info.update(check_bot_process())
            self._send_json(info)
        else:
            self._send_404()
    
    def do_POST(self):
        """Handle POST requests."""
        path, _ = self._get_route()
        
        if path.startswith("/api/jobs/") and path.endswith("/apply"):
            job_id = path.replace("/api/jobs/", "").replace("/apply", "")
            success = mark_job_applied(job_id, applied=True)
            self._send_json({"success": success, "applied": True})
        elif path.startswith("/api/jobs/") and path.endswith("/unapply"):
            job_id = path.replace("/api/jobs/", "").replace("/unapply", "")
            success = mark_job_applied(job_id, applied=False)
            self._send_json({"success": success, "applied": False})
        elif path == "/api/scan":
            triggered = trigger_scan()
            status = get_scan_status()
            self._send_json({"triggered": triggered, "status": status})
        else:
            self._send_404()
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def _serve_dashboard(self):
        """Serve the dashboard HTML file."""
        if DASHBOARD_HTML_PATH.exists():
            html = DASHBOARD_HTML_PATH.read_text()
            self._send_html(html)
        else:
            self._send_html("<h1>Radar Dashboard</h1><p>Dashboard HTML not found. Run: python3 radar.py --dry-run first to populate data.</p>")
    
    def log_message(self, format, *args):
        """Log requests to stdout."""
        if "/api/" in self.path:
            # Quiet mode for API calls
            pass
        else:
            print(f"  📡 {args[0]} {self.path}")


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    """Start the dashboard server."""
    global PORT
    
    args = sys.argv[1:]
    
    if "--port" in args:
        idx = args.index("--port") + 1
        if idx < len(args):
            PORT = int(args[idx])
    
    open_browser = "--open" in args
    
    server = HTTPServer(("0.0.0.0", PORT), RadarDashboardHandler)
    
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║     📊 Industry Research Radar — Dashboard      ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print(f"  ║  Server:  http://localhost:{PORT}                    ║")
    print(f"  ║  DB:      {DB_PATH}  ║")
    print(f"  ║  API:     http://localhost:{PORT}/api/stats         ║")
    print("  ║                                                  ║")
    print("  ║  Press Ctrl+C to stop                            ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    
    if open_browser:
        webbrowser.open(f"http://localhost:{PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  👋 Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
