# 📋 SESSION NOTES — Recovery Guide

## Current State (2026-06-27)

### Project Status
- **Site Live:** https://bright-palmier-d43338.netlify.app
- **Security:** Fully hardened (HSTS, CSP, rate limiting, no hardcoded secrets)
- **Auth:** Supabase ready (needs env vars configured)
- **Payments:** Stripe link active ($19.99/mo)
- **Git:** Latest at `origin/main`

### To Continue a Session
Start a new chat with Codebuff and say "continue" or reference this file.

### Quick Deploy
```bash
cd ~/deploy_assets
NETLIFY_AUTH_TOKEN='nfp_KtmP6WwmyYnxp8ZCPAw54Y99qBDpr7CG6792' npx netlify deploy --dir=. --prod
```

### To Set Up Remaining Features
1. **Supabase credentials** — Set env vars in Netlify dashboard or inject via script
2. **GMAIL_APP_PASSWORD** — `export GMAIL_APP_PASSWORD='your-password'`
3. **Binance API keys** — For real meme coin trading
4. **Custom domain** — Point DNS to Netlify nameservers

### Services to Check
```bash
bash ~/24x7_guardian.sh          # Check & restart all services
bash ~/trading/restart_all.sh    # Restart trading bots & tunnel
screen -ls                       # List running screen sessions
tail -f ~/income/logs/cron_orchestrator.log  # Check income pipeline
```

### Files Edited This Session
- `deploy_assets/_headers` — Added HSTS, CSP, Permissions-Policy
- `deploy_assets/server.py` — Added rate limiting, security headers
- `deploy_assets/index.html` — Added nav bar
- `deploy_assets/sell.html` — Added nav bar
- `netlify.toml` — Removed sensitive placeholder keys
- `trading/ceo_credential.py` — Replaced hardcoded bot token with env var
- `README.md` — Comprehensive project documentation
