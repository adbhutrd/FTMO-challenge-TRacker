#!/usr/bin/env python3
"""
Hardened HTTP Server for deploy_assets/
- No directory listing (returns 403 for directories without index.html)
- Comprehensive security headers on all responses
- Basic rate limiting to prevent abuse
- Runs on port 3000
"""
import http.server
import socketserver
import os
import sys
import time
import collections

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000

# ── Rate limiting ────────────────────────────────────────────────────
RATE_LIMIT = 100                # Max requests per window
RATE_WINDOW = 60                # Window in seconds
request_log = collections.defaultdict(list)


def is_rate_limited(ip):
    now = time.time()
    window_start = now - RATE_WINDOW
    # Clean old entries
    request_log[ip] = [t for t in request_log[ip] if t > window_start]
    if len(request_log[ip]) >= RATE_LIMIT:
        return True
    request_log[ip].append(now)
    return False


class SecureHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Rate limiting
        client_ip = self.client_address[0]
        if is_rate_limited(client_ip):
            self.send_response(429)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Retry-After', '60')
            self.end_headers()
            self.wfile.write(b'429 Too Many Requests - Slow down.')
            return

        # Prevent directory listing
        if os.path.isdir(self.translate_path(self.path)):
            if not self.path.endswith('/'):
                self.send_response(301)
                self.send_header('Location', self.path + '/')
                self.end_headers()
                return
            index_files = ['index.html', 'index.htm']
            for idx in index_files:
                idx_path = os.path.join(self.translate_path(self.path), idx)
                if os.path.exists(idx_path):
                    self.path = os.path.join(self.path, idx)
                    break
            else:
                self.send_response(403)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'403 Forbidden')
                return
        super().do_GET()

    def end_headers(self):
        # Security headers
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload')
        self.send_header('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=(), usb=()')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Server', '')  # Hide server info
        super().end_headers()

    def log_message(self, format, *args):
        # Log to stdout for monitoring, but hide sensitive paths
        path = args[0] if len(args) > 0 else ''
        if any(sensitive in path for sensitive in ['.env', 'config', 'secret', 'token', 'password', 'key']):
            args = (args[0], args[1] if len(args) > 1 else '***', args[2] if len(args) > 2 else '***')
        super().log_message(format, *args)


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(('', PORT), SecureHTTPHandler) as httpd:
        print(f'Hardened server on http://localhost:{PORT} (rate limit: {RATE_LIMIT}/min)')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down...')
            httpd.shutdown()
