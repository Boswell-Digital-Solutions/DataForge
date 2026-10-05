"""Stub of the NeuroForge embedding endpoint. It runs inside the sandbox on a loopback port.

    python stub_neuroforge.py --port PORT --run-id RUN_ID

GET /health answers with the run identifier. POST /api/v1/embed answers with fixed,
synthetic vectors of 1536 numbers. No other path exists. It contacts nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIMENSIONS = 1536
SERVICE = "neuroforge-stub"


def vector_for(text: str) -> list:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [round((digest[i % len(digest)] - 127.5) / 127.5, 6) for i in range(DIMENSIONS)]


def make_handler(run_id: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                self._send(200, {"service": SERVICE, "run_id": run_id})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            if self.path != "/api/v1/embed":
                self._send(404, {"error": "not found"})
                return
            try:
                texts = json.loads(raw).get("texts")
            except (ValueError, AttributeError):
                texts = None
            if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
                self._send(422, {"error": "texts must be a list of strings"})
                return
            self._send(200, {"embeddings": [vector_for(t) for t in texts], "model": "stub", "run_id": run_id})

        def log_message(self, *args):  # silence the default stderr log
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.run_id))
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
