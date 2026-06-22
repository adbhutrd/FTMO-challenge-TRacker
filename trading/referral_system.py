#!/usr/bin/env python3
"""
💰 REFERRAL SYSTEM — Affiliate Tracking for FTMO Tracker
=========================================================
Generates unique referral links, tracks signups, and manages payouts.
Adds referral tracking to the web tracker HTML.

Usage:
    python3 referral_system.py --generate <email>    # Generate referral link
    python3 referral_system.py --track <ref_code>    # Track a visit
    python3 referral_system.py --stats               # Show referral stats
    python3 referral_system.py --leaderboard         # Top referrers
    python3 referral_system.py --embed               # Generate tracker embed HTML
"""

import json
import os
import sys
import hashlib
import random
import string
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

BASE_DIR = Path.home()
TRADING_DIR = BASE_DIR / "trading"
DATA_DIR = TRADING_DIR / "referral_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | REFERRAL | %(message)s",
    handlers=[
        logging.FileHandler(TRADING_DIR / "referral_system.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("referral_system")


def generate_code(email: str = "") -> str:
    """Generate a unique referral code."""
    seed = email + datetime.now().isoformat() + str(random.random())
    hash_part = hashlib.md5(seed.encode()).hexdigest()[:8]
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"FTMO-{hash_part}{random_part}"


class ReferralSystem:
    """Manage referral codes, clicks, and conversions."""

    def __init__(self):
        self.refs_file = DATA_DIR / "referrals.json"
        self.clicks_file = DATA_DIR / "clicks.json"
        self.payouts_file = DATA_DIR / "payouts.json"
        self.load_data()

    def load_data(self):
        """Load all referral data."""
        # Referrers
        if self.refs_file.exists():
            try:
                self.referrers = json.loads(self.refs_file.read_text())
            except:
                self.referrers = {}
        else:
            self.referrers = {}

        # Click tracking
        if self.clicks_file.exists():
            try:
                self.clicks = json.loads(self.clicks_file.read_text())
            except:
                self.clicks = {"total_clicks": 0, "clicks": []}
        else:
            self.clicks = {"total_clicks": 0, "clicks": []}

        # Payouts
        if self.payouts_file.exists():
            try:
                self.payouts = json.loads(self.payouts_file.read_text())
            except:
                self.payouts = {"total_paid": 0.0, "pending": 0.0, "payouts": []}
        else:
            self.payouts = {"total_paid": 0.0, "pending": 0.0, "payouts": []}

        # Affiliate config
        self.commission_per_sale = 5.00  # $5 per Pro sale ($19.99)
        self.commission_pct = 0.25       # 25% commission
        self.min_payout = 20.00          # Min $20 to withdraw


    def save_all(self):
        """Persist all data."""
        self.refs_file.write_text(json.dumps(self.referrers, indent=2))
        self.clicks_file.write_text(json.dumps(self.clicks, indent=2, default=str))
        self.payouts_file.write_text(json.dumps(self.payouts, indent=2, default=str))

    def create_referrer(self, name: str, email: str) -> dict:
        """Create a new referrer with unique code."""
        if email in self.referrers:
            return {"error": "Email already registered", "referrer": self.referrers[email]}

        code = generate_code(email)
        referrer = {
            "name": name,
            "email": email,
            "code": code,
            "created": datetime.now().isoformat(),
            "clicks": 0,
            "conversions": 0,
            "earnings": 0.0,
            "referral_link": f"https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html?ref={code}",
            "active": True,
        }
        self.referrers[email] = referrer
        self.save_all()
        logger.info(f"✅ Referrer created: {name} ({code})")
        return {"success": True, "referrer": referrer}

    def track_click(self, ref_code: str, source: str = "direct") -> dict:
        """Track a referral link click."""
        # Find which referrer owns this code
        ref_email = None
        for email, data in self.referrers.items():
            if data["code"] == ref_code:
                ref_email = email
                data["clicks"] += 1
                break

        click = {
            "ref_code": ref_code,
            "ref_email": ref_email,
            "source": source,
            "ip_hash": "",  # Would store hashed IP in production
            "timestamp": datetime.now().isoformat(),
            "converted": False,
        }
        self.clicks["clicks"].append(click)
        self.clicks["total_clicks"] += 1
        self.save_all()
        return click

    def record_conversion(self, ref_code: str, amount: float = 19.99) -> dict:
        """Record a conversion (someone bought Pro)."""
        ref_email = None
        for email, data in self.referrers.items():
            if data["code"] == ref_code:
                ref_email = email
                commission = amount * self.commission_pct
                data["conversions"] += 1
                data["earnings"] += commission
                self.payouts["pending"] += commission
                break

        if ref_email:
            payout = {
                "ref_email": ref_email,
                "ref_code": ref_code,
                "sale_amount": amount,
                "commission": amount * self.commission_pct,
                "timestamp": datetime.now().isoformat(),
                "status": "pending",
            }
            self.payouts["payouts"].append(payout)
            self.save_all()
            logger.info(f"💰 Conversion recorded: {ref_email} earned ${amount * self.commission_pct:.2f}")
            return payout

        return {"error": "Referral code not found"}

    def process_payout(self, email: str) -> dict:
        """Process payout for a referrer."""
        if email not in self.referrers:
            return {"error": "Referrer not found"}

        ref = self.referrers[email]
        if ref["earnings"] < self.min_payout:
            return {"error": f"Minimum payout is ${self.min_payout}. Current: ${ref['earnings']:.2f}"}

        payout_amount = ref["earnings"]
        ref["earnings"] = 0
        self.payouts["total_paid"] += payout_amount
        self.payouts["pending"] -= payout_amount

        payout_record = {
            "email": email,
            "amount": payout_amount,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
        }
        self.payouts["payouts"].append(payout_record)
        self.save_all()
        logger.info(f"💰 Payout processed: {email} — ${payout_amount:.2f}")
        return {"success": True, "email": email, "amount": payout_amount}

    def get_leaderboard(self, limit: int = 10) -> List[dict]:
        """Get top referrers by earnings."""
        sorted_refs = sorted(
            [r for r in self.referrers.values() if r["active"]],
            key=lambda r: r["earnings"],
            reverse=True,
        )
        return [
            {
                "rank": i + 1,
                "name": r["name"],
                "code": r["code"],
                "clicks": r["clicks"],
                "conversions": r["conversions"],
                "earnings": r["earnings"],
            }
            for i, r in enumerate(sorted_refs[:limit])
        ]

    def generate_tracker_script(self) -> str:
        """Generate JavaScript snippet to embed in the tracker HTML."""
        return """
<script>
// Referral tracking for FTMO Challenge Tracker
(function() {
    // Check URL for referral code
    const urlParams = new URLSearchParams(window.location.search);
    const ref = urlParams.get('ref');
    
    if (ref) {
        // Store referral code
        localStorage.setItem('ftmo_ref_code', ref);
        localStorage.setItem('ftmo_ref_time', new Date().toISOString());
        
        // Track click via pixel (silent)
        const img = new Image();
        img.src = '/track?ref=' + encodeURIComponent(ref) + '&source=' + encodeURIComponent(document.referrer || 'direct');
    }
    
    // Add referral to any pro links
    const refCode = localStorage.getItem('ftmo_ref_code');
    if (refCode) {
        document.querySelectorAll('a[href*="gumroad.com/l/ezteprg"]').forEach(function(link) {
            const sep = link.href.includes('?') ? '&' : '?';
            link.href += sep + 'ref=' + encodeURIComponent(refCode) + '&referrer=' + encodeURIComponent(localStorage.getItem('ftmo_ref_name') || 'friend');
        });
    }
})();
</script>
        """

    def stats(self) -> dict:
        """Get overall stats."""
        total_referrers = len([r for r in self.referrers.values() if r["active"]])
        total_clicks = self.clicks["total_clicks"]
        total_conversions = sum(r["conversions"] for r in self.referrers.values())
        total_earnings = sum(r["earnings"] for r in self.referrers.values())
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

        return {
            "total_referrers": total_referrers,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_earnings": total_earnings,
            "conversion_rate": f"{conversion_rate:.1f}%",
            "pending_payouts": self.payouts["pending"],
            "total_paid": self.payouts["total_paid"],
        }

    def print_stats(self):
        """Print referral stats."""
        s = self.stats()
        print(f"\n{'='*60}")
        print(f"  💰 REFERRAL SYSTEM STATS")
        print(f"{'='*60}")
        print(f"  Referrers:    {s['total_referrers']}")
        print(f"  Total Clicks: {s['total_clicks']}")
        print(f"  Conversions:  {s['total_conversions']} ({s['conversion_rate']})")
        print(f"  Earnings:     ${s['total_earnings']:.2f}")
        print(f"  Paid Out:     ${s['total_paid']:.2f}")
        print(f"  Pending:      ${s['pending_payouts']:.2f}")
        print()

        lb = self.get_leaderboard()
        if lb:
            print(f"  🏆 Leaderboard:")
            for r in lb:
                print(f"    #{r['rank']} {r['name']:20s} | {r['conversions']} sales | ${r['earnings']:.2f}")
            print()


def main():
    system = ReferralSystem()

    if len(sys.argv) < 2:
        print("""
💰 REFERRAL SYSTEM — FTMO Affiliate Tracking

Commands:
  --generate <email> [name]   Create a referral link
  --track <ref_code>          Track a click
  --convert <ref_code>        Record a sale
  --payout <email>            Process payout
  --stats                     Show system stats
  --leaderboard               Show top referrers
  --embed                     Generate JS tracking snippet

Examples:
  python3 referral_system.py --generate trader@email.com "John Trader"
  python3 referral_system.py --track FTMO-abc123def
  python3 referral_system.py --stats
        """)
        return

    cmd = sys.argv[1]

    if cmd == "--generate":
        if len(sys.argv) < 3:
            print("❌ Usage: --generate <email> [name]")
            return
        email = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else email.split("@")[0]
        result = system.create_referrer(name, email)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            ref = result["referrer"]
            print(f"\n✅ Referral link created!")
            print(f"   Code: {ref['code']}")
            print(f"   Link: {ref['referral_link']}")
            print(f"   Share this link to earn ${system.commission_per_sale:.2f} per sale!")

    elif cmd == "--track":
        if len(sys.argv) < 3:
            print("❌ Usage: --track <ref_code>")
            return
        click = system.track_click(sys.argv[2])
        print(f"✅ Click tracked: {click['ref_code']}")

    elif cmd == "--convert":
        if len(sys.argv) < 3:
            print("❌ Usage: --convert <ref_code>")
            return
        result = system.record_conversion(sys.argv[2])
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ Sale recorded! Commission: ${result['commission']:.2f}")

    elif cmd == "--payout":
        if len(sys.argv) < 3:
            print("❌ Usage: --payout <email>")
            return
        result = system.process_payout(sys.argv[2])
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ Payout sent: ${result['amount']:.2f}")

    elif cmd == "--stats":
        system.print_stats()

    elif cmd == "--leaderboard":
        lb = system.get_leaderboard()
        if not lb:
            print("No referrers yet.")
        else:
            print(f"\n  🏆 TOP REFERRERS")
            for r in lb:
                print(f"    #{r['rank']} {r['name']:20s} | {r['clicks']} clicks | {r['conversions']} sales | ${r['earnings']:.2f}")
            print()

    elif cmd == "--embed":
        print(system.generate_tracker_script())

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
