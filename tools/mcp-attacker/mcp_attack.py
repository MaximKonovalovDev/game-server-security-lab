#!/usr/bin/env python3
"""
mcp_attack.py - raw HTTP attacker client for the FlaxMCP plugin lab.

Targets the MCP HTTP endpoint (default http://localhost:8765/mcp) with ZERO
framework code on the attacker side - plain http.client so it runs on any
stock Python 3. Each mode emits one JSON result per test to stdout so the
orchestrator (scripts/mcp-attack-run.ps1) can build reports.

Doctrine (docs/MCP-ATTACK-LAB.md): local editor instance only, never a
tunneled endpoint. Facts-only output.

Usage examples:
  python mcp_attack.py --mode baseline --token <tok>
  python mcp_attack.py --mode no-token
  python mcp_attack.py --mode wrong-token --count 5
  python mcp_attack.py --mode origin-spoof --origin https://evil.example
  python mcp_attack.py --mode method-fuzz
  python mcp_attack.py --mode arg-bombs --token <tok>
  python mcp_attack.py --mode batch --token <tok>
  python mcp_attack.py --mode flood --token <tok> --concurrency 64 --count 64
  python mcp_attack.py --mode sse --token <tok>
  python mcp_attack.py --mode openapi
  python mcp_attack.py --mode endpoints
  python mcp_attack.py --mode timing --token <tok> --count 60
  python mcp_attack.py --mode env-probe
"""

import argparse
import concurrent.futures
import http.client
import json
import os
import random
import statistics
import subprocess
import sys
import threading
import time

DEFAULT_URL = "http://localhost:8765/mcp"
PEEK_BODY = 400  # max bytes of body kept in evidence


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------
class McpTarget:
    """One HTTP endpoint. http.client does the keep-alive + chunking itself."""

    def __init__(self, url, timeout=5.0):
        if "://" not in url:
            url = "http://" + url
        self.url = url
        self.timeout = timeout
        from urllib.parse import urlparse

        u = urlparse(url)
        if u.scheme != "http":
            raise ValueError(f"only http:// supported, got {u.scheme}")
        self.host = u.hostname
        self.port = u.port or 80
        self.path = u.path or "/"

    def request(self, method="POST", body=None, headers=None, timeout=None):
        """Return (status, headers, body, elapsed_ms). Never raises on HTTP."""
        t0 = time.perf_counter()
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout or self.timeout)
        try:
            body_bytes = None if body is None else body if isinstance(body, bytes) else body.encode("utf-8")
            conn.request(method, self.path, body=body_bytes, headers=headers or {})
            resp = conn.getresponse()
            data = resp.read()
            hdrs = {k.lower(): v for k, v in resp.getheaders()}
            elapsed = (time.perf_counter() - t0) * 1000.0
            return resp.status, hdrs, data, elapsed
        finally:
            conn.close()


def peek(body):
    b = body if isinstance(body, bytes) else body
    if b is None:
        return ""
    return b[:PEEK_BODY].decode("utf-8", errors="replace")


def result(case, status, headers, body, elapsed_ms, expected, extra=None):
    out = {
        "case": case,
        "status": status,
        "headers": {k: v for k, v in list(headers.items())[:8]} if headers else {},
        "body": peek(body),
        "elapsed_ms": round(elapsed_ms, 1),
        "expected": expected,
    }
    if extra:
        out["extra"] = extra
    print(json.dumps(out))
    return out


def rpc(method, params=None, rid=1):
    msg = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def auth_headers(token, origin=None):
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "mcp-attack-lab/1.0",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
        h["X-FlaxMcp-Token"] = token
    if origin:
        h["Origin"] = origin
    return h


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
def mode_baseline(tgt, args):
    """M-00 baseline: tools/list with valid token - the control case."""
    status, hdrs, body, ms = tgt.request(
        "POST", rpc("tools/list", rid=1), auth_headers(args.token)
    )
    result("M-00-baseline", status, hdrs, body, ms, "200 + tools/list result")
    return status


def mode_no_token(tgt, args):
    """M-01 no token -> 401 / fail-closed."""
    for i in range(args.count):
        status, hdrs, body, ms = tgt.request("POST", rpc("tools/list", rid=i + 1), auth_headers(None))
        result(f"M-01-no-token-{i}", status, hdrs, body, ms, "401 (or fail-closed 4xx)")
    return 0


def mode_wrong_token(tgt, args):
    """M-02/M-03 wrong + casing-variant tokens -> 401, no oracle leak."""
    samples = ["wrong", "A" * 32, "a" * 32, " x", "x ", "Bearer", "b" * 64, "0" * 8]
    for i in range(args.count):
        tok = samples[i % len(samples)]
        status, hdrs, body, ms = tgt.request("POST", rpc("tools/list", rid=i + 1), auth_headers(tok))
        result(f"M-02-wrong-token-{i}", status, hdrs, body, ms, "401 regardless of token shape")


def mode_origin_spoof(tgt, args):
    """M-10/M-11 wrong or spoofed Origin -> rejected by OriginValidator."""
    origins = [
        args.origin,
        "https://evil.example",
        "http://evil.example",
        "null",
        "http://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1:9999",
        "file://",
    ]
    for i, o in enumerate(set(o for o in origins if o)):
        h = auth_headers(args.token, origin=o)
        h["Host"] = "evil.example"
        status, hdrs, body, ms = tgt.request("POST", rpc("tools/list", rid=i + 1), h)
        result(f"M-10-origin-spoof-{i}", status, hdrs, body, ms, "403/400 - origin rejected")
    # M-11: no Origin at all (browser-style) - loopback CSRF check
    h = auth_headers(args.token)
    status, hdrs, body, ms = tgt.request("POST", rpc("tools/list", rid=99), h)
    result("M-11-no-origin", status, hdrs, body, ms, "rejected if origin required")


def mode_method_fuzz(tgt, args):
    """M-11 HTTP method abuse: only POST may reach dispatch."""
    for m in ["GET", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]:
        status, hdrs, body, ms = tgt.request(m, rpc("tools/list", rid=1), auth_headers(args.token))
        result(f"M-11-method-{m}", status, hdrs, body, ms, "405 (no dispatch on wrong method)")


def mode_arg_bombs(tgt, args):
    """M-30 arg bombs + M-13 unknown tool: probe each discovered tool."""
    tools = []
    status, hdrs, body, ms = tgt.request("POST", rpc("tools/list"), auth_headers(args.token))
    try:
        parsed = json.loads(body)
        for t in parsed.get("result", {}).get("tools", []):
            tools.append(t.get("name"))
    except (ValueError, AttributeError):
        tools = args.tools.split(",") if args.tools else ["manage_security"]
    if not tools:
        tools = ["manage_security"]
    bombs = [
        ("giant-string", lambda: "A" * (512 * 1024)),
        ("deep-nesting", lambda: nested(24)),
        ("wrong-types", lambda: {"x": {"deep": [1, [2, [3]]]}}),
        ("extra-unknown-arg", lambda: {"__unexpected__": "x", "nope": 1}),
        ("empty", lambda: {}),
        ("null", lambda: None),
        ("array", lambda: [1, 2, 3]),
        ("traversal", lambda: {"path": "../../../Windows/System32/config/SAM"}),
        ("abs-path", lambda: {"path": "C:/Windows/System32/calc.exe"}),
        ("unc-path", lambda: {"path": "\\\\server\\share\\file"}),
    ]
    rid = 0
    for name in tools:
        for label, make in bombs:
            rid += 1
            try:
                params = {"name": name, "arguments": make()}
            except Exception:
                params = {"name": name, "arguments": {}}
            status, hdrs, body, ms = tgt.request(
                "POST", rpc("tools/call", params, rid=rid), auth_headers(args.token)
            )
            result(
                f"M-30-bomb-{label}-{name}", status, hdrs, body, ms,
                "structured validation error; tool never executes",
            )
    # M-13 unknown method / tool typo
    status, hdrs, body, ms = tgt.request("POST", rpc("tools/call", {"name": "zz_no_such_tool", "arguments": {}}, rid=rid + 1), auth_headers(args.token))
    result("M-13-unknown-tool", status, hdrs, body, ms, "error, no dispatch")
    status, hdrs, body, ms = tgt.request("POST", rpc("no_such_method", rid=rid + 2), auth_headers(args.token))
    result("M-13-unknown-method", status, hdrs, body, ms, "JSON-RPC method not found")


def nested(depth):
    v = "x"
    for _ in range(depth):
        v = [v]
    return v


def mode_batch(tgt, args):
    """M-14 JSON-RPC batch: each item validated independently, bounded."""
    items = [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "zz_bad"}},
        {"not": "jsonrpc"},
        [],
        {},
        None,
        "string-item",
        {"jsonrpc": "2.0", "id": 3, "method": "ping"},
    ] * args.count
    status, hdrs, body, ms = tgt.request("POST", json.dumps(items), auth_headers(args.token))
    result("M-14-batch", status, hdrs, body, ms, "bounded; per-item errors; no crash")


def mode_flood(tgt, args):
    """M-16 connection flood: accept loop must stay alive."""
    failures = []
    lat = []

    def one(i):
        try:
            status, hdrs, body, ms = tgt.request(
                "POST", rpc("tools/list", rid=i), auth_headers(args.token), timeout=10.0
            )
            return status, ms
        except Exception as e:
            return f"EXC:{type(e).__name__}:{e}", None

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for st, ms in ex.map(one, range(args.count)):
            if isinstance(st, str):
                failures.append(st)
            else:
                lat.append(ms)
    status, hdrs, body, ms = tgt.request("POST", rpc("tools/list", rid=999999), auth_headers(args.token))
    result(
        "M-16-flood", status, hdrs, body, ms,
        "accept loop alive after flood",
        extra={
            "sent": args.count,
            "concurrency": args.concurrency,
            "client_failures": failures[:5],
            "client_failure_count": len(failures),
            "median_lat_ms": round(statistics.median(lat), 1) if lat else None,
        },
    )


def mode_sse(tgt, args):
    """M-17 SSE: stream hijack / mid-stream disconnect / session replay."""
    conn = http.client.HTTPConnection(tgt.host, tgt.port, timeout=args.timeout)
    h = auth_headers(args.token)
    h["Accept"] = "text/event-stream"
    h["Mcp-Session-Id"] = args.session if args.session else "attacker-forged-session"
    conn.request("GET", tgt.path, headers=h)
    resp = conn.getresponse()
    chunk = None
    try:
        chunk = resp.read1(256)
    except Exception as e:
        chunk = f"EXC:{type(e).__name__}"
    result(
        "M-17-sse", resp.status, {k.lower(): v for k, v in resp.getheaders()}, chunk, 0,
        "no cross-session data; stream bounded",
        extra={"session_used": h["Mcp-Session-Id"]},
    )
    conn.close()


def mode_openapi(tgt, args):
    """M-18 OpenAPI endpoint: tool list only, no secrets/paths beyond schema."""
    for p in ["/openapi", "/openapi.json", "/swagger", "/swagger.json", "/docs", "/mcp/openapi", "/.well-known/mcp"]:
        from urllib.parse import urlparse
        u = urlparse(tgt.url)
        t = McpTarget(f"{u.scheme}://{u.netloc}{p}")
        status, hdrs, body, ms = t.request("GET", headers=auth_headers(args.token))
        result(f"M-18-openapi-{p}", status, hdrs, body, ms, "200 schema only (or 404 - fine)")
        if status == 200 and body:
            leaked = set()
            for pat in ["FLAXMCP_TOKEN", "Authorization", "secret", "password"]:
                if pat.lower() in body.decode("utf-8", errors="replace").lower():
                    leaked.add(pat)
            if leaked:
                result(f"M-18-leak-{p}", status, hdrs, body, ms, "no token/secret strings in schema", extra={"leaked_patterns": sorted(leaked)})


def mode_endpoints(tgt, args):
    """Endpoint discovery: what else does the listener serve?"""
    for p in ["/", "/metrics", "/health", "/status", "/favicon.ico", "/mcp", "/sse", "/events"]:
        from urllib.parse import urlparse
        u = urlparse(tgt.url)
        t = McpTarget(f"{u.scheme}://{u.netloc}{p}")
        status, hdrs, body, ms = t.request("GET", headers=auth_headers(args.token))
        result(f"discover-{p or '/'}", status, hdrs, body, ms, "baseline only (404 fine)")


def mode_timing(tgt, args):
    """M-04 FixedTimeEquals timing check: bad-token latency must be flat."""
    good = []
    for _ in range(max(1, args.count // 4)):
        status, hdrs, body, ms = tgt.request("POST", rpc("tools/list"), auth_headers(args.token))
        good.append(ms)
    bad = []
    for i in range(args.count):
        tok = secrets_ish(i)
        status, hdrs, body, ms = tgt.request("POST", rpc("tools/list", rid=i + 1), auth_headers(tok))
        bad.append(ms)
    result(
        "M-04-timing", None, None, None, 0,
        "bad-token latency ~flat (FixedTimeEquals holds)",
        extra={
            "good_median_ms": round(statistics.median(good), 2),
            "good_min_ms": round(min(good), 2),
            "bad_median_ms": round(statistics.median(bad), 2),
            "bad_min_ms": round(min(bad), 2),
            "bad_p90_ms": round(sorted(bad)[int(len(bad) * 0.9)], 2),
            "gap_ms": round(statistics.median(bad) - statistics.median(good), 2),
            "note": "gap < ~15ms = constant-time holds; jitter on shared machines is expected",
        },
    )


def secrets_ish(i):
    return f"bad-token-{i:08x}-{'x' * 24}"


def mode_env_probe(tgt, args):
    """M-06 Position B: sibling/child process visibility of FLAXMCP_TOKEN."""
    found = os.environ.get("FLAXMCP_TOKEN")
    child = subprocess.run(
        ["cmd", "/c", "echo %FLAXMCP_TOKEN%"], capture_output=True, text=True, timeout=10
    )
    inherited = child.stdout.strip()
    result(
        "M-06-env-probe", None, None, None, 0,
        "token only in the launching user's env; no cross-user read",
        extra={
            "current_process_has_token": bool(found),
            "child_inherits_token": bool(inherited),
            "note": "same-USER processes on Windows can read the env block of siblings; "
                    "documented risk in TokenValidator.cs - the fix is launch separation",
        },
    )


# ---------------------------------------------------------------------------
MODES = {
    "baseline": mode_baseline,
    "no-token": mode_no_token,
    "wrong-token": mode_wrong_token,
    "origin-spoof": mode_origin_spoof,
    "method-fuzz": mode_method_fuzz,
    "arg-bombs": mode_arg_bombs,
    "batch": mode_batch,
    "flood": mode_flood,
    "sse": mode_sse,
    "openapi": mode_openapi,
    "endpoints": mode_endpoints,
    "timing": mode_timing,
    "env-probe": mode_env_probe,
}


def main():
    p = argparse.ArgumentParser(description="FlaxMCP plugin attacker client (lab use only)")
    p.add_argument("--mode", choices=sorted(MODES), required=True)
    p.add_argument("--url", default=DEFAULT_URL, help="MCP endpoint (default %(default)s)")
    p.add_argument("--token", default="", help="FLAXMCP_TOKEN for authed modes")
    p.add_argument("--origin", default="https://evil.example")
    p.add_argument("--count", type=int, default=8)
    p.add_argument("--concurrency", type=int, default=32)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--session", default="", help="forged Mcp-Session-Id (sse mode)")
    p.add_argument("--tools", default="", help="comma-separated tool names for arg-bombs")
    args = p.parse_args()

    tgt = McpTarget(args.url, timeout=args.timeout)
    try:
        sys.exit(MODES[args.mode](tgt, args) or 0)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
