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
    # === Fee & Pricing Pages ===
    {
        "slug": "ftmo-challenge-fees-explained",
        "title": "FTMO Challenge Fees — How Much Does an FTMO Challenge Cost? Full Breakdown 2026",
        "description": "Complete breakdown of FTMO challenge fees. See costs for each account size from $10k to $200k, profit splits, and hidden costs.",
        "keywords": "FTMO cost, FTMO fees, FTMO challenge fee, how much is FTMO, FTMO pricing",
        "content": """
<h1>FTMO Challenge Fees: Complete Cost Breakdown</h1>
<p>Before starting an FTMO challenge, you need to understand the costs involved. Here's a complete breakdown of FTMO challenge fees for every account size.</p>

<h2>Challenge Fees by Account Size</h2>
<table>
    <tr><th>Account Size</th><th>Challenge Fee</th><th>Retry Fee</th><th>Profit Split</th></tr>
    <tr><td>$10,000</td><td>€155</td><td>€124</td><td>80%</td></tr>
    <tr><td>$25,000</td><td>€255</td><td>€204</td><td>80%</td></tr>
    <tr><td>$50,000</td><td>€355</td><td>€284</td><td>80%</td></tr>
    <tr><td>$100,000</td><td>€540</td><td>€432</td><td>80%</td></tr>
    <tr><td>$200,000</td><td>€1,080</td><td>€864</td><td>80%</td></tr>
</table>

<h2>What You Get for the Fee</h2>
<ul>
    <li>Your challenge evaluation (Phase 1 + Phase 2 for 2-Step)</li>
    <li>FTMO's proprietary trading platform access</li>
    <li>Real-time performance tracking dashboard</li>
    <li>Verification process after passing</li>
    <li>Funded account with up to 90% profit split</li>
</ul>

<h2>Retry Discount</h2>
<p>If you fail your first attempt, FTMO offers a 20% discount on your next challenge fee. This retry discount applies to the same account size.</p>

<h2>Profit Split After Passing</h2>
<p>Once funded, you keep 80% of all profits. The split can increase to 90% based on your performance and account growth through the scaling plan.</p>

<div class="tip">
<strong>Value Calculation:</strong> A $50k challenge costs €355. If you pass and make 5% ($2,500) in your first month, you keep $2,000. That's a 5.6x return on your challenge fee in one month.
</div>

{cta}
"""
    },
    {
        "slug": "ftmo-vs-other-prop-firms",
        "title": "FTMO vs Other Prop Firms — Complete Comparison 2026 (FTMO vs The Funded Trader vs E8)",
        "description": "Compare FTMO with other top prop trading firms. See how FTMO stacks up against The Funded Trader, E8 Markets, FTT, and others.",
        "keywords": "FTMO vs other prop firms, FTMO vs The Funded Trader, FTMO vs E8, best prop firm, prop firm comparison",
        "content": """
<h1>FTMO vs Other Prop Firms: Complete Comparison 2026</h1>
<p>FTMO is the largest prop trading firm, but it's not the only option. Here's how FTMO compares with other popular prop firms.</p>

<h2>Quick Comparison Table</h2>
<table>
    <tr><th>Feature</th><th>FTMO</th><th>The Funded Trader</th><th>E8 Markets</th><th>FTT (Futures Trading)</th></tr>
    <tr><td>Max Account</td><td>$200k</td><td>$200k</td><td>$100k</td><td>$300k</td></tr>
    <tr><td>Profit Split</td><td>80-90%</td><td>80-90%</td><td>80-90%</td><td>80%</td></tr>
    <tr><td>Phase 1 Target</td><td>10%</td><td>8-10%</td><td>8-10%</td><td>10%</td></tr>
    <tr><td>Phase 2 Target</td><td>5%</td><td>5%</td><td>5%</td><td>5%</td></tr>
    <tr><td>Max Drawdown</td><td>10%</td><td>6-12%</td><td>6-8%</td><td>10%</td></tr>
    <tr><td>Daily Loss</td><td>5% (3% 1-Step)</td><td>5%</td><td>5%</td><td>5%</td></tr>
    <tr><td>Min Trading Days</td><td>4</td><td>3-5</td><td>2-4</td><td>5</td></tr>
    <tr><td>Free Trial</td><td>No</td><td>Yes</td><td>Yes</td><td>No</td></tr>
    <tr><td>Platforms</td><td>MT4, MT5, cTrader</td><td>MT4, MT5, DXtrade</td><td>cTrader, MT5</td><td>Nigel</td></tr>
</table>

<h2>Why Traders Choose FTMO</h2>
<ul>
    <li>Most established prop firm (since 2015)</li>
    <li>Best platform selection (MT4, MT5, cTrader)</li>
    <li>Clear, consistent rules</li>
    <li>Strong reputation and fast payouts</li>
    <li>Generous scaling plan</li>
</ul>

<h2>When to Choose Another Firm</h2>
<ul>
    <li><strong>The Funded Trader:</strong> Lower profit targets and free trials</li>
    <li><strong>E8 Markets:</strong> Fewer minimum trading days (great for scalpers)</li>
    <li><strong>FTT:</strong> Best for futures traders specifically</li>
</ul>

<div class="tip">Whichever firm you choose, use our <a href="{TRACKER_URL}">free challenge tracker</a> to monitor your rules automatically.</div>

{cta}
"""
    },
    {
        "slug": "ftmo-free-trial-discount",
        "title": "FTMO Free Trial and Discount Codes — Is There an FTMO Promo Code in 2026?",
        "description": "Find out if FTMO offers free trials, discount codes, or promo codes in 2026. Learn how to save on your FTMO challenge fee.",
        "keywords": "FTMO free trial, FTMO discount, FTMO promo code, FTMO coupon, FTMO free challenge",
        "content": """
<h1>FTMO Free Trial and Discounts: What's Available</h1>
<p>Many traders ask about FTMO free trials and discount codes. Here's the truth about what's available and how to save money.</p>

<h2>Does FTMO Have a Free Trial?</h2>
<p>FTMO does NOT offer a free trial of their full challenge. However, they do offer:</p>
<ul>
    <li><strong>Free practice:</strong> You can use FTMO's platform demo accounts for free to practice</li>
    <li><strong>Free resources:</strong> Educational materials, webinars, and trading guides</li>
</ul>

<h2>FTMO Discount Codes & Promotions</h2>
<p>FTMO occasionally runs promotions. Current ways to save:</p>
<ul>
    <li><strong>Retry discount:</strong> 20% off if you failed your first challenge</li>
    <li><strong>Holiday sales:</strong> Black Friday, New Year, and anniversary promotions</li>
    <li><strong>Referral program:</strong> Earn discounts by referring other traders</li>
</ul>

<h2>The Best Way to Save Money</h2>
<p>Instead of looking for discount codes, the best way to save on FTMO is to pass on your first attempt. Use tools like our <a href="{TRACKER_URL}">free FTMO tracker</a> to avoid rule violations and pass the first time.</p>

<div class="info">
<strong>Pro Tip:</strong> Start with a smaller account size ($10k or $25k) to minimize your initial investment while you learn the platform.
</div>

{cta}
"""
    },
    # === Strategy & Education ===
    {
        "slug": "ftmo-trading-strategies-that-work",
        "title": "FTMO Trading Strategies That Actually Work — Backtested Approaches for Passing",
        "description": "Learn trading strategies that work for FTMO challenges. Includes trend following, breakout, and scalping approaches that help you pass.",
        "keywords": "FTMO strategy, FTMO trading strategy, best strategy for FTMO, FTMO scalping, FTMO trend following",
        "content": """
<h1>FTMO Trading Strategies That Actually Work</h1>
<p>Not all trading strategies are suitable for FTMO challenges. Here are the approaches that consistently help traders pass.</p>

<h2>1. Trend Following (Most Reliable)</h2>
<p>Trend following is the most popular strategy among successful FTMO traders. Why? Because it has defined risk parameters and doesn't require constant monitoring.</p>
<ul>
    <li><strong>Timeframe:</strong> 1H-4H charts</li>
    <li><strong>Entry:</strong> Pullback to moving average (20 EMA or 50 SMA)</li>
    <li><strong>Stop loss:</strong> Below recent swing low/high</li>
    <li><strong>Take profit:</strong> 2-3x risk (RR ratio)</li>
    <li><strong>Daily risk:</strong> Max 0.5% of account per trade</li>
</ul>

<h2>2. Breakout Trading (Good for Phase 2)</h2>
<p>Breakout strategies work well when you need quick results in Phase 2's shorter target.</p>
<ul>
    <li><strong>Key levels:</strong> Support/resistance from higher timeframes</li>
    <li><strong>Entry:</strong> Candle close above/below level</li>
    <li><strong>Stop loss:</strong> Inside the range</li>
    <li><strong>Volume confirmation:</strong> Higher volume on breakout</li>
</ul>

<h2>3. Scalping (for Experienced Traders)</h2>
<p>Scalping can work for FTMO if you're disciplined about daily loss limits.</p>
<ul>
    <li><strong>Timeframe:</strong> 1-5 minute charts</li>
    <li><strong>Max daily trades:</strong> 5-10</li>
    <li><strong>Stop loss:</strong> Always use tight stops</li>
    <li><strong>Daily profit target:</strong> 0.5% — stop after reaching it</li>
</ul>

<h2>Strategy Selection Guide</h2>
<table>
    <tr><th>Your Style</th><th>Recommended Strategy</th><th>Best Challenge</th></tr>
    <tr><td>Patient, analysis-driven</td><td>Trend Following</td><td>2-Step $100k+</td></tr>
    <tr><td>Quick decision maker</td><td>Breakout Trading</td><td>2-Step Phase 2</td></tr>
    <tr><td>Fast execution</td><td>Scalping</td><td>2-Step (not 1-Step)</td></tr>
</table>

<div class="warning">
<strong>Important:</strong> Whatever strategy you choose, track your rules with our <a href="{TRACKER_URL}">free tracker</a>. Most strategy failures come from rule violations, not bad trades.
</div>

{cta}
"""
    },
    {
        "slug": "ftmo-challenge-for-beginners",
        "title": "FTMO Challenge for Beginners — Step-by-Step Guide to Getting Funded",
        "description": "Complete step-by-step guide for beginners taking their first FTMO challenge. From choosing an account size to getting funded.",
        "keywords": "FTMO for beginners, FTMO challenge beginner, first FTMO challenge, FTMO step by step, beginner prop trading",
        "content": """
<h1>FTMO Challenge for Beginners: Step-by-Step Guide</h1>
<p>Taking your first FTMO challenge can be overwhelming. This guide walks you through everything from account selection to getting funded.</p>

<h2>Step 1: Choose Your Challenge Type</h2>
<p>Start with the <strong>2-Step Challenge</strong>. It has more forgiving rules (5% daily loss limit) and no best day rule, making it better for beginners.</p>

<h2>Step 2: Pick Your Account Size</h2>
<p>Beginners should start with $10,000 or $25,000. The fees are lower (€155-€255) and the profit targets are more achievable while you learn the process.</p>

<h2>Step 3: Learn the Rules</h2>
<p>Before you trade, understand every rule:</p>
<ul>
    <li>Profit target: 10% Phase 1, 5% Phase 2</li>
    <li>Max drawdown: 10% from peak balance</li>
    <li>Daily loss limit: 5% (based on previous day close)</li>
    <li>Minimum trading days: 4 per phase</li>
</ul>
<p>Use our <a href="{TRACKER_URL}">free FTMO tracker</a> to monitor all rules automatically.</p>

<h2>Step 4: Create Your Trading Plan</h2>
<ul>
    <li>Max risk per trade: 0.5% of account</li>
    <li>Daily profit target: 0.5-1%</li>
    <li>Stop trading after 2 consecutive losses</li>
    <li>Minimum 4 trading days per phase</li>
</ul>

<h2>Step 5: Start Trading</h2>
<p>Begin with small positions. Your goal in the first week is to build a 2-3% profit buffer. This gives you room to handle drawdown later.</p>

<h2>Step 6: Track Everything</h2>
<p>After each trading day, log your ending balance in the <a href="{TRACKER_URL}">free tracker</a>. It automatically calculates P&L, drawdown, and progress.</p>

<h2>Step 7: Pass and Get Funded</h2>
<p>Once you hit your profit target and meet all requirements, FTMO verifies your challenge (24-48 hours) and you receive your funded account.</p>

<div class="tip">
<strong>Beginner Tip:</strong> 60% of FTMO challenges fail from rule violations, not trading losses. Track your rules and you're already ahead of most traders.
</div>

{cta}
"""
    },
    # === Advanced Topics ===
    {
        "slug": "ftmo-funded-account-management",
        "title": "FTMO Funded Account Management — How to Trade and Withdraw After Passing",
        "description": "Learn how to manage your FTMO funded account after passing. Includes withdrawal procedures, profit splits, and account maintenance tips.",
        "keywords": "FTMO funded account, FTMO withdrawal, FTMO profit withdrawal, FTMO account management, FTMO payout",
        "content": """
<h1>FTMO Funded Account Management: After You Pass</h1>
<p>Congratulations on passing! Now you need to know how to manage your funded account, make withdrawals, and maintain good standing.</p>

<h2>Profit Split Tiers</h2>
<table>
    <tr><th>Account Performance</th><th>Your Split</th><th>FTMO Split</th></tr>
    <tr><td>Standard</td><td>80%</td><td>20%</td></tr>
    <tr><td>Top Performer (6+ months)</td><td>90%</td><td>10%</td></tr>
</table>

<h2>Withdrawal Process</h2>
<ol>
    <li><strong>Request payout</strong> through the FTMO dashboard</li>
    <li><strong>Verification:</strong> FTMO reviews your recent trading (24-48 hours)</li>
    <li><strong>Payment:</strong> Funds sent via bank transfer, crypto, or Skrill</li>
    <li><strong>Timeline:</strong> Usually 3-7 business days</li>
</ol>

<h2>Account Maintenance Rules</h2>
<p>Once funded, you must follow these rules to keep your account:</p>
<ul>
    <li>Maintain consistent trading activity</li>
    <li>Respect the same rules (drawdown, daily loss)</li>
    <li>No prohibited strategies (grid trading, latency arbitrage)</li>
    <li>Minimum trading activity per period</li>
</ul>

<h2>How to Maximize Your Funded Account</h2>
<ul>
    <li>Aim for 2-5% monthly returns consistently</li>
    <li>Withdraw profits monthly to build your personal capital</li>
    <li>Track your performance with our <a href="{TRACKER_URL}\">free tracker</a></li>
    <li>Use <a href="https://t.me/ArdTradingBot">@ArdTradingBot</a> on Telegram for quick status checks</li>
</ul>

{cta}
"""
    },
    {
        "slug": "how-to-pass-ftmo-phase-1-fast",
        "title": "How to Pass FTMO Phase 1 Fast — Efficient Strategies for the 10% Target",
        "description": "Learn how to pass FTMO Phase 1 efficiently. Strategies for hitting the 10% profit target while managing risk and respecting all rules.",
        "keywords": "pass FTMO Phase 1, FTMO Phase 1 fast, FTMO 10% target, FTMO Phase 1 strategy",
        "content": """
<h1>How to Pass FTMO Phase 1 Fast</h1>
<p>Phase 1 requires 10% profit. Here's how to hit that target efficiently while staying within all the rules.</p>

<h2>The Efficient Phase 1 Strategy</h2>

<h3>Week 1: Build Your Buffer (Goal: 2-3%)</h3>
<ul>
    <li>Trade small: 0.3-0.5% risk per trade</li>
    <li>Daily target: 0.5%</li>
    <li>Stop after reaching 1% or after 2 losses</li>
</ul>

<h3>Week 2: Scale Up (Goal: 5-6%)</h3>
<ul>
    <li>Increase to 0.5-0.7% risk per trade</li>
    <li>You now have a drawdown buffer</li>
    <li>Look for high-probability setups</li>
</ul>

<h3>Week 3: Push for Target (Goal: 10%)</h3>
<ul>
    <li>Maintain consistent risk levels</li>
    <li>Don't rush — the target will come naturally</li>
    <li>Meet minimum 4 trading days requirement</li>
</ul>

<h2>What NOT to Do</h2>
<ul>
    <li>Don't increase risk to rush the target</li>
    <li>Don't trade when emotional after a loss</li>
    <li>Don't ignore drawdown tracking</li>
    <li>Don't forget minimum trading days</li>
</ul>

<div class="tip">
Use our <a href="{TRACKER_URL}">free FTMO tracker</a> to see real-time progress toward your 10% target with automatic drawdown calculation.
</div>

{cta}
"""
    },
    {
        "slug": "ftmo-rules-cheat-sheet",
        "title": "FTMO Rules Cheat Sheet — Quick Reference Guide for Every Rule",
        "description": "Printable FTMO rules cheat sheet. Quick reference for profit targets, drawdown limits, daily loss limits, and best day rule for all challenge types.",
        "keywords": "FTMO cheat sheet, FTMO rules reference, FTMO quick guide, printable FTMO rules",
        "content": """
<h1>FTMO Rules Cheat Sheet — Quick Reference</h1>
<p>Printable quick reference for all FTMO challenge rules. Keep this open while trading.</p>

<h2>2-Step Challenge Rules</h2>
<table>
    <tr><th>Rule</th><th>Value</th><th>Example ($50k)</th></tr>
    <tr><td>Phase 1 Profit Target</td><td>10%</td><td>$5,000</td></tr>
    <tr><td>Phase 2 Profit Target</td><td>5%</td><td>$2,500</td></tr>
    <tr><td>Max Drawdown</td><td>10% (from peak)</td><td>From $55k peak: $5,500 max loss</td></tr>
    <tr><td>Daily Loss Limit</td><td>5% (prev day close)</td><td>After $51k day: $2,550 max loss</td></tr>
    <tr><td>Min Trading Days</td><td>4 per phase</td><td>4 calendar days minimum</td></tr>
    <tr><td>Best Day Rule</td><td>No</td><td>Not applicable</td></tr>
</table>

<h2>1-Step Challenge Rules</h2>
<table>
    <tr><th>Rule</th><th>Value</th><th>Example ($50k)</th></tr>
    <tr><td>Profit Target</td><td>10%</td><td>$5,000</td></tr>
    <tr><td>Max Drawdown</td><td>10% (from peak)</td><td>From $55k peak: $5,500 max loss</td></tr>
    <tr><td>Daily Loss Limit</td><td>3% (prev day close)</td><td>After $51k day: $1,530 max loss</td></tr>
    <tr><td>Min Trading Days</td><td>None</td><td>No minimum</td></tr>
    <tr><td>Best Day Rule</td><td>Yes (≤50% of profit)</td><td>Best day $3k → need total $6k+</td></tr>
</table>

<h2>Drawdown Formula (MOST IMPORTANT)</h2>
<div class="warning">
<strong>Drawdown % = (Peak Balance - Current Balance) / Peak Balance × 100</strong><br>
NOT (Current - Start) / Start × 100 — this is the #1 mistake!
</div>

<h2>Daily Loss Formula</h2>
<div class="info">
<strong>Daily Loss % = (Today's Balance - Yesterday's Balance) / Yesterday's Balance × 100</strong><br>
The daily loss limit is based on PREVIOUS day's close, not starting balance.
</div>

<h2>Quick Tips</h2>
<ul>
    <li>Track everything with our <a href="{TRACKER_URL}">free FTMO tracker</a></li>
    <li>Stop after 2 consecutive losing days</li>
    <li>Never risk more than 50% of daily loss limit in one trade</li>
    <li>If you feel emotional, don't trade</li>
</ul>

{cta}
"""
    },
    {
        "slug": "ftmo-prohibited-strategies",
        "title": "FTMO Prohibited Trading Strategies — What's NOT Allowed and How to Avoid Getting Banned",
        "description": "Complete list of FTMO prohibited trading strategies. Learn what strategies are banned, why, and how to avoid getting flagged.",
        "keywords": "FTMO prohibited strategies, FTMO banned strategies, FTMO rules violation, FTMO banned trading",
        "content": """
<h1>FTMO Prohibited Trading Strategies</h1>
<p>FTMO has a list of prohibited trading strategies. Using them can result in challenge failure or account termination — even if you're profitable.</p>

<h2>Strategies That Will Get You Banned</h2>

<h3>1. Grid Trading</h3>
<p>Placing buy and sell orders at multiple levels to profit from market oscillations. FTMO considers this an automated strategy that doesn't reflect genuine trading skill.</p>

<h3>2. Hedging</h3>
<p>Opening opposite positions on the same or correlated instruments to lock in small profits. This is seen as exploiting the system rather than trading.</p>

<h3>3. Latency Arbitrage</h3>
<p>Exploiting price differences between brokers using high-speed execution. This is explicitly banned and monitored.</p>

<h3>4. Copy Trading (as leader)</h3>
<p>Having other traders copy your trades while you're in an FTMO challenge. You can copy others, but you can't be copied.</p>

<h3>5. News Scalping</h3>
<p>Opening large positions just before major news events and closing immediately after. FTMO views this as gambling, not trading.</p>

<h3>6. Using EAs Without Approval</h3>
<p>Automated trading systems (Expert Advisors) must comply with FTMO's rules. Many EAs are prohibited.</p>

<h2>Safe Alternatives</h2>
<ul>
    <li>Manual trend following</li>
    <li>Breakout trading with defined levels</li>
    <li>Supply and demand zone trading</li>
    <li>Price action strategies</li>
</ul>

<div class="tip">
The best way to avoid prohibited strategies: focus on clean, manual trading and track every trade with our <a href="{TRACKER_URL}">free FTMO tracker</a>.
</div>

{cta}
"""
    },
    # === Comparison & Selection ===
    {
        "slug": "ftmo-50k-vs-100k-account",
        "title": "FTMO $50k vs $100k Account — Which Challenge Should You Take?",
        "description": "Compare FTMO $50k and $100k challenges. See the fees, profit targets, and which account size is best for your trading style.",
        "keywords": "FTMO 50k vs 100k, FTMO 50k challenge, FTMO 100k challenge, FTMO account comparison",
        "content": """
<h1>FTMO $50k vs $100k: Which Account is Right for You?</h1>
<p>Two of FTMO's most popular account sizes. Here's how they compare.</p>

<h2>Side by Side Comparison</h2>
<table>
    <tr><th>Feature</th><th>$50,000</th><th>$100,000</th></tr>
    <tr><td>Challenge Fee</td><td>€355</td><td>€540</td></tr>
    <tr><td>Phase 1 Target (10%)</td><td>$5,000</td><td>$10,000</td></tr>
    <tr><td>Phase 2 Target (5%)</td><td>$2,500</td><td>$5,000</td></tr>
    <tr><td>Max Drawdown</td><td>$5,000</td><td>$10,000</td></tr>
    <tr><td>Daily Loss Limit (2-Step)</td><td>$2,500</td><td>$5,000</td></tr>
    <tr><td>Retry Discount Fee</td><td>€284</td><td>€432</td></tr>
    <tr><td>Profit at 5%/month</td><td>$2,500</td><td>$5,000</td></tr>
</table>

<h2>Choose $50k If:</h2>
<ul>
    <li>You're newer to FTMO challenges</li>
    <li>Lower fee = less financial pressure</li>
    <li>$5,000 profit target feels achievable</li>
    <li>You want lower psychological pressure</li>
</ul>

<h2>Choose $100k If:</h2>
<ul>
    <li>You have experience with prop firm challenges</li>
    <li>You can handle larger position sizes</li>
    <li>You want higher earning potential ($5k/month at 5%)</li>
    <li>The fee difference (€185) isn't a concern</li>
</ul>

<div class="tip">
Track either challenge with our <a href="{TRACKER_URL}">free FTMO tracker</a> — it works for any account size.
</div>

{cta}
"""
    },
    {
        "slug": "ftmo-profit-split-explained",
        "title": "FTMO Profit Split Explained — How Much Do You Keep? 80% vs 90% Split",
        "description": "FTMO profit split explained. Learn how the 80-90% profit split works, how to qualify for 90%, and how to calculate your earnings.",
        "keywords": "FTMO profit split, FTMO 80%, FTMO 90%, FTMO payout, FTMO how much you keep",
        "content": """
<h1>FTMO Profit Split: How Much Do You Actually Keep?</h1>
<p>FTMO offers one of the best profit splits in the industry. Here's exactly how it works.</p>

<h2>Standard Profit Split: 80%</h2>
<p>All funded traders start with an 80% profit split. For every $1,000 you make, you keep $800. FTMO keeps $200.</p>

<table>
    <tr><th>Monthly Profit</th><th>Your 80% Share</th><th>FTMO's 20%</th></tr>
    <tr><td>$1,000</td><td>$800</td><td>$200</td></tr>
    <tr><td>$2,500</td><td>$2,000</td><td>$500</td></tr>
    <tr><td>$5,000</td><td>$4,000</td><td>$1,000</td></tr>
    <tr><td>$10,000</td><td>$8,000</td><td>$2,000</td></tr>
</table>

<h2>Top Performer Split: 90%</h2>
<p>After 6+ months of consistent profitable trading, you can qualify for a 90% split.</p>
<ul>
    <li><strong>Requirements:</strong> 6+ months profitable, no major violations</li>
    <li><strong>At 90%:</strong> Keep $900 per $1,000 made</li>
    <li><strong>Difference:</strong> $100 more per $1,000 vs standard split</li>
</ul>

<h2>Profit Split vs Other Firms</h2>
<ul>
    <li>FTMO: 80-90% ✅</li>
    <li>The Funded Trader: 80-90% ✅</li>
    <li>E8 Markets: 80-90% ✅</li>
    <li>Industry average: 75-80%</li>
</ul>

<h2>How to Maximize Your Earnings</h2>
<ul>
    <li>Track all rules with our <a href="{TRACKER_URL}">free tracker</a></li>
    <li>Withdraw profits monthly</li>
    <li>Aim for consistent 2-5% monthly returns</li>
    <li>Use <a href="https://t.me/ArdTradingBot">@ArdTradingBot</a> for quick tracking</li>
</ul>

{cta}
"""
    },
    # === Scenarios & Examples ===
    {
        "slug": "ftmo-challenge-50k-example",
        "title": "FTMO $50k Challenge Example — Complete Walkthrough from Start to Funded",
        "description": "Follow a complete FTMO $50k challenge example. See how a trader navigates Phase 1, Phase 2, and gets funded step by step.",
        "keywords": "FTMO 50k example, FTMO challenge walkthrough, FTMO 50k funded, FTMO example trade",
        "content": """
<h1>FTMO $50k Challenge: Complete Walkthrough</h1>
<p>Follow this real-world example of a trader completing their $50k FTMO challenge from start to funded account.</p>

<h2>Setup</h2>
<ul>
    <li><strong>Challenge:</strong> 2-Step, $50,000</li>
    <li><strong>Fee Paid:</strong> €355</li>
    <li><strong>Strategy:</strong> Trend following on 1H chart</li>
    <li><strong>Max Risk:</strong> 0.5% per trade ($250)</li>
</ul>

<h2>Phase 1: Days 1-7</h2>
<table>
    <tr><th>Day</th><th>Balance</th><th>P&L</th><th>Drawdown</th><th>Notes</th></tr>
    <tr><td>Start</td><td>$50,000</td><td>-</td><td>0%</td><td>Set up challenge</td></tr>
    <tr><td>Day 1</td><td>$50,400</td><td>+$400</td><td>0%</td><td>Small win, felt market</td></tr>
    <tr><td>Day 2</td><td>$50,150</td><td>-$250</td><td>0.5%</td><td>Took a loss, stopped</td></tr>
    <tr><td>Day 3</td><td>$50,750</td><td>+$600</td><td>0%</td><td>Good trend day</td></tr>
    <tr><td>Day 4</td><td>$51,500</td><td>+$750</td><td>0%</td><td>Met min trading days ✅</td></tr>
    <tr><td>Days 5-7</td><td>$55,500</td><td>+$4,000</td><td>0%</td><td>Phased in, hit target ✅</td></tr>
</table>
<p><strong>Phase 1 Complete:</strong> 7 days, +$5,500 (11%), no violations</p>

<h2>Phase 2: Days 8-12</h2>
<table>
    <tr><th>Day</th><th>Balance</th><th>P&L</th><th>Drawdown</th><th>Notes</th></tr>
    <tr><td>Start Ph2</td><td>$50,000</td><td>-</td><td>0%</td><td>Account reset</td></tr>
    <tr><td>Day 8</td><td>$50,600</td><td>+$600</td><td>0%</td><td>Slow start, patient</td></tr>
    <tr><td>Days 9-12</td><td>$52,800</td><td>+$2,200</td><td>0.3%</td><td>Steady wins, stayed disciplined</td></tr>
</table>
<p><strong>Phase 2 Complete:</strong> 5 days, +$2,800 (5.6%), met 4 trading days ✅</p>

<h2>Verification & Funded</h2>
<ul>
    <li><strong>Total time:</strong> 12 trading days</li>
    <li><strong>Total profit:</strong> $8,300 across both phases</li>
    <li><strong>Fee recovered:</strong> €355 (covered by first $500 of Phase 1 profit)</li>
    <li><strong>Funded account:</strong> $50,000, 80% profit split</li>
</ul>

<h2>Net Earnings Potential (Funded)</h2>
<ul>
    <li>At 3% monthly: $1,500 → keep $1,200</li>
    <li>At 5% monthly: $2,500 → keep $2,000</li>
    <li>At 10% monthly: $5,000 → keep $4,000</li>
</ul>

<div class="tip">
Track your own challenge journey with our <a href="{TRACKER_URL}">free FTMO tracker</a>. See real-time progress just like this example.
</div>

{cta}
"""
    },
    # === Additional Help ===
    {
        "slug": "ftmo-challenge-calculator",
        "title": "FTMO Challenge Calculator — Free Tool to Calculate Profit Targets, Drawdown & Daily Limits",
        "description": "Free FTMO challenge calculator. Calculate profit targets, drawdown limits, and daily loss limits for any account size and challenge type.",
        "keywords": "FTMO challenge calculator, FTMO calculator, FTMO profit calculator, FTMO drawdown calculator free",
        "content": """
<h1>FTMO Challenge Calculator — Free Tool</h1>
<p>Use this calculator to quickly determine your profit targets, drawdown limits, and daily loss limits for any FTMO challenge.</p>

<h2>Quick Calculation Table</h2>
<table>
    <tr><th>Account Size</th><th>10% Target</th><th>5% Target</th><th>Max Drawdown</th><th>Daily Loss (2-Step)</th><th>Daily Loss (1-Step)</th></tr>
    <tr><td>$10,000</td><td>$1,000</td><td>$500</td><td>$1,000</td><td>$500</td><td>$300</td></tr>
    <tr><td>$25,000</td><td>$2,500</td><td>$1,250</td><td>$2,500</td><td>$1,250</td><td>$750</td></tr>
    <tr><td>$50,000</td><td>$5,000</td><td>$2,500</td><td>$5,000</td><td>$2,500</td><td>$1,500</td></tr>
    <tr><td>$100,000</td><td>$10,000</td><td>$5,000</td><td>$10,000</td><td>$5,000</td><td>$3,000</td></tr>
    <tr><td>$200,000</td><td>$20,000</td><td>$10,000</td><td>$20,000</td><td>$10,000</td><td>$6,000</td></tr>
</table>

<h2>How to Calculate Yourself</h2>
<div class="info">
<strong>Profit Target (Phase 1):</strong> Account Size × 0.10<br>
<strong>Profit Target (Phase 2):</strong> Account Size × 0.05<br>
<strong>Max Drawdown:</strong> Account Size × 0.10<br>
<strong>Daily Loss (2-Step):</strong> Previous Balance × 0.05<br>
<strong>Daily Loss (1-Step):</strong> Previous Balance × 0.03
</div>

<h2>Drawdown from Peak Formula</h2>
<p>Remember: drawdown is calculated from your HIGHEST balance, not starting.</p>
<div class="warning">
<strong>Actual Drawdown % = (Peak - Current) / Peak × 100</strong><br>
Example: Start $50k → Peak $54k → Current $51k<br>
Drawdown = ($54k - $51k) / $54k × 100 = <strong>5.56%</strong>
</div>

<p>Don't calculate manually. Use our <a href="{TRACKER_URL}">free FTMO tracker</a> for automatic, real-time calculations.</p>

{cta}
"""
    },
    {
        "slug": "ftmo-max-drawdown-explained",
        "title": "FTMO Max Drawdown Explained — Complete Guide with Examples & Calculator",
        "description": "Everything about FTMO max drawdown. Learn how the 10% drawdown limit works, with examples, common mistakes, and a free tracking tool.",
        "keywords": "FTMO max drawdown, FTMO 10% drawdown, FTMO drawdown limit, FTMO how drawdown works",
        "content": """
<h1>FTMO Max Drawdown: Complete Guide</h1>
<p>The 10% max drawdown rule is the most failed FTMO rule. Here's exactly how it works, with examples and common mistakes.</p>

<h2>How FTMO Drawdown Works</h2>
<p>FTMO's max drawdown is <strong>10% of your peak account balance</strong>. This means:</p>
<ul>
    <li>If your balance only goes down, drawdown is from starting balance</li>
    <li>If you make profit and then lose, drawdown is from the highest point</li>
    <li>The drawdown limit is STATIC (always 10% of starting balance) — but it's calculated from your PEAK</li>
</ul>

<h2>Example Scenarios</h2>
<table>
    <tr><th>Scenario</th><th>Start</th><th>Peak</th><th>Now</th><th>Drawdown</th><th>Status</th></tr>
    <tr><td>Losses only</td><td>$50,000</td><td>$50,000</td><td>$46,000</td><td>8%</td><td>⚠️ Warning</td></tr>
    <tr><td>Up then lose</td><td>$50,000</td><td>$55,000</td><td>$50,000</td><td>9.1%</td><td>⚠️ Critical</td></tr>
    <tr><td>Small profit</td><td>$50,000</td><td>$51,000</td><td>$50,500</td><td>0.98%</td><td>✅ Safe</td></tr>
    <tr><td>Breach</td><td>$50,000</td><td>$56,000</td><td>$50,000</td><td>10.7%</td><td>❌ Failed</td></tr>
</table>

<h2>Critical Insight</h2>
<div class="warning">
<strong>You can fail even while being profitable overall.</strong> In Scenario 2 above, the trader is at break-even ($50k from $50k start) but has 9.1% drawdown because their peak was $55k. One more bad day and they fail — despite not losing any money overall.
</div>

<h2>How to Avoid Drawdown Failure</h2>
<ul>
    <li>Track drawdown from peak, not starting balance</li>
    <li>Use our <a href="{TRACKER_URL}">free FTMO tracker</a> for automatic drawdown calculation</li>
    <li>If drawdown exceeds 5%, reduce position sizes</li>
    <li>Never increase risk to recover from drawdown</li>
</ul>

{cta}
"""
    },
]

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
