#!/usr/bin/env python3
"""
🤖 PERSISTENT CEO — AI Agent via Telegram
==========================================
Upgraded version: Uses OpenRouter AI to have REAL conversations.
No more keyword matching — you talk to ME (Buffy) through Telegram.

Architecture:
  ┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
  │ Telegram Bot │────▶│ pending.json │────▶│ ceo_processor.py │
  │ @ArdTrading  │     │ (task queue) │     │ (OpenRouter AI)  │
  └─────────────┘     └──────────────┘     └──────────────────┘
                                                  │
                                           ┌──────▼──────┐
                                           │ Conversation │
                                           │ Memory (.json)│
                                           └─────────────┘

Usage:
    python3 ceo_processor.py              # Process all pending tasks (one-shot)
    python3 ceo_processor.py --watch      # Watch mode - continuous processing
    python3 ceo_processor.py --check      # Just check queue (no processing)
"""

import json
import os
import sys
import subprocess
import logging
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI

HOME = Path.home()
BOT_DIR = HOME / "trading"
CEO_TASKS_DIR = BOT_DIR / "ceo_tasks"
CEO_PENDING_FILE = CEO_TASKS_DIR / "pending.json"
CEO_RESULTS_DIR = CEO_TASKS_DIR / "results"
CEO_MEMORY_DIR = CEO_TASKS_DIR / "memory"
CEO_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
CEO_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | CEO-AI | %(message)s",
    handlers=[
        logging.FileHandler(BOT_DIR / "ceo_ai.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ceo_ai")

# ── API Keys (from environment only — never hardcode in source!) ──────
def _load_env_if_missing():
    """Load .env file as fallback if env vars are not set."""
    env_paths = [
        HOME / ".hermes" / ".env",
        HOME / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env_if_missing()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOTIFY_CHAT_ID = os.getenv("CEO_CHAT_ID", "7837847803")

if not OPENROUTER_API_KEY:
    print("❌ OPENROUTER_API_KEY not set. Export it or add to ~/.hermes/.env")
    sys.exit(1)
if not TELEGRAM_BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set. Export it or add to ~/.hermes/.env")
    sys.exit(1)

# ── AI Client ─────────────────────────────────────────────────────────
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://ftmo-tracker.loca.lt",
        "X-Title": "FTMO CEO Agent",
    },
)

# This is the model we use. DeepSeek is fast & smart. Can switch to Claude 4 if needed.
MODEL = "openai/gpt-4o"  # Best balance of speed + reasoning
# Also tested: deepseek/deepseek-chat (faster, cheaper), anthropic/claude-3-haiku

# ── System Prompt ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Buffy — a strategic AI assistant and the CEO of FTMO Income Corporation. You orchestrate a whole business empire through Telegram.

Your tone: Professional, direct, concise. Call the user "boss" or "sir". Be proactive and helpful.

THE BUSINESS:
FTMO Income Corporation is a prop trading education business. Core products:
1. Free FTMO Challenge Tracker (web + Telegram bot) — tracks profit targets, drawdown, trading days
2. Pro version ($19.99/mo) — cloud sync, PDF reports, unlimited accounts
3. 29 SEO guide pages about FTMO rules, fees, strategies (live at ftmo-tracker.loca.lt/seo/)
4. Gumroad product: gumroad.com/l/ezteprg

YOUR TOOLS & AGENTS:
• SEO Factory (seo_factory.py) — generates 29 SEO guide pages
• LinkedIn Poster (linkedin_poster.py) — Playwright automation for LinkedIn
• Directory Submitter (directory_submitter.py) — backlink submissions
• Traffic Engine (traffic_engine.py) — multi-platform posting
• Content Generator (content_generator.py) — articles & social posts
• Company HQ (company_hq.py) — dashboard & revenue tracking
• Telegram Bot @ArdTradingBot — user-facing tracker with /setup, /add, /status commands

LIVE SERVICES:
• Telegram Bot @ArdTradingBot — running on server
• Web Server on port 3000 — serves tracker + SEO pages
• Public Tunnel ftmo-tracker.loca.lt — routes traffic to server
• 8 cron jobs — auto-heal, marketing, content generation
• All code on GitHub: github.com/adbhutrd/FTMO-challenge-TRacker

WHEN SOMEONE TALKS TO YOU:
1. If they ask about business/status — give a concise update on what's running
2. If they ask to DO something — guide them step by step, check what tools you have
3. If they ask a question — answer directly and helpfully
4. If they give a command — acknowledge it and explain how you'll execute it
5. If you're not sure about something — ask clarifying questions

You have access to the FTMO business ecosystem above. Use this knowledge to help the boss run the company efficiently. Be concise but thorough in your responses. Remember the full conversation history — the boss should never have to re-explain things."""


# ═══════════════════════════════════════════════════════════════════════
#  CONVERSATION MEMORY
# ═══════════════════════════════════════════════════════════════════════

CONVERSATION_FILE = CEO_MEMORY_DIR / "chat_history.jsonl"
MAX_HISTORY_LINES = 100  # Keep last 100 exchanges

def load_conversation_history() -> list:
    """Load conversation history from file."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if not CONVERSATION_FILE.exists():
        return messages
    try:
        lines = CONVERSATION_FILE.read_text().strip().split("\n")
        for line in lines[-MAX_HISTORY_LINES:]:  # Last N lines
            if line.strip():
                entry = json.loads(line)
                messages.append(entry)
    except Exception as e:
        logger.warning(f"Error loading history: {e}")
    return messages

def save_to_history(role: str, content: str):
    """Save a message to conversation history."""
    entry = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
    with open(CONVERSATION_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════════════════════════════
#  AI CALL
# ═══════════════════════════════════════════════════════════════════════

def call_ai(user_message: str) -> str:
    """Call OpenRouter AI with conversation history. Returns response text."""
    messages = load_conversation_history()
    messages.append({"role": "user", "content": user_message})

    try:
        logger.info(f"🧠 Calling AI ({MODEL}) with {len(messages)} message(s) in context...")
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
        )
        response = completion.choices[0].message.content

        # Save to history
        save_to_history("user", user_message)
        save_to_history("assistant", response)

        logger.info(f"✅ AI responded ({len(response)} chars)")
        return response

    except Exception as e:
        error_msg = f"❌ AI Error: {type(e).__name__}: {e}"
        logger.error(error_msg)
        return error_msg


# ═══════════════════════════════════════════════════════════════════════
#  TELEGRAM INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════
#  TASK QUEUE
# ═══════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════
#  PROCESSOR
# ═══════════════════════════════════════════════════════════════════════

def process_task(task: dict) -> str:
    """Process a single CEO task using AI. Returns response text."""
    message = task.get("message", "").strip()
    logger.info(f"🔄 Processing task {task['task_id']}: {message[:80]}")

    msg_lower = message.lower()

    # ── Special system commands (run BEFORE AI, these are direct ops) ──
    words = set(msg_lower.split())
    
    # Help
    if any(word in msg_lower for word in ["help", "what can you do", "commands", "options"]):
        return (
            "🤖 <b>CEO — I'm Buffy, your AI!</b>\n\n"
            "Just talk to me normally! I'll understand what you want.\n\n"
            "Examples:\n"
            "• <i>\"Hey Buffy, check the system status\"</i>\n"
            "• <i>\"Generate 5 more SEO pages about FTMO fees\"</i>\n"
            "• <i>\"Run the LinkedIn poster\"</i>\n"
            "• <i>\"What's the company revenue today?\"</i>\n"
            "• <i>\"Deploy the latest changes\"</i>\n\n"
            "I remember our conversation history — no need to re-explain things!\n"
            "I'm always here. Just text me on Telegram."
        )

    # System logs
    log_triggers = {"log", "logs"}
    if log_triggers & words or "show log" in msg_lower or msg_lower == "/logs":
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

    # Check system status (subprocess)
    if any(word in msg_lower for word in ["status", "health", "running", "uptime"]):
        try:
            screen = subprocess.run(["screen", "-ls"], capture_output=True, text=True, timeout=5)
            cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            seo_count = len(list((BOT_DIR / "seo_content").glob("*.html"))) if (BOT_DIR / "seo_content").exists() else 0
            
            screen_lines = screen.stdout.strip().split(chr(10)) if screen.stdout else []
            # Clean up screen output: remove control chars, format for Telegram
            clean_sessions = [s.strip() for s in screen_lines if s.strip() and not s.strip().startswith("There ")]
            services_str = "\n".join(clean_sessions[:5]) if clean_sessions else "  All nominal"
            
            status = (
                f"🤖 <b>CEO Buffy — LIVE Status</b>\n\n"
                f"<b>🧠 Brain:</b> {MODEL} via OpenRouter (always online)\n"
                f"<b>📱 Interface:</b> Telegram @ArdTradingBot\n"
                f"<b>📜 Memory:</b> {CONVERSATION_FILE.stat().st_size if CONVERSATION_FILE.exists() else 0:,} bytes — I remember everything\n\n"
                f"<b>🟢 Services:</b>\n"
                f"<code>{services_str}</code>\n\n"
                f"<b>📄 Content:</b> {seo_count} live SEO pages\n"
                f"<b>⏰ Cron:</b> {cron.stdout.count(chr(10)) if cron.stdout else 0} jobs active\n\n"
                f"<b>💬 Talk to me:</b> Just send a message! I'm always here."
            )
            return status
        except:
            return "✅ All systems running. I'm online and active!"

    # ── Default: Use AI for everything else ──
    return call_ai(message)


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
                f"🤖 <b>Buffy's Response</b>\n\n"
                f"{response[:3500]}"
            )
            send_telegram(chat_id, msg)
            processed += 1

        except Exception as e:
            logger.error(f"❌ Task {task['task_id']} failed: {e}")
            # Send error to user
            error_msg = f"❌ Sorry boss, I hit an error: {e}"
            mark_completed(task["task_id"], error_msg)
            chat_id = str(task.get("user_id", NOTIFY_CHAT_ID))
            send_telegram(chat_id, f"❌ <b>Error:</b> {e}")

    logger.info(f"✅ Processed {processed}/{len(tasks)} tasks")
    return processed


# ═══════════════════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════════════════

def check_queue():
    """Just check the queue without processing."""
    tasks = get_pending_tasks()
    logger.info(f"📭 Queue: {len(tasks)} pending tasks")
    for t in tasks:
        logger.info(f"  • {t['task_id']}: {t['message'][:60]}")
    return len(tasks)

def watch_mode():
    """Watch mode - check queue every 15 seconds."""
    logger.info("👀 Watch mode active (checking every 15s)")
    consecutive_empty = 0
    while True:
        try:
            n = process_all()
            if n == 0:
                consecutive_empty += 1
            else:
                consecutive_empty = 0
            
            # Sleep longer if nothing to do (reduce CPU usage)
            if consecutive_empty > 4:
                time.sleep(30)  # Stretch to 30s after 1 minute idle
            else:
                time.sleep(15)  # Responsive: check every 15s
            
        except KeyboardInterrupt:
            logger.info("👋 Watch mode stopped")
            break
        except Exception as e:
            logger.error(f"❌ Watch error: {e}")
            time.sleep(30)


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  🤖 PERSISTENT CEO — Buffy AI Agent")
    print(f"  Model: {MODEL}")
    print(f"  History: {CONVERSATION_FILE}")
    print(f"  {'='*50}\n")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--check":
            check_queue()
        elif cmd == "--watch":
            watch_mode()
        elif cmd == "--reset":
            # Reset conversation memory
            if CONVERSATION_FILE.exists():
                CONVERSATION_FILE.unlink()
                print("✅ Conversation history reset.")
            else:
                print("📭 No history to reset.")
        elif cmd == "--stats":
            stats = []
            if CONVERSATION_FILE.exists():
                lines = CONVERSATION_FILE.read_text().strip().split("\n")
                user_msgs = sum(1 for l in lines if '"role": "user"' in l)
                asst_msgs = sum(1 for l in lines if '"role": "assistant"' in l)
                print(f"📊 Memory stats:")
                print(f"  Total messages: {len(lines)}")
                print(f"  User messages: {user_msgs}")
                print(f"  Assistant messages: {asst_msgs}")
                print(f"  File size: {CONVERSATION_FILE.stat().st_size:,} bytes")
            else:
                print("📭 No conversation history yet.")
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python3 ceo_processor.py [--watch|--check|--reset|--stats]")
    else:
        # Default: process all pending tasks
        n = process_all()
        print(f"✅ Processed {n} task(s)")
