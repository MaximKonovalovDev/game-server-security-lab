#!/usr/bin/env python
"""Fake Flax game server for lab dry-runs.

Mimics the real game server's wire behavior on UDP (default 7777):
  - ENet handshake (CONNECT / VERIFY_CONNECT / ACK), multi-client
  - ConnectionRequest (id 1)  -> ConnectionResponse (id 2) + PlayerList (id 3)
  - ChatMessage (id 8)        -> echoed back to the sender with server Guid
  - periodic PlayersTransform (id 7) ticks to all clients (--tick)
  - unknown packet ids logged (mirrors PacketRegistry warning)
Logs every received payload to stdout (hex) and session events to --log-file.

Usage:
    .venv\\Scripts\\python.exe fake_flax_server.py --port 7777 --log-file server.log
"""

import argparse
import os
import socket
import struct
import sys
import threading
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw-client"))
import flax_enet as fe  # noqa: E402

SERVER_GUID = "3f6c8f2a-1b4e-4a2d-9c81-07d3e5f1a9b2"


class FakeServer:
    def __init__(self, host, port, tick=0.5, log=None):
        self.addr = (host, port)
        self.tick = tick
        self.log = log or sys.stdout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.addr)
        self.peers = {}          # addr -> {connect_id, peer_id, rel_seq, unrel_seq, name, guid}
        self.chat_counter = 0
        self.next_peer_id = 0
        self.running = True

    def say(self, *a):
        print(*a, file=self.log, flush=True)

    # -- helpers -------------------------------------------------------------

    def send_verify(self, addr, connect_id):
        peer_id = self.next_peer_id
        self.next_peer_id += 1
        self.peers[addr] = {
            "connect_id": connect_id, "peer_id": peer_id,
            "rel_seq": 0, "unrel_seq": 0, "name": None, "guid": None,
        }
        v = fe.enet_header(0)
        v += bytes([fe.CMD_VERIFY_CONNECT | fe.CMD_FLAG_ACKNOWLEDGE, fe.CHANNEL_CONTROL]) + struct.pack(">H", 1)
        v += struct.pack(">H", peer_id) + bytes([1, 1])
        v += struct.pack(">I", 1400) + struct.pack(">I", 65536) + struct.pack(">I", 1)
        v += struct.pack(">I", 0) + struct.pack(">I", 0)
        v += struct.pack(">I", 5000) + struct.pack(">I", 2) + struct.pack(">I", 2)
        v += struct.pack(">I", connect_id)
        self.sock.sendto(v, addr)

    def send_to(self, addr, payload, reliable=True):
        p = self.peers[addr]
        self.peers[addr]["rel_seq"] += 1
        seq = self.peers[addr]["rel_seq"]
        hdr = fe.enet_header((1 << 12) | p["peer_id"])
        cmd = (fe.CMD_SEND_RELIABLE | fe.CMD_FLAG_ACKNOWLEDGE) if reliable else fe.CMD_SEND_UNRELIABLE
        body = bytes([cmd, 0]) + struct.pack(">H", seq)
        if reliable:
            body += struct.pack(">H", len(payload)) + payload
        else:
            self.peers[addr]["unrel_seq"] += 1
            body += struct.pack(">H", self.peers[addr]["unrel_seq"]) + struct.pack(">H", len(payload)) + payload
        try:
            self.sock.sendto(hdr + body, addr)
        except ConnectionResetError:
            pass  # destination socket closed; drop
        except OSError as e:
            self.say(f"[*] sendto {addr}: {e}")

    def make_player_list(self, exclude=None):
        players = []
        for addr, p in self.peers.items():
            if p["name"] is not None and addr != exclude:
                players.append((p["name"], p["guid"]))
        out = bytearray(fe.encode_game_packet(3, [("i32", len(players))]))
        for name, guid in players:
            out += fe.enc_str(name) + fe.enc_guid(guid)
        return bytes(out)

    # -- handlers ------------------------------------------------------------

    def on_connection_request(self, addr, payload):
        pid, info = fe.parse_game_packet(payload)
        if pid != 1:
            self.on_unknown(addr, payload)
            return
        name, token = info["username"], bytes.fromhex(info["token"])
        p = self.peers.get(addr)
        self.say(f"[{addr[1]}] ConnectionRequest username={name!r} token_len={len(token)}")
        if p is None:
            self.say(f"[{addr[1]}] !! ConnectionRequest from unauthenticated peer (no handshake)")
            return
        # mirror game logic: sanitize + truncate username like SanitizeUsername
        clean = "".join(ch for ch in name if ch.isprintable())[:24]
        p["name"] = clean
        p["guid"] = str(uuid.UUID(int=uuid.uuid4().int, version=4))
        resp = fe.encode_game_packet(2, [("u8", 0), ("guid", p["guid"])])
        self.send_to(addr, resp)
        # announce + send player list to the new client
        joined = fe.encode_game_packet(4, [("guid", p["guid"]), ("str", clean)])
        for other in list(self.peers):
            if other != addr and self.peers[other]["name"]:
                self.send_to(other, joined)
        self.send_to(addr, self.make_player_list(exclude=None))

    def on_chat(self, addr, payload):
        pid, info = fe.parse_game_packet(payload)
        if pid != 8:
            self.on_unknown(addr, payload)
            return
        p = self.peers.get(addr)
        self.chat_counter += 1
        self.say(f"[{addr[1]}] Chat #{self.chat_counter} len={len(info['message'])} has_sender={info['has_sender']}")
        if p is None or p["name"] is None:
            return
        if not info["has_sender"]:
            return
        # echo with server guid (like a real server relay)
        echo = fe.encode_game_packet(8, [("str", info["message"]), ("u8", 1), ("guid", p["guid"])])
        self.send_to(addr, echo)

    def on_unknown(self, addr, payload):
        self.say(f"[{addr[1]}] PacketRegistry warning: unknown id {payload[0]:#x} len={len(payload)}")

    # -- main loop -----------------------------------------------------------

    def run(self):
        self.say(f"[*] fake Flax server listening on UDP {self.addr[0]}:{self.addr[1]} (tick={self.tick}s)")
        self.sock.settimeout(0.1)
        last_tick = 0.0
        while self.running:
            data, addr = None, None
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                pass
            except ConnectionResetError:
                pass  # Windows: ICMP port-unreachable from closed client sockets
            except OSError:
                break
            if data:
                try:
                    self.handle_datagram(data, addr)
                except ConnectionResetError:
                    pass
                except Exception as e:
                    self.say(f"[{addr[1]}] handler error: {e}")
            now = time.monotonic()
            if self.tick and now - last_tick >= self.tick:
                last_tick = now
                try:
                    self.send_transforms()
                except ConnectionResetError:
                    pass
                except Exception as e:
                    self.say(f"[*] tick error: {e}")

    def handle_datagram(self, data, addr):
        try:
            parsed = fe.parse_datagram(data)
        except Exception as e:
            self.say(f"[{addr[1]}] parse error: {e}")
            return
        if parsed is None:
            self.say(f"[{addr[1]}] short/garbage datagram ({len(data)}B)")
            return
        pid, session, st, cmds = parsed
        for cid, ch, seq, body in cmds:
            if cid == fe.CMD_CONNECT:
                self.say(f"[{addr[1]}] CONNECT connect_id={body['connect_id']:#x}")
                self.send_verify(addr, body["connect_id"])
            elif cid == fe.CMD_ACKNOWLEDGE:
                pass  # quiet
            elif cid == fe.CMD_SEND_RELIABLE and ch == 0:
                if body[:1] == b"\x01":
                    self.on_connection_request(addr, body)
                elif body[:1] == b"\x08":
                    self.on_chat(addr, body)
                else:
                    self.on_unknown(addr, body)
            elif cid == fe.CMD_SEND_UNRELIABLE and ch == 0:
                self.say(f"[{addr[1]}] UNRELIABLE {body['data'].hex()}")
                self.on_unknown(addr, body["data"])
            elif cid in (fe.CMD_PING, fe.CMD_BANDWIDTH_LIMIT, fe.CMD_THROTTLE_CONFIGURE):
                self.say(f"[{addr[1]}] control cmd {cid} ch={ch} seq={seq}")
            elif cid == fe.CMD_DISCONNECT:
                if addr in self.peers:
                    self.say(f"[{addr[1]}] disconnect (peer {self.peers[addr]['peer_id']})")
                    del self.peers[addr]
            else:
                self.say(f"[{addr[1]}] unexpected cmd {cid} ch={ch} seq={seq}")

    def send_transforms(self):
        for addr in list(self.peers):
            p = self.peers[addr]
            if p["name"] is None:
                continue
            entries = []
            for o in self.peers.values():
                if o["name"] is not None:
                    entries.append((o["guid"], (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
            out = bytearray(fe.encode_game_packet(7, [("i32", len(entries))]))
            for guid, pos, rot in entries:
                out += fe.enc_guid(guid)
                for f in pos + rot:
                    out += struct.pack("<f", f)
            self.send_to(addr, bytes(out), reliable=False)


def main():
    p = argparse.ArgumentParser(description="fake Flax game server for lab dry-runs")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7777)
    p.add_argument("--tick", type=float, default=0.5, help="transform tick seconds (0 = off)")
    p.add_argument("--log-file", default="", help="log file (default: stdout)")
    args = p.parse_args()
    log = open(args.log_file, "a", encoding="utf-8") if args.log_file else sys.stdout
    srv = FakeServer(args.host, args.port, tick=args.tick, log=log)
    try:
        srv.run()
    except KeyboardInterrupt:
        pass
    finally:
        srv.running = False
        if args.log_file:
            log.close()


if __name__ == "__main__":
    main()
