#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 🚀 Restart All Income Services — 24/7 Automation
# ═══════════════════════════════════════════════════════════════
# Run this if the machine restarts or services go down:
#   bash ~/trading/restart_all.sh
#
# Check status anytime:
#   screen -ls
# ═══════════════════════════════════════════════════════════════

echo "=========================================="
echo "  🚀 Restarting All Services..."
echo "=========================================="

# ── Kill any existing sessions ──
screen -S ftmo-bot -X quit 2>/dev/null
screen -S site-server -X quit 2>/dev/null
screen -S site-tunnel -X quit 2>/dev/null
pkill -f 'http.server 3000' 2>/dev/null
pkill -f 'localhost.run' 2>/dev/null
pkill -f 'ftmo_telegram_bot' 2>/dev/null
sleep 2

# ── Sync latest files to deploy_assets ──
echo "[0/3] Syncing website files..."
cp ~/trading/ftmo_challenge_tracker.html ~/deploy_assets/
cp ~/trading/sell.html ~/deploy_assets/
cp ~/trading/sell.html ~/deploy_assets/index.html
cp ~/trading/waitlist.html ~/deploy_assets/
echo "  ✅ Website files synced"

# ── 1. FTMO Telegram Bot ──
echo "[1/3] Starting FTMO Telegram Bot..."
# Read token from .env file (no hardcoded secrets!)
source ~/.hermes/.env 2>/dev/null
screen -dmS ftmo-bot bash -c 'cd ~/trading && python3 ftmo_telegram_bot.py'
sleep 2
echo "  ✅ FTMO Bot running (screen: ftmo-bot)"

# ── 2. Site HTTP Server ──
echo "[2/3] Starting website server..."
cd ~/deploy_assets
screen -dmS site-server bash -c 'cd ~/deploy_assets && python3 -m http.server 3000'
sleep 2
if curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ | grep -q 200; then
    echo "  ✅ Website server running on port 3000"
else
    echo "  ❌ Website server failed!"
fi

# ── 3. Tunnel (public URL) ──
echo "[3/3] Starting public tunnel..."
screen -dmS site-tunnel bash -c 'ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -R 80:localhost:3000 localhost.run 2>&1 | tee /tmp/tunnel_output.log'
sleep 12
URL=$(grep -oP 'https://[a-z0-9]+\.lhr\.life|https://[a-z0-9-]+\.loca\.lt' /tmp/tunnel_output.log 2>/dev/null | head -1)
if [ -n "$URL" ]; then
    echo "  ✅ Site live at: $URL"
    echo "$URL" > /tmp/site_live_url.txt
else
    echo "  ⚠️ Tunnel starting... check: cat /tmp/tunnel_output.log"
fi

echo ""
echo "=========================================="
echo "  🟢 ALL SERVICES RUNNING"
echo "=========================================="
echo ""
echo "  Check status:  screen -ls"
echo "  Bot logs:      tail -f ~/trading/ftmo_bot.log"
echo "  Tunnel logs:   cat /tmp/tunnel_output.log"
echo "  Site URL:      cat /tmp/site_live_url.txt"
echo ""

screen -ls > /tmp/services_status.txt 2>/dev/null
echo "Last restarted: $(date)" >> /tmp/services_status.txt
