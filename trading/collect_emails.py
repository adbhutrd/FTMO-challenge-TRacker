#!/usr/bin/env python3
"""
Email Collector for FTMO Tracker Waitlist
=========================================
View and export emails collected via the website's localStorage.

The website stores signups in browser localStorage under 'ftmoWaitlist'.
This script provides a local view of that data and can also serve
as a simple HTTP endpoint to collect emails directly.

Usage:
    python3 collect_emails.py          # Show stats
    python3 collect_emails.py --list   # Show all emails
    python3 collect_emails.py --csv    # Export as CSV
    python3 collect_emails.py --server # Start local collection server
"""

import json
import csv
import sys
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

DATA_FILE = os.path.expanduser("~/trading/waitlist_emails.json")


def load_emails():
    """Load collected emails from local JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return []


def save_emails(emails):
    """Save emails to JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(emails, f, indent=2)
    print(f"💾 Saved {len(emails)} emails to {DATA_FILE}")


def show_stats():
    """Show waitlist statistics."""
    emails = load_emails()
    print("\n" + "=" * 50)
    print("  📊 FTMO TRACKER WAITLIST STATS")
    print("=" * 50)
    print(f"  Total signups:  {len(emails)}")
    
    if emails:
        dates = [e.get('timestamp', 'unknown') for e in emails]
        print(f"  First signup:   {min(dates) if dates else 'N/A'}")
        print(f"  Latest signup:  {max(dates) if dates else 'N/A'}")
        
        # Source breakdown
        sources = {}
        for e in emails:
            src = e.get('source', 'unknown')
            sources[src] = sources.get(src, 0) + 1
        print(f"\n  📍 Sources:")
        for src, count in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"    {src}: {count}")
    print("=" * 50)
    print()


def list_emails():
    """List all captured emails with details."""
    emails = load_emails()
    if not emails:
        print("No emails captured yet.")
        return
    
    print(f"\n{'Email':<35} {'Date':<20} {'Source':<15}")
    print("-" * 70)
    for e in emails:
        email = e.get('email', 'N/A')
        ts = e.get('timestamp', 'N/A')[:16]
        src = e.get('source', 'N/A')[:14]
        print(f"{email:<35} {ts:<20} {src:<15}")
    print(f"\nTotal: {len(emails)} emails\n")


def export_csv():
    """Export emails to CSV file."""
    emails = load_emails()
    if not emails:
        print("No emails to export.")
        return
    
    csv_file = os.path.expanduser(f"~/trading/waitlist_export_{datetime.now().strftime('%Y%m%d')}.csv")
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Email', 'Timestamp', 'Source'])
        for e in emails:
            writer.writerow([
                e.get('email', ''),
                e.get('timestamp', ''),
                e.get('source', '')
            ])
    
    print(f"✅ Exported {len(emails)} emails to {csv_file}")
    print(f"   Open with:  open {csv_file}")
    print(f"   Or import to: Google Sheets, Mailchimp, ConvertKit")


def start_server():
    """Start a local HTTP server to collect emails."""
    
    class EmailHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body) if body.startswith('{') else dict(
                    param.split('=') for param in body.split('&')
                )
                email = data.get('email', data.get('Email', ''))
                
                if email:
                    emails = load_emails()
                    emails.append({
                        'email': email,
                        'timestamp': datetime.now().isoformat(),
                        'source': data.get('source', 'http-server'),
                        'ip': self.client_address[0]
                    })
                    save_emails(emails)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode())
                    print(f"  ✅ Collected: {email}")
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"error": "email required"}')
            except Exception as e:
                print(f"  ❌ Error: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"error": "server error"}')
        
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
<html><body style="font-family:sans-serif;background:#0d1117;color:#e6edf3;padding:40px;text-align:center">
<h1>📊 FTMO Waitlist Server</h1>
<p>Server is running! To collect emails, POST to this URL:</p>
<code style="background:#161b22;padding:8px 16px;border-radius:6px;display:inline-block;margin:16px 0">
curl -X POST http://localhost:8080 -d "email=test@example.com"
</code>
<p style="color:#8b949e;font-size:14px;margin-top:20px">
Update your waitlist.html form action to post to this URL instead of FormSubmit.
</p>
</body></html>
            ''')
    
    port = 8080
    server = HTTPServer(('0.0.0.0', port), EmailHandler)
    print(f"\n🚀 Email collection server running on http://localhost:{port}")
    print(f"   POST emails to: http://localhost:{port}")
    print(f"   View dashboard: http://localhost:{port}")
    print(f"\n   To update your website, change the form action to:\n")
    print(f"   <form action=\"http://YOUR_SERVER_IP:{port}\" method=\"POST\">")
    print(f"\n   Press Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        server.server_close()


def add_email_manually():
    """Manually add an email to the list."""
    email = input("Enter email: ").strip()
    if not email:
        return
    source = input("Source (e.g., reddit, discord): ").strip() or "manual"
    
    emails = load_emails()
    emails.append({
        'email': email,
        'timestamp': datetime.now().isoformat(),
        'source': source
    })
    save_emails(emails)
    print(f"✅ Added: {email}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_stats()
        print("Commands:")
        print("  python3 collect_emails.py --list     List all emails")
        print("  python3 collect_emails.py --csv      Export to CSV")
        print("  python3 collect_emails.py --server   Start collection server")
        print("  python3 collect_emails.py --add      Add email manually")
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd == '--list':
        list_emails()
    elif cmd == '--csv':
        export_csv()
    elif cmd == '--server':
        start_server()
    elif cmd == '--add':
        add_email_manually()
    else:
        show_stats()
