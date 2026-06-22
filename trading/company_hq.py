#!/usr/bin/env python3
"""
🏢 FTMO COMPANY HQ — Telegram Command Center
==============================================
Full company control from Telegram. Status, analytics, deploy, campaigns.
Runs alongside the FTMO bot on the same token.

Commands for Boss (@ArdTradingBot):
  /hq           — Company dashboard
  /revenue      — Revenue & earnings
  /traffic      — Traffic & conversion stats  
  /campaigns    — Active marketing campaigns
  /deploy       — Deploy updates
  /logs [lines] — View system logs
  /status       — All services status
  /broadcast    — Send message to all users
  /restart      — Restart all services
"""

import json
import os
import sys
import subprocess
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

HOME = Path.home()
TRADING_DIR = HOME / "trading"
INCOME_DIR = HOME / "income"
DATA_DIR = TRADING_DIR / "hq_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | HQ | %(message)s",
    handlers=[
        logging.FileHandler(TRADING_DIR / "hq.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("hq")


class CompanyHQ:
    """Company intelligence and control."""

    def __init__(self):
        self.stats_file = DATA_DIR / "company_stats.json"
        self.revenue_file = DATA_DIR / "revenue.json"
        self.campaigns_file = DATA_DIR / "campaigns.json"
        self.load()

    def load(self):
        # Company stats
        if self.stats_file.exists():
            try:
                self.stats = json.loads(self.stats_file.read_text())
            except:
                self.stats = self._default_stats()
        else:
            self.stats = self._default_stats()
            self.save_stats()

        # Revenue tracking
        if self.revenue_file.exists():
            try:
                self.revenue = json.loads(self.revenue_file.read_text())
            except:
                self.revenue = self._default_revenue()
        else:
            self.revenue = self._default_revenue()
            self.save_revenue()

        # Campaigns
        if self.campaigns_file.exists():
            try:
                self.campaigns = json.loads(self.campaigns_file.read_text())
            except:
                self.campaigns = self._default_campaigns()
        else:
            self.campaigns = self._default_campaigns()
            self.save_campaigns()

    def _default_stats(self) -> dict:
        return {
            "company_name": "FTMO Income Corp",
            "founded": datetime.now().isoformat(),
            "total_revenue": 0.0,
            "total_costs": 0.0,
            "profit": 0.0,
            "active_users": 0,
            "total_users": 0,
            "pro_subscribers": 0,
            "website_visits": 0,
            "bot_users": 0,
            "campaigns_run": 0,
            "posts_made": 0,
            "last_updated": datetime.now().isoformat(),
        }

    def _default_revenue(self) -> dict:
        return {
            "total_revenue": 0.0,
            "monthly_recurring": 0.0,  # MRR
            "sources": {
                "gumroad_pro": {"total": 0.0, "count": 0, "mrr": 0.0},
                "affiliate": {"total": 0.0, "count": 0, "mrr": 0.0},
                "fiverr": {"total": 0.0, "count": 0, "mrr": 0.0},
                "other": {"total": 0.0, "count": 0, "mrr": 0.0},
            },
            "transactions": [],
            "last_sale": None,
        }

    def _default_campaigns(self) -> dict:
        return {
            "active": [],
            "completed": [],
            "scheduled": [],
            "stats": {
                "total_campaigns": 0,
                "active_campaigns": 0,
                "total_impressions": 0,
                "total_clicks": 0,
                "total_conversions": 0,
            }
        }

    def save_stats(self):
        self.stats["last_updated"] = datetime.now().isoformat()
        self.stats_file.write_text(json.dumps(self.stats, indent=2))

    def save_revenue(self):
        self.revenue_file.write_text(json.dumps(self.revenue, indent=2, default=str))

    def save_campaigns(self):
        self.campaigns_file.write_text(json.dumps(self.campaigns, indent=2, default=str))

    def record_revenue(self, source: str, amount: float, customer: str = ""):
        """Record a revenue event."""
        if source in self.revenue["sources"]:
            self.revenue["sources"][source]["total"] += amount
            self.revenue["sources"][source]["count"] += 1
            if source == "gumroad_pro":
                self.revenue["sources"][source]["mrr"] += amount

        self.revenue["total_revenue"] += amount
        self.revenue["monthly_recurring"] = sum(
            s["mrr"] for s in self.revenue["sources"].values()
        )
        self.revenue["transactions"].append({
            "source": source,
            "amount": amount,
            "customer": customer,
            "timestamp": datetime.now().isoformat(),
        })
        self.revenue["last_sale"] = datetime.now().isoformat()
        self.save_revenue()
        logger.info(f"💰 Revenue: +${amount:.2f} from {source}" + (f" ({customer})" if customer else ""))

    def get_system_status(self) -> dict:
        """Check all running services."""
        status = {
            "telegram_bot": False,
            "web_server": False,
            "tunnel": False,
            "cron_active": False,
            "marketing_engine": False,
            "timestamp": datetime.now().isoformat(),
        }

        # Check screen sessions
        try:
            result = subprocess.run(["screen", "-ls"], capture_output=True, text=True, timeout=5)
            output = result.stdout
            status["telegram_bot"] = "ftmo-bot" in output
            status["web_server"] = "site-server" in output
            status["tunnel"] = "site-tunnel" in output
        except:
            pass

        # Check cron
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            status["cron_active"] = "marketing_engine" in result.stdout
        except:
            pass

        # Check web server
        try:
            r = requests.get("http://localhost:3000/", timeout=3)
            status["web_server"] = r.status_code == 200
            r2 = requests.get("https://ftmo-tracker.loca.lt/", timeout=5)
            status["tunnel"] = r2.status_code == 200
        except:
            pass

        # Check disk/memory
        try:
            df = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            free = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
            status["disk"] = df.stdout.split("\n")[1].split()[3] if len(df.stdout.split("\n")) > 1 else "?"
            status["memory"] = free.stdout.split("\n")[1].split()[2] if len(free.stdout.split("\n")) > 1 else "?"
        except:
            pass

        # Count bot users
        try:
            user_files = list((TRADING_DIR / "telegram_data").glob("*.json"))
            status["bot_users"] = len(user_files)
        except:
            status["bot_users"] = 0

        status["all_ok"] = all([
            status["telegram_bot"],
            status["web_server"],
            status["tunnel"],
            status["cron_active"],
        ])

        return status

    def get_dashboard(self) -> str:
        """Generate company dashboard text."""
        status = self.get_system_status()

        lines = [
            "🏢 <b>FTMO INCOME CORP — DASHBOARD</b>\n",
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        ]

        # Revenue
        lines.append("<b>💰 REVENUE</b>")
        lines.append(f"  Total:   <b>${self.revenue['total_revenue']:.2f}</b>")
        lines.append(f"  MRR:     <b>${self.revenue['monthly_recurring']:.2f}</b>/mo")
        lines.append(f"  Last sale: {self.revenue['last_sale'] or 'None'}")
        lines.append("")

        # Sources
        lines.append("<b>📊 BY SOURCE</b>")
        for src, data in self.revenue["sources"].items():
            name = src.replace("_", " ").title()
            lines.append(f"  {name}: ${data['total']:.2f} ({data['count']} sales)")
        lines.append("")

        # Services
        lines.append("<b>🟢 SERVICES</b>")
        emoji = lambda ok: "✅" if ok else "❌"
        lines.append(f"  {emoji(status['telegram_bot'])} Telegram Bot  ({status.get('bot_users', 0)} users)")
        lines.append(f"  {emoji(status['web_server'])} Web Server")
        lines.append(f"  {emoji(status['tunnel'])} Public Tunnel")
        lines.append(f"  {emoji(status['cron_active'])} Cron Scheduler")
        lines.append("")

        # Traffic (from marketing engine)
        try:
            post_history = INCOME_DIR / "marketing_data" / "post_history.json"
            if post_history.exists():
                ph = json.loads(post_history.read_text())
                lines.append(f"<b>📢 MARKETING</b>")
                lines.append(f"  Posts made: {ph.get('total_posts', 0)}")
                for plat, pdata in ph.get("platforms", {}).items():
                    lines.append(f"  {plat.title()}: {pdata['count']} posts")
                lines.append("")
        except:
            pass

        # Health
        if status.get("disk"):
            lines.append(f"<b>💻 SYSTEM</b>")
            lines.append(f"  Disk: {status.get('disk', '?')} free")
            lines.append(f"  RAM: {status.get('memory', '?')} used")
            lines.append("")

        # Controls
        lines.append("<b>🎮 COMMANDS</b>")
        lines.append("  /revenue   — Detailed revenue report")
        lines.append("  /traffic   — Traffic analytics")
        lines.append("  /campaigns — Campaign management")
        lines.append("  /logs 50   — View last 50 log lines")
        lines.append("  /restart   — Restart all services")
        lines.append("  /status    — Raw service status")

        return "\n".join(lines)

    def get_revenue_report(self) -> str:
        """Detailed revenue report."""
        lines = [
            "💰 <b>REVENUE REPORT</b>\n",
            f"<b>Total Revenue:</b> ${self.revenue['total_revenue']:.2f}",
            f"<b>Monthly Recurring:</b> ${self.revenue['monthly_recurring']:.2f}/mo\n",
            "<b>Sources:</b>",
        ]

        for src, data in self.revenue["sources"].items():
            name = src.replace("_", " ").title()
            lines.append(f"  • {name}: ${data['total']:.2f} ({data['count']} sales, ${data['mrr']:.2f}/mo MRR)")

        lines.append("")
        lines.append(f"<b>Transactions: {len(self.revenue['transactions'])}</b>")

        recent = self.revenue["transactions"][-10:]
        if recent:
            lines.append("<b>Recent:</b>")
            for t in reversed(recent):
                lines.append(f"  ${t['amount']:.2f} from {t['source']}")

        return "\n".join(lines)

    def start_campaign(self, name: str, platform: str, frequency_hours: int) -> dict:
        """Start a new marketing campaign."""
        campaign = {
            "id": len(self.campaigns["active"]) + len(self.campaigns["completed"]) + 1,
            "name": name,
            "platform": platform,
            "frequency_hours": frequency_hours,
            "started": datetime.now().isoformat(),
            "status": "active",
            "posts_made": 0,
            "clicks": 0,
            "conversions": 0,
        }
        self.campaigns["active"].append(campaign)
        self.campaigns["stats"]["active_campaigns"] = len(self.campaigns["active"])
        self.campaigns["stats"]["total_campaigns"] += 1
        self.save_campaigns()
        logger.info(f"📢 Campaign started: {name} on {platform}")
        return campaign


# Singleton
hq = CompanyHQ()


def format_dashboard() -> str:
    return hq.get_dashboard()


def format_revenue() -> str:
    return hq.get_revenue_report()


def format_status() -> str:
    status = hq.get_system_status()
    emoji = lambda ok: "✅" if ok else "❌"
    lines = [
        "🟢 <b>SYSTEM STATUS</b>\n",
        f"{emoji(status['telegram_bot'])} Telegram Bot @ArdTradingBot",
        f"{emoji(status['web_server'])} Web Server (port 3000)",
        f"{emoji(status['tunnel'])} Public Tunnel (ftmo-tracker.loca.lt)",
        f"{emoji(status['cron_active'])} Cron Scheduler",
        "",
        f"<b>All Systems Go:</b> {'✅ YES' if status.get('all_ok') else '❌ ISSUES FOUND'}",
    ]
    if status.get("disk"):
        lines.extend(["", f"Disk: {status['disk']} free | RAM: {status.get('memory', '?')} used"])
    return "\n".join(lines)


def restart_services():
    """Restart all services via restart_all.sh."""
    try:
        result = subprocess.run(
            ["bash", str(TRADING_DIR / "restart_all.sh")],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"


def get_logs(lines: int = 30) -> str:
    """Get recent log lines from multiple sources."""
    log_files = [
        TRADING_DIR / "ftmo_bot.log",
        TRADING_DIR / "hq.log",
        INCOME_DIR / "logs" / "marketing_engine.log",
    ]
    
    result = []
    for log_file in log_files:
        if log_file.exists():
            try:
                content = subprocess.run(
                    ["tail", f"-{lines//len(log_files)}", str(log_file)],
                    capture_output=True, text=True, timeout=5
                ).stdout
                if content.strip():
                    result.append(f"\n📄 {log_file.name}:")
                    result.append(content)
            except:
                pass
    
    return "\n".join(result) if result else "No logs available."


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dashboard"
    if cmd == "dashboard":
        print(format_dashboard())
    elif cmd == "revenue":
        print(format_revenue())
    elif cmd == "status":
        print(format_status())
    elif cmd == "logs":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        print(get_logs(n))
    elif cmd == "restart":
        print(restart_services())
    elif cmd == "record":
        # Manual revenue recording
        source = sys.argv[2] if len(sys.argv) > 2 else "other"
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else 0
        hq.record_revenue(source, amount)
        print(f"Recorded ${amount:.2f} from {source}")
    else:
        print("Commands: dashboard, revenue, status, logs <n>, restart, record <source> <amount>")
