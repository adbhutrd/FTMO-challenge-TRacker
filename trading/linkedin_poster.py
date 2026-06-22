#!/usr/bin/env python3
"""
💼 LINKEDIN POSTER — Automated Social Traffic
==============================================
Uses Playwright to post on LinkedIn.
LinkedIn is accessible from this server.

Usage:
    python3 linkedin_poster.py --post       # Post next scheduled content
    python3 linkedin_poster.py --schedule   # Generate scheduled posts
    python3 linkedin_poster.py --status     # Show posting stats
"""

import json
import os
import sys
import logging
import random
import subprocess
from datetime import datetime
from pathlib import Path

HOME = Path.home()
TRADING_DIR = HOME / "trading"
LOG_DIR = HOME / "income" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | LINKEDIN | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "linkedin_poster.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("linkedin_poster")

TRACKER_URL = "https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html"
GUMROAD_URL = "https://gumroad.com/l/ezteprg"

SOCIAL_POSTS = [
    # LinkedIn-friendly posts (professional tone)
    {
        "content": f"📊 FTMO Challenge Tracker — Free Tool\n\nMost FTMO challenges fail because of rule violations, not bad trading. I built a free tracker that monitors:\n\n✅ Real-time profit target progress\n✅ Drawdown calculation from peak balance\n✅ Daily loss limits\n✅ Minimum trading days\n✅ Best day rule (1-Step)\n\nNo signup, no account, works offline.\n\nTry it: {TRACKER_URL}\n\n#FTMO #PropTrading #DayTrading #TradingTools",
        "tags": ["FTMO", "PropTrading"],
        "posted": False,
    },
    {
        "content": f"📈 The #1 reason FTMO traders fail their challenge\n\nIt's not bad trading. It's bad TRACKING.\n\nThe #1 mistake: calculating drawdown from starting balance instead of peak balance.\n\nExample:\nStart: $50,000\nPeak: $55,000\nCurrent: $51,500\n\n❌ Wrong: (51,500 - 50,000) / 50,000 = 3% drawdown\n✅ Correct: (55,000 - 51,500) / 55,000 = 6.4% drawdown\n\nThat 3.4% difference can fail your challenge.\n\nUse a tracker that calculates this automatically.\n\nFree tool: {TRACKER_URL}\n\n#FTMO #RiskManagement #Trading",
        "tags": ["FTMO", "RiskManagement"],
        "posted": False,
    },
    {
        "content": f"🚀 I'm giving away this FTMO Challenge Tracker for FREE\n\nAfter failing my first challenge because I lost track of drawdown, I built this:\n\n• Real-time profit target (10% Phase 1, 5% Phase 2)\n• Drawdown warnings at 50%, 80%, and 100%\n• Equity curve chart\n• Trade log with export/import\n• Telegram bot (@ArdTradingBot)\n\nNo strings attached. No email required. Just open and use.\n\n{TRACKER_URL}\n\nPro version with cloud sync: {GUMROAD_URL}\n\n#FTMO #TradingCommunity #FreeTools",
        "tags": ["FTMO", "FreeTools"],
        "posted": False,
    },
    {
        "content": f"💡 FTMO Challenge Tip: Track Drawdown from DAY ONE\n\nHere's what most traders don't realize:\n\nYour max drawdown limit is 10% of your PEAK balance. Not your starting balance.\n\nSo if you hit $52,000 early (up 4%) and drop back to $50,000:\n• Perceived drawdown: 0% (you're at start)\n• ACTUAL drawdown: 3.85% (from $52k peak)\n\nTrack it from day one with our free tool:\n{TRACKER_URL}\n\n#FTMO #TradingTips #PropFirms",
        "tags": ["FTMO", "TradingTips"],
        "posted": False,
    },
    {
        "content": f"🤖 FTMO Challenge Tracker now has a Telegram Bot!\n\nTrack your entire challenge from your phone:\n• Add trading days\n• Check profit target progress\n• View drawdown status\n• Generate equity charts\n• Check phase status\n\nBot: @ArdTradingBot\nCommands: /help to get started\n\nWeb tracker (free, no signup):\n{TRACKER_URL}\n\nBuilt by a trader, for traders.\n\n#FTMO #TelegramBot #TradingTools",
        "tags": ["FTMO", "Telegram"],
        "posted": False,
    },
]

POSTS_FILE = TRADING_DIR / "linkedin_posts.json"


class LinkedInPoster:
    def __init__(self):
        self.posts = SOCIAL_POSTS.copy()
        self.stats_file = TRADING_DIR / "linkedin_stats.json"
        self.load()

    def load(self):
        if self.stats_file.exists():
            try:
                self.stats = json.loads(self.stats_file.read_text())
            except:
                self.stats = self._default_stats()
        else:
            self.stats = self._default_stats()

    def _default_stats(self) -> dict:
        return {
            "total_posted": 0,
            "last_posted": None,
            "posts": [],
            "started": datetime.now().isoformat(),
        }

    def save(self):
        self.stats["last_updated"] = datetime.now().isoformat()
        self.stats_file.write_text(json.dumps(self.stats, indent=2))

    def log_post(self, content: str, success: bool):
        self.stats["posts"].append({
            "content_preview": content[:80],
            "success": success,
            "timestamp": datetime.now().isoformat(),
        })
        if success:
            self.stats["total_posted"] += 1
            self.stats["last_posted"] = datetime.now().isoformat()
        self.save()

    def post_to_linkedin(self, content: str) -> bool:
        """Post to LinkedIn using Playwright browser automation."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed")
            return False

        logger.info("📱 Opening LinkedIn...")
        success = False
        
        try:
            with sync_playwright() as p:
                # Use system chromium with existing profile
                browser = p.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ]
                )
                
                # Try to load LinkedIn cookies
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    storage_state=str(TRADING_DIR / "linkedin_auth.json") if (TRADING_DIR / "linkedin_auth.json").exists() else None
                )
                page = context.new_page()
                
                # Go to LinkedIn feed directly
                page.goto("https://www.linkedin.com/feed/", timeout=30000)
                page.wait_for_timeout(3000)
                logger.info(f"LinkedIn URL: {page.url}")
                
                # Check if actually logged in (feed page, NOT login page)
                is_logged_in = "feed" in page.url.lower() and "login" not in page.url.lower()
                if is_logged_in:
                    logger.info("✅ Logged in to LinkedIn!")
                    page.screenshot(path=TRADING_DIR / "linkedin_feed.png")
                    
                    # Save cookies for next time
                    try:
                        context.storage_state(path=str(TRADING_DIR / "linkedin_auth.json"))
                        logger.info("✅ Saved LinkedIn auth state")
                    except:
                        pass
                    
                    # Click "Start a post"
                    start_post = page.query_selector('[aria-label*="Start a post"], [role="textbox"], .share-box__open')
                    if start_post:
                        start_post.click()
                        page.wait_for_timeout(2000)
                        
                        # Type content into the post editor
                        editor = page.query_selector('[role="textbox"][aria-label*="post"], .ql-editor, [data-placeholder*="What do you want"]')
                        if editor:
                            editor.fill(content[:3000])
                            page.wait_for_timeout(1000)
                            
                            # Click Post button
                            post_btn = page.query_selector('button:has-text("Post")')
                            if post_btn:
                                post_btn.click()
                                page.wait_for_timeout(3000)
                                logger.info("✅ Post submitted!")
                                success = True
                            else:
                                logger.info("Post button not found after filling content")
                                # Fallback: try keyboard shortcut
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(3000)
                                # Check if dialog closed
                                dialog_gone = not page.query_selector('[role="textbox"][aria-label*="post"]')
                                success = dialog_gone
                        else:
                            logger.info("Post editor not found")
                            # Fallback: try clicking the post box directly
                            alt_editor = page.query_selector('[contenteditable="true"]')
                            if alt_editor:
                                alt_editor.click()
                                page.keyboard.type(content[:3000], delay=20)
                                page.wait_for_timeout(1000)
                                page.keyboard.press("Control+Enter")
                                page.wait_for_timeout(2000)
                                logger.info("✅ Posted via fallback keyboard method")
                                success = True
                    else:
                        logger.info("Start post button not found — trying direct feed interaction")
                        page.screenshot(path=TRADING_DIR / "linkedin_feed_state.png")
                else:
                    logger.info("ℹ️ LinkedIn needs initial login — run once with:")
                    logger.info("   cd ~ &&                                   playwright open chromium https://linkedin.com")
                    logger.info("   Then save cookies with: --save-linkedin-cookies")
                    page.screenshot(path=TRADING_DIR / "linkedin_login_required.png")
                
                browser.close()
                
        except Exception as e:
            logger.error(f"LinkedIn error: {e}")
        
        return success

    def post_next(self) -> bool:
        """Post the next unscheduled post."""
        for post in self.posts:
            if not post.get("posted", False):
                logger.info(f"📤 Posting: {post['content'][:60]}...")
                result = self.post_to_linkedin(post["content"])
                post["posted"] = result
                self.log_post(post["content"], result)
                if result:
                    logger.info("✅ Posted successfully")
                else:
                    logger.info("❌ Post failed")
                return result
        
        logger.info("📋 All posts have been used. Generate new ones with --schedule")
        return False

    def print_status(self):
        print(f"\n{'='*50}")
        print(f"  💼 LINKEDIN POSTER STATUS")
        print(f"{'='*50}")
        print(f"  Total posted:   {self.stats['total_posted']}")
        print(f"  Last posted:    {self.stats.get('last_posted', 'Never')}")
        print(f"  Remaining:      {sum(1 for p in self.posts if not p.get('posted', False))}")
        print(f"  Total posts:    {len(self.posts)}")
        print()


def main():
    poster = LinkedInPoster()

    if len(sys.argv) < 2:
        print("""💼 LINKEDIN POSTER — Automated Social Traffic

Commands:
  --post           Post the next scheduled content
  --status         Show posting status
""")
        return

    cmd = sys.argv[1]

    if cmd == "--post":
        poster.post_next()

    elif cmd == "--status":
        poster.print_status()

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
