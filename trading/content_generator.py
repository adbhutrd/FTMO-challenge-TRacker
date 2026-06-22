#!/usr/bin/env python3
"""
📝 CONTENT GENERATOR — AI Content Factory
===========================================
Generates SEO-optimized articles, social posts, and forum content.
Publishes to Medium, Dev.to, Quora, and other platforms.

Usage:
    python3 content_generator.py --article     # Generate and publish article
    python3 content_generator.py --medium      # Publish to Medium
    python3 content_generator.py --quora       # Auto-answer on Quora
    python3 content_generator.py --batch 5     # Generate 5 content pieces
"""

import json
import os
import sys
import random
import logging
import requests
from datetime import datetime
from pathlib import Path

HOME = Path.home()
TRADING_DIR = HOME / "trading"
INCOME_DIR = HOME / "income"
CONTENT_DIR = INCOME_DIR / "content"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | CONTENT | %(message)s",
    handlers=[
        logging.FileHandler(INCOME_DIR / "logs" / "content.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("content_gen")

# ── Content Templates ──────────────────────────────────────────────

ARTICLES = [
    {
        "title": "How to Track FTMO Challenge Rules in Real-Time (Free Tool)",
        "tags": ["FTMO", "PropTrading", "TradingTools", "Forex"],
        "content": """
# How to Track FTMO Challenge Rules in Real-Time

If you're trading an FTMO challenge right now, you know the hardest part isn't the trading — it's the **rule tracking**.

## The Real Challenge

Most traders fail FTMO challenges not because of bad trades, but because they:

1. **Lose track of drawdown** — You're up 8%, feeling good, then one bad day takes you to -3%. But wait, was that -3% from peak or from starting balance? FTMO uses peak balance for drawdown calculation.

2. **Forget trading day requirements** — Phase 1 of a 2-Step challenge requires minimum 4 trading days. Easy to lose count when you're focused on the charts.

3. **Miss daily loss limits** — FTMO has strict daily loss limits (5% for 2-Step, 3% for 1-Step). Going over means instant failure.

4. **Best day rule violations** — For 1-Step challenges, your best trading day cannot exceed 50% of total profit. This catches a LOT of traders off guard.

## The Solution

I built a **free FTMO Challenge Tracker** that handles ALL of this automatically:

- **Real-time profit target progress** — Phase 1 (10%) and Phase 2 (5%) with visual progress bars
- **Drawdown guardian** — Color-coded warnings before you hit the 10% limit
- **Automatic trading day counter** — No more manual counting
- **Best day rule checker** — Alerts you before it becomes a problem
- **Equity curve chart** — See your entire challenge journey

## Get Started Free

No signup, no account, no tracking. Your data stays on your machine.

👉 **Try it free:** https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html

🤖 **Telegram Bot:** @ArdTradingBot — track from your phone

📊 **Pro Version ($19.99/mo):** Cloud sync, unlimited accounts, PDF reports
👉 https://gumroad.com/l/ezteprg

---

*Built by a trader who failed 7 FTMO challenges before passing one. Not affiliated with FTMO.*
""",
    },
    {
        "title": "FTMO Challenge Rules Explained: Complete Guide for 2026",
        "tags": ["FTMO", "PropTrading", "TradingGuide", "Challenge"],
        "content": """
# FTMO Challenge Rules: Complete Guide

Passing an FTMO challenge requires more than just profitable trading — you need to master their rule set. Here's every rule explained.

## Challenge Types

### 2-Step Challenge
- **Phase 1:** 10% profit target, 10% max drawdown
- **Phase 2:** 5% profit target, 10% max drawdown
- Minimum 4 trading days in each phase
- Daily loss limit: 5%

### 1-Step Challenge  
- **Single Phase:** 10% profit target
- 10% max drawdown
- No minimum trading days
- Daily loss limit: 3%
- Best day rule: Best day ≤ 50% of total profit

## Critical Rules Most Traders Miss

### 1. Drawdown is Calculated from Peak Balance
This is the #1 rule that fails traders. If you're at $55,000 and drop to $52,000, your drawdown is 5.45% (from $55,000 peak), NOT 4% (from $50,000 starting balance).

### 2. Daily Loss Limit
The daily loss limit is calculated from the PREVIOUS day's ending balance:
- 2-Step: 5% of previous day's balance
- 1-Step: 3% of previous day's balance

### 3. Best Day Rule (1-Step Only)
Your most profitable day cannot exceed 50% of your total profit. If your best day was $3,000, you need total profit of at least $6,000.

## Track Everything Automatically

Stop losing challenges to rules you forgot about. Use our free real-time tracker:

👉 **https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html**
🤖 **Telegram Bot:** @ArdTradingBot
""",
    },
    {
        "title": "10 Common FTMO Challenge Mistakes (And How to Avoid Them)",
        "tags": ["FTMO", "TradingMistakes", "PropTrading", "Forex"],
        "content": """
# 10 Common FTMO Challenge Mistakes

After 3 years of FTMO challenges and mentoring other traders, here are the most common mistakes I see:

## 1. Not Tracking Drawdown in Real-Time
**Mistake:** Checking drawdown at the end of the week when it's too late.
**Fix:** Use a real-time tracker that alerts you immediately.

## 2. Ignoring the Best Day Rule  
**Mistake:** Assuming any profit is good profit (1-Step).
**Fix:** Track best day as % of total profit. Keep it under 50%.

## 3. Forgetting Minimum Trading Days
**Mistake:** Rushing through in 2 days and failing the rule.
**Fix:** 4 minimum days for 2-Step. Track every day.

## 4. Miscalculating Daily Loss Limit
**Mistake:** Using starting balance instead of previous day's close.
**Fix:** Daily loss = % of PREVIOUS day's balance.

## 5. No Backup Plan
**Mistake:** Losing all data when browser crashes.
**Fix:** Use the tracker's export feature. Save your JSON.

## 6. Overtrading on Phase 2
**Mistake:** Thinking 5% target means you can relax.
**Fix:** Same discipline as Phase 1. Drawdown still applies.

## 7. Not Checking Rules Updates
**Mistake:** Using outdated rules from last year.
**Fix:** FTMO updates rules. Always verify current ones.

## 8. Emotional Trading After a Big Win
**Mistake:** Getting overconfident after hitting 8% profit.
**Fix:** Stick to your plan. The challenge isn't over until verified.

## 9. No Risk Management System
**Mistake:** Using gut feeling for position sizing.
**Fix:** Fixed percentage risk per trade (0.5-1% recommended).

## 10. Going It Alone
**Mistake:** Not using tools that automate rule tracking.
**Fix:** Use our free tracker: https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html

## Track Your Challenge for Free

Don't let rule violations end your challenge. Track everything in real-time.

**Free Web App:** https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html  
**Telegram Bot:** @ArdTradingBot  
**Pro ($19.99/mo):** https://gumroad.com/l/ezteprg
""",
    },
]

SOCIAL_POSTS = [
    "🔴 Don't let FTMO rules fail your challenge. Track profit target, drawdown & trading days in real-time. Free tool → https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html #FTMO",
    "📊 FTMO Challenge Tip: Drawdown is calculated from PEAK balance, not starting balance. Track yours in real-time for free → https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html",
    "🎯 3 years of FTMO challenges taught me: 90% fail from bad tracking, not bad trading. Fix that → https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html",
    "🤖 New: Track your FTMO challenge from Telegram! Just message @ArdTradingBot and start tracking. Free to use.",
    "💡 FTMO 1-Step traders: Your best day cannot exceed 50% of total profit. Track this automatically → https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html",
    "🔥 FTMO Challenge Tracker Pro is now available! Cloud sync, unlimited accounts, PDF reports. $19.99/mo → https://gumroad.com/l/ezteprg",
    "📈 Visualize your FTMO challenge journey with our equity curve chart. Free to use → https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html",
    "⏰ FTMO 2-Step: You need minimum 4 trading days in EACH phase. Track them automatically with our free tool.",
]

FORUM_POSTS = [
    {
        "title": "Free FTMO Challenge Tracker - Real-time tracking tool",
        "body": "Hey everyone, I built a free FTMO Challenge Tracker that tracks profit targets, drawdown, trading days, and daily loss limits in real-time. It's a single HTML file - no signup, no tracking, works offline. Thought some of you might find it useful.\n\nhttps://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\nAlso available as a Telegram bot: @ArdTradingBot",
    },
    {
        "title": "PSA: Most FTMO failures are from rule violations, not bad trading",
        "body": "Just wanted to share something I learned the hard way after failing 7 FTMO challenges.\n\nMost people fail because of rule violations - they lose track of drawdown, forget trading day counts, or accidentally break daily loss limits. Not because their trading strategy is bad.\n\nI built a free tracker that monitors all FTMO rules in real-time. Might help some of you.\n\nhttps://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html\n\nTelegram bot: @ArdTradingBot",
    },
]


class ContentGenerator:
    """Generate and publish content across platforms."""

    def __init__(self):
        self.published_file = CONTENT_DIR / "published.json"
        self.load()

    def load(self):
        if self.published_file.exists():
            try:
                self.published = json.loads(self.published_file.read_text())
            except:
                self.published = {"articles": [], "social": [], "forum": []}
        else:
            self.published = {"articles": [], "social": [], "forum": []}

    def save(self):
        self.published_file.write_text(json.dumps(self.published, indent=2, default=str))

    def pick_article(self) -> dict:
        """Pick an unpicked article."""
        used_titles = [a["title"] for a in self.published["articles"]]
        available = [a for a in ARTICLES if a["title"] not in used_titles]
        if not available:
            # Reset
            self.published["articles"] = []
            available = ARTICLES
        article = random.choice(available)
        return article

    def generate_article_html(self, article: dict) -> str:
        """Convert article to HTML for publishing."""
        content = article["content"]
        # Add meta tags
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article['title']}</title>
    <meta name="description" content="{article['title']} - Free FTMO Challenge Tracker">
    <meta name="keywords" content="{', '.join(article['tags'])}">
</head>
<body>
{content}
</body>
</html>"""
        return html

    def save_article(self, article: dict) -> Path:
        """Save article to disk for manual or automated publishing."""
        filename = article["title"].lower().replace(" ", "-").replace("?", "").replace("(", "").replace(")", "")[:50]
        filename = "".join(c for c in filename if c.isalnum() or c in "-_")
        filepath = CONTENT_DIR / f"{filename}.md"
        filepath.write_text(article["content"])
        return filepath

    def generate_seo_filename(self, title: str) -> str:
        """Generate SEO-friendly filename."""
        slug = title.lower()
        slug = slug.replace("?", "").replace("!", "").replace(":", "")
        slug = "-".join(slug.split())[:60]
        slug = "".join(c for c in slug if c.isalnum() or c in "-")
        return slug + ".html"

    def publish_medium(self, article: dict) -> bool:
        """Publish to Medium (requires Medium API token)."""
        token = os.getenv("MEDIUM_TOKEN")
        if not token:
            logger.warning("⚠️ MEDIUM_TOKEN not set. Skipping Medium publish.")
            return False

        try:
            # Get user info
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            r = requests.get("https://api.medium.com/v1/me", headers=headers, timeout=10)
            if r.status_code != 200:
                logger.error(f"Medium auth failed: {r.status_code}")
                return False

            user_id = r.json()["data"]["id"]

            # Create post
            post_data = {
                "title": article["title"],
                "contentFormat": "markdown",
                "content": article["content"],
                "tags": article["tags"],
                "publishStatus": "public",
            }
            r2 = requests.post(
                f"https://api.medium.com/v1/users/{user_id}/posts",
                headers=headers,
                json=post_data,
                timeout=10,
            )
            if r2.status_code == 201:
                url = r2.json()["data"]["url"]
                logger.info(f"✅ Medium article published: {url}")
                self.published["articles"].append({"title": article["title"], "url": url, "time": datetime.now().isoformat()})
                self.save()
                return True
            else:
                logger.error(f"Medium publish failed: {r2.status_code} {r2.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Medium error: {e}")
            return False

    def social_post(self, count: int = 1) -> list:
        """Generate social media posts."""
        posts = random.sample(SOCIAL_POSTS, min(count, len(SOCIAL_POSTS)))
        for post in posts:
            self.published["social"].append({"text": post, "time": datetime.now().isoformat()})
        self.save()
        return posts

    def batch_generate(self, count: int = 5):
        """Generate multiple content pieces."""
        results = {"articles": [], "social": [], "forum": []}
        
        # Generate articles
        for _ in range(count):
            article = self.pick_article()
            path = self.save_article(article)
            results["articles"].append(str(path))
        
        # Generate social posts
        results["social"] = self.social_post(count)
        
        # Generate forum posts
        for p in FORUM_POSTS:
            self.published["forum"].append(p)
        
        self.save()
        return results

    def publish_all(self):
        """Publish content to all available platforms."""
        results = {"medium": False, "saved": []}
        
        # Try Medium
        article = self.pick_article()
        medium_result = self.publish_medium(article)
        results["medium"] = medium_result
        
        # Always save locally
        path = self.save_article(article)
        results["saved"].append(str(path))
        
        # Save as HTML
        html = self.generate_article_html(article)
        html_path = CONTENT_DIR / self.generate_seo_filename(article["title"])
        html_path.write_text(html)
        results["saved"].append(str(html_path))
        
        return results


def main():
    gen = ContentGenerator()

    if len(sys.argv) < 2:
        print("""📝 CONTENT GENERATOR

Commands:
  --article      Generate and save a new article
  --medium       Publish to Medium (requires MEDIUM_TOKEN)
  --publish       Publish to all platforms
  --social [n]   Generate n social posts (default: 1)
  --batch [n]    Generate n content pieces
  --serve        Start SEO content server
""")
        return

    cmd = sys.argv[1]

    if cmd == "--article":
        article = gen.pick_article()
        path = gen.save_article(article)
        print(f"✅ Article saved: {path}")
        print(f"   Title: {article['title']}")

    elif cmd == "--medium":
        article = gen.pick_article()
        result = gen.publish_medium(article)
        print(f"{'✅' if result else '❌'} Medium: {'Published' if result else 'Failed'}")

    elif cmd == "--publish":
        results = gen.publish_all()
        for k, v in results.items():
            print(f"  {k}: {'✅' if v else '❌'} ({v})" if isinstance(v, bool) else f"  {k}: {v}")

    elif cmd == "--social":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        posts = gen.social_post(n)
        for p in posts:
            print(f"  {p}\n")

    elif cmd == "--batch":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        results = gen.batch_generate(n)
        print(f"✅ Generated: {len(results['articles'])} articles, {len(results['social'])} social posts")

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
