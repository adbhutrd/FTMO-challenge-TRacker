#!/usr/bin/env python3
"""
📬 Campaign Manager — Run Email Campaigns & Automation Sequences
=================================================================
Handles campaign execution, automated sequences, subscriber management,
and report generation. This is the engine that makes everything run.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from .contacts import ContactDB
from .sender import EmailSender

logger = logging.getLogger("email_marketing.campaigns")

BASE_DIR = Path.home() / "income"


class CampaignManager:
    """Manages email campaigns and automation sequences."""

    def __init__(self):
        self.db = ContactDB()
        self.sender = EmailSender(self.db)

    # ── Campaign Execution ──

    def send_campaign(self, campaign_id: int) -> Dict:
        """Execute a campaign to all target subscribers."""
        campaign = self.db.get_campaign(campaign_id)
        if not campaign:
            return {"error": f"Campaign #{campaign_id} not found"}

        logger.info(f"📬 Starting campaign #{campaign_id}: {campaign['name']}")

        # Get target contacts
        target_tags = json.loads(campaign["target_tags"]) if campaign["target_tags"] else []
        if target_tags:
            contacts = []
            for tag in target_tags:
                contacts.extend(self.db.get_contacts_by_tag(tag))
            # Deduplicate
            seen = set()
            contacts = [c for c in contacts if not (c["id"] in seen or seen.add(c["id"]))]
        else:
            contacts = self.db.get_all_contacts()

        if not contacts:
            logger.warning(f"⚠️  No contacts to send campaign #{campaign_id}")
            return {"sent": 0, "total": 0}

        logger.info(f"   Target: {len(contacts)} contacts")

        # Mark campaign as sending
        self.db.send_campaign(campaign_id)

        # Send to each contact
        results = {"sent": 0, "failed": 0, "total": len(contacts)}
        for contact in contacts:
            success = self.sender.send_campaign_email(
                to_email=contact["email"],
                subject=campaign["subject"],
                html_body=self._get_campaign_html(campaign, contact),
                contact_id=contact["id"],
                campaign_id=campaign_id,
            )
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1

            # Small delay to avoid rate limiting
            if len(contacts) > 10:
                time.sleep(0.5)

        # Mark campaign as sent
        self.db._get_conn().execute(
            "UPDATE campaigns SET status = 'sent' WHERE id = ?", (campaign_id,)
        )
        self.db._get_conn().commit()

        logger.info(f"✅ Campaign #{campaign_id} complete: {results['sent']}/{results['total']} sent")
        return results

    def _get_campaign_html(self, campaign: Dict, contact: Dict) -> str:
        """Get the HTML for a campaign email."""
        from .templates import newsletter_email, promotional_email

        name = contact.get("name", "")
        greeting = f"Hi {name}," if name else "Hi there,"

        # Default content based on campaign name
        content = f"""
        <p style="margin:0 0 16px">{greeting}</p>
        <p style="margin:0 0 16px">Here's your latest update from FTMO Tracker Pro.</p>
        <p style="margin:0 0 16px">We're constantly improving our tools to help you pass your FTMO challenge. Check out the latest features and tips on our site.</p>
        <p style="margin:0 0 0">Happy trading! 🚀</p>
        <p style="margin:8px 0 0;color:#8b949e;font-size:13px">— The FTMO Tracker Team</p>
        """

        return newsletter_email(
            title=campaign["subject"],
            content=content,
            cta_url="https://bright-palmier-d43338.netlify.app/ftmo_challenge_tracker.html",
            cta_text="🎯 Track Your Challenge",
        )

    # ── Sequence Processing ──

    def process_sequences(self) -> int:
        """Process all automated sequences - send any due emails."""
        due_emails = self.db.get_due_sequence_emails()
        sent = 0

        for entry in due_emails:
            # Get template
            from .templates import welcome_email, newsletter_email

            if entry["template"] == "welcome":
                html = welcome_email(entry["name"])
            elif entry["template"] == "daily_tip":
                html = self._get_tip_email()
            else:
                html = newsletter_email(
                    title=entry["subject"],
                    content=f"<p>Here's your update from FTMO Tracker Pro.</p>"
                )

            success = self.sender.send_email(
                to_email=entry["email"],
                subject=entry["subject"],
                html_body=html,
                contact_id=entry["contact_id"],
            )

            if success:
                self.db.advance_sequence(entry["progress_id"])
                sent += 1

            time.sleep(0.5)  # Rate limiting

        if sent > 0:
            logger.info(f"📨 Sequence processor: sent {sent} emails")
        return sent

    def _get_tip_email(self) -> str:
        """Generate a random trading tip email."""
        import random
        tips = [
            {
                "title": "The 1% Rule",
                "body": "Never risk more than 1% of your account on a single trade. This is the golden rule of professional traders and absolutely critical for FTMO challenges where drawdown limits are strict.",
                "category": "📊 Risk Management",
            },
            {
                "title": "Track Your Best Day",
                "body": "In FTMO 1-Step challenges, the Best Day Rule means no single day can account for more than 50% of your total profit. Spread your wins across multiple days to stay compliant.",
                "category": "📋 FTMO Rules",
            },
            {
                "title": "Drawdown Math",
                "body": "FTMO's max drawdown is 10% of your initial balance. If you start with $100k, your equity can never fall below $90k. Track this religiously — it's the #1 reason challenges fail.",
                "category": "🛑 Drawdown",
            },
            {
                "title": "Minimum Trading Days",
                "body": "You need a minimum of 4 trading days in a 2-Step challenge. This means 4 separate days with at least 1 trade each. Don't rush to pass in 2 days — the rules won't let you.",
                "category": "📅 Challenge Rules",
            },
            {
                "title": "Phase 2 Strategy Shift",
                "body": "Phase 2 only requires 5% profit target (vs 10% in Phase 1). Adjust your risk accordingly — smaller, consistent gains in Phase 2 are safer and less stressful.",
                "category": "🎯 Strategy",
            },
            {
                "title": "The 5% Daily Loss Limit",
                "body": "In 2-Step challenges, you can't lose more than 5% of your account in a single day. If you're down 4% in a session, close everything and come back tomorrow.",
                "category": "⚠️ Daily Limits",
            },
            {
                "title": "Consistency Over Hero Mode",
                "body": "The traders who pass FTMO challenges aren't the ones making heroic 15% days — they're the ones making consistent 0.5-1% gains day after day. Slow and steady wins.",
                "category": "🏆 Mindset",
            },
            {
                "title": "Use Our Equity Curve",
                "body": "Our tracker's equity curve chart shows your balance over time with the drawdown limit and profit target lines. A rising curve that stays within bounds = a passing challenge.",
                "category": "📈 Tools",
            },
        ]
        tip = random.choice(tips)
        from .templates import daily_tip_email
        return daily_tip_email(tip["title"], tip["body"], tip["category"])

    # ── Welcome Sequence ──

    def setup_welcome_sequence(self) -> int:
        """Set up the default welcome sequence."""
        # Check if sequence already exists
        conn = self.db._get_conn()
        existing = conn.execute("SELECT id FROM sequences WHERE name = 'Welcome Sequence'").fetchone()
        if existing:
            return existing["id"]

        seq_id = self.db.create_sequence(
            "Welcome Sequence",
            "Automated welcome emails for new subscribers"
        )

        # Step 0: Immediate welcome
        self.db.add_sequence_step(seq_id, 0, 0, "🚀 Welcome to FTMO Tracker Pro!", "welcome")

        # Step 1: Day 1 - Quick start guide
        self.db.add_sequence_step(seq_id, 1, 24, "📋 Your FTMO Challenge Quick Start Guide")
        
        # Step 2: Day 3 - Pro tips
        self.db.add_sequence_step(seq_id, 2, 72, "📊 3 Pro Tips to Pass Your Challenge Faster")

        # Step 3: Day 7 - Pro offer
        self.db.add_sequence_step(seq_id, 3, 168, "🔥 Early Bird: 50% Off FTMO Tracker Pro")
        
        logger.info(f"✅ Welcome sequence created (ID: {seq_id})")
        return seq_id

    def enroll_new_subscriber(self, email: str, name: str = "", source: str = "manual") -> Optional[int]:
        """Add a subscriber and enroll them in the welcome sequence.
        The welcome email is sent by the sequence pipeline, not immediately.
        """
        contact_id = self.db.add_contact(email, name, source)
        if contact_id:
            # Enroll in sequence (Step 0 sends welcome after delay)
            self.setup_welcome_sequence()
            conn = self.db._get_conn()
            seq = conn.execute(
                "SELECT id FROM sequences WHERE name = 'Welcome Sequence' LIMIT 1"
            ).fetchone()
            if seq:
                self.db.enroll_in_sequence(contact_id, seq["id"])
            logger.info(f"🎉 New subscriber enrolled: {email}")
        return contact_id

    # ── Newsletter Creation ──

    def create_and_send_newsletter(self, subject: str, content_html: str = "",
                                   target_tag: str = "") -> int:
        """Create a newsletter campaign and optionally send it immediately."""
        campaign_id = self.db.create_campaign(
            name=subject[:100],
            subject=subject,
            template="newsletter",
            target_tags=[target_tag] if target_tag else [],
        )
        return campaign_id

    # ── Promotional Campaigns ──

    def create_promo_campaign(self, title: str, body_text: str,
                               cta_url: str, cta_text: str,
                               target_tag: str = "",
                               urgency: str = "") -> int:
        """Create a promotional campaign."""
        campaign_id = self.db.create_campaign(
            name=title[:100],
            subject=title,
            template="promotional",
            target_tags=[target_tag] if target_tag else [],
        )
        return campaign_id

    # ── Reports ──

    def generate_report(self) -> str:
        """Generate a comprehensive email marketing report."""
        stats = self.db.get_stats()

        report = f"""
{'='*60}
  📧 EMAIL MARKETING REPORT
  {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*60}

📊 SUBSCRIBERS
  Active: {stats['active']}
  Total: {stats['total']}
  Bounced: {stats['bounced']}
  Unsubscribed: {stats['unsubscribed']}

📬 CAMPAIGNS
  Total: {stats['total_campaigns']}
  Sent: {stats['sent_campaigns']}
  Total Opens: {stats['total_opens']}
  Total Clicks: {stats['total_clicks']}
  Open Rate: {stats.get('open_rate', 0)}%

⚡ SEQUENCES
  Active: {stats['active_sequences']}
        """
        print(report)
        return report

    # ── Full Pipeline Run ──

    def run_pipeline(self) -> Dict:
        """Run the full email marketing pipeline: process sequences, check for pending campaigns."""
        results = {}

        # Process automated sequences
        seq_sent = self.process_sequences()
        results["sequence_emails_sent"] = seq_sent

        # Check for scheduled campaigns that need sending
        conn = self.db._get_conn()
        pending = conn.execute(
            "SELECT * FROM campaigns WHERE status = 'draft' AND scheduled_at IS NOT NULL AND scheduled_at <= datetime('now')"
        ).fetchall()
        
        for campaign in pending:
            camp_results = self.send_campaign(campaign["id"])
            results[f"campaign_{campaign['id']}"] = camp_results

        # Generate report
        self.generate_report()
        results["stats"] = self.db.get_stats()

        return results


def main():
    """CLI entry point."""
    import sys
    
    manager = CampaignManager()

    if len(sys.argv) < 2:
        print("""
📧 Email Marketing Manager — Usage:
  pipeline          Run full pipeline (sequences + pending campaigns)
  report            Show email marketing stats
  welcome <email>   Send welcome email and enroll subscriber
  newsletter <subj> Create a new newsletter campaign
  test              Test email connection
        """)
        return

    cmd = sys.argv[1]

    if cmd == "pipeline":
        manager.run_pipeline()
    elif cmd == "report":
        manager.generate_report()
    elif cmd == "welcome" and len(sys.argv) > 2:
        email = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else ""
        manager.enroll_new_subscriber(email, name)
    elif cmd == "test":
        manager.sender.test_connection()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
