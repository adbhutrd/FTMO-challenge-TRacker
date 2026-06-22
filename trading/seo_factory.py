#!/usr/bin/env python3
"""
📈 SEO FACTORY — Automated Content Empire
===========================================
Generates SEO-optimized HTML pages targeting FTMO keywords.
Deploys to web server. Updates sitemap automatically.
Runs completely autonomously — no external accounts needed.

Usage:
    python3 seo_factory.py --generate 5    # Generate 5 new pages
    python3 seo_factory.py --deploy         # Deploy to web server
    python3 seo_factory.py --all            # Generate + deploy
    python3 seo_factory.py --status         # Show content stats
"""

import json
import os
import sys
import random
import shutil
import logging
from datetime import datetime
from pathlib import Path

HOME = Path.home()
TRADING_DIR = HOME / "trading"
DEPLOY_DIR = HOME / "deploy_assets"
SEO_DIR = TRADING_DIR / "seo_content"
SEO_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = HOME / "income" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | SEO | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "seo_factory.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("seo_factory")

LIVE_URL_FILE = HOME / "LIVE_URL.txt"

def get_base_url() -> str:
    """Get the current live URL from LIVE_URL.txt, with fallback."""
    try:
        if LIVE_URL_FILE.exists():
            content = LIVE_URL_FILE.read_text().strip()
            for line in content.split("\n"):
                if "live" in line.lower() or "http" in line:
                    url = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                    if url.startswith("http"):
                        return url.rstrip("/")
    except:
        pass
    return "https://ftmo-tracker.loca.lt"

BASE_URL = get_base_url()
TRACKER_URL = f"{BASE_URL}/ftmo_challenge_tracker.html"
SELL_URL = f"{BASE_URL}/sell.html"
GUMROAD_URL = "https://gumroad.com/l/ezteprg"

STYLES = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; color: #1a1a2e; background: #fafafa; }
    h1 { font-size: 2em; color: #1a1a2e; margin-bottom: 20px; border-bottom: 3px solid #7c3aed; padding-bottom: 10px; }
    h2 { font-size: 1.5em; color: #1a1a2e; margin: 30px 0 15px; }
    h3 { font-size: 1.2em; color: #374151; margin: 20px 0 10px; }
    p { margin: 15px 0; color: #4b5563; }
    ul, ol { margin: 15px 0; padding-left: 25px; color: #4b5563; }
    li { margin: 8px 0; }
    .cta-box { background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; padding: 30px; border-radius: 16px; text-align: center; margin: 40px 0; }
    .cta-box h2 { color: white; margin-top: 0; border: none; }
    .cta-box p { color: rgba(255,255,255,0.9); }
    .cta-button { display: inline-block; background: white; color: #7c3aed; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 18px; margin: 15px 0; transition: transform 0.2s; }
    .cta-button:hover { transform: scale(1.05); }
    .cta-small { color: rgba(255,255,255,0.7); font-size: 14px; margin-top: 10px; }
    .cta-small a { color: white; text-decoration: underline; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    th { background: #7c3aed; color: white; padding: 12px 15px; text-align: left; }
    td { padding: 12px 15px; border-bottom: 1px solid #e5e7eb; }
    tr:last-child td { border-bottom: none; }
    tr:nth-child(even) { background: #f9fafb; }
    .tip { background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px 20px; margin: 20px 0; border-radius: 4px; }
    .warning { background: #fef2f2; border-left: 4px solid #ef4444; padding: 15px 20px; margin: 20px 0; border-radius: 4px; }
    .info { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px 20px; margin: 20px 0; border-radius: 4px; }
    nav { background: #1a1a2e; padding: 15px 20px; border-radius: 8px; margin-bottom: 30px; display: flex; gap: 20px; flex-wrap: wrap; }
    nav a { color: white; text-decoration: none; font-size: 14px; }
    nav a:hover { text-decoration: underline; }
    .faq { margin: 20px 0; }
    .faq-question { background: white; padding: 15px 20px; border-radius: 8px; margin: 10px 0; cursor: pointer; font-weight: bold; border: 1px solid #e5e7eb; }
    .faq-answer { padding: 0 20px 15px; color: #6b7280; display: none; }
    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #9ca3af; text-align: center; }
    @media (max-width: 600px) { body { padding: 15px; } h1 { font-size: 1.5em; } }
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.faq-question').forEach(function(q) {
        q.addEventListener('click', function() {
            var answer = this.nextElementSibling;
            answer.style.display = answer.style.display === 'block' ? 'none' : 'block';
        });
    });
});
</script>
"""

NAV = """
<nav>
    <a href="/ftmo_challenge_tracker.html">📊 Tracker</a>
    <a href="/sell.html">💰 Pro Version</a>
    <a href="/seo/index.html">📚 Guides</a>
    <a href="https://t.me/ArdTradingBot">🤖 Telegram Bot</a>
</nav>
"""

FOOTER = """
<div class="footer">
    <p>FTMO Challenge Tracker — Free real-time tracking tool for prop firm challenges.</p>
    <p>Not affiliated with FTMO.com | <a href="/ftmo_challenge_tracker.html">Tracker</a> | <a href="https://gumroad.com/l/ezteprg">Pro</a> | <a href="https://t.me/ArdTradingBot">Telegram</a></p>
    <p style="margin-top:5px">© 2026 FTMO Tracker — Built by traders for traders</p>
</div>
"""

def get_cta_box() -> str:
    """Build CTA box with current URLs."""
    return f"""
<div class="cta-box">
    <h2>📊 Track Your FTMO Challenge For Free</h2>
    <p>Real-time profit targets, drawdown monitoring, daily loss limits, and equity curves. No signup needed.</p>
    <a href="{TRACKER_URL}" class="cta-button">🚀 Try the Free Tracker</a>
    <p class="cta-small">Also available on Telegram: <a href="https://t.me/ArdTradingBot">@ArdTradingBot</a> &bull; Pro: <a href="{GUMROAD_URL}">$19.99/mo</a></p>
</div>"""

# ── SEO CONTENT DATABASE ──────────────────────────────────────────

PAGES = [
    {
        "slug": "common-ftmo-challenge-mistakes",
        "title": "10 Common FTMO Challenge Mistakes That Cost Traders Their Fees",
        "description": "Learn the 10 most common FTMO challenge mistakes. Avoid these errors to save your challenge fee and pass on your first attempt.",
        "keywords": "FTMO mistakes, FTMO challenge mistakes, FTMO failure reasons, FTMO common errors",
        "content": """
<h1>10 Common FTMO Challenge Mistakes That Cost Traders Their Fees</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-1-step-vs-2-step",
        "title": "FTMO 1-Step vs 2-Step Challenge — Which One Should You Choose?",
        "description": "Compare FTMO 1-Step and 2-Step challenges. Learn the pros and cons of each, and which one is right for your trading style.",
        "keywords": "FTMO 1-Step vs 2-Step, FTMO challenge comparison, which FTMO challenge",
        "content": """
<h1>FTMO 1-Step vs 2-Step Challenge — Which One Should You Choose?</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-50k-vs-100k-account",
        "title": "FTMO $50k vs $100k Account — Which Challenge Should You Take?",
        "description": "Compare FTMO $50k and $100k challenges. See the fees, profit targets, and which account size is best for your trading style.",
        "keywords": "FTMO 50k vs 100k, FTMO 50k challenge, FTMO 100k challenge, FTMO account comparison",
        "content": """
<h1>FTMO $50k vs $100k Account — Which Challenge Should You Take?</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-account-sizes",
        "title": "FTMO Account Sizes — Compare $10k, $25k, $50k, $100k, $200k Challenges",
        "description": "Compare FTMO account sizes from $10,000 to $200,000. See profit targets, drawdown limits, and fee structures for each account size.",
        "keywords": "FTMO account sizes, FTMO 50k, FTMO 100k, FTMO 200k, FTMO pricing",
        "content": """
<h1>FTMO Account Sizes — Compare $10k, $25k, $50k, $100k, $200k Challenges</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-best-day-rule",
        "title": "FTMO Best Day Rule — What It Is and How to Avoid Violating It (1-Step)",
        "description": "Complete guide to the FTMO best day rule (1-Step only). Learn how it works, why it catches traders off guard, and how to track it automatically.",
        "keywords": "FTMO best day rule, FTMO 50% rule, FTMO 1-step rule, best day 50%",
        "content": """
<h1>FTMO Best Day Rule — What It Is and How to Avoid Violating It (1-Step)</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-challenge-50k-example",
        "title": "FTMO $50k Challenge Example — Complete Walkthrough from Start to Funded",
        "description": "Follow a complete FTMO $50k challenge example. See how a trader navigates Phase 1, Phase 2, and gets funded step by step.",
        "keywords": "FTMO 50k example, FTMO challenge walkthrough, FTMO 50k funded, FTMO example trade",
        "content": """
<h1>FTMO $50k Challenge Example — Complete Walkthrough from Start to Funded</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-challenge-calculator",
        "title": "FTMO Challenge Calculator — Free Tool to Calculate Profit Targets, Drawdown & Daily Limits",
        "description": "Free FTMO challenge calculator. Calculate profit targets, drawdown limits, and daily loss limits for any account size and challenge type.",
        "keywords": "FTMO challenge calculator, FTMO calculator, FTMO profit calculator, FTMO drawdown calculator free",
        "content": """
<h1>FTMO Challenge Calculator — Free Tool to Calculate Profit Targets, Drawdown & Daily Limits</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-challenge-fees-explained",
        "title": "FTMO Challenge Fees — How Much Does an FTMO Challenge Cost? Full Breakdown 2026",
        "description": "Complete breakdown of FTMO challenge fees. See costs for each account size from $10k to $200k, profit splits, and hidden costs.",
        "keywords": "FTMO cost, FTMO fees, FTMO challenge fee, how much is FTMO, FTMO pricing",
        "content": """
<h1>FTMO Challenge Fees — How Much Does an FTMO Challenge Cost? Full Breakdown 2026</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-challenge-for-beginners",
        "title": "FTMO Challenge for Beginners — Step-by-Step Guide to Getting Funded",
        "description": "Complete step-by-step guide for beginners taking their first FTMO challenge. From choosing an account size to getting funded.",
        "keywords": "FTMO for beginners, FTMO challenge beginner, first FTMO challenge, FTMO step by step, beginner prop trading",
        "content": """
<h1>FTMO Challenge for Beginners — Step-by-Step Guide to Getting Funded</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-challenge-rules-complete-guide",
        "title": "FTMO Challenge Rules: Complete Guide 2026 — Profit Targets, Drawdown & Daily Loss Limits",
        "description": "Complete guide to FTMO challenge rules. Learn about profit targets, drawdown calculations, daily loss limits, best day rule, and minimum trading days.",
        "keywords": "FTMO rules, FTMO challenge rules, FTMO profit target, FTMO drawdown, FTMO daily loss limit",
        "content": """
<h1>FTMO Challenge Rules: Complete Guide 2026 — Profit Targets, Drawdown & Daily Loss Limits</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-daily-loss-limit",
        "title": "FTMO Daily Loss Limit — Complete Guide (5% for 2-Step, 3% for 1-Step)",
        "description": "Complete guide to FTMO daily loss limits. Learn how the 5% (2-Step) and 3% (1-Step) daily loss limits work and how to track them.",
        "keywords": "FTMO daily loss, FTMO daily loss limit, 5% daily loss, 3% daily loss",
        "content": """
<h1>FTMO Daily Loss Limit — Complete Guide (5% for 2-Step, 3% for 1-Step)</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-drawdown-calculator",
        "title": "FTMO Drawdown Calculator — Calculate Drawdown Correctly from Peak Balance",
        "description": "Free FTMO drawdown calculator. Learn how FTMO calculates drawdown from peak balance, not starting balance. Includes examples and tracking tools.",
        "keywords": "FTMO drawdown, FTMO drawdown calculator, peak drawdown, FTMO max drawdown",
        "content": """
<h1>FTMO Drawdown Calculator — Calculate Drawdown Correctly from Peak Balance</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-free-trial-discount",
        "title": "FTMO Free Trial and Discount Codes — Is There an FTMO Promo Code in 2026?",
        "description": "Find out if FTMO offers free trials, discount codes, or promo codes in 2026. Learn how to save on your FTMO challenge fee.",
        "keywords": "FTMO free trial, FTMO discount, FTMO promo code, FTMO coupon, FTMO free challenge",
        "content": """
<h1>FTMO Free Trial and Discount Codes — Is There an FTMO Promo Code in 2026?</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-funded-account-management",
        "title": "FTMO Funded Account Management — How to Trade and Withdraw After Passing",
        "description": "Learn how to manage your FTMO funded account after passing. Includes withdrawal procedures, profit splits, and account maintenance tips.",
        "keywords": "FTMO funded account, FTMO withdrawal, FTMO profit withdrawal, FTMO account management, FTMO payout",
        "content": """
<h1>FTMO Funded Account Management — How to Trade and Withdraw After Passing</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-max-drawdown-explained",
        "title": "FTMO Max Drawdown Explained — Complete Guide with Examples & Calculator",
        "description": "Everything about FTMO max drawdown. Learn how the 10% drawdown limit works, with examples, common mistakes, and a free tracking tool.",
        "keywords": "FTMO max drawdown, FTMO 10% drawdown, FTMO drawdown limit, FTMO how drawdown works",
        "content": """
<h1>FTMO Max Drawdown Explained — Complete Guide with Examples & Calculator</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-phase-1-vs-phase-2",
        "title": "FTMO Phase 1 vs Phase 2 — What Changes After You Pass Phase 1",
        "description": "Understand the differences between FTMO Phase 1 (10% target) and Phase 2 (5% target). Learn what changes and what stays the same.",
        "keywords": "FTMO Phase 1, FTMO Phase 2, FTMO 2-step, FTMO promotion",
        "content": """
<h1>FTMO Phase 1 vs Phase 2 — What Changes After You Pass Phase 1</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-profit-split-explained",
        "title": "FTMO Profit Split Explained — How Much Do You Keep? 80% vs 90% Split",
        "description": "FTMO profit split explained. Learn how the 80-90% profit split works, how to qualify for 90%, and how to calculate your earnings.",
        "keywords": "FTMO profit split, FTMO 80%, FTMO 90%, FTMO payout, FTMO how much you keep",
        "content": """
<h1>FTMO Profit Split Explained — How Much Do You Keep? 80% vs 90% Split</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-profit-target",
        "title": "FTMO Profit Target — How to Track Phase 1 (10%) and Phase 2 (5%) Progress",
        "description": "Learn how FTMO profit targets work. Phase 1 requires 10% profit, Phase 2 requires 5%. Track your progress in real-time with our free tool.",
        "keywords": "FTMO profit target, FTMO 10%, FTMO phase 2, 5% profit target",
        "content": """
<h1>FTMO Profit Target — How to Track Phase 1 (10%) and Phase 2 (5%) Progress</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-prohibited-strategies",
        "title": "FTMO Prohibited Trading Strategies — What's NOT Allowed and How to Avoid Getting Banned",
        "description": "Complete list of FTMO prohibited trading strategies. Learn what strategies are banned, why, and how to avoid getting flagged.",
        "keywords": "FTMO prohibited strategies, FTMO banned strategies, FTMO rules violation, FTMO banned trading",
        "content": """
<h1>FTMO Prohibited Trading Strategies — What's NOT Allowed and How to Avoid Getting Banned</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-risk-management",
        "title": "FTMO Risk Management — Position Sizing, Stop Losses & Daily Limits",
        "description": "Master FTMO risk management. Learn position sizing, stop loss placement, and how to manage daily loss limits to pass your challenge.",
        "keywords": "FTMO risk management, FTMO position sizing, FTMO stop loss, FTMO risk",
        "content": """
<h1>FTMO Risk Management — Position Sizing, Stop Losses & Daily Limits</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-rules-cheat-sheet",
        "title": "FTMO Rules Cheat Sheet — Quick Reference Guide for Every Rule",
        "description": "Printable FTMO rules cheat sheet. Quick reference for profit targets, drawdown limits, daily loss limits, and best day rule for all challenge types.",
        "keywords": "FTMO cheat sheet, FTMO rules reference, FTMO quick guide, printable FTMO rules",
        "content": """
<h1>FTMO Rules Cheat Sheet — Quick Reference Guide for Every Rule</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-scaling-plan",
        "title": "FTMO Scaling Plan — How to Grow Your Account to $400k+",
        "description": "Learn how FTMO's scaling plan works. Grow your funded account up to $4 million by consistently passing account increases.",
        "keywords": "FTMO scaling plan, FTMO account growth, FTMO 400k, FTMO 4 million",
        "content": """
<h1>FTMO Scaling Plan — How to Grow Your Account to $400k+</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-trading-psychology",
        "title": "FTMO Trading Psychology — Mental Strategies for Passing Your Challenge",
        "description": "Master the mental game of FTMO challenges. Learn psychological strategies for handling drawdown, staying disciplined, and passing under pressure.",
        "keywords": "FTMO psychology, trading psychology FTMO, FTMO mental game, FTMO discipline",
        "content": """
<h1>FTMO Trading Psychology — Mental Strategies for Passing Your Challenge</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-trading-strategies-that-work",
        "title": "FTMO Trading Strategies That Actually Work — Backtested Approaches for Passing",
        "description": "Learn trading strategies that work for FTMO challenges. Includes trend following, breakout, and scalping approaches that help you pass.",
        "keywords": "FTMO strategy, FTMO trading strategy, best strategy for FTMO, FTMO scalping, FTMO trend following",
        "content": """
<h1>FTMO Trading Strategies That Actually Work — Backtested Approaches for Passing</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-verification-process",
        "title": "FTMO Verification Process — What Happens After You Pass Your Challenge",
        "description": "Learn what happens after you pass an FTMO challenge. The verification process, profit split, and how to get your funded account.",
        "keywords": "FTMO verification, FTMO after passing, FTMO funded account, FTMO profit split",
        "content": """
<h1>FTMO Verification Process — What Happens After You Pass Your Challenge</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "ftmo-vs-other-prop-firms",
        "title": "FTMO vs Other Prop Firms — Complete Comparison 2026 (FTMO vs The Funded Trader vs E8)",
        "description": "Compare FTMO with other top prop trading firms. See how FTMO stacks up against The Funded Trader, E8 Markets, FTT, and others.",
        "keywords": "FTMO vs other prop firms, FTMO vs The Funded Trader, FTMO vs E8, best prop firm, prop firm comparison",
        "content": """
<h1>FTMO vs Other Prop Firms — Complete Comparison 2026 (FTMO vs The Funded Trader vs E8)</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "how-to-pass-ftmo-challenge-first-attempt",
        "title": "How to Pass Your FTMO Challenge on the First Attempt — 10 Proven Strategies",
        "description": "Learn proven strategies for passing your FTMO challenge on the first attempt. Includes rule tracking tips, risk management, and mental preparation.",
        "keywords": "pass FTMO first attempt, FTMO strategy, FTMO tips, pass FTMO challenge",
        "content": """
<h1>How to Pass Your FTMO Challenge on the First Attempt — 10 Proven Strategies</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "how-to-pass-ftmo-phase-1-fast",
        "title": "How to Pass FTMO Phase 1 Fast — Efficient Strategies for the 10% Target",
        "description": "Learn how to pass FTMO Phase 1 efficiently. Strategies for hitting the 10% profit target while managing risk and respecting all rules.",
        "keywords": "pass FTMO Phase 1, FTMO Phase 1 fast, FTMO 10% target, FTMO Phase 1 strategy",
        "content": """
<h1>How to Pass FTMO Phase 1 Fast — Efficient Strategies for the 10% Target</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
    {
        "slug": "what-is-ftmo-challenge",
        "title": "What Is an FTMO Challenge? Complete Guide to Prop Firm Trading",
        "description": "Everything you need to know about FTMO challenges. Learn how prop firm challenges work, the rules, costs, and how to get funded.",
        "keywords": "what is FTMO, FTMO challenge, FTMO prop firm, FTMO funded, how FTMO works",
        "content": """
<h1>What Is an FTMO Challenge? Complete Guide to Prop Firm Trading</h1>
<p>Coming soon - this page is being updated.</p>
{cta}
"""
    },
]

# ── PAGE GENERATION]

# ── PAGE GENERATION ──────────────────────────────────────────────

def generate_page(page_data: dict) -> str:
    """Generate a complete HTML page from template data."""
    content = page_data["content"]
    content = content.replace("{TRACKER_URL}", TRACKER_URL)
    content = content.replace("{GUMROAD_URL}", GUMROAD_URL)
    content = content.replace("{BASE_URL}", BASE_URL)
    content = content.format(cta=get_cta_box())
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_data['title']}</title>
    <meta name="description" content="{page_data['description']}">
    <meta name="keywords" content="{page_data['keywords']}">
    <link rel="canonical" href="{BASE_URL}/seo/{page_data['slug']}.html">
    {STYLES}
</head>
<body>
    {NAV}
    {content}
    {FOOTER}
    <img src="{TRACKER_URL}?ref=organic&src=seo&page={page_data['slug']}" width="1" height="1" alt="" style="display:none">
</body>
</html>"""
    return html


def generate_index() -> str:
    """Generate the SEO content index page."""
    items = "\n".join(
        f'<li><a href="{p["slug"]}.html">{p["title"]}</a><br><span style="color:#6b7280;font-size:14px">{p["description"][:120]}...</span></li>'
        for p in PAGES
    )
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FTMO Challenge Guides & Resources — Free Tracker</title>
    <meta name="description" content="Comprehensive FTMO challenge guides and resources. Learn about rules, strategies, and tracking tools.">
    <meta name="keywords" content="FTMO guides, FTMO resources, FTMO tutorial, FTMO how to">
    {STYLES}
</head>
<body>
    {NAV}
    <h1>📚 FTMO Challenge Guides & Resources</h1>
    <p>Comprehensive guides to help you pass your FTMO challenge. All rules explained, strategies shared, and tracking tools provided.</p>
    
    <div class="info" style="margin:20px 0">
        <strong>Quick Start:</strong> Use our <a href="/ftmo_challenge_tracker.html">free FTMO tracker</a> to monitor all rules automatically.
        Telegram: <a href="https://t.me/ArdTradingBot">@ArdTradingBot</a>
    </div>
    
    <h2>All Guides</h2>
    <ul style="line-height:2">
        {items}
    </ul>
    
    <hr style="margin:30px 0">
    
    <h2>Popular Topics</h2>
    <ul>
        <li><a href="ftmo-challenge-rules-complete-guide.html">FTMO Rules Complete Guide</a></li>
        <li><a href="how-to-pass-ftmo-challenge-first-attempt.html">Pass on First Attempt</a></li>
        <li><a href="common-ftmo-challenge-mistakes.html">Common Mistakes to Avoid</a></li>
        <li><a href="ftmo-1-step-vs-2-step.html">1-Step vs 2-Step</a></li>
        <li><a href="ftmo-drawdown-calculator.html">Drawdown Calculator</a></li>
    </ul>
    
    {get_cta_box()}
    {FOOTER}
</body>
</html>"""
    return html


def generate_sitemap(pages: list) -> str:
    """Generate XML sitemap."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    
    # Main pages
    main_pages = [
        ("/ftmo_challenge_tracker.html", "daily", "1.0"),
        ("/sell.html", "weekly", "0.9"),
        ("/seo/index.html", "weekly", "0.9"),
    ]
    for path, freq, priority in main_pages:
        lines.append(f"  <url><loc>{BASE_URL}{path}</loc><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")
    
    for p in pages:
        lines.append(f"  <url><loc>{BASE_URL}/seo/{p['slug']}.html</loc><lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>")
    
    lines.append("</urlset>")
    return "\n".join(lines)


def generate_robots() -> str:
    """Generate robots.txt."""
    return f"""User-agent: *
Allow: /
Sitemap: {BASE_URL}/seo/sitemap.xml
"""


def generate_all(deploy: bool = True):
    """Generate all SEO pages and deploy."""
    logger.info(f"📝 Generating {len(PAGES)} SEO pages...")
    
    # Generate individual pages
    generated = []
    for page_data in PAGES:
        html = generate_page(page_data)
        filepath = SEO_DIR / f"{page_data['slug']}.html"
        filepath.write_text(html)
        generated.append(page_data['slug'])
        logger.info(f"  ✅ {page_data['slug']}.html")
    
    # Generate index
    index_html = generate_index()
    (SEO_DIR / "index.html").write_text(index_html)
    logger.info(f"  ✅ index.html")
    
    # Generate sitemap
    sitemap = generate_sitemap(PAGES)
    (SEO_DIR / "sitemap.xml").write_text(sitemap)
    logger.info(f"  ✅ sitemap.xml")
    
    # Generate robots.txt
    robots = generate_robots()
    (SEO_DIR / "robots.txt").write_text(robots)
    logger.info(f"  ✅ robots.txt")
    
    logger.info(f"\n✅ Generated {len(PAGES) + 3} files in {SEO_DIR}")
    
    if deploy:
        deploy_to_server()
    
    return generated


def deploy_to_server():
    """Deploy all SEO content to web server directory."""
    deploy_seo_dir = DEPLOY_DIR / "seo"
    deploy_seo_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all files
    for f in SEO_DIR.glob("*"):
        if f.is_file():
            shutil.copy2(f, deploy_seo_dir / f.name)
    
    logger.info(f"✅ Deployed {len(list(SEO_DIR.glob('*')))} files to {deploy_seo_dir}")
    
    # Test access
    import subprocess
    test_pages = [p["slug"] for p in PAGES[:2]] + ["index.html", "sitemap.xml"]
    working = 0
    for slug in test_pages:
        try:
            r = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
                 f"http://localhost:3000/seo/{slug}"],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip() == "200":
                working += 1
        except:
            pass
    
    logger.info(f"✅ {working}/{len(test_pages)} test pages accessible via web server")


def show_status():
    """Show SEO content stats."""
    seo_files = list(SEO_DIR.glob("*.html")) + list(SEO_DIR.glob("*.xml"))
    deploy_files = list((DEPLOY_DIR / "seo").glob("*")) if (DEPLOY_DIR / "seo").exists() else []
    
    print(f"\n{'='*50}")
    print(f"  📈 SEO CONTENT STATUS")
    print(f"{'='*50}")
    print(f"  Pages defined:  {len(PAGES)}")
    print(f"  Files generated: {len(seo_files)}")
    print(f"  Files deployed:  {len(deploy_files)}")
    print(f"\n  📄 Generated files:")
    for f in sorted(seo_files):
        size = f.stat().st_size
        print(f"    {f.name:55s} {size:>6,} bytes")
    print(f"\n  🌐 Base URL: https://ftmo-tracker.loca.lt/seo/")
    print()


def main():
    if len(sys.argv) < 2:
        print("""📈 SEO FACTORY — Automated Content Empire

Commands:
  --generate [n]   Generate n pages (default: all)
  --deploy          Deploy to web server
  --all             Generate all + deploy
  --status          Show content stats
""")
        return

    cmd = sys.argv[1]

    if cmd == "--generate":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else len(PAGES)
        pages = PAGES[:count]
        for p in pages:
            html = generate_page(p)
            filepath = SEO_DIR / f"{p['slug']}.html"
            filepath.write_text(html)
            print(f"✅ {p['slug']}.html")

    elif cmd == "--deploy":
        deploy_to_server()
        print("✅ Deployed")

    elif cmd == "--all":
        generate_all(deploy=True)
        print(f"✅ All {len(PAGES)} pages generated and deployed")

    elif cmd == "--status":
        show_status()

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
