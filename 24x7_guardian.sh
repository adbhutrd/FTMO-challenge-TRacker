#!/bin/bash
# 🤖 24/7 GUARDIAN — Auto-Heal System
# =======================================
# Monitors and restarts all income-generating systems.
# Runs every 2 minutes via cron.
#
# Installed: */2 * * * * /home/enishshah2/24x7_guardian.sh

LOG="/home/enishshah2/income/logs/guardian.log"
TUNNEL_URL_FILE="/tmp/tunnel_url.txt"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$DATE] $1" >> "$LOG" 2>/dev/null; }

# Keep log under 500 lines
[ -f "$LOG" ] && tail -n 500 "$LOG" > /tmp/g_log.tmp && mv /tmp/g_log.tmp "$LOG"

log "=== GUARDIAN CHECK ==="

# 0️⃣ Command Center (port 8080)
if ! pgrep -f 'command_center.py' > /dev/null; then
  log "⚠️  Command Center DOWN — restarting..."
  cd /home/enishshah2/deploy_assets && nohup python3 command_center.py 8080 > /tmp/command_center.log 2>&1 &
  sleep 2
  pgrep -f 'command_center.py' > /dev/null && log "✅ Command Center restarted" || log "❌ Command Center restart FAILED"
else
  log "✅ Command Center OK"
fi

# 1️⃣ Local server on port 3000
if ! curl -sf http://localhost:3000/ > /dev/null 2>&1; then
  log "⚠️  Server DOWN — restarting..."
  fuser -k 3000/tcp 2>/dev/null
  sleep 1
  cd /home/enishshah2/deploy_assets && nohup python3 server.py 3000 > /tmp/server.log 2>&1 &
  sleep 2
  if curl -sf http://localhost:3000/ > /dev/null 2>&1; then
    log "✅ Server restarted OK"
  else
    log "❌ Server restart FAILED"
  fi
else
  log "✅ Server OK"
fi

# 2️⃣ Public tunnel (localhost.run) — check SSH process
if pgrep -f "localhost.run" > /dev/null 2>&1; then
  # Tunnel process is running — test the URL
  TUNNEL_URL=$(cat "$TUNNEL_URL_FILE" 2>/dev/null)
  if [ -n "$TUNNEL_URL" ] && curl -sf -o /dev/null "$TUNNEL_URL" 2>/dev/null; then
    log "✅ Tunnel OK ($TUNNEL_URL)"
  else
    log "⚠️  Tunnel process running but URL stale — leaving it"
  fi
else
  log "⚠️  Tunnel DOWN — restarting..."
  # Start tunnel and capture URL
  ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 \
    -R 80:localhost:3000 nokey@localhost.run 2>&1 | \
    grep -oP 'https://[a-z0-9]+\.lhr\.life' | head -1 > "$TUNNEL_URL_FILE" &
  sleep 15
  NEW_URL=$(cat "$TUNNEL_URL_FILE" 2>/dev/null)
  if [ -n "$NEW_URL" ]; then
    log "✅ Tunnel restarted ($NEW_URL)"
  else
    log "⚠️  Tunnel restart pending (SSH may still be connecting)"
  fi
fi

# 3️⃣ FTMO Telegram Bot
if ! pgrep -f "ftmo_telegram_bot.py" > /dev/null; then
  log "⚠️  FTMO Bot DOWN — restarting..."
  screen -dmS ftmo-bot bash -c "cd /home/enishshah2/trading && python3 ftmo_telegram_bot.py"
  sleep 2
  pgrep -f "ftmo_telegram_bot.py" > /dev/null && log "✅ FTMO Bot restarted" || log "❌ FTMO Bot restart FAILED"
else
  log "✅ FTMO Bot OK"
fi

# 4️⃣ CEO AI Processor
if ! pgrep -f "ceo_processor.py" > /dev/null; then
  log "⚠️  CEO Processor DOWN — restarting..."
  screen -dmS ceo-ai bash -c "cd /home/enishshah2/trading && python3 ceo_processor.py --watch"
  sleep 2
  pgrep -f "ceo_processor.py" > /dev/null && log "✅ CEO Processor restarted" || log "❌ CEO Processor restart FAILED"
else
  log "✅ CEO Processor OK"
fi

# 5️⃣ MayaDice bot
if ! pgrep -f "mayadice.py" > /dev/null; then
  log "⚠️  MayaDice DOWN — restarting..."
  cd /home/enishshah2/MayaDice && nohup python3 mayadice.py watch > /dev/null 2>&1 &
  sleep 2
  pgrep -f "mayadice.py" > /dev/null && log "✅ MayaDice restarted" || log "❌ MayaDice restart FAILED"
else
  log "✅ MayaDice OK"
fi

# 6️⃣ Run meme-coin bot every cycle
LAST_MEME=$(stat -c %Y /home/enishshah2/income/logs/cron_meme_bot.log 2>/dev/null || echo 0)
NOW=$(date +%s)
MEME_AGE=$(( (NOW - LAST_MEME) / 60 ))
if [ "$MEME_AGE" -gt 18 ]; then
  log "⚠️  Meme bot stale ($MEME_AGE min) — running..."
  cd /home/enishshah2/meme-coin-bot && \
    /home/enishshah2/agentic-aama/.venv/bin/python3 bot/main.py --once \
    >> /home/enishshah2/income/logs/cron_meme_bot.log 2>&1
  log "✅ Meme bot cycle done"
fi

# 7️⃣ Social content if stale (>6 hours)
LAST_SOCIAL=$(stat -c %Y /home/enishshah2/income/logs/cron_social.log 2>/dev/null || echo 0)
SOCIAL_AGE=$(( (NOW - LAST_SOCIAL) / 3600 ))
if [ "$SOCIAL_AGE" -gt 6 ]; then
  log "⚠️  Social bot stale — running..."
  cd /home/enishshah2/income && \
    /home/enishshah2/agentic-aama/.venv/bin/python3 tools/enhanced_social_bot.py --batch 3 \
    >> /home/enishshah2/income/logs/cron_social.log 2>&1
  log "✅ Social content generated"
fi

# 8️⃣ Bug bounty monitor if stale (>4 hours)
LAST_PROG=$(stat -c %Y /home/enishshah2/income/logs/cron_programs.log 2>/dev/null || echo 0)
PROG_AGE=$(( (NOW - LAST_PROG) / 3600 ))
if [ "$PROG_AGE" -gt 4 ]; then
  log "⚠️  Program monitor stale — running..."
  cd /home/enishshah2/income && \
    /home/enishshah2/agentic-aama/.venv/bin/python3 tools/enhanced_program_bot.py --once \
    >> /home/enishshah2/income/logs/cron_programs.log 2>&1
  log "✅ Bug bounty monitor done"
fi

log "=== GUARDIAN CHECK COMPLETE ===\n"
