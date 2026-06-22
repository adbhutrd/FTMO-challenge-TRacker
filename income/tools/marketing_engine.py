#!/usr/bin/env python3
"""
🚀 MARKETING ENGINE — Automated Income Generator
=================================================
Posts promotional content to Reddit, Discord, Twitter/X, and more.
Runs autonomously on a schedule. Generates varied content from templates.

Usage:
    python3 marketing_engine.py --run-all     # Run all enabled platforms
    python3 marketing_engine.py --reddit      # Post to Reddit
    python3 marketing_engine.py --discord     # Post to Discord
    python3 marketing_engine.py --schedule    # Run scheduled posts
    python3 marketing_engine.py --status      # Show posting history
"""

import json
import os
import sys
import random
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

BASE_DIR = Path.home()
TRADING_DIR = BASE_DIR / "trading"
INCOME_DIR = BASE_DIR / "income"
LOG_DIR = INCOME_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = INCOME_DIR / "marketing_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | MARKETING | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "marketing_engine.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("marketing_engine")


# ═══════════════════════════════════════════════════════════════════
#  CONTENT TEMPLATES
# ═══════════════════════════════════════════════════════════════════

REDDIT_TITLES = [
    "3 years of FTMO challenges taught me one thing — 90% of failures aren't from bad trading, they're from bad tracking.",
    "I built a free FTMO Challenge Tracker because I was tired of failing rules instead of markets.",
    "Stop losing FTMO challenges to rules you forgot about. This free tracker catches every one.",
    "Real-time FTMO tracking — profit target, drawdown, daily loss limits. All in one free tool.",
    "Failed my first FTMO challenge because I lost track of drawdown. Built this so it never happens again.",
    "FTMO traders: what if you never had to manually calculate drawdown again?",
    "I automated FTMO rule tracking so I can focus on trading, not spreadsheets.",
]

REDDIT_BODIES = [
    """I've been trading FTMO challenges for 3 years. Failed 7 before I passed my first one.

Here's what I learned:

Most people fail not because of bad trades, but because they:
• Lose track of their drawdown mid-challenge
• Forget how many trading days they've done
• Don't realize they're 1 bad day away from breaching

So I built a tracker that does all of this automatically:

📊 **FTMO Challenge Tracker — free to use**

**What it tracks:**
🎯 Profit Target — Real-time progress bar for Phase 1 (10%) & Phase 2 (5%)
🛑 Drawdown Guardian — Color-coded warnings before you hit the 10% limit
📅 Trading Days — Automatic counter with minimum day requirements
📈 Equity Curve — Live chart with profit target & drawdown lines
📋 Trade Log — Every day logged with P&L, drawdown %, and notes
🔄 1-Step & 2-Step — Full rule engine for both types
🤖 Telegram Bot — Track from your phone (@ArdTradingBot)

**How it works:**
1. Set your challenge type & account size → 10 seconds
2. After each trading day, enter your ending balance → 5 seconds
3. Watch real-time progress → done

No signup. No account. No tracking. Your data stays on YOUR machine.

Free version: Full tracker, all features, forever.
Pro version ($19.99/mo): Cloud sync, unlimited accounts, PDF reports, email alerts.

👉 **Try it free:** https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html

Built this for the community — feedback welcome!""",

    """If you're trading an FTMO challenge right now, answer these 3 questions:

1. What's your exact profit target remaining?
2. How much drawdown have you used?
3. How many trading days have you completed?

If you can't answer all 3 instantly, you need a tracker.

I built a free one that does it all automatically:

📊 **FTMO Challenge Tracker**

🎯 Real-time profit target
🛑 Drawdown warnings
📅 Trading day counter
📈 Equity curve chart
🔄 1-Step & 2-Step support

**Free:** https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html
**Telegram bot:** @ArdTradingBot
**Pro version:** https://gumroad.com/l/ezteprg ($19.99/mo)

No signup needed. Just open and use.""",
]

DISCORD_MESSAGES = [
    "📊 **FTMO Challenge Tracker** — track your challenge in real-time!\n\n🎯 Profit target • 🛑 Drawdown • 📅 Trading days • 📈 Chart\n\n**Free:** https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n**Telegram bot:** @ArdTradingBot\n**Pro:** https://gumroad.com/l/ezteprg",
    "📈 **Tracking your FTMO challenge just got easier.**\n\nReal-time profit target progress, drawdown warnings, trading day counter, equity curve chart. All free, no signup.\n\n👉 https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\n🤖 Also available on Telegram: @ArdTradingBot",
    "🔥 **Pro tip:** Most FTMO challenge failures are from rule violations, not bad trading. Track every rule in real-time with this free tool.\n\n👉 https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\nOr use the Telegram bot: @ArdTradingBot",
]

TWITTER_POSTS = [
    "Tracking your FTMO challenge should be automatic. Profit targets, drawdown, trading days — all in real-time. Free to use.\n\nhttps://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\n#FTMO #PropTrading #DayTrading",
    "90% of FTMO failures aren't from bad trading — they're from bad tracking. Built a free tool to fix that.\n\nhttps://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\n#FTMO #TradingTools",
    "Failed your FTMO challenge because you lost track of drawdown? Same. So I built a tracker.\n\nFree, no signup, works offline.\n\nhttps://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\n#PropTrading",
    "📊 FTMO Challenge Tracker\n\n🎯 Profit target • 🛑 Drawdown • 📅 Days • 📈 Chart\n\nFree: https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\nBot: @ArdTradingBot\n\n#FTMO #DayTrading",
    "Real-time FTMO tracking. 1-Step & 2-Step. No signup, no account, works offline.\n\nBuilt by a trader for traders. Free forever.\n\nhttps://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\n#PropTrading #Trading",
]


# ═══════════════════════════════════════════════════════════════════
#  POSTING ENGINE
# ═══════════════════════════════════════════════════════════════════

class PostTracker:
    """Tracks all posts made to avoid duplicates and enforce schedules."""

    def __init__(self):
        self.file_path = DATA_DIR / "post_history.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.file_path.exists():
            try:
                return json.loads(self.file_path.read_text())
            except:
                pass
        return {
            "total_posts": 0,
            "posts": [],
            "platforms": {},
            "last_post_time": None,
            "started": datetime.now().isoformat(),
        }

    def save(self):
        self.file_path.write_text(json.dumps(self.data, indent=2, default=str))

    def can_post(self, platform: str, cooldown_hours: int = 24) -> bool:
        """Check if enough time has passed since last post on this platform."""
        plat = self.data["platforms"].get(platform)
        if not plat or not plat.get("last_post"):
            return True
        last = datetime.fromisoformat(plat["last_post"])
        elapsed = datetime.now() - last
        return elapsed.total_seconds() >= cooldown_hours * 3600

    def log_post(self, platform: str, content: str, url: str = ""):
        """Record a post."""
        post = {
            "id": self.data["total_posts"] + 1,
            "platform": platform,
            "content": content[:200],
            "url": url,
            "time": datetime.now().isoformat(),
        }
        self.data["posts"].append(post)
        self.data["total_posts"] += 1
        self.data["last_post_time"] = datetime.now().isoformat()
        if platform not in self.data["platforms"]:
            self.data["platforms"][platform] = {"count": 0, "last_post": None}
        self.data["platforms"][platform]["count"] += 1
        self.data["platforms"][platform]["last_post"] = datetime.now().isoformat()
        self.save()
        return post

    def get_stats(self) -> dict:
        """Get posting statistics."""
        return {
            "total_posts": self.data["total_posts"],
            "platforms": self.data["platforms"],
            "last_post": self.data["last_post_time"],
            "started": self.data["started"],
            "recent": self.data["posts"][-10:],
        }

    def status(self):
        """Print status."""
        stats = self.get_stats()
        print(f"\n{'='*60}")
        print(f"  📢 MARKETING ENGINE STATUS")
        print(f"  Started: {stats['started'][:19]}")
        print(f"  Total posts: {stats['total_posts']}")
        print(f"  Last post: {stats['last_post'] or 'Never'}")
        print(f"{'='*60}")
        if stats['platforms']:
            print(f"\n  📍 Per Platform:")
            for plat, data in stats['platforms'].items():
                print(f"    {plat:15s}: {data['count']} posts (last: {data['last_post'][:19] if data['last_post'] else 'Never'})")
        if stats['recent']:
            print(f"\n  📋 Recent Posts:")
            for p in reversed(stats['recent'][-5:]):
                print(f"    {p['time'][:19]} | {p['platform']:10s} | {p['content'][:60]}")
        print()


# ═══════════════════════════════════════════════════════════════════
#  PLATFORM POSTERS
# ═══════════════════════════════════════════════════════════════════

def post_reddit(title: str, body: str, subreddit: str = "FTMO") -> Optional[str]:
    """
    Post to Reddit via API. Requires Reddit OAuth app credentials.
    Returns post URL on success, None on failure.

    To set up:
    1. Go to https://www.reddit.com/prefs/apps
    2. Create a "script" app
    3. Set these env vars:
       REDDIT_CLIENT_ID=your_client_id
       REDDIT_CLIENT_SECRET=your_client_secret
       REDDIT_USERNAME=your_username
       REDDIT_PASSWORD=your_password
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    if not all([client_id, client_secret, username, password]):
        logger.warning("⚠️ Reddit API credentials not configured. Use REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD")
        return None

    try:
        import requests

        # Authenticate
        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        headers = {"User-Agent": f"linux:FTMO-Marketing-Bot:v1.0 (by /u/{username})"}
        r = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers)
        if r.status_code != 200:
            logger.error(f"Reddit auth failed: {r.status_code} {r.text[:200]}")
            return None

        token = r.json()["access_token"]
        headers["Authorization"] = f"bearer {token}"

        # Submit post
        submit_data = {
            "title": title,
            "text": body,
            "sr": subreddit,
            "kind": "self",
        }
        r2 = requests.post("https://oauth.reddit.com/api/submit", data=submit_data, headers=headers)
        result = r2.json()

        if result.get("error"):
            logger.error(f"Reddit post failed: {result}")
            return None

        post_id = result.get("json", {}).get("data", {}).get("id", "")
        if post_id:
            url = f"https://reddit.com/r/{subreddit}/comments/{post_id}/"
            logger.info(f"✅ Reddit post live: {url}")
            return url
        else:
            logger.error(f"Reddit post failed - no ID: {result}")
            return None

    except ImportError:
        logger.warning("requests not installed. Install: pip3 install requests")
        return None
    except Exception as e:
        logger.error(f"Reddit post error: {e}")
        return None


def post_discord(message: str, webhook_url: Optional[str] = None) -> bool:
    """Post to Discord via webhook."""
    webhook = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        logger.warning("⚠️ DISCORD_WEBHOOK_URL not set. Skipping Discord post.")
        return False

    try:
        import requests
        data = {"content": message}
        r = requests.post(webhook, json=data)
        if r.status_code in (200, 204):
            logger.info("✅ Discord post successful")
            return True
        else:
            logger.error(f"Discord post failed: {r.status_code}")
            return False
    except Exception as e:
        logger.error(f"Discord post error: {e}")
        return False


def post_twitter(text: str) -> bool:
    """Post to Twitter/X via API. Requires Twitter API credentials."""
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        logger.warning("⚠️ Twitter API credentials not configured. Skipping.")
        return False

    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        resp = client.create_tweet(text=text)
        if resp.data:
            logger.info(f"✅ Tweet posted: {resp.data['id']}")
            return True
        return False
    except ImportError:
        logger.warning("tweepy not installed. Install: pip3 install tweepy")
        return False
    except Exception as e:
        logger.error(f"Twitter post error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
#  SCHEDULER
# ═══════════════════════════════════════════════════════════════════

class MarketingScheduler:
    """Schedules and executes marketing posts across platforms."""

    def __init__(self):
        self.tracker = PostTracker()
        self.load_config()

    def load_config(self):
        config_path = DATA_DIR / "schedule_config.json"
        if config_path.exists():
            try:
                self.config = json.loads(config_path.read_text())
            except:
                self.config = self._default_config()
        else:
            self.config = self._default_config()

    def _default_config(self) -> dict:
        return {
            "reddit": {
                "enabled": True,
                "subreddits": ["FTMO", "DayTrading", "Forex", "Trading"],
                "cooldown_hours": 72,
                "cooldown_same_subreddit": 168,  # 7 days per subreddit
            },
            "discord": {
                "enabled": True,
                "cooldown_hours": 24,
            },
            "twitter": {
                "enabled": False,  # Needs API keys
                "cooldown_hours": 12,
            },
            "schedule": {
                "reddit_days": ["monday", "wednesday", "friday"],
                "discord_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "best_hours": [9, 10, 11, 14, 15, 16, 19, 20],  # EST
            }
        }

    def run_reddit(self) -> bool:
        """Post to Reddit using a fresh template."""
        if not self.config["reddit"]["enabled"]:
            logger.info("Reddit posting disabled in config.")
            return False

        if not self.tracker.can_post("reddit", self.config["reddit"]["cooldown_hours"]):
            logger.info("Reddit cooldown active. Skipping.")
            return False

        title = random.choice(REDDIT_TITLES)
        body = random.choice(REDDIT_BODIES)
        subreddit = random.choice(self.config["reddit"]["subreddits"])

        url = post_reddit(title, body, subreddit)
        if url:
            self.tracker.log_post("reddit", title, url)
            return True
        return False

    def run_discord(self) -> bool:
        """Post to Discord."""
        if not self.config["discord"]["enabled"]:
            return False

        if not self.tracker.can_post("discord", self.config["discord"]["cooldown_hours"]):
            logger.info("Discord cooldown active. Skipping.")
            return False

        message = random.choice(DISCORD_MESSAGES)
        success = post_discord(message)
        if success:
            self.tracker.log_post("discord", message)
        return success

    def run_twitter(self) -> bool:
        """Post to Twitter."""
        if not self.config["twitter"]["enabled"]:
            return False

        if not self.tracker.can_post("twitter", self.config["twitter"]["cooldown_hours"]):
            return False

        text = random.choice(TWITTER_POSTS)
        success = post_twitter(text)
        if success:
            self.tracker.log_post("twitter", text)
        return success

    def run_all(self) -> dict:
        """Run all enabled platforms."""
        logger.info(f"\n{'='*60}")
        logger.info(f"  🚀 MARKETING ENGINE — RUNNING ALL PLATFORMS")
        logger.info(f"{'='*60}\n")

        results = {
            "reddit": self.run_reddit(),
            "discord": self.run_discord(),
            "twitter": self.run_twitter(),
            "timestamp": datetime.now().isoformat(),
        }

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"\n{'='*60}")
        logger.info(f"  📊 Results: {success_count}/3 posts made")
        logger.info(f"{'='*60}\n")

        return results

    def run_scheduled(self):
        """Check if we should post based on schedule and post if so."""
        now = datetime.now()
        today = now.strftime("%A").lower()
        hour = now.hour

        logger.info(f"Checking schedule: {today} @ {hour}:00")

        results = {}

        # Reddit: post only on specific days
        if today in self.config["schedule"]["reddit_days"] and hour in self.config["schedule"]["best_hours"]:
            results["reddit"] = self.run_reddit()

        # Discord: post on weekdays
        if today in self.config["schedule"]["discord_days"] and hour in self.config["schedule"]["best_hours"]:
            results["discord"] = self.run_discord()

        # Twitter: any day, any hour (if configured)
        if hour in [9, 12, 15, 18]:  # 4x daily
            results["twitter"] = self.run_twitter()

        if not results:
            logger.info("No platforms ready to post right now. Waiting for next scheduled slot.")

        return results


def setup_cron():
    """Set up cron jobs for automated marketing."""
    scheduler_path = Path(__file__).resolve()
    cron_lines = [
        "# FTMO Marketing Engine - Auto-generated",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "# Marketing engine - check every hour, post if scheduled",
        "0 * * * * cd /home/enishshah2 && python3 income/tools/marketing_engine.py --schedule >> /home/enishshah2/income/logs/cron_marketing.log 2>&1",
        "",
        "# Post to Reddit every 3 days (specific hours)",
        "0 9,15,20 * * 1,3,5 cd /home/enishshah2 && python3 income/tools/marketing_engine.py --reddit >> /home/enishshah2/income/logs/cron_marketing.log 2>&1",
        "",
        "# Post to Discord on weekdays",
        "0 10,16,21 * * 1-5 cd /home/enishshah2 && python3 income/tools/marketing_engine.py --discord >> /home/enishshah2/income/logs/cron_marketing.log 2>&1",
        "",
    ]

    cron_file = DATA_DIR / "cron_jobs.txt"
    cron_file.write_text("\n".join(cron_lines) + "\n")
    logger.info(f"✅ Cron jobs written to {cron_file}")
    logger.info("   Install: crontab " + str(cron_file))
    return cron_file


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    scheduler = MarketingScheduler()

    if len(sys.argv) < 2:
        print("""
🚀 MARKETING ENGINE — FTMO Tracker Promo

Commands:
  --run-all      Post to all enabled platforms now
  --reddit       Post to Reddit now
  --discord      Post to Discord now
  --twitter      Post to Twitter now
  --schedule     Check schedule and post if time
  --status       Show posting history
  --setup-cron   Generate cron job config
  --stats        Detailed stats

Usage: python3 marketing_engine.py <command>
        """)
        return

    cmd = sys.argv[1]

    if cmd == "--run-all":
        scheduler.run_all()

    elif cmd == "--reddit":
        scheduler.run_reddit()

    elif cmd == "--discord":
        scheduler.run_discord()

    elif cmd == "--twitter":
        scheduler.run_twitter()

    elif cmd == "--schedule":
        scheduler.run_scheduled()

    elif cmd == "--status":
        scheduler.tracker.status()

    elif cmd == "--setup-cron":
        setup_cron()

    elif cmd == "--stats":
        stats = scheduler.tracker.get_stats()
        print(json.dumps(stats, indent=2, default=str))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
