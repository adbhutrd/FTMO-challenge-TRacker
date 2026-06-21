#!/bin/bash
# Deploy Live - Uses screen for persistent server + tunnel
# These sessions survive even if this script ends

cd ~/deploy_assets

# Kill any old sessions
screen -S site-server -X quit 2>/dev/null
screen -S site-tunnel -X quit 2>/dev/null
pkill -f 'http.server 3000' 2>/dev/null
pkill -f 'ssh.*localhost.run' 2>/dev/null
sleep 1

# Start Python HTTP server in a screen session (detached)
screen -dmS site-server bash -c "python3 -m http.server 3000 2>&1 | tee /tmp/site_server_output.log"
sleep 2

# Verify server
if curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ | grep -q '200'; then
    echo "✓ Server running on localhost:3000"
else
    echo "✗ Server failed"
    screen -S site-server -X quit
    exit 1
fi

# Start SSH tunnel in a screen session - output goes to a log file
screen -dmS site-tunnel bash -c "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -R 80:localhost:3000 localhost.run 2>&1 | tee /tmp/site_tunnel_output.log"

echo "✓ Tunnel starting... (waiting for URL)"
sleep 8

# Extract URL from tunnel output
URL=$(grep -oP 'https://[a-z0-9]+\.lhr\.life' /tmp/site_tunnel_output.log 2>/dev/null | head -1)

if [ -n "$URL" ]; then
    echo "$URL" > /tmp/site_live_url.txt
    echo ""
    echo "======================================"
    echo "  🚀 SITE IS LIVE AT: $URL"
    echo "======================================"
    echo ""
    echo "  Pages:"
    echo "    Main:     $URL/"
    echo "    Tracker:  $URL/ftmo_challenge_tracker.html"
    echo "    BugFlow:  $URL/bugflow.html"
    echo "    Waitlist: $URL/waitlist.html"
    echo ""
    echo "  Tunnel log: screen -r site-tunnel"
    echo "  Server log: screen -r site-server"
    echo ""
    echo "  To stop later:"
    echo "    screen -S site-server -X quit"
    echo "    screen -S site-tunnel -X quit"
else
    echo "✗ URL not found yet. Check logs:"
    echo "  cat /tmp/site_tunnel_output.log"
    echo "  Wait a bit longer and check: cat /tmp/site_tunnel_output.log | grep -oP 'https://[a-z0-9]+\.lhr\.life'"
fi
