# Wire Format — Flax 1.12 Game Server (reverse-engineered)

**Target:** `samples\game-project` server on UDP port 7777 (default).
**Engine:** Flax 1.12.6912. **Transport:** ENet (vendored amalgamation in
`Source/ThirdParty/enet`, used by `ENetDriver.cpp`).
**Derived from:** engine source (GitHub FlaxEngine/FlaxEngine), ENet
`protocol.h`, `FlaxEngine.CSharp.dll` reflection probes, and the game's
`NetworkPackets.cs` / `NetworkCombatSync.cs`.

---

## 1. ENet datagram framing (all multi-byte fields BIG-ENDIAN)

```
ENetProtocolHeader:
  uint16 peerID   (BE):  bits 15 = SENT_TIME, 14 = COMPRESSED,
                         13-12 = session id (2 bits), 11-0 = peer id
  uint16 sentTime (BE)   [only present if SENT_TIME set]

Commands (repeated until datagram end):
  uint8  command   bits 3-0 = command id, bit 7 = ACK requested,
                   bit 6 = UNSEQUENCED
  uint8  channelID (0xFF = control channel, 0 = data)
  uint16 reliableSequenceNumber (BE)
  + per-command body (see table)
```

| Command | id | Body after header |
|---|---|---|
| ACKNOWLEDGE | 1 | `u16 BE receivedReliableSequenceNumber`, `u16 BE receivedSentTime` |
| CONNECT | 2 | `u16 outgoingPeerID, u8 inSession, u8 outSession, u32 mtu, u32 windowSize, u32 channelCount, u32 inBW, u32 outBW, u32 throttleInterval, u32 throttleAccel, u32 throttleDecel, u32 connectID, u32 data` (52B) |
| VERIFY_CONNECT | 3 | same as CONNECT minus `data` (48B) |
| DISCONNECT | 4 | `u32 data` |
| PING | 5 | — |
| SEND_RELIABLE | 6 | `u16 BE dataLength` + payload |
| SEND_UNRELIABLE | 7 | `u16 BE unreliableSequenceNumber, u16 BE dataLength` + payload |
| SEND_FRAGMENT | 8 | `u16 startSeq, u16 dataLength, u32 fragCount, u32 fragNumber, u32 totalLength, u32 fragOffset` + fragment |
| SEND_UNSEQUENCED | 9 | `u16 BE group, u16 BE dataLength` + payload |
| BANDWIDTH_LIMIT | 10 | `u32 in, u32 out` |
| THROTTLE_CONFIGURE | 11 | `u32 interval, u32 accel, u32 decel` |

Flax config: **1 channel**, channel 0 used for everything; no compression,
no checksum. `ReliableOrdered` → ENet reliable (command 6, ACK flag 0x80).
`Unreliable` → command 7; `UnreliableOrdered` → command 7 with reliable-ACK
flag cleared (ordered via seq). MTU default 1400 → payloads > ~1388 bytes are
fragmented by ENet (SEND_FRAGMENT).

### Handshake (client ⇒ server)

1. Client → `CONNECT` (cmd 0x82 = 2|0x80, channel 0xFF, control seq **1**,
   outgoingPeerID **0**, sessions 0/0, mtu 1400, window 65536, channelCount 1,
   bandwidths 0, throttle 5000/2/2, connectID random).
2. Server → `VERIFY_CONNECT` (0x83, control seq 1, outgoingPeerID = assigned
   client id 0,1,2…, sessions 1/1, same window/mtu/throttle, same connectID).
3. Client → `ACK` (receivedReliableSequenceNumber = 1). **Without this ACK the
   server peer never reaches CONNECTED** and the game never sees the client.
4. Client header on later datagrams: `(outSession << 12) | clientId`
   (outSession = verify.outgoingSessionID).

## 2. Game message payload (Flax NetworkMessage, LITTLE-ENDIAN)

Sent as the raw payload of channel-0 commands. First byte = packet id.

| Type | Wire format |
|---|---|
| byte/bool | 1 byte raw |
| int16/32/64, uint16/32/64, float, double | raw little-endian |
| string | `u16 LE char count` + UTF-16LE bytes (**no length cap — up to 65535 chars / 128 KiB**) |
| Guid | 16 raw bytes, .NET layout: `i32 LE + i16 LE + i16 LE + 8 raw` |
| Vector3 | 3 × float LE (12B) |
| Quaternion | 4 × float LE (16B) |

### Packet schemas

| ID | Name | Fields (wire order) | Direction |
|---|---|---|---|
| 1 | ConnectionRequest | `u8 id, str Username, i32 LE tokenLen, bytes Token[≤1024]` | C→S |
| 2 | ConnectionResponse | `u8 id, u8 State (0=Accepted,1=Rejected), Guid ID` | S→C |
| 3 | PlayerList | `u8 id, i32 LE count, count × (str Name, Guid ID)` | S→C |
| 4 | PlayerConnected | `u8 id, Guid ID, str Username` | S→C |
| 5 | PlayerDisconnected | `u8 id, Guid ID` | S→C |
| 6 | PlayerTransform | (reserved; no schema, registry omits) | — |
| 7 | PlayersTransform | `u8 id, i32 LE count, count × (Guid, Vector3 pos, Quaternion rot)` (44B/entry) | S→C |
| 8 | ChatMessage | `u8 id, str Message, bool hasSender, Guid SenderID?` | both |
| 200 | CombatEvent | `u8 id, u8 EventType (0=Hit,1=Damage,2=Death,3=Dismember), i32 attacker, i32 target, f32 damage, u8 kind, bool isCritical, f32 impactX, f32 impactY, f32 impactZ` (28B) | S→C |

## 3. Attack surface notes (from code audit, see reports/FINDINGS-001)

- **No cap on `ConnectionRequest.Username` string** (`ReadString` allocates up
  to 128 KiB before `SanitizeUsername` caps at 24 chars). Client→server.
- **`PlayerList`/`PlayersTransform` counts are unbounded** — `ReadInt32` → list
  alloc. Server→client (malicious-server / faked-server attacks; also any
  client can *receive* them).
- **No handshake rate limit**: ConnectionRequest handling has no throttle; chat
  has one (5/s/sender, window resets 1/s). Client→server.
- **No transform validation**: server accepts any PlayerTransform-shaped data.
- **Unknown packet ids**: `PacketRegistry` logs a warning per unknown id —
  `packet-soup` mode generates log-spam.

## 4. Lab tools that speak this format

| Tool | Purpose |
|---|---|
| `tools/raw-client/flax_enet.py` | pure-Python ENet client: handshake, crafted payloads, floods, fuzzing |
| `tools/dissector/flax_enet.lua` | Wireshark dissector for udp.port 7777 |
| `tools/wire-probe/` | .NET reflection probe that empirically extracted this format |
