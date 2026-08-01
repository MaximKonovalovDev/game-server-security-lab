#!/usr/bin/env python
"""boofuzz fuzzer for the FlaxMCP HTTP endpoint (localhost:8765/mcp).

Fuzzes a raw HTTP/1.1 POST (JSON-RPC body + key headers) over TCP - same
boofuzz style as tools/boofuzz/fuzz_enet.py but for the MCP surface.

Fuzzed fields: method name, jsonrpc version literal, id type/value, params
structure, and the auth header value (token). Each case is a fresh connection
so the HttpListener's keep-alive/chunking paths don't mask faults.

Crash oracle: a plain "tools/list" probe every --probe-every cases; if the
server stops answering, the run aborts with a CRASH report.

Usage:
    ..\\boofuzz\\.venv\\Scripts\\python.exe fuzz_mcp.py --host 127.0.0.1 --port 8765 --cases 800
"""

import argparse
import os

from boofuzz import (  # noqa: E402
    Session,
    Target,
    s_byte,
    s_get,
    s_initialize,
    s_static,
    s_string,
    FuzzLoggerText,
)
from boofuzz.connections import TCPSocketConnection  # noqa: E402

CRASH_MARKER = "CRASH"


class McpHttpConnection(TCPSocketConnection):
    """TCP connection that verifies listener liveness every N cases."""

    def __init__(self, host, port, probe_every=25, **kw):
        super().__init__(host, port, send_timeout=5.0, recv_timeout=3.0, **kw)
        self.probe_every = probe_every
        self.case_count = 0
        self.alive = True

    def open(self):
        self.case_count += 1
        super().open()
        if self.case_count % self.probe_every == 0:
            self._probe()

    def _probe(self):
        import socket

        s = socket.create_connection((self.host, self.port), timeout=2.0)
        try:
            s.sendall(
                b"POST /mcp HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                b"Content-Length: 52\r\n\r\n"
                b'{"jsonrpc":"2.0","id":999999,"method":"tools/list"}'
            )
            s.settimeout(2.0)
            data = s.recv(256)
            self.alive = b"HTTP/1.1" in data
        except OSError:
            self.alive = False
        finally:
            s.close()
        if not self.alive:
            raise ConnectionError(
                f"{CRASH_MARKER} server not answering probe at case {self.case_count}"
            )


def build_session(host, port, cases, probe_every):
    conn = McpHttpConnection(host, port, probe_every=probe_every)

    s_initialize("McpPost")
    s_static(b"POST /mcp HTTP/1.1\r\n")
    s_static(b"Host: localhost\r\n")
    s_static(b"Content-Type: application/json\r\n")
    s_static(b"Accept: application/json, text/event-stream\r\n")
    s_string("Authorization: Bearer ", max_len=64, name="auth_prefix")
    s_string("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", max_len=512, name="token")
    s_static(b"\r\n")
    s_static(b"Content-Length: ")
    s_string("201", max_len=16, name="content_length")
    s_static(b"\r\n\r\n")
    s_static(b'{"jsonrpc":"')
    s_string("2.0", max_len=32, name="jsonrpc_version")
    s_static(b'","id":')
    s_byte(1, name="rpc_id")
    s_static(b',"method":"')
    s_string("tools/list", max_len=512, name="method")
    s_static(b'","params":')
    s_string('{"name":"manage_security","arguments":{}}', max_len=2048, name="params")
    s_static(b"}")

    target = Target(connection=conn, max_recv_bytes=65535)
    session = Session(
        target=target,
        index_end=cases,
        sleep_time=0.0,
        reuse_target_connection=False,
        receive_data_after_each_request=True,
        ignore_connection_reset=False,
        ignore_connection_aborted=False,
        fuzz_loggers=[FuzzLoggerText()],
        db_filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuzz-mcp-results.db"),
        console_gui=False,
        keep_web_open=False,
        web_port=0,
    )
    session.connect(s_get("McpPost"))
    return session


def main():
    global args
    p = argparse.ArgumentParser(description="boofuzz MCP HTTP fuzzer for the FlaxMCP plugin")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--cases", type=int, default=500)
    p.add_argument("--probe-every", type=int, default=25, help="liveness probe interval (cases)")
    args = p.parse_args()

    print(f"[*] target {args.host}:{args.port}  cases={args.cases}  probe_every={args.probe_every}")
    print("[*] seed request: POST /mcp tools/list with fake bearer token")
    session = build_session(args.host, args.port, args.cases, args.probe_every)
    try:
        session.fuzz()
        print("[*] run finished without crash probe trigger")
    except ConnectionError as e:
        print(f"[!] {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("[!] interrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
