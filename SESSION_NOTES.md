# SESSION NOTES — Continuation Guide

## How to Resume Work

Start a new chat with Codebuff and reference this file:
> "Read CHECKPOINT.md and SESSION_NOTES.md, then continue from where we left off."

---

## Step-by-Step Continuation

### If you want to PUSH to GitHub (commit is local):
```bash
cd ~
gh auth login
# Then:
git push origin main
```

### If you want to DEPLOY the site:
```bash
cd ~/deploy_assets
npx netlify-cli login
npx netlify-cli deploy --dir=. --prod
```

### If you want to TEST the meme-coin bot:
```bash
cd ~/meme-coin-bot
/home/enishshah2/agentic-aama/.venv/bin/python3 bot/main.py --once
```

### If you want to CHECK cron logs:
```bash
tail -20 ~/income/logs/cron_meme_bot.log
tail -20 ~/income/logs/cron_programs.log
tail -20 ~/income/logs/cron_social.log
tail -20 ~/income/logs/cron_orchestrator.log
```

### If you want to ENABLE email sending:
```bash
export GMAIL_APP_PASSWORD='your-16-char-google-app-password'
```

### If you want RUN AI Avatar Generator:
1. Go to https://colab.research.google.com
2. File → Upload Notebook → upload `~/deploy_assets/colab_divine_avatar.ipynb`
3. Click Runtime → Run All (free GPU)

### If you want to VIEW the dashboard (after deploy):
Open: https://rad-beignet-b47738.netlify.app/dashboard

### If you want a FRESH Stripe account:
1. Go to https://stripe.com and create account
2. Get your publishable + secret keys
3. Run: `nano ~/freebuff/.env.local`
4. Replace the Stripe keys at the top

---

## Key Facts
- **Git remote:** https://github.com/adbhutrd/FTMO-challenge-TRacker.git
- **Branch:** main
- **Stripe payment link:** https://buy.stripe.com/5kQ00lejT79186sdvh8Ra00
- **Gemini API key:** In freebuff/.env.local (gitignored)
- **All .env files are gitignored** — API keys safe
