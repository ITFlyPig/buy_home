#!/usr/bin/env python3
"""带缓存控制的HTTP服务器"""
import http.server
import socketserver
import os

os.chdir('/Users/yanxi/Downloads/0绿城/kiro-data/data-warehouse/杭州买房指南/visualization')

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        pass

PORT = 9999

with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
    print(f"Serving HTTP on port {PORT} with no-cache headers...")
    httpd.serve_forever()
