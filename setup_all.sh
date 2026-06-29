#!/bin/bash
# ============================================================
#  🚀 INCOME SYSTEM — COMPLETE SETUP
#  One command to install & start everything
# ============================================================
# Usage: bash setup_all.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "================================================"
echo "   🚀 INCOME SYSTEM — COMPLETE SETUP"
echo "================================================"
echo -e "${NC}"

# Record start time
START=$(date +%s)

# ─── 1. System Updates ─────────────────────────────────
echo -e "\n${YELLOW}[1/7]${NC} Updating system packages..."
sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-venv curl git jq 2>/dev/null
echo -e "${GREEN}  ✅ System packages updated${NC}"

# ─── 2. Python Setup ──────────────────────────────────
echo -e "\n${YELLOW}[2/7]${NC} Setting up Python environments..."

# Main venv
if [ ! -d "$HOME/venv" ]; then
    python3 -m venv "$HOME/venv"
    echo -e "${GREEN}  ✅ Created main venv${NC}"
fi

# Meme-coin bot venv
if [ ! -d "$HOME/meme-coin-bot/venv" ]; then
    python3 -m venv "$HOME/meme-coin-bot/venv"
    echo -e "${GREEN}  ✅ Created meme-coin-bot venv${NC}"
fi

# ─── 3. Install Dependencies ───────────────────────────
echo -e "\n${YELLOW}[3/7]${NC} Installing Python dependencies..."

source "$HOME/venv/bin/activate"
pip install -q python-binance pandas numpy requests python-dotenv 2>/dev/null
echo -e "${GREEN}  ✅ Main dependencies installed${NC}"

source "$HOME/meme-coin-bot/venv/bin/activate"
pip install -q python-binance pandas numpy python-dotenv 2>/dev/null
echo -e "${GREEN}  ✅ Trading bot dependencies installed${NC}"

# ─── 4. Setup .env for Meme-Coin Bot ───────────────────
echo -e "\n${YELLOW}[4/7]${NC} Setting up environment..."

if [ ! -f "$HOME/meme-coin-bot/.env" ]; then
    cp "$HOME/meme-coin-bot/.env.example" "$HOME/meme-coin-bot/.env"
    echo -e "${YELLOW}  ⚠️  Edit ~/meme-coin-bot/.env to add your Binance API keys${NC}"
    echo -e "${YELLOW}     For now, using PAPER mode with \$100 balance${NC}"
else
    echo -e "${GREEN}  ✅ .env already exists${NC}"
fi

# ─── 5. Create Directories ─────────────────────────────
echo -e "\n${YELLOW}[5/7]${NC} Creating working directories..."

mkdir -p "$HOME/income/logs"
mkdir -p "$HOME/income/data"
mkdir -p "$HOME/deploy_assets"
mkdir -p "$HOME/income/tools"
echo -e "${GREEN}  ✅ Directories created${NC}"

# ─── 6. Install Cron Jobs ──────────────────────────────
echo -e "\n${YELLOW}[6/7]${NC} Setting up cron jobs..."

# Generate cron config
cd "$HOME/income"
python3 tools/income_orchestrator.py cron

# Install crontab (ask user)
CRON_FILE="$HOME/income/logs/cron_jobs.txt"
echo ""
echo -e "${BLUE}  To install cron jobs, run:${NC}"
echo -e "  ${GREEN}crontab ${CRON_FILE}${NC}"
echo ""
echo -e "${YELLOW}  Or run manually to test:${NC}"
echo -e "  cd ~/meme-coin-bot && python3 bot/main.py --once"
echo -e "  cd ~/income && python3 tools/enhanced_program_bot.py --once"
echo -e "  cd ~/income && python3 tools/enhanced_social_bot.py --batch 3"
echo -e "${GREEN}  ✅ Cron config ready${NC}"

# ─── 7. Final Summary ──────────────────────────────────
END=$(date +%s)
DURATION=$((END - START))

echo -e "\n${BLUE}"
echo "================================================"
echo "   ✅ SETUP COMPLETE (${DURATION}s)"
echo "================================================"
echo -e "${NC}"
echo ""
echo -e "${GREEN}  📁 Your Income System is ready!${NC}"
echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │                                             │"
echo "  │  💰 TRADING BOT                             │"
echo "  │     cd ~/meme-coin-bot                      │"
echo "  │     python3 bot/main.py --once              │"
echo "  │                                             │"
echo "  │  📡 PROGRAM MONITOR                         │"
echo "  │     cd ~/income/tools                       │"
echo "  │     python3 enhanced_program_bot.py --once  │"
echo "  │                                             │"
echo "  │  📱 SOCIAL CONTENT                          │"
echo "  │     python3 enhanced_social_bot.py --batch 5│"
echo "  │                                             │"
echo "  │  🤖 RUN ALL BOTS                            │"
echo "  │     python3 income_orchestrator.py start    │"
echo "  │                                             │"
echo "  │  📊 INCOME DASHBOARD                        │"
echo "  │     Open: ~/income/tracker_dashboard.html   │"
echo "  │                                             │"
echo "  │  📧 SETUP EMAIL (optional)                  │"
echo "  │     export GMAIL_APP_PASSWORD='your-pass'   │"
echo "  │                                             │"
echo "  └─────────────────────────────────────────────┘"
echo ""
echo -e "${BLUE}  Next steps:${NC}"
echo "  1. ${YELLOW}Get Binance testnet API keys:${NC} https://testnet.binance.vision/"
echo "  2. ${YELLOW}Add your API keys to:${NC} ~/meme-coin-bot/.env"
echo "  3. ${YELLOW}Run the bots:${NC} python3 ~/income/tools/income_orchestrator.py start"
echo "  4. ${YELLOW}Open the dashboard:${NC} firefox ~/income/tracker_dashboard.html"
echo "  5. ${YELLOW}(Optional) Setup email:${NC} export GMAIL_APP_PASSWORD='your-pass'"
echo ""
echo -e "${GREEN}  Good luck — go earn! 🚀${NC}"
echo ""
