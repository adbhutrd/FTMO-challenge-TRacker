#!/bin/bash
# 🤖 Radar Telegram Bot — Auto-start wrapper
# Reads the bot token from ~/.radar_token and starts the bot.
#
# Usage:
#   ./radar_bot.sh              # Start the bot
#   echo 'your_token' > ~/.radar_token   # Set your token once
#
# This script is called by crontab's @reboot entry.

HOME_DIR="$HOME"
TOKEN_FILE="$HOME_DIR/.radar_token"
BOT_SCRIPT="$HOME_DIR/radar_bot.py"
LOG_FILE="$HOME_DIR/radar_data/bot.log"

# Ensure log directory exists
mkdir -p "$HOME_DIR/radar_data"

# Load the bot token
if [ -f "$TOKEN_FILE" ]; then
    BOT_TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n\r ')
    if [ -n "$BOT_TOKEN" ]; then
        export RADAR_TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
        echo "[$(date)] Starting Telegram bot..." >> "$LOG_FILE"
        cd "$HOME_DIR" && python3 "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1
    else
        echo "[$(date)] ERROR: ~/.radar_token is empty" >> "$LOG_FILE"
    fi
else
    echo "[$(date)] ERROR: ~/.radar_token not found" >> "$LOG_FILE"
fi
