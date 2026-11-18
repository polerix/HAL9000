#!/usr/bin/env python3
"""
HAL 9000 — localhost sidecar
============================

A tiny loopback-only HTTP service that holds the Anthropic API key so the
browser terminal never has to. Standard library only; no framework, no
new dependencies.

    GET  /api/health   -> {"ok": bool, "model": str}
    POST /api/ask      -> {"reply": str}
         body: {"utterance": str, "crewName": str, "weather": object|null}

Design rules this file is required to keep:

  * It binds 127.0.0.1 and only 127.0.0.1. The bind address is a module
    constant with no override — never 0.0.0.0, never an env var that
    could be set to one by accident.
  * The API key comes from the environment. It is never logged, never
    echoed, never returned in a response body and never put in an error.
  * The HAL system prompt is assembled here (in hal_claude), not in the
    page. The browser POSTs plain data only, so a tampered page cannot
    rewrite HAL's character.

Run:
    ANTHROPIC_API_KEY=... python3 hal_sidecar.py
    python3 hal_sidecar.py --port 3001
"""

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import hal_claude

# Loopback only. Deliberately not configurable.
HOST = "127.0.0.1"
DEFAULT_PORT = 3001
MAX_BODY = 16 * 1024

# Origins allowed to call the sidecar from a browser: the page opened from
# disk (Origin: null) or served from loopback on any port.
_LOOPBACK_ORIGIN = re.compile(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$")
# Host header must name loopback too: blocks DNS-rebinding from a remote page.
_LOOPBACK_HOST = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$", re.I)


def _allowed_origin(origin):
    if origin in (None, "", "null"):
        return "null"
    if _LOOPBACK_ORIGIN.match(origin):
        return origin
    return None


class HalSidecarHandler(BaseHTTPRequestHandler):
    server_version = "HAL9000-sidecar/1.0"
    protocol_version = "HTTP/1.1"

    # -- plumbing ----------------------------------------------------------
    def log_message(self, fmt, *args):
        """Method, path and status only. Never bodies, never headers."""
        sys.stderr.write("[sidecar] %s - %s\n"
                         % (self.address_string(), hal_claude.redact(fmt % args)))

    def _cors(self, origin):
        allow = _allowed_origin(origin)
        if allow is None:
            return False
        self.send_header("Access-Control-Allow-Origin", allow)
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Vary", "Origin")
        return True

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors(self.headers.get("Origin"))
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return bool(_LOOPBACK_HOST.match(host)) if host else True

    # -- routes ------------------------------------------------------------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors(self.headers.get("Origin"))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden."})
        if self.path.split("?")[0] == "/api/health":
            # ok reports readiness, not the key itself.
            return self._json(200, {"ok": bool(hal_claude.api_key()),
                                    "model": hal_claude.MODEL})
        self._json(404, {"error": "Not found."})

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden."})
        if self.path.split("?")[0] != "/api/ask":
            return self._json(404, {"error": "Not found."})

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"error": "Bad Content-Length."})
        if length <= 0 or length > MAX_BODY:
            return self._json(400, {"error": "Body must be 1..%d bytes." % MAX_BODY})

        try:
            req = json.loads(self.rfile.read(length))
            if not isinstance(req, dict):
                raise ValueError
        except Exception:                                     # noqa: BLE001
            return self._json(400, {"error": "Body must be a JSON object."})

        utterance = req.get("utterance")
        if not isinstance(utterance, str) or not utterance.strip():
            return self._json(400, {"error": "Field 'utterance' is required."})

        try:
            reply = hal_claude.ask(
                utterance,
                crew_name=req.get("crewName"),
                weather=req.get("weather"),
            )
        except hal_claude.HalClaudeError as e:
            # hal_claude guarantees this message carries no key; redact again
            # anyway, because this one goes over the wire.
            return self._json(502, {"error": hal_claude.redact(str(e))})

        self._json(200, {"reply": reply})


def main(argv=None):
    ap = argparse.ArgumentParser(description="HAL 9000 localhost sidecar")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args(argv)

    httpd = ThreadingHTTPServer((HOST, args.port), HalSidecarHandler)
    key_state = "present" if hal_claude.api_key() else "MISSING (replies will fail)"
    print(f"[sidecar] HAL 9000 sidecar on http://{HOST}:{args.port}")
    print(f"[sidecar] model: {hal_claude.MODEL}")
    print(f"[sidecar] ANTHROPIC_API_KEY: {key_state}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[sidecar] stopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
