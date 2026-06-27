#!/usr/bin/env python3
"""
🎨 Email Templates — HTML Email Templates for Marketing & Newsletters
======================================================================
Professional, responsive HTML email templates optimized for deliverability.
All templates are inline-styled for maximum email client compatibility.
"""

from datetime import datetime


def _base_template(body_html: str, title: str = "") -> str:
    """Base email wrapper with consistent branding."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title or "FTMO Tracker Pro"}</title></head>
<body style="margin:0;padding:0;background-color:#0d1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0d1117">
<tr><td align="center" style="padding:20px 10px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%">

<!-- Header -->
<tr><td style="padding:20px 0;text-align:center;border-bottom:1px solid #30363d">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="text-align:center">
<a href="https://bright-palmier-d43338.netlify.app" style="text-decoration:none">
<span style="font-size:24px;font-weight:800;background:linear-gradient(135deg,#7c3aed,#58a6ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">FTMO Tracker Pro</span>
</a>
</td>
</tr>
</table>
</td></tr>

<!-- Body -->
<tr><td style="padding:30px 0;color:#e6edf3;font-size:15px;line-height:1.7">
{body_html}
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 0;border-top:1px solid #30363d;text-align:center">
<p style="margin:0 0 8px;font-size:12px;color:#8b949e">
You're receiving this because you subscribed to FTMO Tracker Pro updates.
</p>
<p style="margin:0 0 8px;font-size:12px;color:#8b949e">
<a href="https://bright-palmier-d43338.netlify.app" style="color:#7c3aed;text-decoration:none">Unsubscribe</a> |
<a href="https://bright-palmier-d43338.netlify.app" style="color:#7c3aed;text-decoration:none">Visit Site</a>
</p>
<p style="margin:0;font-size:11px;color:#484f58">FTMO Tracker Pro · Not affiliated with FTMO.com</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _button_html(url: str, text: str, color: str = "#7c3aed") -> str:
    """Generate a responsive email button."""
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" style="margin:20px auto">
<tr><td align="center" style="background:{color};border-radius:8px;padding:0">
<a href="{url}" style="display:inline-block;padding:14px 32px;font-size:16px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px">{text}</a>
</td></tr>
</table>"""


# ── Templates ──

def welcome_email(name: str = "") -> str:
    """Welcome email for new subscribers."""
    greeting = f"Hi {name}," if name else "Hi there,"
    body = f"""
    <h2 style="color:#7c3aed;margin:0 0 16px">🚀 Welcome to FTMO Tracker Pro!</h2>
    <p style="margin:0 0 16px">{greeting}</p>
    <p style="margin:0 0 16px">Thanks for joining! You're now part of a growing community of traders who never miss a rule and pass their FTMO challenges with confidence.</p>

    <h3 style="color:#58a6ff;margin:24px 0 12px">🎯 Here's what you get:</h3>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 20px">
    <tr><td style="padding:6px 0;color:#e6edf3">✅ <strong>Free FTMO Tracker</strong> — Real-time rule checking</td></tr>
    <tr><td style="padding:6px 0;color:#e6edf3">✅ <strong>Drawdown Guardian</strong> — Never breach a rule again</td></tr>
    <tr><td style="padding:6px 0;color:#e6edf3">✅ <strong>Pro Tips & Strategies</strong> — Exclusive content</td></tr>
    <tr><td style="padding:6px 0;color:#e6edf3">✅ <strong>Early Access to Pro</strong> — 50% off launch pricing</td></tr>
    </table>

    {_button_html("https://bright-palmier-d43338.netlify.app/ftmo_challenge_tracker.html", "🎯 Start Tracking Free")}

    <p style="margin:20px 0 0;color:#8b949e;font-size:13px">Stay tuned for tips, strategies, and exclusive offers to help you pass your FTMO challenge faster.</p>
    <p style="margin:8px 0 0;color:#8b949e;font-size:13px">Happy trading! 🚀</p>
    """
    return _base_template(body, "Welcome to FTMO Tracker Pro!")


def newsletter_email(title: str, content: str, cta_url: str = "", cta_text: str = "") -> str:
    """Newsletter template for regular updates."""
    cta = _button_html(cta_url, cta_text) if cta_url and cta_text else ""
    body = f"""
    <h2 style="color:#7c3aed;margin:0 0 16px">{title}</h2>
    <div style="margin:0 0 16px;color:#e6edf3;font-size:15px;line-height:1.7">
    {content}
    </div>
    {cta}
    <p style="margin:20px 0 0;color:#8b949e;font-size:12px">— The FTMO Tracker Team</p>
    """
    return _base_template(body, title)


def promotional_email(title: str, body_text: str, cta_url: str, cta_text: str, urgency: str = "") -> str:
    """Promotional/sales email template."""
    urgency_banner = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 20px;background:rgba(210,153,34,0.12);border:1px solid rgba(210,153,34,0.3);border-radius:8px;width:100%">
    <tr><td style="padding:12px 16px;text-align:center;color:#d29922;font-size:14px;font-weight:600">{urgency}</td></tr>
    </table>""" if urgency else ""

    body = f"""
    <h2 style="color:#7c3aed;margin:0 0 16px">{title}</h2>
    {urgency_banner}
    <div style="margin:0 0 16px;color:#e6edf3;font-size:15px;line-height:1.7">
    {body_text}
    </div>
    {_button_html(cta_url, cta_text)}

    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:20px 0 0;background:#161b22;border:1px solid #30363d;border-radius:8px;width:100%">
    <tr><td style="padding:16px">
    <p style="margin:0;color:#8b949e;font-size:12px;text-align:center">
    🛡️ 30-day money-back guarantee · No questions asked
    </p>
    </td></tr>
    </table>
    """
    return _base_template(body, title)


def daily_tip_email(tip_title: str, tip_body: str, category: str = "📊 Trading Tip") -> str:
    """Daily trading tip / educational email."""
    body = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 20px;background:#161b22;border:1px solid #30363d;border-radius:12px;width:100%">
    <tr><td style="padding:24px">
    <p style="margin:0 0 8px;font-size:12px;color:#7c3aed;font-weight:600;text-transform:uppercase">{category}</p>
    <h3 style="margin:0 0 12px;color:#e6edf3;font-size:18px">{tip_title}</h3>
    <div style="color:#c9d1d9;font-size:14px;line-height:1.7">{tip_body}</div>
    </td></tr>
    </table>
    {_button_html("https://bright-palmier-d43338.netlify.app/ftmo_challenge_tracker.html", "🎯 Track Your Challenge")}
    """
    return _base_template(body, tip_title)


def re_engagement_email(days_inactive: int) -> str:
    """Re-engagement email for inactive subscribers."""
    body = f"""
    <h2 style="color:#7c3aed;margin:0 0 16px">👋 Haven't seen you in a while!</h2>
    <p style="margin:0 0 16px">It's been {days_inactive} days since you joined, and we wanted to check in.</p>
    <p style="margin:0 0 16px">Did you know our free FTMO tracker has helped <strong>260+ traders</strong> pass their challenges? Here's a quick refresher:</p>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 20px">
    <tr><td style="padding:6px 0;color:#e6edf3">🎯 Real-time profit target tracking</td></tr>
    <tr><td style="padding:6px 0;color:#e6edf3">🛑 Automatic drawdown calculations</td></tr>
    <tr><td style="padding:6px 0;color:#e6edf3">📱 Works on any device, no signup needed</td></tr>
    </table>
    {_button_html("https://bright-palmier-d43338.netlify.app/ftmo_challenge_tracker.html", "🎯 Try It Free Now")}
    <p style="margin:20px 0 0;color:#8b949e;font-size:12px">
    Don't want to hear from us? <a href="https://bright-palmier-d43338.netlify.app" style="color:#7c3aed">Unsubscribe</a>
    </p>
    """
    return _base_template(body, "Miss you!")
