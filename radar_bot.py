#!/usr/bin/env python3
"""
🤖 Industry Research Radar — Telegram Bot
===========================================
Telegram bot for the Industry Research Radar. Lets you check stats,
browse jobs, trigger scans, and receive new job alerts — all from Telegram.

Commands:
  /start       — Welcome message with available commands
  /status      — Dashboard stats (total jobs, applied, last scan, by company)
  /jobs        — List recent matching jobs (optional: company filter)
  /companies   — List all tracked companies with job counts
  /scans       — Show scan history (last 10)
  /scan        — Trigger a new scan (runs in background)
  /apply <id>  — Mark a job as applied (use the ID from /jobs output)
  /alerts      — Show or toggle new job alerts via Telegram

Setup:
  1. Create a bot via @BotFather on Telegram and get a token
  2. Export RADAR_TELEGRAM_BOT_TOKEN=your_token_here
  3. python3 radar_bot.py

Requires: python-telegram-bot >= 22.0
"""

import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | RADAR-BOT | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("radar_bot")

# ── Paths ────────────────────────────────────────────────────────────
HOME = Path.home()
DATA_DIR = HOME / "radar_data"
DB_PATH = DATA_DIR / "radar.db"
SCAN_SCRIPT = Path(__file__).parent / "radar.py"
SUBSCRIBERS_PATH = DATA_DIR / "telegram_subscribers.json"

# ── Company Icons & Display ─────────────────────────────────────────
COMPANY_ICONS = {
    "ASML": "🔬", "Philips": "💡", "ING": "🏦", "Booking.com": "🏨",
    "Adyen": "💳", "Elastic": "🔎", "Mollie": "💸", "KPN": "📡",
    "TomTom": "🗺️", "ABN AMRO": "🏛️", "NCSC": "🛡️",
}

COMPANY_LIST = [
    "ASML", "Philips", "ING", "Booking.com", "Adyen",
    "Elastic", "Mollie", "KPN", "TomTom", "ABN AMRO", "NCSC",
]


# ── Database Helpers ─────────────────────────────────────────────────

def get_conn():
    """Get a database connection."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Ensure applied column exists
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN applied INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    return conn


def get_stats():
    """Get dashboard statistics."""
    conn = get_conn()
    if not conn:
        return None
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied = 1").fetchone()[0]
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
        "new_jobs": total - applied,
        "total_scans": total_scans,
        "last_scan": last_scan[0] if last_scan else "Never",
        "by_company": [dict(r) for r in by_company],
    }


def get_jobs(company: str = None, status: str = None, limit: int = 15):
    """Get jobs with optional filters."""
    conn = get_conn()
    if not conn:
        return []
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if company:
        query += " AND company = ?"
        params.append(company)
    if status == "applied":
        query += " AND applied = 1"
    elif status == "new":
        query += " AND applied = 0"
    query += " ORDER BY first_seen DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_applied(job_id: str, applied: bool = True) -> bool:
    """Mark a job as applied or unmark it."""
    conn = get_conn()
    if not conn:
        return False
    conn.execute("UPDATE jobs SET applied = ? WHERE id = ?", (1 if applied else 0, job_id))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


def get_scan_history(limit: int = 10):
    """Get recent scan history."""
    conn = get_conn()
    if not conn:
        return []
    rows = conn.execute(
        "SELECT * FROM scan_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Alert Subscribers ───────────────────────────────────────────────

def load_subscribers() -> dict:
    """Load alert subscriber settings from JSON file."""
    if SUBSCRIBERS_PATH.exists():
        try:
            return json.loads(SUBSCRIBERS_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_subscribers(data: dict):
    """Save alert subscriber settings to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUBSCRIBERS_PATH.write_text(json.dumps(data, indent=2))


def set_alerts(chat_id: int, enabled: bool) -> bool:
    """Enable or disable Telegram alerts for a chat."""
    subs = load_subscribers()
    key = str(chat_id)
    if enabled:
        subs[key] = {
            "chat_id": chat_id,
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        subs.pop(key, None)
    save_subscribers(subs)
    return True


def is_alerts_enabled(chat_id: int) -> bool:
    """Check if alerts are enabled for a chat."""
    subs = load_subscribers()
    entry = subs.get(str(chat_id), {})
    return entry.get("enabled", False)


def get_all_subscribers() -> list[int]:
    """Get all chat IDs that have alerts enabled."""
    subs = load_subscribers()
    return [int(cid) for cid, data in subs.items() if data.get("enabled")]


# ── Scan Runner ─────────────────────────────────────────────────────

async def run_scan_async(chat_id: Optional[int] = None) -> dict:
    """Run a full radar scan asynchronously and return results."""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(SCAN_SCRIPT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(HOME),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        returncode = proc.returncode

        # Parse output for new jobs
        output = stdout.decode() + stderr.decode()
        new_count = 0
        total_found = 0
        new_jobs = []
        started = False

        for line in output.split("\n"):
            if "SCAN SUMMARY" in line:
                started = True
            if started and "New jobs discovered:" in line:
                try:
                    new_count = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            if started and "Total matching jobs found:" in line:
                try:
                    total_found = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            if "🆕 NEW:" in line:
                title = line.split("🆕 NEW:")[-1].strip()[:80]
                new_jobs.append(title)

        result = {
            "success": returncode == 0,
            "total_found": total_found,
            "new_count": new_count,
            "new_jobs": new_jobs,
            "returncode": returncode,
            "error": stderr.decode()[:500] if stderr else "",
        }
        return result
    except asyncio.TimeoutError:
        return {"success": False, "error": "Scan timed out after 5 minutes", "new_jobs": []}
    except Exception as e:
        return {"success": False, "error": str(e)[:200], "new_jobs": []}


# ── Formatting Helpers ──────────────────────────────────────────────

def format_stats(stats: dict) -> str:
    """Format stats into a Telegram-friendly message."""
    if not stats:
        return "❌ No data yet. Run a scan first with /scan"

    lines = [
        "📊 *Radar Dashboard Status*\n",
        f"• Total jobs:      {stats['total_jobs']}",
        f"• New / Unapplied:  {stats['new_jobs']}",
        f"• Applied:          {stats['applied_jobs']}",
        f"• Scans run:        {stats['total_scans']}",
        f"• Last scan:        {stats['last_scan'][:19]}",
        "",
        "📋 *Jobs by Company:*",
    ]

    if stats["by_company"]:
        max_name = max(len(c["company"]) for c in stats["by_company"])
        for c in stats["by_company"]:
            icon = COMPANY_ICONS.get(c["company"], "🏢")
            bar = "█" * min(c["count"], 20)
            applied_str = f" ✅{c['applied_count']}" if c["applied_count"] > 0 else ""
            lines.append(
                f"  {icon} `{c['company']:<{max_name}}`  "
                f"{c['count']:>3} jobs{applied_str}"
            )
    else:
        lines.append("  No jobs tracked yet.")

    return "\n".join(lines)


def format_jobs(jobs: list, show_all: bool = False) -> str:
    """Format job listings for Telegram."""
    if not jobs:
        return "🔍 No matching jobs found."

    # Show compact IDs (first 12 chars of the job ID)
    lines = [f"📋 *Jobs* ({len(jobs)} total):\n"]
    for j in jobs:
        icon = COMPANY_ICONS.get(j["company"], "🏢")
        short_id = j["id"][:12]
        applied = "✅" if j.get("applied") else "🆕"
        title = j["title"][:55]
        lines.append(f"{applied} `{short_id}` {icon} *{title}*")
    lines.append("")
    lines.append("Use `/apply <id_prefix>` to mark a job as applied.")
    lines.append("Use `/jobs <company>` to filter by company.")
    return "\n".join(lines)


def format_companies() -> str:
    """Format company list with job counts."""
    stats = get_stats()
    if not stats or not stats["by_company"]:
        return "No data yet."

    lines = ["🏢 *Tracked Companies*\n"]
    for c in stats["by_company"]:
        icon = COMPANY_ICONS.get(c["company"], "🏢")
        applied_str = f" (✅{c['applied_count']} applied)" if c["applied_count"] > 0 else ""
        lines.append(f"{icon} *{c['company']}* — {c['count']} jobs{applied_str}")
    return "\n".join(lines)


def format_scans(scans: list) -> str:
    """Format scan history for Telegram."""
    if not scans:
        return "No scans run yet."

    lines = ["📜 *Scan History* (last 10):\n"]
    for s in scans:
        time_str = s["scan_time"][:19] if s["scan_time"] else "?"
        company = s["company"] or "🌐 Full Scan"
        icon = COMPANY_ICONS.get(company, "🌐") if company != "ALL" else "🌐"
        lines.append(
            f"  {icon} `{company}` — 📋 {s['jobs_found']} found"
            f"{', 🆕 ' + str(s['new_matches']) + ' new' if s['new_matches'] else ''}"
        )
    return "\n".join(lines)


def format_help() -> str:
    """Format help message."""
    return (
        "🤖 *Industry Research Radar — Telegram Bot*\n\n"
        "`/start`       — Welcome & commands\n"
        "`/status`      — Dashboard stats & jobs by company\n"
        "`/jobs`        — Recent matching jobs\n"
        "`/jobs <company>` — Filter by company\n"
        "`/companies`   — All tracked companies with counts\n"
        "`/scans`       — Scan history (last 10)\n"
        "`/scan`        — Trigger a new scan\n"
        "`/apply <id>`  — Mark job as applied\n"
        "`/alerts`      — Toggle new job alerts via Telegram\n\n"
        "💡 Tip: Use `/status` first to see the big picture!"
    )


# ── Error Message ───────────────────────────────────────────────────

def error_msg(text: str) -> str:
    return f"❌ {text}"


# ═══════════════════════════════════════════════════════════════════════
#  TELEGRAM BOT — Commands
# ═══════════════════════════════════════════════════════════════════════

# Track if a scan is currently in progress (to prevent concurrent scans)
_scan_in_progress = False
_scan_lock = asyncio.Lock()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start."""
    await update.message.reply_text(format_help(), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help."""
    await update.message.reply_text(format_help(), parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status."""
    msg = await update.message.reply_text("📊 Loading stats...")
    stats = get_stats()
    await msg.edit_text(format_stats(stats), parse_mode="Markdown")


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /jobs [company] [status]."""
    args = context.args
    company = None
    status = None

    if args:
        # Check if first arg is a company name
        for c in COMPANY_LIST:
            if c.lower() == args[0].lower():
                company = c
                break
        # Check for status flag
        for a in args:
            if a.lower() in ("new", "unapplied"):
                status = "new"
            elif a.lower() == "applied":
                status = "applied"

    msg = await update.message.reply_text("🔍 Loading jobs...")
    jobs = get_jobs(company=company, status=status, limit=20)
    await msg.edit_text(format_jobs(jobs), parse_mode="Markdown")


async def cmd_companies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /companies."""
    msg = await update.message.reply_text("🏢 Loading companies...")
    reply = format_companies()
    await msg.edit_text(reply, parse_mode="Markdown")


async def cmd_scans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scans."""
    msg = await update.message.reply_text("📜 Loading scan history...")
    scans = get_scan_history(limit=10)
    await msg.edit_text(format_scans(scans), parse_mode="Markdown")


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scan — triggers a full scan."""
    global _scan_in_progress

    async with _scan_lock:
        if _scan_in_progress:
            await update.message.reply_text(
                "⏳ A scan is already running. Please wait for it to finish.",
                parse_mode="Markdown",
            )
            return
        _scan_in_progress = True

    chat_id = update.effective_chat.id
    msg = await update.message.reply_text(
        "⏳ *Starting scan...* This takes about 1–2 minutes.\n\nI'll notify you when it's done.",
        parse_mode="Markdown",
    )

    try:
        result = await run_scan_async(chat_id=chat_id)

        if result["success"]:
            new_jobs_list = result.get("new_jobs", [])
            new_count = result.get("new_count", 0)
            total_found = result.get("total_found", 0)

            reply = (
                f"✅ *Scan Complete!*\n\n"
                f"📋 {total_found} matching jobs found\n"
                f"🆕 {new_count} new jobs discovered\n"
            )

            if new_jobs_list and new_count > 0:
                reply += "\n*New Jobs:*\n"
                for title in new_jobs_list[:5]:
                    reply += f"  • {title}\n"
                if len(new_jobs_list) > 5:
                    reply += f"  ...and {len(new_jobs_list) - 5} more\n"
                reply += "\nCheck /jobs to see all listings."
            else:
                reply += "\nNo new jobs this time. Check /jobs for existing listings."

            await msg.edit_text(reply, parse_mode="Markdown")

            # Send stats as followup
            stats = get_stats()
            status_text = format_stats(stats)
            await update.message.reply_text(status_text, parse_mode="Markdown")

        else:
            error_detail = result.get("error", "Unknown error")
            await msg.edit_text(
                f"❌ *Scan Failed*\n\n`{error_detail}`",
                parse_mode="Markdown",
            )
    except Exception as e:
        await msg.edit_text(
            f"❌ *Scan Error*\n\n`{str(e)[:200]}`",
            parse_mode="Markdown",
        )
    finally:
        async with _scan_lock:
            _scan_in_progress = False


async def cmd_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /apply <job_id_prefix>."""
    if not context.args:
        await update.message.reply_text(
            error_msg("Usage: /apply <job_id>\n\nGet the job ID from /jobs output (first 12 chars shown)."),
            parse_mode="Markdown",
        )
        return

    prefix = context.args[0].strip()

    # Find job by ID prefix
    conn = get_conn()
    if not conn:
        await update.message.reply_text(error_msg("No database found. Run a scan first."), parse_mode="Markdown")
        return

    row = conn.execute(
        "SELECT id, company, title, applied FROM jobs WHERE id LIKE ?",
        (prefix + "%",),
    ).fetchone()
    conn.close()

    if not row:
        await update.message.reply_text(
            error_msg(f"No job found with ID `{prefix}`.\n\nUse /jobs to see available job IDs."),
            parse_mode="Markdown",
        )
        return

    job_id, company, title, currently_applied = row["id"], row["company"], row["title"], row["applied"]

    if currently_applied:
        await update.message.reply_text(
            f"ℹ️ *{title}* at {COMPANY_ICONS.get(company, '')} {company} is already marked as applied.",
            parse_mode="Markdown",
        )
        return

    success = mark_applied(job_id, applied=True)
    if success:
        icon = COMPANY_ICONS.get(company, "🏢")
        await update.message.reply_text(
            f"✅ Applied! Marked as applied:\n"
            f"  {icon} *{company}* — `{title[:60]}`\n\n"
            f"Use /jobs to see your updated list.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(error_msg("Failed to update job status."), parse_mode="Markdown")


async def cmd_unapply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unapply <job_id_prefix> — unmark a job as applied."""
    if not context.args:
        await update.message.reply_text(
            error_msg("Usage: /unapply <job_id>\n\nGet the job ID from /jobs output (first 12 chars shown)."),
            parse_mode="Markdown",
        )
        return

    prefix = context.args[0].strip()

    conn = get_conn()
    if not conn:
        await update.message.reply_text(error_msg("No database found."), parse_mode="Markdown")
        return

    row = conn.execute(
        "SELECT id, company, title, applied FROM jobs WHERE id LIKE ?",
        (prefix + "%",),
    ).fetchone()
    conn.close()

    if not row:
        await update.message.reply_text(
            error_msg(f"No job found with ID `{prefix}`.\n\nUse /jobs to see available job IDs."),
            parse_mode="Markdown",
        )
        return

    job_id, company, title, currently_applied = row["id"], row["company"], row["title"], row["applied"]

    if not currently_applied:
        await update.message.reply_text(
            f"ℹ️ *{title}* at {COMPANY_ICONS.get(company, '')} {company} is not marked as applied.",
            parse_mode="Markdown",
        )
        return

    success = mark_applied(job_id, applied=False)
    if success:
        icon = COMPANY_ICONS.get(company, "🏢")
        await update.message.reply_text(
            f"↩️ Unmarked! Reverted to unapplied:\n"
            f"  {icon} *{company}* — `{title[:60]}`",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(error_msg("Failed to update job status."), parse_mode="Markdown")


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alerts [on|off] — toggle new job alerts via Telegram."""
    chat_id = update.effective_chat.id
    args = context.args

    if args:
        action = args[0].lower()
        if action in ("on", "enable", "true", "1", "yes"):
            set_alerts(chat_id, True)
            await update.message.reply_text(
                "🔔 *Alerts ON*\n\nI'll send you a Telegram message every time a scan finds new matching jobs.",
                parse_mode="Markdown",
            )
            return
        elif action in ("off", "disable", "false", "0", "no"):
            set_alerts(chat_id, False)
            await update.message.reply_text(
                "🔕 *Alerts OFF*\n\nYou won't receive new job alerts via Telegram anymore.",
                parse_mode="Markdown",
            )
            return

    # Toggle
    currently = is_alerts_enabled(chat_id)
    if currently:
        set_alerts(chat_id, False)
        await update.message.reply_text(
            "🔕 *Alerts OFF*\n\nYou won't receive new job alerts anymore.",
            parse_mode="Markdown",
        )
    else:
        set_alerts(chat_id, True)
        await update.message.reply_text(
            "🔔 *Alerts ON*\n\nI'll send you a Telegram message when new matching jobs are found during a scan.",
            parse_mode="Markdown",
        )


# ── Error Handler ───────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle Telegram API errors."""
    logger.error(f"Telegram error: {context.error}")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Start the Telegram bot."""
    token = os.getenv("RADAR_TELEGRAM_BOT_TOKEN")
    if not token:
        print()
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║     🤖 Radar Telegram Bot — Setup Required      ║")
        print("  ╠══════════════════════════════════════════════════╣")
        print("  ║                                                 ║")
        print("  ║  Set your Telegram bot token:                   ║")
        print("  ║                                                 ║")
        print("  ║    export RADAR_TELEGRAM_BOT_TOKEN='your_token'  ║")
        print("  ║    python3 radar_bot.py                         ║")
        print("  ║                                                 ║")
        print("  ║  Don't have a token? Message @BotFather on      ║")
        print("  ║  Telegram to create a new bot.                  ║")
        print("  ╚══════════════════════════════════════════════════╝")
        print()
        sys.exit(1)

    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  🤖 Industry Research Radar — Telegram Bot      ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print("  ║  Bot is running...                              ║")
    print("  ║  Press Ctrl+C to stop                           ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    # Build the application with post_init to register commands with Telegram
    async def post_init(app):
        """Register bot commands with Telegram's / menu on startup."""
        commands = [
            ("start", "Welcome & command list"),
            ("status", "Dashboard stats & jobs by company"),
            ("jobs", "List matching jobs (optional: company)"),
            ("companies", "All tracked companies with counts"),
            ("scans", "Show scan history"),
            ("scan", "Trigger a new full scan"),
            ("apply", "Mark a job as applied"),
            ("unapply", "Unmark a job"),
            ("alerts", "Toggle new job alerts"),
            ("help", "Show available commands"),
        ]
        await app.bot.set_my_commands(commands)
        logger.info("✅ Bot commands registered with Telegram")

    application = Application.builder().token(token).post_init(post_init).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("jobs", cmd_jobs))
    application.add_handler(CommandHandler("companies", cmd_companies))
    application.add_handler(CommandHandler("scans", cmd_scans))
    application.add_handler(CommandHandler("scan", cmd_scan))
    application.add_handler(CommandHandler("apply", cmd_apply))
    application.add_handler(CommandHandler("unapply", cmd_unapply))
    application.add_handler(CommandHandler("alerts", cmd_alerts))

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
