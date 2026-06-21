#!/bin/bash
# Start the live site server and tunnel
# This keeps the tunnel alive even if the connection drops

cd ~/deploy_assets || { echo "deploy_assets not found"; exit 1; }

# Kill any existing instances
pkill -f 'http.server 3000' 2>/dev/null
pkill -f 'ssh.*localhost.run' 2>/dev/null
sleep 1

# Start Python HTTP server
nohup python3 -m http.server 3000 > /tmp/server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
sleep 2

# Test server
if curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ | grep -q '200'; then
    echo "Server running on localhost:3000 ✅"
else
    echo "Server failed to start ❌"
    exit 1
fi

# Start tunnel - runs in loop so it reconnects if dropped
nohup bash -c '
while true; do
    URL=$(ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -R 80:localhost:3000 localhost.run 2>&1 | grep -oP "https://[a-z0-9]+\.lhr\.life" | head -1)
    echo "Tunnel URL: $URL" > /tmp/tunnel_url.txt
    echo "Site live at: $URL"
    sleep 5
done
' > /tmp/tunnel_loop.log 2>&1 &

TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"

# Wait for tunnel to connect
sleep 10

if [ -f /tmp/tunnel_url.txt ]; then
    URL=$(cat /tmp/tunnel_url.txt)
    echo ""
    echo "=============================================="
    echo "🚀 SITE IS LIVE AT: $URL"
    echo "=============================================="
    echo ""
    echo "Pages:"
    echo "  Main:    $URL/"
    echo "  Tracker: $URL/ftmo_challenge_tracker.html"
    echo "  BugFlow: $URL/bugflow.html"
    echo "  Waitlist: $URL/waitlist.html"
else
    echo "Tunnel failed to start. Check /tmp/tunnel_loop.log"
    cat /tmp/tunnel_loop.log
fi

# Save PIDs for later management
echo "$SERVER_PID" > /tmp/site_server.pid
echo "$TUNNEL_PID" > /tmp/site_tunnel.pid
