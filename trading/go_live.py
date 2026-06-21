#!/usr/bin/env python3
"""
Go Live! - Serves your site and creates a public URL via SSH tunnel.
Keeps itself alive. Prints the URL for you to share.
"""

import os
import sys
import subprocess
import time
import threading
import signal
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

PORT = 9876
SITE_DIR = os.path.expanduser("~/deploy_assets")
SERVER_PID_FILE = "/tmp/site_server.pid"
URL_FILE = "/tmp/site_url.txt"

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Be quiet

def start_server():
    """Start the HTTP server"""
    os.chdir(SITE_DIR)
    server = HTTPServer(("0.0.0.0", PORT), QuietHandler)
    print(f"  ✓ HTTP server running on port {PORT}")
    sys.stdout.flush()
    server.serve_forever()

def start_tunnel():
    """Start SSH tunnel and capture URL"""
    cmd = [
        "ssh", "-T",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=15",
        "-o", "ExitOnForwardFailure=yes",
        "-R", f"80:localhost:{PORT}",
        "localhost.run"
    ]
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    url = None
    for line in proc.stdout:
        line = line.strip()
        # Look for the URL pattern in localhost.run output
        match = re.search(r'https://[a-z0-9]+\.lhr\.life', line)
        if match:
            url = match.group(0)
            with open(URL_FILE, 'w') as f:
                f.write(url)
            print(f"\n{'='*50}")
            print(f"  🚀 SITE IS LIVE AT: {url}")
            print(f"{'='*50}")
            print(f"\n  Pages:")
            print(f"    Main:     {url}/")
            print(f"    Tracker:  {url}/ftmo_challenge_tracker.html")
            print(f"    BugFlow:  {url}/bugflow.html")
            print(f"    Waitlist: {url}/waitlist.html")
            print(f"\n  Keep this terminal open. Press Ctrl+C to stop.")
            sys.stdout.flush()
    
    proc.wait()

def cleanup(signum=None, frame=None):
    print("\nShutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    if not os.path.exists(SITE_DIR):
        print(f"Error: {SITE_DIR} not found!")
        sys.exit(1)
    
    print(f"\n{'='*50}")
    print(f"  Starting your site...")
    print(f"{'='*50}\n")
    
    # Start HTTP server in a thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    
    # Quick check
    try:
        s = socket.socket()
        s.connect(("localhost", PORT))
        s.close()
        print("  ✓ Local server verified")
    except:
        print("  ✗ Server failed to start!")
        sys.exit(1)
    
    # Start tunnel (this blocks)
    start_tunnel()
