#!/usr/bin/env python3
"""
fake_mcp_server.py - deliberately INSTRUMENTED MCP mock for validating the
attacker kit WITHOUT the user's editor. Implements just enough of the MCP
HTTP surface to exercise every mcp_attack.py mode:

  - token check (Bearer or X-FlaxMcp-Token) vs FAKE_MCP_TOKEN, fail-closed
  - Origin check vs localhost
  - tools/list + tools/call (manage_security stub, arg validation)
  - GET /mcp SSE-ish stream (session id header) + OpenAPI-ish /openapi.json
  - /metrics + /health endpoints on the same listener

This is a TEST MIRROR of the plugin's surface, NOT the plugin. It exists so
the lab tooling is proven before pointing it at the real editor.

Usage:
  set FAKE_MCP_TOKEN=lab-secret  (optional; unset = fail-closed mode)
  .\\.venv\\Scripts\\python.exe fake_mcp_server.py --port 8765
"""

import argparse
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("FAKE_MCP_TOKEN", "lab-secret")
TOOLS = [
    {"name": "manage_security", "description": "Security pack ops console.",
     "inputSchema": {"type": "object", "properties": {"action": {"type": "string"}}}},
    {"name": "project_read", "description": "Read a project file.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
]


def jsonrpc_error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def jsonrpc_result(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def handle_rpc(body, rid):
    try:
        msg = json.loads(body)
    except ValueError:
        return jsonrpc_error(rid, -32700, "Parse error")
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return jsonrpc_error(rid, -32600, "Invalid Request")
    method = msg.get("method", "")
    params = msg.get("params") or {}
    if method == "tools/list":
        return jsonrpc_result(rid, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        if not any(t["name"] == name for t in TOOLS):
            return jsonrpc_error(rid, -32602, "Unknown tool: %s" % name)
        if not isinstance(args, dict):
            return jsonrpc_error(rid, -32602, "arguments must be an object")
        if name == "manage_security":
            action = args.get("action")
            if not isinstance(action, str):
                return jsonrpc_error(rid, -32602, "action must be a string")
            if len(action) > 4096:
                return jsonrpc_error(rid, -32602, "action too large")
            return jsonrpc_result(rid, {"ok": True, "action": action})
        if name == "project_read":
            path = args.get("path", "")
            if ".." in path or path.startswith("/") or re.match(r"^[A-Za-z]:", path) or path.startswith("\\\\"):
                return jsonrpc_error(rid, -32602, "path rejected by ProjectPathGuard")
            return jsonrpc_result(rid, {"content": "file: " + path})
        return jsonrpc_error(rid, -32601, "Method not found")
    if method == "initialize":
        return jsonrpc_result(rid, {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}}})
    if method == "ping":
        return jsonrpc_result(rid, {})
    return jsonrpc_error(rid, -32601, "Method not found")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, status, body, ctype="application/json", extra=None):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _check_auth(self):
        tok = None
        h = self.headers
        auth = h.get("Authorization", "")
        if auth.startswith("Bearer "):
            tok = auth[7:]
        tok = tok or h.get("X-FlaxMcp-Token")
        if not TOKEN:
            return True  # fail-closed when unset: server refuses all requests
        return tok == TOKEN

    def do_GET(self):
        if self.path == "/mcp" and self.headers.get("Accept") == "text/event-stream":
            if not self._check_auth():
                return self._send(401, json.dumps({"error": "unauthorized"}))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Mcp-Session-Id", "sess-" + str(time.time_ns()))
            self.end_headers()
            for i in range(3):
                self.wfile.write(b"event: message\ndata: " + json.dumps({"seq": i}).encode() + b"\n\n")
                self.wfile.flush()
                time.sleep(0.05)
            return
        if self.path == "/openapi.json":
            if not self._check_auth():
                return self._send(401, json.dumps({"error": "unauthorized"}))
            return self._send(200, json.dumps({"openapi": "3.0.0", "paths": {"/mcp": {"post": {}}}, "tools": [t["name"] for t in TOOLS]}))
        if self.path in ("/metrics", "/health"):
            if self.path == "/health" or self._check_auth():
                return self._send(200, json.dumps({"ok": True}), extra={"Content-Type": "text/plain"} if self.path == "/metrics" else {})
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if not self._check_auth():
            return self._send(401, json.dumps({"error": "unauthorized"}))
        origin = self.headers.get("Origin")
        if origin and not (origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")):
            return self._send(403, json.dumps({"error": "origin rejected"}))
        length = int(self.headers.get("Content-Length", "0"))
        if length > 200_000:
            return self._send(413, json.dumps({"error": "payload too large"}))
        body = self.rfile.read(length)
        try:
            msg = json.loads(body)
        except ValueError:
            return self._send(400, json.dumps(jsonrpc_error(None, -32700, "Parse error")))
        if isinstance(msg, list):
            if len(msg) > 50:
                return self._send(400, json.dumps({"error": "batch too large"}))
            out = [handle_rpc(json.dumps(i) if isinstance(i, dict) else b"", i.get("id")) for i in msg]
            return self._send(200, json.dumps(out))
        rid = msg.get("id") if isinstance(msg, dict) else None
        return self._send(200, json.dumps(handle_rpc(body, rid)))

    def do_HEAD(self):
        return self._send(405, "")
    do_PUT = do_DELETE = do_PATCH = do_TRACE = do_HEAD


def main():
    p = argparse.ArgumentParser(description="instrumented MCP mock for kit validation")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    print(f"[*] fake MCP server on :{args.port}  FAKE_MCP_TOKEN={'set' if TOKEN else 'UNSET (fail-closed mode)'}")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
