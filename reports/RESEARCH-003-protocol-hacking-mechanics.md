# RESEARCH-003 — Protocol-Hacking Deep Dive: How Packet Games Are Actually Broken (2026-08-01)

Deep dive into the *mechanics* of packet-level game hacking — the actual techniques, tools, and case
studies — plus a measured ENet attack surface from the vendored source, and the defense-prep spec
for the Flax lab. Complements RESEARCH-001 (lab audit) and RESEARCH-002 (games killed by cheaters).

---

## 1. The five ways packet games are actually broken

Every real-world case from the Korean MMO era (RYL, Lineage 2, Ragnarok, MapleStory) through AoS
and 2026 web games reduces to five techniques:

### 1.1 Winsock/LSP interception (WPE Pro era)
- **WPE Pro** (Winsock Packet Editor): attaches to a process, hooks the winsock layer (LSP), sniffs
  `send/sendto/recv/recvfrom`, lets you create filters that *rewrite* packets on the fly, or replay
  recorded packets at custom intervals. Flow per 2007 CE-forum tutorial: attach → sniff → stop →
  filter → search bytes → change value → uncheck RECVFROM/RECV → apply → on.
- **l2phx** (L2 Packet Hack, by xkor) was WPE's L2-specific descendant: full sniff/send/replace GUI,
  plus *per-server decryption modules* (`newxor.dll`) because top servers added custom packet
  encryption. When a protection blocked LSP-based tools, the cheat scene moved in-process.
- Attack shape: nothing leaves the game's own code — the client still does the work, the wrapper
  lies about the arguments. Server-side validation is the only defense; WPE cannot touch a packet
  the client never sends (e.g. a server-calculated HP change).

### 1.2 In-process function hooking (MapleStory, AoS hacks)
- Nullz's MapleStory guide: find the Send function (`004A83AC` in old GMS), overwrite the first 5
  bytes with a `JMP` to your callback (after `VirtualProtect` to PAGE_EXECUTE_READWRITE), inspect
  the packet before it ships, then `jmp` back. Same for Recv.
- **Injecting custom packets**: locate the class instance pointer, call the game's *native* send
  function with your own packet buffer — the server sees a packet from the real client that the
  game UI never produced.
- **MaplePE**: DLL injection + `WriteProcessMemory`-style patching, packet list with byte editor,
  replay. Needs "bypass Security Client if it blocks WriteProcessMemory" (i.e. HackShield).
- **matvec21/Ace-of-Spades-Hack**: a DLL hack (dllmain.cpp + offsets.h + structures.h) — offsets
  found by reverse engineering the game binary. Classic structure: `offsets.h` hardcodes the
  addresses, thread.cpp runs the cheat loop.
- Defense shape: this is why "don't trust the client" is non-negotiable — memory patches cannot be
  stopped by a small studio, only *observed* (behavioral telemetry), and the damage they can do is
  bounded entirely by server validation.

### 1.3 MITM proxy (packet editor between client and server)
- Ragnarok proxy packet editor (2009, elitepvpers): the client connects to a local proxy instead of
  the server; the proxy forwards traffic but lets you script packet modification in VBscript.
  Works where WPE fails (protected clients) because nothing is injected into the game process.
- **Pwn Adventure 3** (see §4): LiveOverflow/Beaujeant build an async TCP proxy, parse packets,
  edit them, and inject arbitrary packets — teleporting, item generation, "packet spoof brute
  force".
- Defense shape: proxy lies about what the *client* sent; indistinguishable from a bot that just
  sends forged packets. Same defense: server validation.

### 1.4 Full protocol reimplementation (the nuclear option)
- **OpenKore** (Ragnarok): a complete open-source Perl bot that speaks the protocol itself — no
  game client at all. Server info extracted by sniffing login packets (2-byte size + opcode +
  data).
- **openspades / pyspades / BetterSpades** (Ace of Spades): full server+client reimplementation
  from the public protocol documentation. piqueserver.org/aosprotocol documents every 0.75 packet
  byte-for-byte (Position 13 B, World Update 1+24·players, Hit 3 B with the note *"The server
  should verify that this is possible to prevent abuse (such as hitting without shooting, facing
  the wrong way)"* — our exact NET-3 problem, in the wild, in 2012).
- **l2js-client** (Lineage 2): a JavaScript client — protocol overview docs describe the wire
  format publicly (2-byte little-endian size header, 1–3 opcode bytes, encrypted payload).
- Defense shape: if your protocol is documented/reversible, *anyone* can write a client. There is
  no transport defense; only server authority + secret session state (HMAC tickets) can stop a
  full-reimplementation bot — and even then only if the keys stay server-side.

### 1.5 Encryption/anti-cheat bypass (GameGuard, HackShield, SmartGuard)
- L2 SmartGuard ("protection S"): blocked LSP tools and export-table tampering; scene responded
  with black-box analysis (Habr article "We bypass the commercial protection using the black box
  method"): intercept `SendPacket`, find the network handler pointer at fixed offsets
  (`*(*(unh+0x48)+0x68)`), write per-server decryption DLLs.
- MapleStory HackShield: CRC checks on game memory → patch the CRC function or disable EHSvc.dll
  (gist: "how to disable hackshield from big-bang era maplestory"); MaplePE bypasses by running
  as admin or patching the security client.
- RYL: GameGuard bypass was standard practice (RESEARCH-002).
- **Key insight**: every anti-cheat was bypassed within its own lifetime. The only layer the
  research consistently calls unbypassable is **server-side behavioral analysis** (GAN-Aimbots
  paper; Anybrain; YAACS). For our lab: client-side AC is out of scope; server telemetry is the
  play.

---

## 2. ENet attack surface (from vendored lsalzman/enet source + CVE history)

Confirmed from `tools/reference/enet/` (git-ignored vendor copy):

| Surface | Where | Facts |
|---|---|---|
| **No encryption / no auth** | protocol docs | ENet "omits authentication, ... encryption" — all traffic plaintext, trivially sniffable, forgeable |
| **Peer exhaustion flood** | protocol.c:300-331 | CONNECT flood from one IP is only rejected once `duplicatePeers` (host.c:103) is set — **default is `ENET_PROTOCOL_MAXIMUM_PEER_ID` = 4095**, i.e. unlimited peers per IP unless you set it (Flax exposes `duplicatePeers=2` per RESEARCH-001) |
| **Peer cap** | host.c:34 | `peerCount > 4095` rejected at host-create; but a server with e.g. 16 slots accepts CONNECTs and only rejects when full — handshake CPU cost is the DoS surface |
| **Fragment reassembly** | peer.c:850-988 | `fragments` bitmap allocated per (fragmentCount) — validated against `ENET_PROTOCOL_MAXIMUM_FRAGMENT_COUNT` (protocol.c:578-581, 696-699), but fragmented packets advance `incomingReliableSequenceNumber` by `fragmentCount-1` (peer.c:826-828) — a resource-pressure angle |
| **Handshake MITM** | protocol.c:428, 979 | CONNECT/VERIFY carry only `connectID` (random) + outgoing peer IDs — no key exchange; an on-path attacker can hijack/impersonate (NAT rebinding style) |
| **Timeouts** | enet.h:224-226 | peer timeout limit 32 × min 5000 ms → max 30000 ms; slow-drip keep-alive abuse keeps dead peers alive |
| **Historical CVEs** | NVD | CVE-2006-1194 (signedness error in `enet_protocol_handle_incoming_commands`; remote DoS in Cube, Sauerbraten, Duke3D w32) and CVE-2006-1195 (`enet_protocol_handle_send_fragment` crash DoS) — ENet protocol layer *has* a remote-DoS history; fixed long ago, but the fuzzing of command parsing (our boofuzz plan) is exactly where they lived |
| **Bandwidth limits** | enet.h:363-394 | `enet_host_bandwidth_limit` exists and throttling is built in — but is opt-in per host; unchecked servers are fully exposed to flood |

### What this means for the Flax lab
1. Transport hardening is *mostly config*: `duplicatePeers=2`, `ConnectionsLimit`, bandwidth
   limits — no code needed (NET-1/NET-2 findings).
2. All security lives in the app layer: plaintext + no auth = packet forgery is trivial with our
   own `flax_enet.py`. That is the lab's premise and it is confirmed by the library's design.
3. DoS on the handshake (CONNECT flood at a small peer cap) is the easiest live attack — Portwarp
   tunnel exposes port 7777, attacker floods CONNECT with random connectIDs → server CPU + slot
   churn. Rate-limit handshake attempts per IP in the app layer.
4. Fragment-flood abuse is a second-order attack (advances reliable sequence numbers, forces
   reassembly state) — keep max fragment count sane at the app layer.

---

## 3. Case study: Ace of Spades — the ENet game that got fully broken

- AoS 0.75 uses ENet for everything; protocol documented publicly (piqueserver.org/aosprotocol,
  protocol075.html: ~40 packets, all byte-layouts, both directions, including disconnect-reason
  codes 1 banned / 2 IP limit / 3 wrong version / 4 server full / 10 kicked).
- Result: **three independent reimplementations** (pyspades server, openspades client, BetterSpades
  client) — full protocol-level bots/clients written from docs, zero reverse engineering needed.
- Doc itself carries the validation warnings: Hit packet = "server should verify that this is
  possible to prevent abuse"; Chat = "reasonable limits should be placed on length and frequency".
  Even a tiny indie game got these notes because it was rebuilt by the community.
- **Lesson for Flax**: our WIRE-FORMAT.md + flax_enet.lua dissector are already reproducing the
  piqueserver situation — good for us (attacker mindset), bad if published. Keep protocol docs
  private; treat "protocol known" as the baseline threat, not the worst case.

---

## 4. Case study: Pwn Adventure 3 — the canonical training blueprint (and our lab template)

Vector35's intentionally-vulnerable Unity MMO (Ghost in the Shellcode CTF 2015), now free:
`pwnadventure.com`. The documented attack methodology matches our lab exactly:

1. **Define targets** (network, saved data, game logic binary, rendering).
2. **RE the protocol**: identify IP/port, build use cases (don't move / jump / move / strafe /
   look), watch sizes/frequency/patterns, isolate variables, locate the variable. The location
   packet was solved by differential analysis: `- - X X X X Y Y Y Y Z Z Z Z P P YA YA R R U S`
   emerges from walking each axis in turn.
3. **Build a Wireshark Lua dissector** (they did exactly what our flax_enet.lua does — `Proto`
   + offset loop + opcode table, verified with `le_uint()` etc.).
4. **Build an async proxy** (Python, asyncore) to parse and edit traffic in flight; spawn location
   edits, item generation, teleportation, packet replay, spoof-brute-force.
5. **RE the binary / patch / hook** (Ghidra, x32dbg, CE).
6. CharonV's takeaway list: never trust the client; keep secrets server-side; patch management;
   detect deviation from normal behavior; set up a reporting system.

**Use it**: the first phases (1-4) are 1:1 our lab phases (we already have the dissector + raw
client + fake server; the missing piece is the *live* server to point the proxy at). The Pwn3
repo (github.com/beaujeant/PwnAdventure3: pwn3-gs.md protocol doc + pwn3-gs.lua dissector +
asyncproxy.py) is the reference implementation for our attack-run script.

---

## 5. The 2026 cheat taxonomy (Anybrain, gamesindustry.biz Mar 2026) — full list

The 7 pillars (with the detection signal for each):
1. **Pixel-based AI bots** — local ML reads pixels, auto-triggers input. Tell: inhumanly consistent
   reaction times in a narrow ms window across thousands of encounters. Exploits cloud-streamed
   games to run outside detection.
2. **Computer vision** — reads the screen as one image, no memory access. Tell: mismatch between
   input and UI state; smoothness of mouse path.
3. **DMA cards** — second PC reads game PC's memory via DMA. Invisible to software AC; only
   behavioral detection works.
4. **State manipulation** — speed hacks, lag switching; "regular teleportation or packet bursts
   that coincide exactly with engagement windows". Easy to spot, still common (this is our
   NET-3 class of attack).
5. **Overlays/ESP** — wallhacks; tell: gaze data tracking enemies through walls without firing.
6. **Automation/macros** — MMO farming; tell: frame-perfect combos for 3+ hours without error.
7. **Exploits** — unintended game logic (clip through map); tell: out-of-bounds triggers /
   impossible coordinates in the log. "Exploits tend to go viral — use your community as QA."

Plus: **CaaS** (Discord/TikTok distribution, near-zero skill), **private cheats** ($200+/mo,
auto-updating on every patch), and the emerging threat: **humanized AI models** — bots trained to
make mistakes (intentional jitter, lazy aiming, varied reaction times) on purpose.

Market data (PlaynixVPN roundup): ~14% cheater rate in *unprotected* FPS lobbies; Valorant <0.5%
(kernel AC + behavioral ML); Warzone 3-8%; Fortnite 5-10%; 4-6 hours to detect a new cheat
variant post-ban-wave. Vanguard numbers show the ceiling — and it still doesn't stop CV bots.

**Path forward (Anybrain)**: layered stack — bespoke AC or kernel AC → code obfuscation/packing →
file+memory tamper protection → behavioral profiling AI → MFA/account security. For a solo indie:
the layers we can actually run are server validation + telemetry + fast patch cadence + MFA.

---

## 6. Web-game hacking mechanics (for the future web build)

- **WebSocket interception is 5 lines of JS**: monkey-patch `WebSocket.prototype.send` and
  `addEventListener('message')` in a content script (MAIN world, document_start) — or use an
  off-the-shelf extension (WebSocket DevTools, 1.1k+ stars, MIT: background capture, message
  simulation, block/replay) or Burp Repeater frames.
- **CSWSH** (cross-site WebSocket hijacking): browser sends cookies with the WS handshake
  regardless of origin; if the server doesn't check `Origin`, any webpage can connect as the
  victim and exfiltrate.
- **The recurring pitfall**: "The auth decision happens once, at handshake time" — no per-message
  auth → token reuse/replay, and many servers "accept any auth message without validating the
  token". Also: token not invalidated on logout = persistence vector.
- Defense: per-message HMAC or short-lived tickets (already in our plan), Origin checks, auth
  before ANY data message, tokens bound to connection ID, server-side rate limits.
- ENet's own docs literally list the web analog: no lobby auth, no encryption — same posture.

---

## 7. Defense-prep spec for the Flax server (from all of the above)

### L1 — Transport (config, no code)
- `duplicatePeers = 2` (default is unlimited! confirmed in source), `ConnectionsLimit` sane
  (16-32), `enet_host_bandwidth_limit` set on host, peer timeouts left at defaults.
- Rate-limit handshake attempts per IP at the app layer (CONNECT flood = cheapest attack).

### L2 — Application (server authority; the only unbypassable layer)
- Server owns ALL state transitions: hits, damage, inventory, spawns, chat rate. Client sends
  *intent*, server validates (AoS doc's own "server should verify" note; Pwn3's "never trust the
  client").
- Movement: validate position deltas vs max speed per tick (NET-3), timestamp + monotonic
  counters per session to kill replay (Pwn3's packet replay / "ghosting" attack).
- Packet rate + size caps per session; connection-time counters (NET-1/NET-4).

### L3 — Session integrity (cheap, big payoff)
- At VERIFY, derive a per-session HMAC key from server secret + client connectID; HMAC critical
  packets. This alone kills WPE-style filters, proxy editors, and replay — until the binary is
  reversed, which for Flax (C#/managed + IL2CPP-ish pain) is expensive for a cheater.
- Keep the key server-side; never ship it in the client bundle for the web build (JS = always
  extractable — HMAC there is only anti-accident, not anti-cheat).

### L4 — Telemetry (the mini-Watchdog)
- Log per-session: packet rate, sizes, inter-arrival variance, movement deltas, hit accuracy,
  session uptime. Alert on anomalies (state manipulation pillar: "packet bursts that coincide
  with engagement windows"; automation pillar: frame-perfect repetition).
- Keep it cheap: counters + occasional full logs, JSON lines, rotated. No ML needed at our scale —
  thresholds catch the 7-pillar classics; human review catches the rest.

### L5 — Operations
- Patch cadence beats any ban wave: industry number is 4-6 h for a new variant to appear after a
  wave — for us, ship fixes in days, not months (Hypixel lesson: slow enforcement = cheaters
  normalize).
- Community report channel (Anybrain: exploits go viral — use players as QA).
- MFA/revocable tickets for any account system (both pillars list credential/AI-phishing).
- Never publish protocol docs (AoS lesson: documentation = bot clients).

### Lab mapping
- Research-001 NET-1..5 findings = L2/L3 items. Our tools (fuzz_enet.py, flax_enet.py,
  fake_flax_server.py) = the attacker the spec defends against. Attack-run.ps1 = the Pwn3 proxy
  pattern, applied live once the Portwarp tunnel is up.
- After the live server test, the follow-up is a DEFENSE checklist derived from this spec, wired
  as acceptance criteria for the NET-* fixes in the game repo.

---

## Sources (all fetched 2026-08-01)
- piqueserver.org/aosprotocol (+ protocol075.html) — AoS 0.75 protocol documentation
- github.com/yvt/openspades, github.com/piqueserver/piqueserver, xtreme8000/BetterSpades
- github.com/matvec21/Ace-of-Spades-Hack (dllmain/offsets structure)
- weekly-geekly.imtqy.com (Habr mirror) "bypass the commercial protection ... packet hack for lineage 2" (LSP → SendPacket → newxor.dll, SmartGuard)
- github.com/unc1e/Lineage-2-Intrelude-packet-hack-for-SmartGuard
- maxcheaters.com "L2 Packet Opcode Lists"; npetrovski.github.io/l2js-client protocol overview
- wiki.cheatengine.org Packet editing; forum.cheatengine.org WPE Pro tutorial (2007); itstillworks.com WPE Pro Ragnarok workflow; security.stackexchange.com "How to deal with WPE users"
- forums.openkore.com (server-info extraction via sniffing); github.com/hmrten/l2cap; github.com/maaaxim/bot
- excellzone.forumotion.net Nullz's MapleStory Packets guide (function hooks, packet injection, class instance)
- github.com/zhyonc/MaplePE; unknowncheats.me HackShield Bypass MapleStory; gist gogogosco (disable hackshield)
- elitepvpers.com Ragnarok Packet Editor (proxy-based, 2009)
- NVD: CVE-2006-1194, CVE-2006-1195 (ENet protocol.c remote DoS; Cube/Sauerbraten/Duke3D)
- github.com/beaujeant/PwnAdventure3 (pwn3-gs.md, pwn3-gs.lua, asyncproxy.py); jaiminton.com PA3 walkthrough (TCP proxy, replay, teleport, Ghidra); LiveOverflow PA3 series; charonv.net/pwn-adventure (mitigation list); slideshare "Reverse Engineering a (M)MORPG"
- gamesindustry.biz "A guide to identifying cheating in online video games in 2026" (Anybrain 7 pillars + path forward)
- playnixvpn.com "AI Anti-Cheat in 2026" (cheater-rate stats, $200/mo private cheats, 4-6h window)
- gist.github.com/Demaga WebSocket interception (Chrome/Firefox); github.com/law-chain-hot/websocket-devtools; bugbounty.info WebSocket Security (CSWSH, no per-message auth)
- steamcommunity.com Starbound server vulnerability disclosure (sector name validation → arbitrary file write)
- vendored source analysis: tools/reference/enet (host.c, protocol.c, peer.c, enet.h)
- arxiv.org 2501.10881 (secret-sharing packet-cheat protocols; timing/inconsistency/collusion taxonomy)
