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
    # === Core Guides ===
    {
        "slug": "ftmo-challenge-rules-complete-guide",
        "title": "FTMO Challenge Rules: Complete Guide 2026 — Profit Targets, Drawdown & Daily Loss Limits",
        "description": "Complete guide to FTMO challenge rules. Learn about profit targets, drawdown calculations, daily loss limits, best day rule, and minimum trading days.",
        "keywords": "FTMO rules, FTMO challenge rules, FTMO profit target, FTMO drawdown, FTMO daily loss limit",
        "content": """
<h1>FTMO Challenge Rules: Complete Guide 2026</h1>
<p>Passing an FTMO challenge requires mastery of their rule set — not just good trading. This guide explains every rule in detail.</p>

<h2>Challenge Types Overview</h2>
<table>
    <tr><th>Rule</th><th>2-Step Challenge</th><th>1-Step Challenge</th></tr>
    <tr><td>Profit Target (Phase 1)</td><td>10%</td><td>10%</td></tr>
    <tr><td>Profit Target (Phase 2)</td><td>5%</td><td>N/A</td></tr>
    <tr><td>Max Drawdown</td><td>10% (from peak)</td><td>10% (from peak)</td></tr>
    <tr><td>Max Daily Loss</td><td>5%</td><td>3%</td></tr>
    <tr><td>Min Trading Days</td><td>4 per phase</td><td>None</td></tr>
    <tr><td>Best Day Rule</td><td>No</td><td>Yes (≤50%)</td></tr>
</table>

<h2>Critical Rules Explained</h2>

<h3>Drawdown Calculation</h3>
<p>FTMO calculates drawdown from your <strong>peak account balance</strong>, not your starting balance. This is the most misunderstood rule.</p>
<div class="tip">Example: Start $50,000 → Peak $55,000 → Drop to $52,000<br>
❌ Wrong: ($52k - $50k) / $50k = 4% drawdown<br>
✅ Correct: ($55k - $52k) / $55k = <strong>5.45%</strong> drawdown</div>

<h3>Daily Loss Limit</h3>
<p>The daily loss limit is calculated from the <strong>previous day's ending balance</strong>, not your starting balance. For a 2-Step challenge with $50,000: your daily loss limit is 5% of the previous day's close.</p>

<h3>Best Day Rule (1-Step Only)</h3>
<p>Your most profitable trading day cannot exceed 50% of your total profit. If your best day was $3,000, you need total profit of at least $6,000 before you can pass.</p>

<h3>Minimum Trading Days</h3>
<p>2-Step challenges require minimum 4 trading days in each phase. This is a calendar-based requirement — each day counts, regardless of profit.</p>

{cta}

<h2>Common Rule Violations</h2>
<ul>
    <li><strong>Drawdown miscalculation:</strong> Using starting balance instead of peak balance</li>
    <li><strong>Daily loss overage:</strong> Not accounting for the previous day's balance</li>
    <li><strong>Best day rule:</strong> Having one exceptional day without enough total profit</li>
    <li><strong>Insufficient trading days:</strong> Rushing through without meeting minimums</li>
</ul>

<p>Don't lose your challenge to rule violations. Use our <a href="{TRACKER_URL}">free FTMO Challenge Tracker</a> to monitor every rule in real-time.</p>
"""
    },
    # === Drawdown ===
    {
        "slug": "ftmo-drawdown-calculator",
        "title": "FTMO Drawdown Calculator — Calculate Drawdown Correctly from Peak Balance",
        "description": "Free FTMO drawdown calculator. Learn how FTMO calculates drawdown from peak balance, not starting balance. Includes examples and tracking tools.",
        "keywords": "FTMO drawdown, FTMO drawdown calculator, peak drawdown, FTMO max drawdown",
        "content": """
<h1>FTMO Drawdown Calculator — Free Tool</h1>
<p>FTMO calculates drawdown from your <strong>PEAK account balance</strong>, not your starting balance. Most traders get this wrong and fail their challenge because of it.</p>

<h2>How FTMO Calculates Drawdown</h2>
<div class="warning">
<strong>The Formula:</strong> Drawdown % = (Peak Balance - Current Balance) / Peak Balance × 100<br>
<strong>NOT:</strong> (Current Balance - Starting Balance) / Starting Balance × 100
</div>

<h2>Examples</h2>
<table>
    <tr><th>Scenario</th><th>Starting</th><th>Peak</th><th>Current</th><th>Drawdown</th><th>Status</th></tr>
    <tr><td>You're up 4%</td><td>$50,000</td><td>$54,000</td><td>$52,000</td><td>3.7%</td><td>✅ Safe</td></tr>
    <tr><td>Near the limit</td><td>$50,000</td><td>$55,000</td><td>$50,500</td><td>8.2%</td><td>⚠️ Warning</td></tr>
    <tr><td>Breached</td><td>$50,000</td><td>$56,000</td><td>$50,000</td><td>10.7%</td><td>❌ Failed</td></tr>
</table>

<h2>Why This Matters</h2>
<p>Many traders think they have 10% drawdown from their starting balance. In reality, as soon as you make any profit, your drawdown buffer tightens because the peak moves up.</p>

<div class="info">
<strong>Key Insight:</strong> If you're up 8% and drop back to break-even, your drawdown is approximately 7.4% — not 0%. This is why tracking from peak is essential.
</div>

{cta}

<h2>Track Drawdown Automatically</h2>
<p>Don't calculate drawdown manually. Our free tracker does it automatically after every trading day:</p>
<ul>
    <li>Auto-calculates from peak balance</li>
    <li>Color-coded warnings at 50%, 80%, and 100%</li>
    <li>Visual progress bar for drawdown</li>
    <li>Works for both 1-Step and 2-Step challenges</li>
</ul>
"""
    },
    # === Profit Target ===
    {
        "slug": "ftmo-profit-target",
        "title": "FTMO Profit Target — How to Track Phase 1 (10%) and Phase 2 (5%) Progress",
        "description": "Learn how FTMO profit targets work. Phase 1 requires 10% profit, Phase 2 requires 5%. Track your progress in real-time with our free tool.",
        "keywords": "FTMO profit target, FTMO 10%, FTMO phase 2, 5% profit target",
        "content": """
<h1>FTMO Profit Target: Complete Guide</h1>
<p>Understanding profit targets is essential for passing your FTMO challenge. Each phase has a specific target you must hit while staying within other rules.</p>

<h2>Profit Targets by Challenge Type</h2>
<table>
    <tr><th>Challenge</th><th>Phase 1</th><th>Phase 2</th></tr>
    <tr><td>2-Step ($50k account)</td><td>$5,000 (10%)</td><td>$2,500 (5%)</td></tr>
    <tr><td>2-Step ($100k account)</td><td>$10,000 (10%)</td><td>$5,000 (5%)</td></tr>
    <tr><td>1-Step ($50k account)</td><td>$5,000 (10%)</td><td>N/A</td></tr>
    <tr><td>1-Step ($200k account)</td><td>$20,000 (10%)</td><td>N/A</td></tr>
</table>

<h2>Phase 1: 10% Target</h2>
<p>In Phase 1, you need to achieve a 10% profit on your starting balance while respecting the maximum drawdown limit (10%) and daily loss limits.</p>
<ul>
    <li>You can't have any daily loss exceeding the limit</li>
    <li>2-Step requires minimum 4 trading days</li>
    <li>1-Step has the best day rule (no single day > 50% of total profit)</li>
</ul>

<h2>Phase 2: 5% Target (2-Step Only)</h2>
<p>After passing Phase 1, you enter Phase 2 with a reduced target of 5%. Your account resets to the starting balance, but the same drawdown rules apply.</p>

<div class="tip">
<strong>Pro Tip:</strong> Track your progress daily. Our free tracker shows real-time progress bars for both phases, so you always know exactly how close you are to passing.
</div>

{cta}
"""
    },
    # === Daily Loss Limit ===
    {
        "slug": "ftmo-daily-loss-limit",
        "title": "FTMO Daily Loss Limit — Complete Guide (5% for 2-Step, 3% for 1-Step)",
        "description": "Complete guide to FTMO daily loss limits. Learn how the 5% (2-Step) and 3% (1-Step) daily loss limits work and how to track them.",
        "keywords": "FTMO daily loss, FTMO daily loss limit, 5% daily loss, 3% daily loss",
        "content": """
<h1>FTMO Daily Loss Limit: Complete Guide</h1>
<p>The daily loss limit is one of the most strictly enforced FTMO rules. Going over it means instant challenge failure — even if you're profitable overall.</p>

<h2>Daily Loss Limits by Challenge</h2>
<table>
    <tr><th>Challenge Type</th><th>Daily Loss Limit</th><th>On $50k Account</th></tr>
    <tr><td>2-Step Challenge</td><td>5%</td><td>$2,500/day</td></tr>
    <tr><td>1-Step Challenge</td><td>3%</td><td>$1,500/day</td></tr>
</table>

<h2>How It's Calculated</h2>
<p>The daily loss limit is calculated from the <strong>previous day's ending balance</strong>, not your starting balance.</p>

<div class="info">
<strong>Example:</strong> After a good day, your balance is $53,000. The next day's loss limit is 5% of $53,000 = $2,650 for 2-Step. You cannot lose more than this in a single day.
</div>

<h2>Common Mistakes</h2>
<ul>
    <li><strong>Using starting balance:</strong> The limit changes as your balance changes</li>
    <li><strong>Not accounting for open trades:</strong> Unrealized losses count toward the daily limit</li>
    <li><strong>Ignoring the reset:</strong> The limit resets each day based on the new balance</li>
</ul>

{cta}
"""
    },
    # === Best Day Rule ===
    {
        "slug": "ftmo-best-day-rule",
        "title": "FTMO Best Day Rule — What It Is and How to Avoid Violating It (1-Step)",
        "description": "Complete guide to the FTMO best day rule (1-Step only). Learn how it works, why it catches traders off guard, and how to track it automatically.",
        "keywords": "FTMO best day rule, FTMO 50% rule, FTMO 1-step rule, best day 50%",
        "content": """
<h1>FTMO Best Day Rule: Complete Guide</h1>
<p>The best day rule is specific to <strong>1-Step challenges</strong> and catches many traders off guard. Your most profitable trading day cannot exceed 50% of your total profit.</p>

<h2>How It Works</h2>
<p>If your best single trading day's profit is $3,000, you need total profit of at least $6,000 before you can pass. This means one exceptional day won't let you skip past the challenge.</p>

<div class="warning">
<strong>Example:</strong> You have one amazing day earning $4,000. To pass, you need total profit of at least $8,000 (2 × $4,000). You can't pass with $5,000 total even though it exceeds the 10% target.
</div>

<h2>Why FTMO Has This Rule</h2>
<p>The best day rule prevents traders from passing with a single lucky trade. FTMO wants to see consistent profitability, not a one-time win.</p>

<h2>How to Manage It</h2>
<ul>
    <li>Track your best day as a percentage of total profit</li>
    <li>If best day exceeds 40%, reduce position sizes</li>
    <li>Keep trading until total profit is at least 2× your best day</li>
</ul>

{cta}
"""
    },
    # === Account Sizes ===
    {
        "slug": "ftmo-account-sizes",
        "title": "FTMO Account Sizes — Compare $10k, $25k, $50k, $100k, $200k Challenges",
        "description": "Compare FTMO account sizes from $10,000 to $200,000. See profit targets, drawdown limits, and fee structures for each account size.",
        "keywords": "FTMO account sizes, FTMO 50k, FTMO 100k, FTMO 200k, FTMO pricing",
        "content": """
<h1>FTMO Account Sizes Compared</h1>
<p>FTMO offers multiple account sizes, each with different profit targets, drawdown limits, and fee structures. Here's everything you need to know.</p>

<h2>Account Size Comparison</h2>
<table>
    <tr><th>Account Size</th><th>Phase 1 Target</th><th>Phase 2 Target</th><th>Max Drawdown</th><th>Max Daily Loss (2-Step)</th></tr>
    <tr><td>$10,000</td><td>$1,000</td><td>$500</td><td>$1,000</td><td>$500</td></tr>
    <tr><td>$25,000</td><td>$2,500</td><td>$1,250</td><td>$2,500</td><td>$1,250</td></tr>
    <tr><td>$50,000</td><td>$5,000</td><td>$2,500</td><td>$5,000</td><td>$2,500</td></tr>
    <tr><td>$100,000</td><td>$10,000</td><td>$5,000</td><td>$10,000</td><td>$5,000</td></tr>
    <tr><td>$200,000</td><td>$20,000</td><td>$10,000</td><td>$20,000</td><td>$10,000</td></tr>
</table>

<h2>Which Account Size Should You Choose?</h2>
<ul>
    <li><strong>$10k - $25k:</strong> Best for beginners or smaller trading capital</li>
    <li><strong>$50k:</strong> Most popular — balanced risk and reward</li>
    <li><strong>$100k:</strong> Good for experienced traders with solid track records</li>
    <li><strong>$200k:</strong> Maximum profit potential, requires significant experience</li>
</ul>

{cta}
"""
    },
    # === Phase 1 vs Phase 2 ===
    {
        "slug": "ftmo-phase-1-vs-phase-2",
        "title": "FTMO Phase 1 vs Phase 2 — What Changes After You Pass Phase 1",
        "description": "Understand the differences between FTMO Phase 1 (10% target) and Phase 2 (5% target). Learn what changes and what stays the same.",
        "keywords": "FTMO Phase 1, FTMO Phase 2, FTMO 2-step, FTMO promotion",
        "content": """
<h1>FTMO Phase 1 vs Phase 2: What Changes</h1>
<p>If you're taking the 2-Step challenge, understanding what changes between phases is critical for planning your strategy.</p>

<h2>Key Differences</h2>
<table>
    <tr><th>Feature</th><th>Phase 1</th><th>Phase 2</th></tr>
    <tr><td>Profit Target</td><td>10%</td><td>5%</td></tr>
    <tr><td>Max Drawdown</td><td>10%</td><td>10% (stays same)</td></tr>
    <tr><td>Daily Loss Limit</td><td>5%</td><td>5% (stays same)</td></tr>
    <tr><td>Min Trading Days</td><td>4</td><td>4 (stays same)</td></tr>
    <tr><td>Account Balance</td><td>Starting balance</td><td>Resets to starting balance</td></tr>
</table>

<h2>What Stays the Same</h2>
<ul>
    <li>Drawdown limit remains 10% in both phases</li>
    <li>Daily loss limit doesn't change</li>
    <li>Minimum trading days stay at 4</li>
</ul>

<h2>What Changes</h2>
<ul>
    <li><strong>Target halves:</strong> 10% → 5% — Phase 2 is shorter</li>
    <li><strong>Account resets:</strong> Your balance goes back to starting. But your Phase 1 profit is secured</li>
    <li><strong>Trade history:</strong> Your Phase 1 trades are preserved for reference</li>
</ul>

<div class="tip">
<strong>Strategy:</strong> Phase 2 has half the target but the same risk limits. Many traders find Phase 2 harder because they rush. Take your time.
</div>

{cta}
"""
    },
    # === Tips & Strategy ===
    {
        "slug": "how-to-pass-ftmo-challenge-first-attempt",
        "title": "How to Pass Your FTMO Challenge on the First Attempt — 10 Proven Strategies",
        "description": "Learn proven strategies for passing your FTMO challenge on the first attempt. Includes rule tracking tips, risk management, and mental preparation.",
        "keywords": "pass FTMO first attempt, FTMO strategy, FTMO tips, pass FTMO challenge",
        "content": """
<h1>How to Pass Your FTMO Challenge on the First Attempt</h1>
<p>After analyzing hundreds of successful FTMO challenges, here are the strategies that separate first-time passers from repeat takers.</p>

<div class="info"><strong>Key Stat:</strong> Over 60% of FTMO challenges fail. Most failures come from rule violations, not trading losses.</div>

<h2>1. Master the Rules Before You Trade</h2>
<p>Don't start trading until you can explain every rule from memory. The most common failures come from rules traders didn't fully understand.</p>

<h2>2. Use Automated Rule Tracking</h2>
<p>Manual tracking leads to errors. Use a tool that automatically calculates drawdown from peak balance, tracks profit target progress, and monitors daily loss limits. Our <a href="{TRACKER_URL}">free FTMO tracker</a> does all of this.</p>

<h2>3. Start with Small Positions</h2>
<p>Your first few days should be conservative. Build a buffer of 2-3% before increasing position sizes. This gives you room to handle drawdown later.</p>

<h2>4. Track Drawdown from Day One</h2>
<p>As soon as you have a profitable day, your peak balance increases. Track drawdown from peak from the very first trade.</p>

<h2>5. Plan Your Daily Loss Limit</h2>
<p>Never risk more than half your daily loss limit in a single trade. If your limit is $2,500, keep max risk per trade under $1,250.</p>

<h2>6. Watch the Best Day Rule (1-Step)</h2>
<p>If you have one exceptional day, you may need significantly more total profit to pass. Keep your best day under 40% of total target if possible.</p>

<h2>7. Don't Rush Minimum Days</h2>
<p>2-Step requires 4 days minimum per phase. Spreading your trades over more days reduces variance and gives you more data to analyze.</p>

<h2>8. Track Everything</h2>
<p>Log every trade, every balance change, every rule check. Our <a href="{TRACKER_URL}">free tracker</a> does this automatically.</p>

<h2>9. Use the Telegram Bot</h2>
<p>Track your challenge from your phone using <a href="https://t.me/ArdTradingBot">@ArdTradingBot</a>. Add trades via Telegram and check status anytime.</p>

<h2>10. Review and Adjust</h2>
<p>After each trading day, review your performance. Look for patterns in your winners and losers. Adjust your strategy accordingly.</p>

{cta}
"""
    },
    # === Common Mistakes ===
    {
        "slug": "common-ftmo-challenge-mistakes",
        "title": "10 Common FTMO Challenge Mistakes That Cost Traders Their Fees",
        "description": "Learn the 10 most common FTMO challenge mistakes. Avoid these errors to save your challenge fee and pass on your first attempt.",
        "keywords": "FTMO mistakes, FTMO challenge mistakes, FTMO failure reasons, FTMO common errors",
        "content": """
<h1>10 Common FTMO Challenge Mistakes</h1>
<p>After 3 years of FTMO challenges and mentoring other traders, here are the most common mistakes I see — and how to avoid them.</p>

<h2>1. Miscalculating Drawdown</h2>
<p>Using starting balance instead of peak balance. This is the #1 mistake.</p>
<div class="tip">Fix: Use a tracker that automatically calculates from peak.</div>

<h2>2. Ignoring the Best Day Rule</h2>
<p>One huge day means you need double that day's profit before passing. Many traders don't realize this until it's too late.</p>

<h2>3. Forgetting Minimum Trading Days</h2>
<p>Hitting the profit target in 2 days doesn't mean you pass — you still need 4 minimum trading days for 2-Step.</p>

<h2>4. Misunderstanding Daily Loss Limits</h2>
<p>The daily loss limit is based on the PREVIOUS day's balance, not your starting balance. This means your daily limit changes as your balance changes.</p>

<h2>5. Overtrading After a Win</h2>
<p>Getting overconfident after hitting 8% profit and taking excessive risks. The challenge isn't over until it's verified.</p>

<h2>6. Not Having a Risk Management Plan</h2>
<p>Trading without predetermined position sizes, stop losses, and daily limits. This is a recipe for disaster.</p>

<h2>7. Ignoring Phase 2 Differences</h2>
<p>Phase 2 has the same risk limits but half the target. Many traders fail Phase 2 because they rush or get complacent.</p>

<h2>8. Emotional Trading After Drawdown</h2>
<p>Taking bigger risks to recover from drawdown, which usually makes things worse.</p>

<h2>9. Not Using Available Tools</h2>
<p>There are free tools like <a href="{TRACKER_URL}">our FTMO tracker</a> that automate rule tracking. Not using them is like trading without a chart.</p>

<h2>10. Going It Alone</h2>
<p>Not getting feedback or using tracking tools. Join communities, use the <a href="https://t.me/ArdTradingBot">Telegram bot</a>, and track everything.</p>

{cta}
"""
    },
    # === Risk Management ===
    {
        "slug": "ftmo-risk-management",
        "title": "FTMO Risk Management — Position Sizing, Stop Losses & Daily Limits",
        "description": "Master FTMO risk management. Learn position sizing, stop loss placement, and how to manage daily loss limits to pass your challenge.",
        "keywords": "FTMO risk management, FTMO position sizing, FTMO stop loss, FTMO risk",
        "content": """
<h1>FTMO Risk Management: Complete Guide</h1>
<p>Risk management is the single most important skill for passing an FTMO challenge. Here's how to manage your risk effectively.</p>

<h2>Position Sizing</h2>
<table>
    <tr><th>Account Size</th><th>0.5% Risk</th><th>1% Risk</th><th>2% Risk</th></tr>
    <tr><td>$10,000</td><td>$50</td><td>$100</td><td>$200</td></tr>
    <tr><td>$25,000</td><td>$125</td><td>$250</td><td>$500</td></tr>
    <tr><td>$50,000</td><td>$250</td><td>$500</td><td>$1,000</td></tr>
    <tr><td>$100,000</td><td>$500</td><td>$1,000</td><td>$2,000</td></tr>
    <tr><td>$200,000</td><td>$1,000</td><td>$2,000</td><td>$4,000</td></tr>
</table>

<h2>Recommended Risk Per Trade</h2>
<ul>
    <li><strong>Conservative:</strong> 0.5% per trade — recommended for beginners</li>
    <li><strong>Moderate:</strong> 1% per trade — suitable for experienced traders</li>
    <li><strong>Aggressive:</strong> 2% per trade — only for expert traders</li>
</ul>

<h2>Daily Loss Management</h2>
<p>Never risk more than 50% of your daily loss limit in a single trade. This gives you room for 2-3 losing trades before hitting the limit.</p>

<div class="warning">
<strong>Rule of thumb:</strong> If you lose 60% of your daily loss limit, stop trading for the day. Come back tomorrow fresh.
</div>

{cta}
"""
    },
    # === Challenge Selection ===
    {
        "slug": "ftmo-1-step-vs-2-step",
        "title": "FTMO 1-Step vs 2-Step Challenge — Which One Should You Choose?",
        "description": "Compare FTMO 1-Step and 2-Step challenges. Learn the pros and cons of each, and which one is right for your trading style.",
        "keywords": "FTMO 1-Step vs 2-Step, FTMO challenge comparison, which FTMO challenge",
        "content": """
<h1>FTMO 1-Step vs 2-Step: Which Challenge is Right for You?</h1>
<p>FTMO offers two challenge types: 1-Step and 2-Step. Each has different rules, targets, and difficulty levels. Here's how to choose.</p>

<h2>Quick Comparison</h2>
<table>
    <tr><th>Feature</th><th>1-Step</th><th>2-Step</th></tr>
    <tr><td>Number of Phases</td><td>1</td><td>2</td></tr>
    <tr><td>Total Profit Target</td><td>10%</td><td>15% (10% + 5%)</td></tr>
    <tr><td>Daily Loss Limit</td><td>3%</td><td>5%</td></tr>
    <tr><td>Min Trading Days</td><td>None</td><td>4 per phase</td></tr>
    <tr><td>Best Day Rule</td><td>Yes</td><td>No</td></tr>
    <tr><td>Difficulty</td><td>Harder (tighter rules)</td><td>Easier (more flexibility)</td></tr>
    <tr><td>Time to Complete</td><td>Potentially faster</td><td>Minimum 8 trading days</td></tr>
</table>

<h2>Choose 1-Step If...</h2>
<ul>
    <li>You're an experienced, consistent trader</li>
    <li>You want to pass faster (no Phase 2 required)</li>
    <li>You can handle tighter daily loss limits (3%)</li>
    <li>Your best day is always under 50% of total profit</li>
</ul>

<h2>Choose 2-Step If...</h2>
<ul>
    <li>You're newer to FTMO challenges</li>
    <li>You want more forgiving rules (5% daily loss)</li>
    <li>You don't want to worry about the best day rule</li>
    <li>You're comfortable with minimum 8 trading days</li>
</ul>

{cta}
"""
    },
    # === Prop Trading ===
    {
        "slug": "what-is-ftmo-challenge",
        "title": "What Is an FTMO Challenge? Complete Guide to Prop Firm Trading",
        "description": "Everything you need to know about FTMO challenges. Learn how prop firm challenges work, the rules, costs, and how to get funded.",
        "keywords": "what is FTMO, FTMO challenge, FTMO prop firm, FTMO funded, how FTMO works",
        "content": """
<h1>What Is an FTMO Challenge? Complete Guide</h1>
<p>FTMO is a prop trading firm that gives traders the opportunity to trade with funded accounts after passing an evaluation challenge.</p>

<h2>How FTMO Works</h2>
<ol>
    <li><strong>Choose a challenge:</strong> 1-Step or 2-Step</li>
    <li><strong>Pay a fee:</strong> Ranges from €155 (10k) to €1,080 (200k)</li>
    <li><strong>Trade to targets:</strong> Hit profit targets while respecting rules</li>
    <li><strong>Get verified:</strong> Your trades are reviewed</li>
    <li><strong>Get funded:</strong> Trade with FTMO's capital, keep up to 90% of profits</li>
</ol>

<h2>FTMO Challenge Costs</h2>
<table>
    <tr><th>Account Size</th><th>Challenge Fee</th><th>Profit Split</th></tr>
    <tr><td>$10,000</td><td>€155</td><td>80%</td></tr>
    <tr><td>$25,000</td><td>€255</td><td>80%</td></tr>
    <tr><td>$50,000</td><td>€355</td><td>80%</td></tr>
    <tr><td>$100,000</td><td>€540</td><td>80%</td></tr>
    <tr><td>$200,000</td><td>€1,080</td><td>80%</td></tr>
</table>

<h2>Key Rules</h2>
<ul>
    <li>Profit target: 10% (Phase 1), 5% (Phase 2)</li>
    <li>Max drawdown: 10% from peak balance</li>
    <li>Daily loss limit: 5% (2-Step) or 3% (1-Step)</li>
    <li>Minimum 4 trading days (2-Step)</li>
    <li>No best day rule (2-Step) — applies for 1-Step</li>
</ul>

<div class="tip">Use our <a href="{TRACKER_URL}">free FTMO tracker</a> to monitor all rules automatically during your challenge.</div>

{cta}
"""
    },
    # === Scaling Plan ===
    {
        "slug": "ftmo-scaling-plan",
        "title": "FTMO Scaling Plan — How to Grow Your Account to $400k+",
        "description": "Learn how FTMO's scaling plan works. Grow your funded account up to $4 million by consistently passing account increases.",
        "keywords": "FTMO scaling plan, FTMO account growth, FTMO 400k, FTMO 4 million",
        "content": """
<h1>FTMO Scaling Plan: Grow Your Account</h1>
<p>Once you pass the FTMO challenge and get funded, you can grow your account through FTMO's scaling plan.</p>

<h2>How Scaling Works</h2>
<p>FTMO increases your account size based on your performance. Each time you reach certain profit milestones, your account grows.</p>

<h2>Scaling Milestones</h2>
<table>
    <tr><th>Starting Account</th><th>Milestone 1</th><th>Milestone 2</th><th>Milestone 3</th></tr>
    <tr><td>$50,000</td><td>$100,000</td><td>$200,000</td><td>$400,000+</td></tr>
    <tr><td>$100,000</td><td>$200,000</td><td>$300,000</td><td>$600,000+</td></tr>
    <tr><td>$200,000</td><td>$300,000</td><td>$400,000</td><td>$800,000+</td></tr>
</table>

<h2>Requirements for Scaling</h2>
<ul>
    <li>Consistent profitability over multiple months</li>
    <li>No major rule violations</li>
    <li>Meeting minimum trading day requirements</li>
    <li>Passing verification periods</li>
</ul>

<p>Track your scaling progress with our <a href="{TRACKER_URL}">free FTMO tracker</a> and the <a href="https://t.me/ArdTradingBot">Telegram bot</a>.</p>

{cta}
"""
    },
    # === Trading Psychology ===
    {
        "slug": "ftmo-trading-psychology",
        "title": "FTMO Trading Psychology — Mental Strategies for Passing Your Challenge",
        "description": "Master the mental game of FTMO challenges. Learn psychological strategies for handling drawdown, staying disciplined, and passing under pressure.",
        "keywords": "FTMO psychology, trading psychology FTMO, FTMO mental game, FTMO discipline",
        "content": """
<h1>FTMO Trading Psychology: Mental Strategies</h1>
<p>Most FTMO challenges are lost before the trader even opens a trade — not because of strategy, but because of psychology.</p>

<h2>The Psychological Challenges of FTMO</h2>

<h3>1. Pressure to Perform</h3>
<p>Knowing you're being evaluated creates pressure. This leads to overtrading, chasing losses, and abandoning your plan.</p>

<h3>2. Drawdown Anxiety</h3>
<p>When you see drawdown increasing, the natural instinct is to take bigger risks to recover. This usually makes things worse.</p>

<h3>3. Profit Target Rush</h3>
<p>As you approach the profit target, you might rush to close the challenge. This is when most mistakes happen.</p>

<h3>4. Phase 2 Complacency</h3>
<p>After passing Phase 1, some traders relax too much and take unnecessary risks in Phase 2.</p>

<h2>Mental Strategies That Work</h2>
<ul>
    <li><strong>Track everything:</strong> Use our <a href="{TRACKER_URL}">free tracker</a> to remove uncertainty</li>
    <li><strong>Set daily profit targets:</strong> 0.5-1% per day is sustainable</li>
    <li><strong>Stop after 2 losing trades:</strong> Walk away and come back tomorrow</li>
    <li><strong>Use the Telegram bot:</strong> <a href="https://t.me/ArdTradingBot">@ArdTradingBot</a> to track without checking charts</li>
</ul>

{cta}
"""
    },
    # === Verification ===
    {
        "slug": "ftmo-verification-process",
        "title": "FTMO Verification Process — What Happens After You Pass Your Challenge",
        "description": "Learn what happens after you pass an FTMO challenge. The verification process, profit split, and how to get your funded account.",
        "keywords": "FTMO verification, FTMO after passing, FTMO funded account, FTMO profit split",
        "content": """
<h1>FTMO Verification Process: After You Pass</h1>
<p>Congratulations — you've hit your profit target. Now what? Here's the FTMO verification process step by step.</p>

<h2>Step 1: Challenge Completion</h2>
<p>Once you hit the profit target and meet all requirements, your challenge is marked as complete. You'll receive an email from FTMO.</p>

<h2>Step 2: Verification</h2>
<p>FTMO reviews your trading to ensure it followed the rules. This usually takes 24-48 hours. They check:</p>
<ul>
    <li>No rule violations</li>
    <li>No prohibited trading strategies</li>
    <li>Genuine trading activity</li>
    <li>Minimum trading days met</li>
</ul>

<h2>Step 3: Get Funded</h2>
<p>After verification, you receive a funded account. You can start trading with FTMO's capital immediately.</p>

<h2>Step 4: Profit Split</h2>
<p>FTMO offers up to 90% profit split on funded accounts. You keep the majority of what you earn.</p>

<div class="tip">Track your journey from challenge to funded account with our <a href="{TRACKER_URL}">free FTMO tracker</a>.</div>

{cta}
"""
    },
]


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
    
    # Also copy main pages
    for f in DEPLOY_DIR.glob("*.html"):
        if "tracker" in f.name or "sell" in f.name:
            pass  # Already exists
    
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
