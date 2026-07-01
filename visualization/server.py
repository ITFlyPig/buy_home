#!/usr/bin/env python3
"""带缓存控制的HTTP服务器"""
import http.server
import socketserver

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        pass

PORT = 8767

with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
    print(f"Serving HTTP on port {PORT} with no-cache headers...")
    httpd.serve_forever()
