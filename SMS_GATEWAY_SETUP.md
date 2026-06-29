# 📱 SMS Gateway Setup Guide

Open-source SMS gateway using a spare Android phone.  
**No monthly fees, no third-party API — your own number, your own hardware.**

## Architecture

```
Your SIM Card → Android Phone (sms-gate.app) → Tailscale → This Server → Your Apps
                                                              ↕
                                                         SQLite Queue
```

## What You Need

| Item | Details |
|------|---------|
| **Spare Android phone** | Android 5.0+, any old phone works |
| **SIM card** | Any active SIM with SMS capability (pay-as-you-go is fine) |
| **This server** | Your existing VPS or local machine |
| **Tailscale** | Free mesh VPN (tailscale.com) |

---

## Step 1: Set Up Tailscale

Tailscale gives your phone and server a secure private connection.

### On your server:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Follow the URL to authenticate
```

### On your Android phone:
1. Install **Tailscale** from Google Play Store
2. Open Tailscale, sign in with the same account
3. Enable the VPN connection
4. Note the **Tailscale IP** (shown in the app, e.g., `100.x.x.x`)

---

## Step 2: Install sms-gate.app on Android

1. **Download:** Open Chrome on your phone and go to:
   [https://github.com/alexpevzner/sms-gate/releases](https://github.com/alexpevzner/sms-gate/releases)
   
2. **Install the APK** (allow "Install from unknown sources" if prompted)

3. **Open the app** and grant these permissions:
   - ✅ SMS access
   - ✅ Notifications
   - ✅ Ignore battery optimization (for background reliability)

4. **Disable RCS** (Important!)
   - Open your default SMS/Message app
   - Settings → RCS chats → Turn off

5. **Configure Local Mode:**
   - In sms-gate.app → Settings → Enable **Local Mode**
   - Note the **port number** (default: `8080`)
   - Generate/Copy the **API Key** from settings

6. **Test:** The app will show "Server running on http://0.0.0.0:8080"

---

## Step 3: Configure the Server

### Generate the config:
```bash
cd ~
python3 sms_gateway.py setup
```

### Edit the config:
```bash
nano ~/.env.sms
```

Fill in your values:
```env
# Android phone Tailscale IP
SMS_PHONE_IP=100.x.x.x        # ← Your phone's Tailscale IP
SMS_PHONE_PORT=8080

# API key from sms-gate.app
SMS_API_KEY=your_api_key_here  # ← From the app settings

# This server
SMS_SERVER_PORT=8765

# Your number for system alerts
SMS_DEFAULT_PHONE=+1234567890  # ← Your actual phone number
```

### Verify the connection:
```bash
python3 sms_gateway.py check
# Should say: ✅ Configuration OK
#            ✅ Phone reachable
```

---

## Step 4: Start the Server

### Run directly (for testing):
```bash
python3 sms_gateway.py serve
```

### Run as a service (for production):
```bash
# Create service file
sudo tee /etc/systemd/system/sms-gateway.service << 'EOF'
[Unit]
Description=SMS Gateway Service
After=network.target

[Service]
Type=simple
User=enishshah2
WorkingDirectory=/home/enishshah2
ExecStart=/usr/bin/python3 /home/enishshah2/sms_gateway.py serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable sms-gateway
sudo systemctl start sms-gateway
```

### Check it's running:
```bash
curl http://localhost:8765/health
# {"status":"ok","phone":"ok","queue_pending":0,"uptime":"running"}
```

---

## Step 5: Set Up Incoming SMS (Optional)

To receive SMS replies, configure the webhook in sms-gate.app:

1. In the app → Settings → **Webhook URL**
2. Set it to: `http://<your-server-tailscale-ip>:8765/webhook/incoming`
3. The server will log all incoming SMS and trigger handlers

---

## Step 6: Test It

### Send a test SMS to yourself:
```bash
python3 sms_gateway.py test +1234567890
# ✅ SMS sent! Check your phone.
```

### Send via API:
```bash
curl -X POST http://localhost:8765/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "message": "Hello from the API!"}'
```

### Send a system alert:
```bash
curl -X POST http://localhost:8765/alert \
  -H "Content-Type: application/json" \
  -d '{"message": "CPU > 90% on trading server"}'
```

### Check stats:
```bash
curl http://localhost:8765/stats
```

---

## Integration with Existing Services

### Send from Python code:
```python
import requests

# To any number
requests.post("http://localhost:8765/send", json={
    "phone": "+1234567890",
    "message": "FTMO challenge update: +$500 today!",
})

# System alert (uses configured default phone)
requests.post("http://localhost:8765/alert", json={
    "message": "Server restarted at 3:00 AM",
})
```

### Integrate with FTMO Telegram Bot:
Add SMS alerts when challenge status changes:
```python
from sms_gateway import send_sms

# Inside your bot code:
if challenge_passed:
    send_sms("+1234567890",
        "🎉 FTMO Phase 1 Passed! Move to Phase 2!")
```

### Integrate with cron jobs:
Add to any cron task:
```bash
# At the end of your cron script:
curl -X POST http://localhost:8765/alert \
  -H "Content-Type: application/json" \
  -d '{"message": "Daily report: pipeline completed successfully"}'
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ❌ `phone_offline` | Phone lost Tailscale. Reconnect the VPN on the phone. |
| ❌ `Connection refused` | sms-gate.app not running. Open the app on the phone. |
| ❌ `401 Unauthorized` | Wrong API key. Regenerate in sms-gate.app settings. |
| ❌ SMS not sending | Check SIM has credit. Disable RCS on the phone. |
| ❌ Phone battery dying | Keep plugged in. Use a smart plug with charge limiting. |

### Auto-reconnect for Android phone:
```bash
# Add a cron job to check phone connectivity every 5 minutes
*/5 * * * * curl -sf http://localhost:8765/health | grep -q '"ok"' || curl -X POST http://localhost:8765/alert -H "Content-Type: application/json" -d '{"message":"SMS PHONE OFFLINE — Reconnect Tailscale on the Android phone"}'
```

---

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `python3 sms_gateway.py setup` | Generate .env.sms template |
| `python3 sms_gateway.py check` | Verify configuration and phone |
| `python3 sms_gateway.py serve` | Start the HTTP server |
| `python3 sms_gateway.py send +123.. "msg"` | Send an SMS immediately |
| `python3 sms_gateway.py test +123..` | Send a test SMS to yourself |
| `python3 sms_gateway.py stats` | Show system statistics |
| `python3 sms_gateway.py alerts` | Show recent messages |

---

*Built with ❤️ using open-source software — sms-gate.app, Tailscale, FastAPI, and SQLite*
