#!/usr/bin/env python
"""boofuzz fuzzer for the Flax game server (UDP 7777, ENet framing).

Each test case opens a fresh ENet session (CONNECT / VERIFY_CONNECT / ACK
handshake via flax_enet.py) and sends ONE framed SEND_RELIABLE containing a
mutated ConnectionRequest (packet id 1).

Fuzzed fields: packet id byte, username (u16le char-count + UTF-16LE, count
itself fuzzable), token length (i32le) and token bytes.

Crash oracle: a fresh out-of-band handshake probe every --probe-every cases;
if the server no longer answers the probe, the run aborts with a CRASH report.

Usage:
    .venv\\Scripts\\python.exe fuzz_enet.py --host 127.0.0.1 --port 7777 --cases 2000
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw-client"))
import flax_enet as fe  # noqa: E402

from boofuzz import (  # noqa: E402
    Session,
    Target,
    s_byte,
    s_bytes,
    s_block,
    s_get,
    s_initialize,
    s_int,
    s_size,
    s_string,
    FuzzLoggerText,
    FuzzLoggerCsv,
)
from boofuzz.connections import UDPSocketConnection  # noqa: E402

CRASH_MARKER = "CRASH"


class EnetUDPSocketConnection(UDPSocketConnection):
    """UDPSocketConnection that speaks ENet: handshake on open(), frame in send()."""

    def __init__(self, host, port, username="fuzz", send_timeout=5.0, recv_timeout=3.0, probe_every=25):
        super().__init__(host, port, send_timeout=send_timeout, recv_timeout=recv_timeout)
        self.username = username
        self.probe_every = probe_every
        self.client = None
        self.case_count = 0

    def open(self):
        self.case_count += 1
        self.client = fe.EnetClient(self.host, self.port, timeout=3.0)
        if not self.client.connect():
            raise ConnectionError("ENet handshake failed (server down or not listening)")
        self._probe_if_due()

    def send(self, data):
        try:
            self.client.send_reliable(data)
            return len(data)
        except OSError as e:
            raise ConnectionError(f"send failed: {e}")

    def recv(self, max_bytes=None):
        try:
            self.client.pump(0.1)
            return b""
        except OSError as e:
            raise ConnectionError(f"recv failed: {e}")

    def close(self):
        try:
            if self.client:
                self.client.disconnect()
        finally:
            self.client = None

    def _probe_if_due(self):
        """Every N test cases, verify the server still accepts fresh handshakes."""
        if self.case_count % self.probe_every != 0:
            return
        probe = fe.EnetClient(self.host, self.port, timeout=1.5)
        alive = probe.connect()
        if probe.sock:
            probe.sock.close()
        if not alive:
            raise ConnectionError(
                f"{CRASH_MARKER} server not answering handshake probe at case {self.case_count}"
            )


def build_session(host, port, username, cases, probe_every):
    conn = EnetUDPSocketConnection(host, port, username=username, probe_every=probe_every)

    s_initialize("ConnectionRequest")
    s_byte(1, name="packet_id")
    with s_block("username_block"):
        s_size(length=2, endian="<", block_name="username", math=lambda x: x // 2, name="username_len")
        s_string(username, encoding="utf-16-le", max_len=65535, name="username")
    s_int(0, endian="<", name="token_len")
    s_bytes(b"A" * 32, max_len=1024, name="token")

    target = Target(connection=conn, max_recv_bytes=65535)
    loggers = [FuzzLoggerText()]
    if args.csv:
        loggers.append(FuzzLoggerCsv(csv_file_path=args.csv))
    session = Session(
        target=target,
        index_end=cases,
        sleep_time=0.0,
        reuse_target_connection=False,
        receive_data_after_each_request=True,
        ignore_connection_reset=False,
        ignore_connection_aborted=False,
        fuzz_loggers=loggers,
        db_filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuzz-results.db"),
        console_gui=False,
        keep_web_open=False,
        web_port=0,
    )
    session.connect(s_get("ConnectionRequest"))
    return session


def main():
    global args
    p = argparse.ArgumentParser(description="boofuzz ENet fuzzer for the Flax game server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7777)
    p.add_argument("--username", default="fuzzbot")
    p.add_argument("--cases", type=int, default=500)
    p.add_argument("--probe-every", type=int, default=25, help="liveness probe interval (cases)")
    p.add_argument("--csv", default="", help="optional CSV log path")
    args = p.parse_args()

    print(f"[*] target {args.host}:{args.port}  cases={args.cases}  probe_every={args.probe_every}")
    print(f"[*] seed packet: ConnectionRequest(username={args.username!r}, token=32xA)")
    session = build_session(args.host, args.port, args.username, args.cases, args.probe_every)
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
