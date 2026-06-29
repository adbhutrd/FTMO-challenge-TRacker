#!/usr/bin/env python3
"""
📱 SMS Notifier — SMS Alerts for FTMO Tracker & Trading Bots
==============================================================
Integration module connecting the SMS gateway to your Telegram bot and services.

Architecture:
  FTMO Telegram Bot  ──→  sms_notifier.py  ──→  sms_gateway.py  ──→  Android Phone → SMS
  Trading Bots       ──→  sms_notifier.py  ──→  sms_gateway.py  ──→  Android Phone → SMS
  Cron Jobs          ──→  sms_notifier.py  ──→  sms_gateway.py  ──→  Android Phone → SMS

Usage:
  from sms_notifier import notify_trade, notify_status, notify_alert
  
  # After adding a trade:
  notify_trade("+1234567890", day=5, pnl=500, balance=50500)
  
  # When challenge status changes:
  notify_status("+1234567890", "passed", "🎉 Phase 1 complete!")
  
  # System alert:
  notify_alert("Server CPU > 90%")
"""

import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sms_notifier")

# ── SMS Gateway Connection ──────────────────────────────────────────
# The SMS gateway runs as a local HTTP server (port 8765 by default)
# We send SMS by calling its REST API

SMS_GATEWAY_URL = os.getenv("SMS_GATEWAY_URL", "http://localhost:8765")
DEFAULT_PHONE = os.getenv("SMS_DEFAULT_PHONE", "")


# ═══════════════════════════════════════════════════════════════════════
#  CORE SENDING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _send(phone: str, message: str) -> dict:
    """
    Send an SMS via the gateway API.
    Falls back to logging if gateway is unreachable.
    """
    try:
        resp = requests.post(
            f"{SMS_GATEWAY_URL}/send",
            json={"phone": phone, "message": message, "immediate": True},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"✅ SMS sent (ID: {data.get('message_id')})")
            return data
        else:
            logger.warning(f"⚠️ SMS gateway returned {resp.status_code}")
            return {"status": "error", "detail": f"HTTP {resp.status_code}"}
    except requests.ConnectionError:
        logger.warning("⚠️ SMS gateway not running (start with: python3 sms_gateway.py serve)")
        # Log the message anyway so it's not lost
        _log_fallback(phone, message)
        return {"status": "queued_locally", "detail": "gateway offline, logged"}
    except Exception as e:
        logger.error(f"❌ SMS send error: {e}")
        return {"status": "error", "detail": str(e)}


def _log_fallback(phone: str, message: str):
    """Log SMS to file when gateway is offline."""
    log_dir = Path.home() / "sms_gateway" / "fallback"
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "phone": phone,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    log_file = log_dir / f"sms_fallback_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"📝 SMS logged to {log_file} (gateway was offline)")


# ═══════════════════════════════════════════════════════════════════════
#  FTMO TRACKER NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════

def notify_trade(
    phone: str,
    day: int,
    pnl: float,
    balance: float,
    total_pnl: float = 0,
    notes: str = "",
    challenge_type: str = "2step",
) -> dict:
    """
    Send an SMS when a new trading day is recorded.
    
    Example SMS:
      📊 FTMO Day 5: +$500
      Balance: $50,500 | Total: +$1,200
      📈 2-Step · Phase 1
    """
    pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
    total_str = f"+${total_pnl:,.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):,.2f}"
    
    message = (
        f"📊 FTMO Day {day}: {pnl_str}\n"
        f"Balance: ${balance:,.2f} | Total: {total_str}\n"
        f"📈 {challenge_type.upper()} · Phase 1"
    )
    if notes:
        message += f"\n📝 {notes[:60]}"
    
    return _send(phone, message)


def notify_challenge_passed(phone: str, phase: int = 1) -> dict:
    """
    Send an SMS when a challenge phase is passed.
    
    Example SMS:
      🎉 FTMO PHASE 1 PASSED!
      Move to Phase 2 with /promote
      🔗 https://bright-palmier-d43338.netlify.app
    """
    message = (
        f"🎉 FTMO PHASE {phase} PASSED!\n"
        f"Congratulations! Move to Phase 2 using /promote on Telegram.\n"
        f"🔗 https://bright-palmier-d43338.netlify.app"
    )
    return _send(phone, message)


def notify_challenge_failed(phone: str, reason: str = "Max Drawdown") -> dict:
    """
    Send an SMS when a challenge fails.
    
    Example SMS:
      ❌ FTMO Challenge Failed
      Reason: Max Drawdown exceeded
      💪 Reset with /reset and try again!
    """
    message = (
        f"❌ FTMO Challenge Failed\n"
        f"Reason: {reason}\n"
        f"💪 Reset with /reset on Telegram and try again!"
    )
    return _send(phone, message)


def notify_drawdown_warning(phone: str, used: float, max_dd: float, pct: float) -> dict:
    """
    Send an SMS when drawdown is approaching the limit.
    
    Example SMS:
      ⚠️ FTMO Drawdown Warning
      $4,500 / $5,000 used (90%)
      🔴 Near max drawdown limit!
    """
    emoji = "🔴" if pct > 90 else "🟡"
    message = (
        f"{emoji} FTMO Drawdown Warning\n"
        f"${used:,.0f} / ${max_dd:,.0f} used ({pct:.0f}%)\n"
        f"{'🔴 NEAR LIMIT!' if pct > 90 else '⚠️ Be careful!'}"
    )
    return _send(phone, message)


def notify_daily_summary(phone: str, stats: dict) -> dict:
    """
    Send a daily summary SMS with key metrics.
    
    Expected stats dict keys:
      - total_pnl, trades_today, profit_progress, days_traded, status
    """
    pnl = stats.get("total_pnl", 0)
    pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
    
    message = (
        f"📊 FTMO Daily Summary\n"
        f"P&L: {pnl_str}\n"
        f"Trades today: {stats.get('trades_today', 0)}\n"
        f"Progress: {stats.get('profit_progress', 0):.0f}%\n"
        f"Days: {stats.get('days_traded', 0)} | Status: {stats.get('status', 'N/A')}"
    )
    return _send(phone, message)


# ═══════════════════════════════════════════════════════════════════════
#  SYSTEM & CRON ALERTS
# ═══════════════════════════════════════════════════════════════════════

def notify_alert(message: str, phone: str = "") -> dict:
    """
    Send a system alert SMS.
    If phone is empty, uses DEFAULT_PHONE from env.
    """
    target = phone or DEFAULT_PHONE
    if not target:
        logger.warning("⚠️ No phone number for alert. Set SMS_DEFAULT_PHONE")
        _log_fallback("(unset)", message)
        return {"status": "error", "detail": "no phone configured"}
    return _send(target, f"🔔 {message}")


def notify_service_restart(service_name: str, phone: str = "") -> dict:
    """Notify that a service was restarted."""
    return notify_alert(f"🔄 Service restarted: {service_name}", phone)


def notify_cron_complete(job_name: str, status: str, details: str = "", phone: str = "") -> dict:
    """Notify when a cron job completes."""
    emoji = "✅" if status == "success" else "❌"
    message = f"{emoji} Cron: {job_name} — {status}"
    if details:
        message += f"\n{details[:100]}"
    return notify_alert(message, phone)


# ═══════════════════════════════════════════════════════════════════════
#  INTEGRATION GUIDE — How to add SMS to ftmo_telegram_bot.py
# ═══════════════════════════════════════════════════════════════════════
#
#  To integrate, add these lines at the TOP of ftmo_telegram_bot.py:
#
#      # 📱 SMS Alerts
#      import sys
#      sys.path.insert(0, str(Path.home()))
#      from sms_notifier import (
#          notify_trade, notify_challenge_passed, notify_challenge_failed,
#          notify_drawdown_warning, notify_daily_summary, notify_alert,
#      )
#      SMS_PHONE = os.getenv("SMS_DEFAULT_PHONE", "+1234567890")
#
#  Then add SMS calls at these trigger points:
#
#  ── In cmd_add() — when a trade is recorded ─────────────────────────
#      After the trade is saved and stats calculated:
#
#          # === ADD THIS ===
#          if os.getenv("SMS_DEFAULT_PHONE"):
#              notify_trade(
#                  phone=SMS_PHONE,
#                  day=len(user.trades),
#                  pnl=last['daily_pnl'] if stats.stats else 0,
#                  balance=balance,
#                  total_pnl=stats.total_pnl,
#                  notes=notes,
#                  challenge_type=user.challenge_type,
#              )
#              # Also check for warnings
#              if stats.status == "passed":
#                  notify_challenge_passed(SMS_PHONE, user.phase)
#              elif stats.status == "failed":
#                  notify_challenge_failed(SMS_PHONE)
#              elif stats.static_drawdown_pct > 80:
#                  notify_drawdown_warning(
#                      SMS_PHONE, stats.static_drawdown_dollars,
#                      stats.max_drawdown, stats.static_drawdown_pct,
#                  )
#
#  ── In cmd_promote() — when moving to Phase 2 ──────────────────────
#      After user.promote_phase():
#
#          # === ADD THIS ===
#          if os.getenv("SMS_DEFAULT_PHONE"):
#              notify_challenge_passed(SMS_PHONE, phase=2)
#              notify_alert("🚀 FTMO Challenge promoted to Phase 2!")
#
#  ── In the CEO bot's cmd_deploy() — deploy complete ────────────────
#      After successful deploy:
#
#          # === ADD THIS ===
#          notify_alert("🚀 Website deploy complete!")


# ═══════════════════════════════════════════════════════════════════════
#  CLI — Test SMS notifications from command line
# ═══════════════════════════════════════════════════════════════════════

def cli():
    """Test SMS notifications."""
    import sys
    
    args = sys.argv[1:]
    phone = args[1] if len(args) > 1 else DEFAULT_PHONE
    
    if not args:
        print("""
📱 SMS Notifier — Test Commands

  python3 sms_notifier.py trade <phone> [day] [pnl]  — Test trade notification
  python3 sms_notifier.py passed <phone> [phase]     — Test challenge passed
  python3 sms_notifier.py failed <phone>             — Test challenge failed
  python3 sms_notifier.py warning <phone> [pct]      — Test drawdown warning
  python3 sms_notifier.py summary <phone>            — Test daily summary
  python3 sms_notifier.py alert <phone> <message>    — Test system alert
  python3 sms_notifier.py test <phone>               — Send all test messages
        """)
        return
    
    cmd = args[0]
    
    if cmd == "trade":
        phone = args[1]
        day = int(args[2]) if len(args) > 2 else 5
        pnl = float(args[3]) if len(args) > 3 else 500
        r = notify_trade(phone, day, pnl, 50000 + pnl, total_pnl=2000)
        print(f"Trade notification: {r}")
    
    elif cmd == "passed":
        phone = args[1]
        phase = int(args[2]) if len(args) > 2 else 1
        r = notify_challenge_passed(phone, phase)
        print(f"Passed notification: {r}")
    
    elif cmd == "failed":
        phone = args[1]
        r = notify_challenge_failed(phone)
        print(f"Failed notification: {r}")
    
    elif cmd == "warning":
        phone = args[1]
        pct = float(args[2]) if len(args) > 2 else 85
        r = notify_drawdown_warning(phone, 4500, 5000, pct)
        print(f"Warning notification: {r}")
    
    elif cmd == "summary":
        phone = args[1]
        stats = {"total_pnl": 1200, "trades_today": 1, "profit_progress": 24, "days_traded": 6, "status": "Active"}
        r = notify_daily_summary(phone, stats)
        print(f"Summary notification: {r}")
    
    elif cmd == "alert":
        phone = args[1]
        message = " ".join(args[2:]) if len(args) > 2 else "Test alert from CLI"
        r = notify_alert(message, phone)
        print(f"Alert: {r}")
    
    elif cmd == "test":
        phone = args[1]
        print(f"\n📱 Sending all test SMS types to {phone}...\n")
        notify_trade(phone, 5, 500, 50500, total_pnl=2000)
        notify_challenge_passed(phone, 1)
        notify_challenge_failed(phone)
        notify_drawdown_warning(phone, 4500, 5000, 90)
        notify_alert("This is a test alert from SMS Notifier!", phone)
        print(f"\n✅ All test messages sent to {phone}")
    
    else:
        print(f"Unknown command: {cmd}")
        print("Run without arguments for help.")


if __name__ == "__main__":
    cli()
