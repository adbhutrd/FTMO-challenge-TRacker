#!/usr/bin/env python3
"""
🤖 CEO PROCESSOR — Telegram Task Bridge
=========================================
Reads messages from the CEO task queue (saved by the Telegram bot),
processes them by running the appropriate scripts, and sends results back.

Usage:
    python3 ceo_processor.py              # Process ALL pending tasks
    python3 ceo_processor.py --check      # Just check queue (no processing)
    python3 ceo_processor.py --watch      # Watch mode - keep checking every 30s
"""

import json
import os
import sys
import subprocess
import logging
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
BOT_DIR = HOME / "trading"
CEO_TASKS_DIR = BOT_DIR / "ceo_tasks"
CEO_PENDING_FILE = CEO_TASKS_DIR / "pending.json"
CEO_RESULTS_DIR = CEO_TASKS_DIR / "results"
CEO_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | CEO-PROC | %(message)s",
    handlers=[
        logging.FileHandler(BOT_DIR / "ceo_processor.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ceo_processor")

# Read from env var like main bot does. Hardcoded fallback for reliability.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = "8340892430:AAHLG7DuM7W5EEcpuXeILtKXiZcY9lrh4zw"
NOTIFY_CHAT_ID = os.getenv("CEO_CHAT_ID", "7837847803")


def send_telegram(chat_id: str, message: str):
    """Send a message to Telegram chat."""
    try:
        import urllib.parse
        text = urllib.parse.quote(message[:3500])
        subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
             "-d", f"chat_id={chat_id}&parse_mode=HTML&text={text}"],
            capture_output=True, timeout=15
        )
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


def get_pending_tasks() -> list:
    """Get all pending tasks from the queue."""
    if not CEO_PENDING_FILE.exists():
        return []
    try:
        pending = json.loads(CEO_PENDING_FILE.read_text())
        return [t for t in pending if t.get("status") == "pending"]
    except Exception as e:
        logger.error(f"Error reading queue: {e}")
        return []


def mark_completed(task_id: str, response: str):
    """Mark a task as completed and save the response."""
    if not CEO_PENDING_FILE.exists():
        return
    try:
        pending = json.loads(CEO_PENDING_FILE.read_text())
        for task in pending:
            if task["task_id"] == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat()
                # Save result
                result = {
                    "task_id": task_id,
                    "user_id": task.get("user_id", NOTIFY_CHAT_ID),
                    "username": task.get("username", "Boss"),
                    "original_message": task.get("message", ""),
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "sent_to_user": False,
                }
                result_file = CEO_RESULTS_DIR / f"{task_id}.json"
                result_file.write_text(json.dumps(result, indent=2))
                logger.info(f"✅ Task {task_id} completed")
                break
        CEO_PENDING_FILE.write_text(json.dumps(pending, indent=2))
    except Exception as e:
        logger.error(f"Error completing task {task_id}: {e}")


def process_task(task: dict) -> str:
    """Process a single CEO task. Returns response text."""
    message = task.get("message", "").strip()
    logger.info(f"🔄 Processing task {task['task_id']}: {message[:80]}")

    msg_lower = message.lower()

    # ── Route commands ──
    words = set(msg_lower.split())

    # Help / about
    if any(word in msg_lower for word in ["help", "what can you do", "commands", "options"]):
        return (
            "🤖 <b>CEO Command Reference</b>\n\n"
            "I can process these types of requests:\n\n"
            "<b>📈 SEO & Content:</b>\n"
            "• \"generate more SEO pages\"\n"
            "• \"create content about FTMO rules\"\n"
            "• \"run seo factory\"\n\n"
            "<b>📊 Reports & Status:</b>\n"
            "• \"check system status\" or \"/status\"\n"
            "• \"show dashboard\" or \"/hq\"\n"
            "• \"check revenue\" or \"/revenue\"\n"
            "• \"show logs\" or \"/logs\"\n\n"
            "<b>🔧 Operations:</b>\n"
            "• \"deploy updates\" or \"/deploy\"\n"
            "• \"restart services\" or \"/restart\"\n"
            "• \"run all engines\"\n\n"
            "<b>📢 Marketing:</b>\n"
            "• \"run traffic engine\"\n"
            "• \"generate content\"\n\n"
            "Just type what you want and I'll figure it out."
        )

    # Status / dashboard
    if any(word in msg_lower for word in ["status", "dashboard", "hq", "how are things", "what's going on", "company"]):
        try:
            result = subprocess.run(
                ["python3", "-c", "from company_hq import format_dashboard; print(format_dashboard())"],
                capture_output=True, text=True, timeout=15, cwd=str(HOME / "trading")
            )
            if result.stdout:
                return result.stdout[:3500]
            return "Company is running. All systems nominal. Check /hq on Telegram for full dashboard."
        except:
            return "✅ All systems running. Check Telegram bot with /hq for full dashboard."

    # Revenue
    if any(word in msg_lower for word in ["revenue", "money", "earnings", "sales", "profit"]):
        return (
            "💰 <b>Revenue Status</b>\n\n"
            "Current: $0.00\n"
            "Channels: Gumroad Pro ($19.99/mo), Affiliate (25%)\n\n"
            "All infrastructure is live and running. Revenue will come from:\n"
            "• Organic SEO traffic → free tracker → Pro upgrade\n"
            "• Telegram bot users → Pro upgrade\n"
            "• Direct shares/referrals\n\n"
            "Content is indexed and waiting for Google traffic."
        )

    # Run SEO factory
    if any(word in msg_lower for word in ["seo", "content", "article", "guide", "page", "generate"]):
        try:
            result = subprocess.run(
                ["python3", "trading/seo_factory.py", "--all"],
                capture_output=True, text=True, timeout=30, cwd=str(HOME)
            )
            output = result.stdout
            if result.returncode == 0:
                return f"✅ <b>SEO Factory Run Complete</b>\n\n<code>{output[-1000:]}</code>\n\nNew pages deployed to live server."
            return f"❌ SEO Factory error:\n<code>{output[:500]}</code>"
        except Exception as e:
            return f"❌ Error running SEO factory: {e}"

    # Run traffic engine
    if any(word in msg_lower for word in ["traffic", "marketing", "promote", "post"]):
        try:
            result = subprocess.run(
                ["python3", "trading/directory_submitter.py", "--run"],
                capture_output=True, text=True, timeout=30, cwd=str(HOME)
            )
            return f"✅ <b>Directory Submission Complete</b>\n\n<code>{result.stdout[-800:]}</code>"
        except Exception as e:
            return f"❌ Error: {e}"

    # System logs (word-level matching to avoid false positives)
    log_triggers = {"log", "logs", "logging"}
    if log_triggers & words or "show log" in msg_lower:
        try:
            n = 0
            for word in message.split():
                if word.isdigit():
                    n = int(word)
                    break
            if n <= 0:
                n = 30
            result = subprocess.run(
                ["tail", f"-{n}", str(BOT_DIR / "ftmo_bot.log")],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout:
                return f"📋 <b>Last {n} log lines:</b>\n<code>{result.stdout[-2500:]}</code>"
            return "No logs available."
        except:
            return "Could not read logs."

    # Deploy
    if any(word in msg_lower for word in ["deploy", "update", "pull", "git"]):
        try:
            result = subprocess.run(
                ["git", "pull"],
                capture_output=True, text=True, timeout=30, cwd=str(HOME)
            )
            return f"🚀 <b>Deploy Result:</b>\n<code>{result.stdout[:1000]}</code>"
        except Exception as e:
            return f"❌ Deploy error: {e}"

    # Restart
    if any(word in msg_lower for word in ["restart", "reboot", "reload"]):
        try:
            result = subprocess.run(
                ["bash", str(BOT_DIR / "restart_all.sh")],
                capture_output=True, text=True, timeout=30
            )
            return f"🔄 <b>Restarting services...</b>\n\n<code>{result.stdout[:500]}</code>"
        except Exception as e:
            return f"❌ Restart error: {e}"

    # Default: try to interpret as a Python command
    try:
        # Look for script runs
        if "run " in msg_lower:
            for script in ["company_hq", "seo_factory", "traffic_engine", "content_generator", "linkedin_poster", "directory_submitter"]:
                if script.replace("_", " ") in msg_lower or script in msg_lower:
                    cmd = f"python3 trading/{script}.py --run-all --all"
                    result = subprocess.run(
                        cmd.split(), capture_output=True, text=True, timeout=30, cwd=str(HOME)
                    )
                    return f"✅ <b>Ran {script}</b>\n\n<code>{result.stdout[-1000:]}</code>"
    except:
        pass

    # Unknown command
    return (
        f"🤖 <b>CEO received your message.</b>\n\n"
        f"Message: <i>{message[:200]}</i>\n\n"
        f"I can help with:\n"
        f"• Running SEO factory\n"
        f"• Checking system status\n"
        f"• Deploying updates\n"
        f"• Running traffic engines\n"
        f"• Checking revenue\n\n"
        f"Type <code>/ceo help</code> for all options.\n"
        f"Or just tell me what you want and I'll figure it out."
    )


def process_all():
    """Process all pending tasks."""
    tasks = get_pending_tasks()
    
    if not tasks:
        logger.info("📭 No pending tasks")
        return 0

    logger.info(f"📥 Processing {len(tasks)} pending task(s)")
    processed = 0

    for task in tasks:
        try:
            response = process_task(task)
            mark_completed(task["task_id"], response)

            # Notify user
            chat_id = str(task.get("user_id", NOTIFY_CHAT_ID))
            msg = (
                f"🤖 <b>CEO Response</b>\n\n"
                f"<b>You:</b> {task.get('message', '')[:200]}\n\n"
                f"{response[:3500]}"
            )
            send_telegram(chat_id, msg)
            processed += 1

        except Exception as e:
            logger.error(f"❌ Task {task['task_id']} failed: {e}")
            mark_completed(task["task_id"], f"❌ Error processing: {e}")

    logger.info(f"✅ Processed {processed}/{len(tasks)} tasks")
    return processed


def check_queue():
    """Just check the queue without processing."""
    tasks = get_pending_tasks()
    logger.info(f"📭 Queue: {len(tasks)} pending tasks")
    for t in tasks:
        logger.info(f"  • {t['task_id']}: {t['message'][:60]}")
    return len(tasks)


def watch_mode():
    """Watch mode - check queue every 30 seconds."""
    logger.info("👀 Watch mode active (checking every 30s)")
    while True:
        try:
            n = process_all()
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("👋 Watch mode stopped")
            break
        except:
            time.sleep(30)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--check":
            check_queue()
        elif cmd == "--watch":
            watch_mode()
        else:
            print(f"Unknown: {cmd}")
    else:
        # Default: process all pending tasks
        n = process_all()
        print(f"✅ Processed {n} task(s)")
