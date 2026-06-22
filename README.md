# 📊 FTMO Challenge Tracker

Track your FTMO challenge progress in real-time — profit targets, drawdown limits, trading days, and more. Use it as a **web app** (offline, no signup) or a **Telegram bot** (always with you).

**Live site:** [https://ftmo-tracker.loca.lt](https://ftmo-tracker.loca.lt)
**Telegram bot:** [@ArdTradingBot](https://t.me/ArdTradingBot)
**Pro version:** [https://gumroad.com/l/ezteprg](https://gumroad.com/l/ezteprg)

---

## ✨ Features

| Feature | Free | Pro |
|---------|------|-----|
| Profit target tracking (10% / 5%) | ✅ | ✅ |
| Max drawdown guard (10%) | ✅ | ✅ |
| Daily loss limit warnings | ✅ | ✅ |
| Trading day counter | ✅ | ✅ |
| Equity curve chart | ✅ | ✅ |
| Trade log with P&L | ✅ | ✅ |
| 1-Step & 2-Step support | ✅ | ✅ |
| Best Day Rule (1-Step) | ✅ | ✅ |
| Export / Import data | ✅ | ✅ |
| **Cloud sync (all devices)** | ❌ | ✅ |
| **Unlimited accounts** | ❌ | ✅ |
| **PDF reports** | ❌ | ✅ |
| **Email notifications** | ❌ | ✅ |
| **Priority support** | ❌ | ✅ |

---

## 🚀 Quick Start

### Web App (Free)

Zero setup. Just open the link and start tracking:

1. Go to [ftmo-tracker.loca.lt/ftmo_challenge_tracker.html](https://ftmo-tracker.loca.lt/ftmo_challenge_tracker.html)
2. Select your **challenge type** (1-Step or 2-Step) and **account size**
3. After each trading day, enter your **ending balance**
4. Watch real-time progress — profit target, drawdown, and days

Your data is stored in your browser's local storage. Export it anytime as JSON.

### Telegram Bot (Free)

Message [@ArdTradingBot](https://t.me/ArdTradingBot) on Telegram and start tracking from your phone:

```
/setup 2step 50000
/add 50200
/status
```

No signup, no account needed.

---

## 📋 Project Structure

```
├── trading/
│   ├── ftmo_telegram_bot.py      # Telegram bot (Python)
│   ├── ftmo_challenge_tracker.html  # Web tracker (single HTML)
│   ├── sell.html                  # Sales / landing page
│   ├── waitlist.html              # Email waitlist page
│   ├── restart_all.sh             # Auto-restart script (24/7)
│   ├── ftmo_bot.env               # Bot token config
│   ├── telegram_data/             # Per-user JSON storage
│   ├── promo_content.txt          # Promo copy for Reddit/Discord/Twitter
│   ├── REDDIT_POST.md             # Reddit post template
│   ├── GUMROAD_SETUP.md           # Gumroad product setup guide
│   └── ftmo_bot.log               # Bot logs
├── income/
│   ├── fiverr_gig.txt             # Fiverr gig copy
│   ├── upwork_proposal.txt        # Upwork proposal templates
│   ├── build_portfolio.py         # Portfolio builder
│   └── tools/                     # Income automation tools
├── LIVE_URL.txt                   # Current live site URL
└── README.md                      # You are here
```

---

## 🤖 Telegram Bot — Full Command Reference

### Setup

| Command | Description |
|---------|-------------|
| `/setup 2step 50000` | Set up a 2-Step $50k challenge |
| `/setup 2step 50000 50000` | Set up with a custom starting balance |
| `/setup 1step 100000` | Set up a 1-Step $100k challenge |

### Tracking

| Command | Description |
|---------|-------------|
| `/add 50200` | Add a trading day with ending balance |
| `/add 50200 great day` | Add with optional notes |
| `/add 2026-06-20 50200` | Add with a custom date |
| `/status` | Full challenge progress report |
| `/log` | View trade history (last 20 days) |

### Charts & Data

| Command | Description |
|---------|-------------|
| `/chart` | Generate equity curve chart (PNG) |
| `/export` | Download your data as JSON |
| `/delete 1` | Delete the first trading day |

### Management

| Command | Description |
|---------|-------------|
| `/reset` | Reset all data (with confirmation) |
| `/promote` | Move to Phase 2 (2-Step only) |
| `/about` | About & Pro version info |
| `/start` | Welcome message and command help |

---

## 🧠 FTMO Rules Engine

The tracker implements FTMO's official challenge rules exactly:

| Rule | 2-Step | 1-Step |
|------|--------|--------|
| **Phase 1 profit target** | 10% | 10% |
| **Phase 2 profit target** | 5% | 5% |
| **Max drawdown** | 10% (static from initial) | 10% (static from initial) |
| **Max daily loss** | 5% | 3% |
| **Min trading days** | 4 (each phase) | 0 |
| **Best day rule** | N/A | Max 50% of total profit |

### Statuses

- 🟢 **In Progress** — Everything on track
- 🟡 **Near Drawdown Limit** — Used >80% of max drawdown
- 🟡 **Daily Loss Limit Hit** — Exceeded daily loss on a trading day
- 🟡 **Best Day > 50%** — Best day exceeds half of total profit (1-Step)
- ✅ **Phase Passed!** — Hit profit target, met day requirements
- ❌ **Failed** — Hit max drawdown limit

---

## 🔧 Self-Hosting

### Telegram Bot

```bash
# 1. Get a token from @BotFather on Telegram
# 2. Set the token
export TELEGRAM_BOT_TOKEN="your:token"

# 3. Install dependencies
pip3 install python-telegram-bot matplotlib

# 4. Run
python3 trading/ftmo_telegram_bot.py
```

### Website

```bash
# Start HTTP server
cd deploy_assets
python3 -m http.server 3000

# Or with public tunnel
ssh -R 80:localhost:3000 localhost.run
```

### 24/7 Auto-Restart

```bash
bash trading/restart_all.sh
```

A cron job checks every minute if services are running and restarts them if needed.

---

## 💰 Pro Version ($19.99/mo)

Upgrade for cloud sync, unlimited accounts, PDF reports, and email alerts:

👉 [gumroad.com/l/ezteprg](https://gumroad.com/l/ezteprg)

---

## 📢 Marketing

- **Reddit:** Copy from `trading/REDDIT_POST.md` and post to r/FTMO, r/DayTrading
- **Twitter / Discord:** Copy from `trading/promo_content.txt`
- **Fiverr:** Copy from `income/fiverr_gig.txt`
- **Upwork:** Copy from `income/upwork_proposal.txt`

---

## 🛠 Tech Stack

- **Web:** Vanilla HTML + CSS + JavaScript (Chart.js for charts) — single-file, no build step
- **Bot:** Python `python-telegram-bot` + `matplotlib` for chart generation
- **Storage:** LocalStorage (web) / JSON files (bot)
- **Deployment:** Python HTTP server + localhost.run tunnel

---

## 📄 License

MIT — free to use, modify, and distribute.

*Not affiliated with FTMO.com. Built for the trading community by a trader.*
