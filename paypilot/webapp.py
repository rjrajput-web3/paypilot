"""PayPilot web demo — stdlib-only HTTP server + chat UI.

Run:  python3 -m paypilot.webapp   (then open http://127.0.0.1:8080)
Env:  PORT, PAYPAL_MODE, PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET (see .env.example)

Zero dependencies: html/css/js served from static/index.html, JSON chat API
at POST /api/chat.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .adapter import pick_adapter
from .agent import Agent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(BaseHTTPRequestHandler):
    agent: Agent  # set at startup

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            path = os.path.join(ROOT, "static", "index.html")
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/health":
            self._json({"ok": True, "mode": self.agent.adapter.name})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode() or "{}")
        except Exception:
            return self._json({"error": "invalid JSON"}, 400)
        message = str(payload.get("message", "")).strip()
        if not message:
            return self._json({"error": "empty message"}, 400)
        result = self.agent.handle(message)
        self._json({"reply": result["reply"],
                    "mode": result["mode"],
                    "intent": result["intent"]["name"]})

    def log_message(self, *args):  # quieter logs
        pass


def main() -> None:
    adapter = pick_adapter()
    Handler.agent = Agent(adapter)
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"PayPilot running in {adapter.name} mode → http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
