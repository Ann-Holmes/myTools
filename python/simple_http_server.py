#!/usr/bin/env python3
"""Simple HTTP server with browser-friendly file viewing."""

import http.server
import socketserver
import os
import logging
import socket
from functools import partial

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class BrowserFriendlyHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that opens HTML files directly in browser."""

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def translate_path(self, path):
        """Translate URL path to filesystem path."""
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        root = os.getcwd()
        path = path.lstrip('/')
        return os.path.join(root, path)

    def log_message(self, format, *args):
        # Use client_address[0] directly to avoid DNS reverse lookup
        client_ip = self.client_address[0]
        logger.info("%s %s", client_ip, args[0])


def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_server(port=8000, directory=None):
    """Start HTTP server."""
    if directory:
        os.chdir(directory)

    handler = partial(BrowserFriendlyHandler, directory=os.getcwd())

    # Allow address reuse to avoid "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True

    # Bind to all interfaces (0.0.0.0) for LAN access
    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        local_ip = get_local_ip()
        logger.info("Serving at http://localhost:%s", port)
        logger.info("Serving at http://%s:%s (LAN access)", local_ip, port)
        logger.info("Directory: %s", os.getcwd())
        logger.info("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple HTTP server for file viewing")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    parser.add_argument("-d", "--directory", type=str, default=None, help="Directory to serve (default: current)")

    args = parser.parse_args()

    run_server(port=args.port, directory=args.directory)
