#!/usr/bin/env python3
"""
Secure HTTP Server for deploy_assets/
- No directory listing (returns 403 for directories without index.html)
- Security headers on all responses
- Runs on port 3000
"""
import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000


class SecureHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
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
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(('', PORT), SecureHTTPHandler) as httpd:
        print(f'Secure server on http://localhost:{PORT}')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down...')
            httpd.shutdown()
