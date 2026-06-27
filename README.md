# 🚀 Enish Shah — Autonomous Income & Trading System

> **Live Site:** https://bright-palmier-d43338.netlify.app
> **Telegram Bot:** @ArdTradingBot
> **Contact:** enishshah2@gmail.com

---

## 📋 Overview

Full-stack autonomous system combining **FTMO challenge tracking**, **trading bots**, **content automation**, **security services**, and **income generation pipelines**. All running 24/7 with auto-healing guardian scripts.

### Core Products

| Product | Description | Status |
|---------|-------------|--------|
| [FTMO Challenge Tracker](https://bright-palmier-d43338.netlify.app/ftmo_challenge_tracker.html) | Real-time FTMO rule tracking (Free + Pro) | ✅ Live |
| [Trading Bots](trading/) | FTMO Telegram bot, content generator, SEO factory | ✅ Running |
| [Income Pipelines](income/) | Email marketing, social content, bug bounty monitoring | ✅ Automated |
| [Security Services](https://bright-palmier-d43338.netlify.app/portfolio.html) | Web pentest, API audit, recon services | ✅ Live |
| [Automation Pro](https://bright-palmier-d43338.netlify.app/earn.html) | Done-for-you bot deployment & management | ✅ Live |

---

## 🏗️ Project Structure

```
~/                        # Project root
├── deploy_assets/        # 🌐 LIVE WEBSITE (Netlify)
│   ├── index.html              # Main landing page
│   ├── sell.html               # Pro sales page
│   ├── ftmo_challenge_tracker.html  # Core tracker app
│   ├── auth.html               # Supabase auth
│   ├── waitlist.html           # Early access waitlist
│   ├── portfolio.html          # Security consulting portfolio
│   ├── income.html             # Security services page
│   ├── earn.html               # Automation services page
│   ├── supabase-client.js      # Cloud sync & auth client
│   ├── server.py               # Local HTTP server (hardened)
│   ├── command_center.py       # System monitoring
│   ├── _headers                # Security headers (HSTS, CSP)
│   ├── _redirects              # URL redirects
│   └── seo/                    # 30+ SEO content pages
│
├── trading/              # TRADING BOTS & AUTOMATION
│   ├── ftmo_telegram_bot.py    # Telegram bot (@ArdTradingBot)
│   ├── ceo_processor.py        # AI-powered trading analysis
│   ├── ceo_credential.py       # Credential manager
│   ├── content_generator.py    # AI content creation
│   ├── seo_factory.py          # SEO page generator
│   ├── traffic_engine.py       # Marketing automation
│   ├── referral_system.py      # Referral tracking
│   ├── email_marketing.py      # Email campaigns
│   └── restart_all.sh          # Service restart script
│
├── income/               # INCOME & MARKETING PIPELINE
│   ├── tools/                  # Income bots
│   │   ├── income_orchestrator.py  # Master orchestrator
│   │   ├── email_marketing/        # Email pipeline
│   │   ├── program_bot.py         # Bug bounty monitor
│   │   ├── social_bot.py          # Social content
│   │   └── marketing_engine.py    # Marketing automation
│   └── logs/                    # Cron job logs
│
├── meme-coin-bot/        # MEME COIN TRADING
│   ├── config.py               # Configuration (paper mode)
│   ├── executor.py             # Trade executor
│   └── utils.py                # Market utilities
│
├── 24x7_guardian.sh      # 🛡️ Auto-heal guardian script
├── netlify.toml          # Netlify deployment config
└── archive/              # Historical files & logs
```

---

## 🛡️ Security Hardening Status

| Measure | Status |
|---------|--------|
| HSTS (Strict-Transport-Security) | ✅ `max-age=31536000; preload` |
| Content-Security-Policy | ✅ Scripts, styles, CDN locked |
| X-Frame-Options: DENY | ✅ Clickjacking protection |
| Permissions-Policy | ✅ Camera/mic/geo blocked |
| Cross-Origin-Opener-Policy | ✅ `same-origin` |
| Rate Limiting (local server) | ✅ 100 req/min per IP |
| No hardcoded secrets in source | ✅ All tokens loaded from env |
| .gitignore covers .env, .key, .pem | ✅ Sensitive files excluded |

---

## 🤖 Running Services

All services are monitored by `24x7_guardian.sh` and auto-restart on failure.

| Service | Tech | Status |
|---------|------|--------|
| Web Server :3000 | Python HTTP Server | 🔵 Running |
| FTMO Telegram Bot | Python + python-telegram-bot | 🔵 Running |
| CEO AI Processor | GPT-4o / DeepSeek | 🔵 Running |
| MayaDice Bot | Python | 🔵 Running |
| Hermes AI Gateway | Python | 🔵 Running |
| Public Tunnel | localhost.run | 🔵 Running |
| All Cron Jobs (8) | crontab | 🔵 Active |

### Cron Jobs
```
*/15 * * * *   Meme coin bot
0 * * * *      Bug bounty monitor
0 8,18 * * *   Social content
0 21 * * *     Daily summary
0 */6 * * *    Full orchestrator & email marketing
```

---

## 💰 Monetization

| Source | Price | Payment |
|--------|-------|---------|
| FTMO Tracker Pro | $19.99/month | Stripe |
| Custom Bot Dev | $49–$199 | Crypto/PayPal/Bank |
| Bug Bounty Setup | $19.99/month | Stripe |
| Security Audit | $400–$2,000 | PayPal/Bank |
| Full Automation Suite | Custom | Any method |

---

## 🚀 Quick Start

### Local Development
```bash
cd ~/deploy_assets
python3 server.py 3000
# Opens at http://localhost:3000
```

### Restart All Services
```bash
bash ~/trading/restart_all.sh
```

### Deploy to Netlify
```bash
cd ~/deploy_assets
NETLIFY_AUTH_TOKEN='your-token' npx netlify deploy --dir=. --prod
```

### Run Income Pipeline
```bash
cd ~/income && python3 -m tools.income_orchestrator start
```

---

## 📝 Changelog

### 2026-06-27 — Full Security Hardening & Polish
- **Security:** Added HSTS, CSP, Permissions-Policy, Cross-Origin-Opener-Policy
- **Secrets:** Removed hardcoded Telegram token from `ceo_credential.py`
- **Config:** Removed `SUPABASE_SERVICE_ROLE_KEY` from `netlify.toml`
- **Server:** Added rate limiting (100 req/min), logging sanitization
- **Deploy:** Site live at `bright-palmier-d43338.netlify.app`
- **Cleanup:** Archived old scan outputs, logs, duplicate files

### 2026-06-24 — Netherlands PhD Route Planning
- Research on PhD positions, professors, research groups
- 20 research ideas with proof from top conferences

### 2026-06-22 — Supabase Auth, Stripe Payments, UI Upgrade
- Supabase auth integration (sign in, cloud sync, pro plan)
- Stripe payment link for FTMO Tracker Pro ($19.99/mo)
- Guardian script with Hermes Gateway monitoring
- Full UI upgrade on all pages

---

## 🎯 Roadmap

- [x] Supabase auth & cloud sync
- [x] Stripe payment integration
- [x] Security hardening (headers, rate limiting, secrets)
- [x] SEO content (30+ pages)
- [ ] Custom domain purchase & SSL
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Automated social media posting
- [ ] Real meme coin trading (Binance API)

---

## 🔗 Quick Links

| Resource | Link |
|----------|------|
| Live Site | https://bright-palmier-d43338.netlify.app |
| FTMO Tracker | https://bright-palmier-d43338.netlify.app/ftmo_challenge_tracker.html |
| Pro Version | https://bright-palmier-d43338.netlify.app/sell.html |
| Telegram Bot | https://t.me/ArdTradingBot |
| Portfolio | https://bright-palmier-d43338.netlify.app/portfolio.html |
| Stripe Payment | https://buy.stripe.com/5kQ00lejT79186sdvh8Ra00 |
| GitHub | https://github.com/adbhutrd/FTMO-challenge-TRacker.git |

---

*Built with ❤️ by Enish Shah · MSc Cyber Security (Distinction)*
