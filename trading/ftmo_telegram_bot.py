#!/usr/bin/env python3
"""
📊 FTMO Challenge Tracker — Telegram Bot
=========================================
Track your FTMO challenge progress via Telegram.
Replicates all functionality from the web tracker.

Setup:
  1. Message @BotFather on Telegram → /newbot → get token
  2. Set token: export TELEGRAM_BOT_TOKEN="your:token"
  3. Run: python3 ftmo_telegram_bot.py

Commands:
  /setup  <type> <account> <balance>  — Set up challenge
  /add    <ending_balance> [notes]    — Add trading day
  /status                              — Show current progress
  /log                                  — Show trade log
  /chart                                — Generate equity curve
  /export                               — Export your data
  /reset                                — Reset all data
  /promote                              — Move to Phase 2
  /about                                — About & Pro version
"""

import json
import os
import sys
import io
import re
import tempfile
import subprocess
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# Optional: chart generation
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    CHART_SUPPORT = True
except ImportError:
    CHART_SUPPORT = False

# Telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        filters, ContextTypes, ConversationHandler,
    )
    TELEGRAM_SUPPORT = True
except ImportError:
    TELEGRAM_SUPPORT = False

# ── Paths ──────────────────────────────────────────────────────────────
HOME = Path.home()
BOT_DIR = HOME / "trading"
DATA_DIR = BOT_DIR / "telegram_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | FTMO-BOT | %(message)s",
    handlers=[
        logging.FileHandler(BOT_DIR / "ftmo_bot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ftmo_bot")


# ═══════════════════════════════════════════════════════════════════════
#  FTMO RULES ENGINE (ported from JavaScript tracker)
# ═══════════════════════════════════════════════════════════════════════

FTMO_RULES = {
    "2step": {
        "profit_targets": {1: 0.10, 2: 0.05},
        "max_daily_loss": 0.05,
        "max_total_drawdown": 0.10,
        "min_trading_days": 4,
        "best_day_rule": False,
    },
    "1step": {
        "profit_targets": {1: 0.10, 2: 0.05},
        "max_daily_loss": 0.03,
        "max_total_drawdown": 0.10,
        "min_trading_days": 0,
        "best_day_rule": True,
    },
}


def get_rules(challenge_type: str, phase: int) -> dict:
    return FTMO_RULES.get(challenge_type, FTMO_RULES["2step"]).copy()


def get_profit_target(start_balance: float, challenge_type: str, phase: int) -> float:
    rules = get_rules(challenge_type, phase)
    return start_balance * rules["profit_targets"][phase]


def get_max_drawdown(start_balance: float) -> float:
    return start_balance * 0.10


def get_daily_loss_limit(start_balance: float, challenge_type: str) -> float:
    rules = get_rules(challenge_type, 1)
    return start_balance * rules["max_daily_loss"]


def format_currency(value: float) -> str:
    """Format as currency with sign."""
    if value >= 0:
        return f"+${value:,.2f}"
    return f"-${abs(value):,.2f}"


def format_currency_plain(value: float) -> str:
    """Format as plain currency."""
    return f"${value:,.2f}"


def format_pct(value: float) -> str:
    return f"{value:+.2f}%" if value >= 0 else f"{value:.2f}%"


# ═══════════════════════════════════════════════════════════════════════
#  USER DATA STORAGE
# ═══════════════════════════════════════════════════════════════════════

class UserData:
    """Per-user data storage in JSON files."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.file_path = DATA_DIR / f"{user_id}.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.file_path.exists():
            try:
                return json.loads(self.file_path.read_text())
            except (json.JSONDecodeError, Exception):
                pass
        return {
            "challenge_type": "2step",
            "account_size": 50000,
            "phase": 1,
            "start_balance": 50000,
            "current_balance": 50000,
            "trades": [],
            "created": datetime.now().isoformat(),
        }

    def save(self):
        self.file_path.write_text(json.dumps(self.data, indent=2, default=str))

    # ── Properties ──
    @property
    def challenge_type(self) -> str:
        return self.data.get("challenge_type", "2step")

    @challenge_type.setter
    def challenge_type(self, value: str):
        self.data["challenge_type"] = value

    @property
    def account_size(self) -> int:
        return self.data.get("account_size", 50000)

    @account_size.setter
    def account_size(self, value: int):
        self.data["account_size"] = value

    @property
    def phase(self) -> int:
        return self.data.get("phase", 1)

    @phase.setter
    def phase(self, value: int):
        self.data["phase"] = value

    @property
    def start_balance(self) -> float:
        return self.data.get("start_balance", 50000)

    @start_balance.setter
    def start_balance(self, value: float):
        self.data["start_balance"] = value

    @property
    def current_balance(self) -> float:
        return self.data.get("current_balance", self.start_balance)

    @current_balance.setter
    def current_balance(self, value: float):
        self.data["current_balance"] = value

    @property
    def trades(self) -> list:
        return self.data.get("trades", [])

    @trades.setter
    def trades(self, value: list):
        self.data["trades"] = value

    # ── Methods ──
    def add_trade(self, balance: float, notes: str = ""):
        trade = {
            "date": date.today().isoformat(),
            "balance": balance,
            "notes": notes,
        }
        self.trades.append(trade)
        self.current_balance = balance
        self.save()

    def delete_trade(self, index: int) -> bool:
        if 0 <= index < len(self.trades):
            self.trades.pop(index)
            self.current_balance = self.trades[-1]["balance"] if self.trades else self.start_balance
            self.save()
            return True
        return False

    def reset(self):
        self.data["trades"] = []
        self.data["current_balance"] = self.start_balance
        self.data["phase"] = 1
        self.save()

    def promote_phase(self):
        if self.challenge_type == "2step" and self.phase == 1:
            self.phase = 2
            self.save()
            return True
        return False

    def to_dict(self) -> dict:
        return self.data.copy()


# ═══════════════════════════════════════════════════════════════════════
#  CALCULATIONS ENGINE
# ═══════════════════════════════════════════════════════════════════════

class ChallengeStats:
    """Calculate all FTMO challenge stats from user data."""

    def __init__(self, user: UserData):
        self.user = user
        self._calc()

    def _calc(self):
        u = self.user
        self.start_balance = u.start_balance
        self.current_balance = u.current_balance
        self.challenge_type = u.challenge_type
        self.phase = u.phase
        self.trades = u.trades
        self.account_size = u.account_size

        self.rules = get_rules(self.challenge_type, self.phase)
        self.profit_target = get_profit_target(self.start_balance, self.challenge_type, self.phase)
        self.max_drawdown = get_max_drawdown(self.start_balance)
        self.daily_loss_limit = get_daily_loss_limit(self.start_balance, self.challenge_type)

        # Calculate trade stats
        self.total_pnl = self.current_balance - self.start_balance
        self.total_pnl_pct = (self.total_pnl / self.start_balance) * 100 if self.start_balance > 0 else 0

        peak_balance = self.start_balance
        self.stats = []
        for i, trade in enumerate(self.trades):
            prev = self.trades[i - 1]["balance"] if i > 0 else self.start_balance
            daily_pnl = trade["balance"] - prev
            cumulative = trade["balance"] - self.start_balance

            if trade["balance"] > peak_balance:
                peak_balance = trade["balance"]

            drawdown_pct = ((peak_balance - trade["balance"]) / peak_balance) * 100 if peak_balance > 0 else 0
            drawdown_dollars = peak_balance - trade["balance"]
            daily_loss_pct = (daily_pnl / prev) * 100 if prev > 0 else 0
            daily_loss_violation = abs(daily_loss_pct) > (self.daily_loss_limit / self.start_balance) * 100 and daily_pnl < 0

            self.stats.append({
                "day": i + 1,
                "date": trade["date"],
                "balance": trade["balance"],
                "daily_pnl": daily_pnl,
                "daily_pnl_pct": daily_loss_pct,
                "cumulative_pnl": cumulative,
                "drawdown_pct": drawdown_pct,
                "drawdown_dollars": drawdown_dollars,
                "notes": trade.get("notes", ""),
                "daily_loss_violation": daily_loss_violation,
            })

        # Current drawdown (static: 10% of initial balance)
        self.static_drawdown_dollars = max(0, self.start_balance - self.current_balance)
        self.static_drawdown_pct = (self.static_drawdown_dollars / self.max_drawdown) * 100 if self.max_drawdown > 0 else 0

        # Profit progress
        self.profit_progress = min(100, max(0, (self.total_pnl / self.profit_target) * 100)) if self.profit_target > 0 else 0

        # Days progress
        self.min_days_required = self.rules["min_trading_days"]
        self.days_progress = min(100, (len(self.trades) / self.min_days_required) * 100) if self.min_days_required > 0 else 100

        # Best day rule (1-Step only)
        self.best_day_violation = False
        if self.challenge_type == "1step" and self.total_pnl > 0:
            best_day = max((s["daily_pnl"] for s in self.stats if s["daily_pnl"] > 0), default=0)
            self.best_day_pnl = best_day
            self.best_day_pct = (best_day / self.total_pnl) * 100 if self.total_pnl > 0 else 0
            self.best_day_violation = self.best_day_pct > 50
        else:
            self.best_day_pnl = 0
            self.best_day_pct = 0

        # Status
        self.status, self.status_label, self.status_emoji = self._determine_status()

    def _determine_status(self):
        if self.current_balance <= self.start_balance - self.max_drawdown:
            return "failed", "Failed (Max Drawdown)", "❌"
        elif self.total_pnl >= self.profit_target and len(self.trades) >= self.min_days_required and not self.best_day_violation:
            return "passed", "Phase Passed! 🎉", "✅"
        elif self.total_pnl >= self.profit_target and self.best_day_violation:
            return "risk", "Best Day > 50% — Keep Trading", "⚠️"
        elif self.static_drawdown_dollars > self.max_drawdown * 0.8:
            return "risk", "Near Drawdown Limit", "⚠️"

        # Check daily loss violation
        if any(s["daily_loss_violation"] for s in self.stats):
            return "risk", "Daily Loss Limit Hit", "⚠️"

        return "in_progress", "In Progress", "📊"


# ═══════════════════════════════════════════════════════════════════════
#  CHART GENERATION
# ═══════════════════════════════════════════════════════════════════════

def generate_chart(stats: ChallengeStats, user: UserData) -> Optional[bytes]:
    """Generate an equity curve chart and return PNG bytes."""
    if not CHART_SUPPORT:
        return None

    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")

        # Data
        labels = ["Start"] + [s["date"] for s in stats.stats]
        balances = [stats.start_balance] + [s["balance"] for s in stats.stats]

        # Plot
        ax.plot(labels, balances, color="#7c3aed", linewidth=2, marker="o", markersize=4, label="Balance")
        ax.axhline(y=stats.start_balance + stats.profit_target, color="#2ea043", linestyle="--", linewidth=1, label=f"Profit Target ({format_currency_plain(stats.profit_target)})")
        ax.axhline(y=stats.start_balance - stats.max_drawdown, color="#da3633", linestyle="--", linewidth=1, label=f"Max Drawdown ({format_currency_plain(stats.max_drawdown)})")

        # Style
        ax.tick_params(colors="#8b949e")
        ax.spines["bottom"].set_color("#30363d")
        ax.spines["top"].set_color("#30363d")
        ax.spines["left"].set_color("#30363d")
        ax.spines["right"].set_color("#30363d")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        plt.xticks(rotation=45, ha="right", color="#8b949e", fontsize=9)
        plt.yticks(color="#8b949e")
        plt.legend(loc="best", facecolor="#161b22", edgecolor="#30363d", labelcolor="#e6edf3")
        plt.grid(True, alpha=0.1, color="#30363d")
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Chart generation failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
#  FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════════

def format_status(stats: ChallengeStats) -> str:
    """Format the full status message."""
    lines = [
        f"{stats.status_emoji}  <b>FTMO Challenge Status</b>",
        f"",
        f"<b>{stats.status_label}</b>",
        f"{stats.challenge_type.upper()} · Phase {stats.phase} · {format_currency_plain(stats.account_size)} account",
        f"",
    ]

    # Profit Target
    progress_bar = _progress_bar(stats.profit_progress)
    profit_color = "🟢" if stats.profit_progress >= 100 else ""
    lines.append(f"🎯 <b>Profit Target:</b> {format_currency_plain(stats.profit_target)}")
    lines.append(f"   {progress_bar}")
    lines.append(f"   {format_currency_plain(max(0, stats.total_pnl))} earned · {format_currency_plain(max(0, stats.profit_target - stats.total_pnl))} left")
    lines.append(f"")

    # Drawdown
    dd_progress = stats.static_drawdown_pct
    dd_bar = _progress_bar(dd_progress)
    dd_warn = " 🔴" if dd_progress > 80 else " 🟡" if dd_progress > 50 else ""
    lines.append(f"🛑 <b>Drawdown:</b> {format_currency_plain(stats.static_drawdown_dollars)} / {format_currency_plain(stats.max_drawdown)}{dd_warn}")
    lines.append(f"   {dd_bar}")
    lines.append(f"")

    # Trading Days
    days_bar = _progress_bar(stats.days_progress)
    lines.append(f"📅 <b>Trading Days:</b> {len(stats.trades)} / {stats.min_days_required}")
    lines.append(f"   {days_bar}")
    lines.append(f"")

    # Best Day (1-Step)
    if stats.challenge_type == "1step" and stats.total_pnl > 0:
        bd_emoji = "✅" if not stats.best_day_violation else "❌"
        lines.append(f"📌 <b>Best Day Rule:</b> {stats.best_day_pct:.1f}% {bd_emoji}")
        lines.append(f"   Best day: {format_currency_plain(stats.best_day_pnl)} of {format_currency_plain(stats.total_pnl)}")
        lines.append(f"")

    # Warning
    if stats.best_day_violation:
        lines.append(f"⚠️ <b>Best day exceeds 50% of total profit!</b>")
        lines.append(f"   Keep trading until best day is under 50%.")
        lines.append(f"")

    # P&L
    pnl_color = "🟢" if stats.total_pnl >= 0 else "🔴"
    lines.append(f"{pnl_color} <b>Total P&L:</b> {format_currency(stats.total_pnl)} ({format_pct(stats.total_pnl_pct)})")

    return "\n".join(lines)


def format_trade_log(stats: ChallengeStats) -> str:
    """Format the trade log as a table."""
    if not stats.stats:
        return "<i>No trading days yet. Add your first with /add</i>"

    lines = ["📋 <b>Trading Days Log</b>", f"{'='*30}", ""]
    for s in reversed(stats.stats[-20:]):  # Last 20
        pnl_str = f"<code>{'+' if s['daily_pnl'] >= 0 else ''}{s['daily_pnl']:+,.2f}</code>"
        dd_color = "🔴" if s["drawdown_pct"] > 8 else "🟡" if s["drawdown_pct"] > 5 else ""
        warning = "⚠️" if s["daily_loss_violation"] else ""
        notes = f" — {s['notes']}" if s.get("notes") else ""
        lines.append(f"<b>Day {s['day']}</b> ({s['date']})")
        lines.append(f"  Balance: {format_currency_plain(s['balance'])}")
        lines.append(f"  P&L: {pnl_str} | DD: {s['drawdown_pct']:.2f}%{dd_color} {warning}{notes}")
        lines.append("")

    lines.append(f"📊 <b>Total P&L:</b> {format_currency(stats.total_pnl)} ({format_pct(stats.total_pnl_pct)})")
    return "\n".join(lines)


def format_export(user: UserData) -> str:
    """Format user data as JSON string."""
    return json.dumps(user.to_dict(), indent=2, default=str)


def _progress_bar(pct: float, width: int = 12) -> str:
    """Generate a text progress bar."""
    filled = int((pct / 100) * width)
    filled = max(0, min(width, filled))
    bar = "█" * filled + "░" * (width - filled)
    return f"<code>{bar}</code> {pct:.0f}%"


# ═══════════════════════════════════════════════════════════════════════
#  TELEGRAM COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message."""
    msg = (
        "📊 <b>FTMO Challenge Tracker Bot</b>\n\n"
        "Track your FTMO challenge progress in real-time via Telegram!\n\n"
        "<b>Commands:</b>\n"
        "🔹 <code>/setup 2step 50000 50000</code> — Set up your challenge\n"
        "   (type: 1step or 2step, account: 10000-200000, balance)\n"
        "🔹 <code>/add 50200</code> — Add a trading day (ending balance)\n"
        "🔹 <code>/add 50200 great day</code> — Add with notes\n"
        "🔹 <code>/status</code> — View your current progress\n"
        "🔹 <code>/log</code> — View trade history\n"
        "🔹 <code>/chart</code> — Equity curve chart\n"
        "🔹 <code>/export</code> — Export your data\n"
        "🔹 <code>/promote</code> — Move to Phase 2 (2-Step only)\n"
        "🔹 <code>/reset</code> — Reset all data\n"
        "🔹 <code>/about</code> — About & Pro version\n\n"
        "<b>Quick start:</b>\n"
        "1. <code>/setup 2step 50000 50000</code>\n"
        "2. After each trading day: <code>/add 50500</code>\n"
        "3. Check <code>/status</code> anytime\n\n"
        "🔥 <b>Pro version:</b> Cloud sync, unlimited accounts, PDF reports — "
        "<a href='https://gumroad.com/l/ezteprg'>$19.99/mo</a>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set up a new challenge: /setup <type> <account_size> <start_balance>"""
    user_id = update.effective_user.id
    user = UserData(user_id)
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Usage: <code>/setup &lt;type&gt; &lt;account_size&gt; [start_balance]</code>\n\n"
            "Examples:\n"
            "<code>/setup 2step 50000</code> — 2-Step, $50k account\n"
            "<code>/setup 2step 50000 50000</code> — With starting balance\n"
            "<code>/setup 1step 100000</code> — 1-Step, $100k account\n\n"
            "Types: <code>2step</code> or <code>1step</code>\n"
            "Account sizes: 10000, 25000, 50000, 100000, 200000",
            parse_mode="HTML",
        )
        return

    # Parse challenge type
    ctype = args[0].lower()
    if ctype not in ("1step", "2step"):
        await update.message.reply_text("❌ Invalid type. Use <code>1step</code> or <code>2step</code>.", parse_mode="HTML")
        return
    user.challenge_type = ctype

    # Parse account size
    try:
        acct = int(args[1].replace(",", "").replace("$", ""))
    except ValueError:
        await update.message.reply_text("❌ Account size must be a number (e.g., 50000)", parse_mode="HTML")
        return

    valid_sizes = [10000, 25000, 50000, 100000, 200000]
    if acct not in valid_sizes:
        await update.message.reply_text(
            f"❌ Invalid account size. Valid options: {', '.join(f'${s:,}' for s in valid_sizes)}",
            parse_mode="HTML",
        )
        return
    user.account_size = acct
    user.start_balance = acct

    # Parse optional start balance
    offset = 2
    if len(args) >= 3:
        # Could be date or start balance
        try:
            # Check if it's a date (YYYY-MM-DD format)
            datetime.strptime(args[2], "%Y-%m-%d")
            offset = 3  # Date was provided, check next arg for balance
        except ValueError:
            pass

        try:
            bal = float(args[offset].replace(",", "").replace("$", ""))
            if bal > 0:
                user.start_balance = bal
        except (ValueError, IndexError):
            pass  # Use default

    # Reset trades on new setup
    user.data["trades"] = []
    user.current_balance = user.start_balance
    user.phase = 1
    user.save()

    # Show confirmation
    stats = ChallengeStats(user)
    msg = (
        f"✅ <b>Challenge Configured!</b>\n\n"
        f"📋 {ctype.upper()} · Phase 1\n"
        f"💰 Account: {format_currency_plain(acct)}\n"
        f"🏦 Starting: {format_currency_plain(user.start_balance)}\n"
        f"🎯 Target: {format_currency_plain(stats.profit_target)}\n"
        f"🛑 Max Drawdown: {format_currency_plain(stats.max_drawdown)}\n"
        f"📅 Min Days: {stats.min_days_required}\n\n"
        f"Add your first trading day: <code>/add {user.start_balance + 200:.0f}</code>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a trading day: /add <ending_balance> [notes]
    
    Also supports: /add YYYY-MM-DD <ending_balance> [notes]
    """
    user_id = update.effective_user.id
    user = UserData(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: <code>/add &lt;ending_balance&gt; [notes]</code>\n\n"
            "Examples:\n"
            "<code>/add 50200</code>\n"
            "<code>/add 50200 great day, followed plan</code>\n"
            "<code>/add 2026-06-20 50200</code> (with custom date)\n"
            "<code>/add 2026-06-20 50200 good day</code>",
            parse_mode="HTML",
        )
        return

    if user.start_balance <= 0:
        await update.message.reply_text(
            "❌ No challenge set up yet. Use <code>/setup</code> first.",
            parse_mode="HTML",
        )
        return

    # Check if first arg is a date (YYYY-MM-DD)
    custom_date = None
    balance_idx = 0
    if len(args) >= 2:
        try:
            custom_date = datetime.strptime(args[0], "%Y-%m-%d").date()
            balance_idx = 1  # Balance is the second argument
        except ValueError:
            pass  # First arg is not a date, it's the balance

    try:
        balance = float(args[balance_idx].replace(",", "").replace("$", ""))
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Ending balance must be a number (e.g., 50200)", parse_mode="HTML")
        return

    if balance <= 0:
        await update.message.reply_text("❌ Balance must be greater than $0.", parse_mode="HTML")
        return

    notes_start = balance_idx + 1
    notes = " ".join(args[notes_start:]) if len(args) > notes_start else ""

    if custom_date:
        # Add with custom date
        user.data["trades"].append({
            "date": custom_date.isoformat(),
            "balance": balance,
            "notes": notes,
        })
        user.data["trades"].sort(key=lambda t: t["date"])
        user.current_balance = balance
        user.save()
    else:
        user.add_trade(balance, notes)

    # Show trade result
    stats = ChallengeStats(user)
    last = stats.stats[-1] if stats.stats else None

    msg_parts = [f"✅ <b>Day {len(user.trades)} Recorded</b>\n"]
    if last:
        daily_pnl = last["daily_pnl"]
        emoji = "🟢" if daily_pnl >= 0 else "🔴"
        msg_parts.append(f"{emoji} Daily P&L: {format_currency(daily_pnl)}")
        msg_parts.append(f"📊 Balance: {format_currency_plain(balance)}")
        msg_parts.append(f"📈 Total P&L: {format_currency(stats.total_pnl)}")
        msg_parts.append("")

    # Check if any warnings
    warnings = []
    if stats.static_drawdown_pct > 80:
        warnings.append("🔴 <b>Warning:</b> Near max drawdown limit!")
    if stats.best_day_violation:
        warnings.append("⚠️ <b>Best day rule:</b> Best day exceeds 50% of total profit!")
    if stats.status == "passed":
        if user.challenge_type == "2step" and user.phase == 1:
            warnings.append("🎉 <b>Phase 1 Passed!</b> Use <code>/promote</code> to move to Phase 2.")
        else:
            warnings.append("🎉 <b>Challenge Passed!</b> Congratulations!")
    if stats.status == "failed":
        warnings.append("❌ <b>Challenge Failed.</b> Use <code>/reset</code> to start over.")

    if warnings:
        msg_parts.append("")
        msg_parts.extend(warnings)

    await update.message.reply_text("\n".join(msg_parts), parse_mode="HTML")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current challenge status."""
    user_id = update.effective_user.id
    user = UserData(user_id)

    if not user.trades and user.start_balance <= 0:
        await update.message.reply_text(
            "📊 No challenge data yet.\n\n"
            "Set up your challenge first: <code>/setup 2step 50000</code>",
            parse_mode="HTML",
        )
        return

    stats = ChallengeStats(user)
    msg = format_status(stats)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trade log."""
    user_id = update.effective_user.id
    user = UserData(user_id)
    stats = ChallengeStats(user)
    msg = format_trade_log(stats)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send equity curve chart."""
    user_id = update.effective_user.id
    user = UserData(user_id)
    stats = ChallengeStats(user)

    if not stats.stats:
        await update.message.reply_text(
            "📈 Not enough data for a chart. Add some trades first with <code>/add</code>.",
            parse_mode="HTML",
        )
        return

    if not CHART_SUPPORT:
        await update.message.reply_text(
            "❌ Chart generation requires matplotlib.\nInstall: <code>pip3 install matplotlib</code>",
            parse_mode="HTML",
        )
        return

    await update.message.reply_chat_action("upload_photo")

    chart_bytes = generate_chart(stats, user)
    if chart_bytes:
        await update.message.reply_photo(
            photo=chart_bytes,
            caption=f"📈 Equity Curve — {stats.challenge_type.upper()} Phase {stats.phase}",
        )
    else:
        await update.message.reply_text("❌ Failed to generate chart.", parse_mode="HTML")


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export user data as JSON file."""
    user_id = update.effective_user.id
    user = UserData(user_id)
    data = format_export(user)

    # Send as file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(data)
        f.flush()
        with open(f.name, "rb") as fh:
            await update.message.reply_document(
                document=fh,
                filename=f"ftmo_challenge_{date.today().isoformat()}.json",
                caption="📊 Your FTMO challenge data",
            )
        os.unlink(f.name)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all data with confirmation."""
    user_id = update.effective_user.id
    user = UserData(user_id)

    if not user.trades:
        await update.message.reply_text("No data to reset.", parse_mode="HTML")
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, reset everything", callback_data="reset_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="reset_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ <b>This will delete ALL your trading data.</b>\n\nAre you sure?",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def cmd_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Move to Phase 2 (2-Step only)."""
    user_id = update.effective_user.id
    user = UserData(user_id)

    if user.challenge_type != "2step":
        await update.message.reply_text(
            "❌ Promotion is only for 2-Step challenges.",
            parse_mode="HTML",
        )
        return

    if user.phase != 1:
        await update.message.reply_text(
            "❌ You're already in Phase 2.",
            parse_mode="HTML",
        )
        return

    # Check if they passed phase 1
    stats = ChallengeStats(user)
    if stats.status != "passed":
        await update.message.reply_text(
            "❌ You need to pass Phase 1 first.\n"
            f"🎯 Profit target: {format_currency_plain(stats.profit_target)}\n"
            f"📈 Current: {format_currency_plain(max(0, stats.total_pnl))}\n"
            f"📅 Days: {len(user.trades)}/{stats.min_days_required}",
            parse_mode="HTML",
        )
        return

    user.promote_phase()
    stats = ChallengeStats(user)
    msg = (
        "🎉 <b>Promoted to Phase 2!</b>\n\n"
        f"Phase 2 profit target: {format_currency_plain(stats.profit_target)} (5%)\n"
        f"Keep tracking: <code>/add &lt;balance&gt;</code>\n\n"
        "Your trade history is preserved for reference."
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a trading day: /delete <day_number>"""
    user_id = update.effective_user.id
    user = UserData(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: <code>/delete &lt;day_number&gt;</code>\n\n"
            "Use <code>/log</code> to see day numbers, then:\n"
            "<code>/delete 1</code>  — deletes the first trading day",
            parse_mode="HTML",
        )
        return

    if not user.trades:
        await update.message.reply_text("❌ No trading days to delete.", parse_mode="HTML")
        return

    try:
        day_num = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Day number must be a number (e.g., /delete 1)", parse_mode="HTML")
        return

    if day_num < 1 or day_num > len(user.trades):
        await update.message.reply_text(
            f"❌ Invalid day. You have {len(user.trades)} trading days (1-{len(user.trades)}).",
            parse_mode="HTML",
        )
        return

    # Delete by index (day_num - 1)
    deleted = user.trades[day_num - 1]
    user.delete_trade(day_num - 1)

    await update.message.reply_text(
        f"🗑️ <b>Deleted Day {day_num}</b> ({deleted['date']})\n"
        f"   Balance: {format_currency_plain(deleted['balance'])}\n"
        f"   Remaining: {len(user.trades)} trading days",
        parse_mode="HTML",
    )


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About and Pro version info."""
    msg = (
        "📊 <b>FTMO Challenge Tracker Bot</b>\n\n"
        "Track your FTMO challenge rules in real-time:\n"
        "🎯 Profit target progress\n"
        "🛑 Drawdown monitoring\n"
        "📅 Trading day counter\n"
        "📈 Equity curve chart\n"
        "📋 Complete trade log\n"
        "🔄 1-Step & 2-Step support\n\n"
        "Built with ❤️ for the FTMO trading community.\n"
        "Not affiliated with FTMO.com\n\n"
        "🔥 <b>Pro Version — $19.99/mo</b>\n"
        "✅ Cloud sync across devices\n"
        "✅ Unlimited accounts\n"
        "✅ PDF report export\n"
        "✅ Email notifications\n"
        "👉 <a href='https://gumroad.com/l/ezteprg'>Get Pro Access</a>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command."""
    await cmd_start(update, context)


# Callback handler for inline buttons (reset confirmation)
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "reset_confirm":
        user_id = update.effective_user.id
        user = UserData(user_id)
        user.reset()
        await query.edit_message_text(
            "✅ <b>All data has been reset.</b>\n\n"
            "Set up a new challenge: <code>/setup 2step 50000</code>",
            parse_mode="HTML",
        )
    elif query.data == "reset_cancel":
        await query.edit_message_text("✅ Reset cancelled. Your data is safe.")


# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Sorry, something went wrong. Please try again.",
        )


# ═══════════════════════════════════════════════════════════════════════
#  🤖 CEO CHAT BRIDGE — Talk to the AI CEO via Telegram
# ═══════════════════════════════════════════════════════════════════════

CEO_TASKS_DIR = BOT_DIR / "ceo_tasks"
CEO_TASKS_DIR.mkdir(parents=True, exist_ok=True)
CEO_PENDING_FILE = CEO_TASKS_DIR / "pending.json"
CEO_RESULTS_DIR = CEO_TASKS_DIR / "results"
CEO_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def save_ceo_task(user_id: int, username: str, message: str) -> str:
    """Save a message for the CEO to process. Returns task_id."""
    import uuid
    task_id = str(uuid.uuid4())[:8]
    task = {
        "task_id": task_id,
        "user_id": user_id,
        "username": username,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
    }
    # Load pending queue
    pending = []
    if CEO_PENDING_FILE.exists():
        try:
            pending = json.loads(CEO_PENDING_FILE.read_text())
        except:
            pass
    pending.append(task)
    CEO_PENDING_FILE.write_text(json.dumps(pending, indent=2))
    logger.info(f"🤖 CEO task {task_id} from @{username}: {message[:60]}...")
    return task_id

def check_ceo_results(user_id: int) -> list:
    """Check for CEO results for a specific user."""
    results = []
    if not CEO_RESULTS_DIR.exists():
        return results
    for f in sorted(CEO_RESULTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            if data.get("user_id") == user_id and not data.get("sent_to_user", False):
                results.append(data)
                data["sent_to_user"] = True
                f.write_text(json.dumps(data, indent=2))
        except:
            pass
    return results

def get_pending_tasks() -> list:
    """Get all pending tasks for the CEO to process."""
    if not CEO_PENDING_FILE.exists():
        return []
    try:
        pending = json.loads(CEO_PENDING_FILE.read_text())
        return [t for t in pending if t.get("status") == "pending"]
    except:
        return []

def complete_ceo_task(task_id: str, response: str):
    """Mark a CEO task as completed and save the response."""
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
                    "user_id": task["user_id"],
                    "username": task["username"],
                    "original_message": task["message"],
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "sent_to_user": False,
                }
                result_file = CEO_RESULTS_DIR / f"{task_id}.json"
                result_file.write_text(json.dumps(result, indent=2))
                break
        CEO_PENDING_FILE.write_text(json.dumps(pending, indent=2))
    except:
        pass

async def cmd_ceo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message to the CEO (AI agent).
    
    Usage: /ceo <your message>
    The CEO will process your request and reply.
    """
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Only the company owner can talk to the CEO.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "🤖 <b>CEO Chat Bridge</b>\n\n"
            "Send me a message and I'll forward it to the CEO (AI agent) for processing.\n\n"
            "Usage: <code>/ceo &lt;your request&gt;</code>\n\n"
            "Examples:\n"
            "<code>/ceo generate more SEO pages</code>\n"
            "<code>/ceo check the system status</code>\n"
            "<code>/ceo post a new article about FTMO rules</code>\n"
            "<code>/ceo what is the company doing right now?</code>\n\n"
            "You can also just send any message directly — non-command messages are also forwarded to the CEO.\n\n"
            "<i>The CEO will process your request when they are next active and reply here.</i>",
            parse_mode="HTML",
        )
        return
    
    message = " ".join(context.args)
    task_id = save_ceo_task(update.effective_user.id, update.effective_user.username or "Unknown", message)
    
    await update.message.reply_text(
        f"🤖 <b>Message sent to CEO!</b>\n\n"
        f"Task ID: <code>{task_id}</code>\n"
        f"Message: <i>{message[:100]}</i>\n\n"
        f"The CEO will process your request. Check back with <code>/ceocheck</code> for responses, "
        f"or I'll notify you when done.",
        parse_mode="HTML",
    )


async def cmd_ceocheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check for CEO responses."""
    if not is_boss(update.effective_user.id):
        return
    
    results = check_ceo_results(update.effective_user.id)
    
    if not results:
        await update.message.reply_text(
            "📭 No new CEO responses. Try <code>/ceo &lt;message&gt;</code> to send a request.",
            parse_mode="HTML",
        )
        return
    
    for result in results:
        msg = (
            f"🤖 <b>CEO Response</b>\n\n"
            f"<b>You said:</b> <i>{result.get('original_message', '')[:200]}</i>\n\n"
            f"{result.get('response', '')[:3500]}"
        )
        try:
            await update.message.reply_text(msg, parse_mode="HTML")
        except:
            # If parse_mode fails, send without HTML
            await update.message.reply_text(msg)


async def cmd_ceostatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show CEO task queue status."""
    if not is_boss(update.effective_user.id):
        return
    
    pending = get_pending_tasks()
    completed = len(list(CEO_RESULTS_DIR.glob("*.json"))) if CEO_RESULTS_DIR.exists() else 0
    
    msg = (
        f"🤖 <b>CEO Status</b>\n\n"
        f"📥 Pending tasks: {len(pending)}\n"
        f"✅ Completed tasks: {completed}\n"
        f"\n"
        f"<b>Pending:</b>\n"
    )
    
    if pending:
        for task in pending[-5:]:  # Last 5
            msg += f"• <code>{task['task_id']}</code>: {task['message'][:50]}...\n"
    else:
        msg += "No pending tasks.\n"
    
    msg += (
        f"\n<b>Talk to CEO:</b> <code>/ceo &lt;message&gt;</code>\n"
        f"<b>Check replies:</b> <code>/ceocheck</code>"
    )
    
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_ceohistory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show CEO chat history."""
    if not is_boss(update.effective_user.id):
        return
    
    results = []
    if CEO_RESULTS_DIR.exists():
        for f in sorted(CEO_RESULTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            try:
                data = json.loads(f.read_text())
                results.append(data)
            except:
                pass
    
    if not results:
        await update.message.reply_text("📭 No CEO chat history yet.")
        return
    
    msg = "🤖 <b>CEO Chat History (Last 10)</b>\n\n"
    for r in results:
        user_msg = r.get('original_message', '')[:60]
        ceo_resp = r.get('response', '')[:80]
        msg += f"🧑 <b>You:</b> {user_msg}...\n"
        msg += f"🤖 <b>CEO:</b> {ceo_resp}...\n\n"
    
    await update.message.reply_text(msg, parse_mode="HTML")


async def non_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages — forward to CEO."""
    if not update.message or not update.message.text:
        return
    
    # Only forward from boss
    if not is_boss(update.effective_user.id):
        return
    
    message = update.message.text.strip()
    if not message:
        return
    
    task_id = save_ceo_task(update.effective_user.id, update.effective_user.username or "Boss", message)
    
    await update.message.reply_text(
        f"🤖 Message forwarded to CEO. Task: <code>{task_id}</code>\n"
        f"Check response: <code>/ceocheck</code>",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════
#  🏢 COMPANY HQ — ADMIN COMMANDS (Boss only: 7837847803)
# ═══════════════════════════════════════════════════════════════════════

BOSS_USER_ID = 7837847803

def is_boss(user_id: int) -> bool:
    return user_id == BOSS_USER_ID

async def cmd_hq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Company dashboard."""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ This command is for the company owner only.")
        return
    try:
        from company_hq import format_dashboard
        msg = format_dashboard()
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_revenue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revenue report."""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Owner only.")
        return
    try:
        from company_hq import format_revenue
        msg = format_revenue()
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_sysstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """System status."""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Owner only.")
        return
    try:
        from company_hq import format_status
        msg = format_status()
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_boss_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View logs. Usage: /logs <lines>"""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Owner only.")
        return
    try:
        from company_hq import get_logs
        n = int(context.args[0]) if context.args else 30
        msg = get_logs(n)
        if len(msg) > 4000:
            # Send as file if too long
            with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
                f.write(msg)
                f.flush()
                with open(f.name, "rb") as fh:
                    await update.message.reply_document(document=fh, filename="system_logs.log")
                os.unlink(f.name)
        else:
            await update.message.reply_text(f"<code>{msg[:3500]}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart all services."""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Owner only.")
        return
    await update.message.reply_text("🔄 Restarting all services...")
    try:
        from company_hq import restart_services
        result = restart_services()
        await update.message.reply_text(f"✅ Restart complete:\n<code>{result[:500]}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Restart error: {e}")

async def cmd_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deploy latest updates."""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Owner only.")
        return
    await update.message.reply_text("🚀 Deploying updates...")
    try:
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=30, cwd=str(HOME))
        output = result.stdout + result.stderr
        subprocess.run(["bash", str(BOT_DIR / "restart_all.sh")], capture_output=True, timeout=30)
        await update.message.reply_text(f"✅ Deploy complete:\n<code>{output[:500]}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Deploy error: {e}")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all bot users."""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Owner only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = " ".join(context.args)
    await update.message.reply_text(f"📢 Broadcasting to all users...")
    
    sent = 0
    errors = 0
    for user_file in (DATA_DIR).glob("*.json"):
        try:
            uid = int(user_file.stem)
            if uid == update.effective_user.id:
                continue
            await context.bot.send_message(chat_id=uid, text=f"📢 <b>Broadcast:</b>\n{message}", parse_mode="HTML")
            sent += 1
        except:
            errors += 1
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users. Errors: {errors}")

async def cmd_campaigns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Campaign management."""
    if not is_boss(update.effective_user.id):
        await update.message.reply_text("⛔ Owner only.")
        return
    msg = (
        "📢 <b>CAMPAIGNS</b>\n\n"
        "<b>Active Cron Jobs:</b>\n"
        "• Marketing engine: every hour\n"
        "• Reddit posts: Mon/Wed/Fri 9AM, 3PM, 8PM\n"
        "• Discord posts: Weekdays 10AM, 4PM, 9PM\n"
        "• Auto-healing: every minute\n\n"
        "<b>Commands:</b>\n"
        "<code>/run-reddit</code> — Post to Reddit now\n"
        "<code>/run-discord</code> — Post to Discord now\n"
        "<code>/traffic</code> — Traffic engine stats\n"
        "<code>/logs 50</code> — View logs"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_run_reddit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_boss(update.effective_user.id):
        return
    await update.message.reply_text("📢 Attempting Reddit post...")
    try:
        result = subprocess.run(["python3", "income/tools/marketing_engine.py", "--reddit"], capture_output=True, text=True, timeout=30, cwd=HOME)
        await update.message.reply_text(f"<code>{result.stdout[-500:]}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_boss(update.effective_user.id):
        return
    try:
        result = subprocess.run(["python3", "trading/traffic_engine.py", "--stats"], capture_output=True, text=True, timeout=15, cwd=HOME)
        await update.message.reply_text(f"<code>{result.stdout[-1000:]}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_boss(update.effective_user.id):
        return
    try:
        result = subprocess.run(["python3", "trading/content_generator.py", "--article"], capture_output=True, text=True, timeout=15, cwd=HOME)
        await update.message.reply_text(f"<code>{result.stdout[-1000:]}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    if not TELEGRAM_SUPPORT:
        print("❌ python-telegram-bot not installed.")
        print("   Install: pip3 install python-telegram-bot")
        sys.exit(1)

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set.")
        print("   Get a token from @BotFather on Telegram, then:")
        print("   export TELEGRAM_BOT_TOKEN='your:token'")
        print(f"   python3 {__file__}")
        sys.exit(1)

    # Create application
    app = Application.builder().token(token).build()
    
    # Debug: log every incoming update (silent, no replies)
    async def debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        msg = update.effective_message
        if user and msg:
            logger.info(f"📩 Received from @{user.username or '?'} ({user.id}): \"{msg.text or '[non-text]'}\"")
        else:
            logger.info(f"📩 Received update: {update.update_id}")
    
    # Register debug handler in group=-1 (runs first, doesn't block others)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, debug_all), group=-1)

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("setup", cmd_setup))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("chart", cmd_chart))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("promote", cmd_promote))
    app.add_handler(CommandHandler("about", cmd_about))
    
    # 🏢 Company HQ — Admin commands (boss only)
    app.add_handler(CommandHandler("hq", cmd_hq))
    app.add_handler(CommandHandler("revenue", cmd_revenue))
    app.add_handler(CommandHandler("sysstatus", cmd_sysstatus))
    app.add_handler(CommandHandler("logs", cmd_boss_logs))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("deploy", cmd_deploy))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("campaigns", cmd_campaigns))
    app.add_handler(CommandHandler("runreddit", cmd_run_reddit))
    app.add_handler(CommandHandler("traffic", cmd_traffic))
    app.add_handler(CommandHandler("content", cmd_content))

    # 🤖 CEO Chat Bridge — Talk to the AI CEO
    app.add_handler(CommandHandler("ceo", cmd_ceo))
    app.add_handler(CommandHandler("ceocheck", cmd_ceocheck))
    app.add_handler(CommandHandler("ceostatus", cmd_ceostatus))
    app.add_handler(CommandHandler("ceohistory", cmd_ceohistory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, non_command_handler))

    # Callback handler for inline buttons
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(button_callback))

    # Error handler
    app.add_error_handler(error_handler)

    print(f"\n{'='*50}")
    print(f"  📊 FTMO Challenge Tracker Bot")
    print(f"  Token: {token[:8]}...{token[-4:]}")
    print(f"  Data: {DATA_DIR}")
    print(f"  Logs: {BOT_DIR / 'ftmo_bot.log'}")
    print(f"{'='*50}")
    print(f"\n  🚀 Bot is running... Press Ctrl+C to stop.\n")

    # Start polling
    app.run_polling()


if __name__ == "__main__":
    main()
