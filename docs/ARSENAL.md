# Game Server Security Arsenal — Frameworks, Workflows & Skills

Research compiled 2026-07-31 for: Flax Engine (C#) multiplayer game, custom
packet protocol, UDP, Windows host. Sources: GitHub research + curated lists
(awesome-game-security, OWASP GSF, security-hardening lists).

Legend: `[use]` = adopt directly · `[study]` = read for concepts/patterns · `[tbd]` = later phase

---

## PART A — FRAMEWORKS & MASTER WORKFLOW (the "how")

### A1. The master workflow (anti-cheat by architecture)
The one workflow that prevents 80% of game cheating — *server-authoritative design*:

```
client input → server VALIDATES → server simulates → server broadcasts truth
```

Validation checklist that must exist for EVERY client->server message:
- movement speed limits (max units/sec × dt)          → kills speed hacks
- teleport/position delta plausibility                 → kills teleports
- action cooldowns + resource costs                    → kills spam/dupe
- physics/geometry boundaries                           → kills wall-clipping
- line-of-sight checks (hitscan)                        → kills wall-hacks-as-aim
- actor ownership: only the owner may move their pawn   → kills hijacking
- packet rate budget per connection                     → kills flood DoS
- every length/count on the wire capped BEFORE allocation → kills memory DoS

**Your status:** NET-1..NET-5 in `reports/FINDINGS-001-initial-audit.md` are
exactly the failures of this checklist. Movement validation (NET-3) must exist
BEFORE transforms ship.

### A2. Reference frameworks (read the code, steal the patterns)
| Repo | What it is | Use |
|---|---|---|
| **OWASP Game Security Framework (OGSF)** | The game-security playbook: threat models, multiplayer trust, abuse scenarios, virtual economy risks | [use] checklist source |
| **gmh5225/awesome-game-security** | THE curated hub: offensive + defensive game security, wiki/AGENTS.md, skills (anti-cheat-systems, windows-kernel-security, reverse-engineering-tools) | [use] index + learning path |
| **violetweather/Certael** | Server-authoritative anti-cheat framework w/ Godot/Unity/Unreal adapters — read how it structures validators | [study] validator architecture |
| **vul-os/magnetite** | Rust game platform: deterministic replay verification + composable cheat validators | [study] deterministic replay detection concept |
| **oomph-ac/oomph** | Minecraft Bedrock MiTM anti-cheat proxy — movement validation, combat checks (real-world speed/teleport rules) | [study] movement-check math |
| **AlSch092/UltimateAntiCheat** | Usermode AC: memory-edit detection, injection detection, integrity checks (AGPL — concepts only) | [study] client-side layer (Phase 3) |
| **niemand-sec/AntiCheat-Testing-Framework** | Stress-test your anti-cheat itself | [use] Phase 3 |
| **Unity Netcode security guide (dr-codes article)** | Engine-agnostic server-authority patterns + validation checklist | [use] checklist cross-reference |

### A3. The testing workflow (what we run in this lab)
```
1. WIRE   — start server (lab scene/dedicated), confirm 7777 listening
2. BASELINE — capture real traffic (Wireshark/tshark loopback), save PCAPs
3. DISSECT — write a Wireshark Lua dissector for YOUR packet format (1 hour, forever useful)
4. ATTACK  — rogue client scenarios (forged transforms, spoofed sender, big counts, floods)
5. FUZZ    — boofuzz field-level + radamsa mutation on captured PCAPs
6. REPLAY  — wireplay / custom replay of recorded sessions
7. LOAD    — connection flood, packet flood, churn (hping3/PowerShell/Ostinato)
8. OBSERVE — server alive? log markers? memory/CPU? report PASS/FAIL
9. FIX + RETEST — same test twice after code change
```

---

## PART B — TOOL LAYERS (the arsenal)

### B1. Capture & analysis [Phase 1]
| Tool | Role | Skill needed |
|---|---|---|
| Wireshark + tshark | packet capture, filter `udp.port == 7777` | BPF filters, follow stream |
| **Wireshark Lua dissector** | parse YOUR protocol into named fields | Lua basics + your wire format |
| Termshark | TUI for tshark in the orchestrator | — |
| Npcap | loopback capture on Windows (enable loopback) | admin install |
| **clumsy** | network condition simulator (latency/loss/dupe via WinDivert) | test bad networks too |
| tc netem (Linux only) | same on Linux | — |

### B2. Crafting & injection [Phase 1]
| Tool | Role | Skill needed |
|---|---|---|
| **Rogue client [build]** | modified-client attack simulation using your own codec | C#, Flax networking |
| netcat (ncat) / socat | raw UDP garbage: `echo x \| ncat -u 127.0.0.1 7777` | one-liners |
| Packet Sender | quick GUI/CLI UDP-TCP send | — |
| Scapy | L3/L4 crafting (floods, fragmentation, spoofing) | Python + layers |
| boofuzz | field-level protocol fuzzing (length bombs etc.) | protocol definition |
| radamsa | mutate captured PCAP payloads | — |
| wireplay | replay TCP/UDP sessions from PCAPs | — |
| hping3 | custom packets + floods | TCP/IP headers |
| nmap/masscan | surface scan of test host | — |
| Ostinato / iperf3 | high-volume traffic, bandwidth | — |

### B3. Reverse engineering / memory [Phase 2 — VM ONLY]
| Tool | Role | Skill needed |
|---|---|---|
| dnSpy / ILSpy | decompile Game.CSharp.dll — see your netcode as an attacker | .NET IL reading |
| Cheat Engine | memory scanning, speed hacks, .NET/Mono dissection | memory model |
| Squalr | CE alternative (C#) | — |
| ReClass.NET | reconstruct native data structures | C++ memory layout |
| Process Hacker | modules/handles/threads inspection | Windows internals |
| Frida | runtime hooking/instrumentation | scripting |
| Ghidra / Cutter | native engine reversing (transport framing lives in native) | assembly basics |

### B4. Hosting-side hardening [Phase 3 — before going live]
| Resource | Role |
|---|---|
| dedicatedgameservers.net 2026 hardening checklist | RCON on 0.0.0.0, SSH, firewall, updates — the classic launch mistakes |
| decalage2/awesome-security-hardening | curated hardening hub (CIS, Docker bench, Lynis, fail2ban...) |
| Lynis | server audit scan |
| Windows firewall / VPS provider firewall | only expose 7777/UDP (+ 7778 TCP if needed) |
| Fail2ban (Linux VPS) | brute-force blocking |

---

## PART C — SKILL ROADMAP (what each phase teaches)

| Skill | Phase | Where learned |
|---|---|---|
| Read netcode like an attacker (ingress paths, alloc-before-validate) | 1 | audit practice (already done in FINDINGS-001) |
| Wireshark dissection + Lua | 1 | write dissector for your protocol |
| Protocol fuzzing methodology | 1 | boofuzz/radamsa on your packets |
| Server-authoritative validation math | 1 | oomph + Unity guide + your NET-3 |
| C# reverse engineering | 2 | dnSpy on your own build |
| Memory hacking basics | 2 | Cheat Engine in VM |
| Windows internals (process/module/handle) | 2 | Process Hacker + awesome-game-security wiki |
| Host hardening | 3 | checklist + Lynis on VPS |

---

## PART D — GITHUB "STEAL OR MOVE TO" SWEEP (verified 2026-08-01)

Round 3 of research: stop reinventing wheels — find existing repos to steal
patterns from or move to. 6 web searches + 4 GitHub API queries
(`q=enet`, `flax+engine+networking`, `game+anti+cheat+testing`, `memory+hacking+python`)
+ curated review. Top-of-list data: stars/forks/license/activity at search time.

### D1. ENet wire-format ground truth & reference clients
| Repo | What it is | Verdict |
|---|---|---|
| **lsalzman/enet** | Canonical ENet C library (3,245★, MIT, active Jun 2026) | [use] wire-format ground truth — re-verify WIRE-FORMAT.md + boofuzz defs against its source |
| **zpl-c/enet** | Maintained C fork (1,071★, MIT, Jun 2026) | [use] same; modern API |
| **nxrighthere/ENet-CSharp** | C# ENet binding (906★, MIT, Jul 2025) | [use] rogue-client codec reference — same language as the game |
| **zpl-c/librg** | World-sync library on ENet (1,485★, BSD-3, Jan 2026) | [study] how they chunk/organize packets over ENet |
| **xtreme8000/BetterSpades** | Ace of Spades client on ENet (281★, GPL-3.0) | [study] real-world ENet client: handshake, channel use, reliability |
| **kbirk/enet-example** | Minimal C++ ENet client+server pair (44 commits) | [study] smallest working send/receive pair |
| **nsetzer/mpgameserver** | Python UDP game server, security-focused (61★, LGPL-2.1) | [study] rate-limit/validation patterns for the fake-server work |

### D2. Flax & game frameworks
| Repo | What it is | Verdict |
|---|---|---|
| **FlaxEngine/NetworkSample** | Official sample: players lobby + chat on Flax networking (25★, MIT, Jul 2021) | [use] vanilla-Flax baseline — design NET-3 validators to fit official patterns |
| **NazaraEngine** | C++ game framework w/ networking (837★, MIT, Jul 2026) | [study] transport design |
| **Tornamic/CoopAndreas** | GTA:SA co-op mod on ENet (565★, GPL-3.0, active Jul 2026) | [study] mature ENet usage in a real game |

### D3. Wireshark dissector
| Repo | What it is | Verdict |
|---|---|---|
| **cgutman/wireshark-enet-dissector** | Pre-existing ENet Wireshark dissector | ✅ **absorbed 2026-08-01** — ENet-core coverage merged into `flax_enet.lua`: CONNECT/VERIFY full layout (bandwidth + throttle fields, connect data), DISCONNECT data, BANDWIDTH_LIMIT, THROTTLE_CONFIGURE, FRAGMENT start seq; fixed pre-existing bug (CONNECT connectID read at +40 = `data` field; now +36 per lsalzman/enet protocol.h, bodies 44B/40B). Game-message dissection + flags + expert info stay ours. |

### D4. Reversing & attack-side knowledge (Phase 2 VM)
| Repo | What it is | Verdict |
|---|---|---|
| **dnSpyEx/dnSpy** | Maintained revival of dnSpy (10,712★, GPL-3.0) | [use] already selected — TOOLCHAIN status table, VM only |
| **ridpath/gamehacking-cheatsheet** | Memory analysis, AC evasion, engine reversing (79★, MIT, Jan 2026) | [use] already in TOOLCHAIN Layer 4 — expand from it |
| **ethanedits/Apex-Legends-SDK** | Apex cheat SDK (156★, NO LICENSE, 2022) | skip — no license, EAC-specific, unrelated engine |
| **cybryk/kernelmodeinjector** | Kernel-mode DLL injector (47★, NO LICENSE) | skip — out of scope, no license |

### D5. Gaps confirmed — still our original work
- **No ENet-specific protocol fuzzers / packet-crafting libraries exist** → `fuzz_enet.py` + `flax_enet.py` stay ours.
- No Flax-specific security research repos at all.

### Recommended adoptions (proposed, confirm before vendoring)
1. ✅ `[use]` ENet-CSharp as rogue-client codec reference (C#, matches game) — **cloned 2026-08-01** to `tools/reference/ENet-CSharp` (git-ignored).
2. ✅ `[use]` lsalzman/enet source → re-verify WIRE-FORMAT.md + fuzz defs — **cloned 2026-08-01** to `tools/reference/enet` (git-ignored); CONNECT/VERIFY body sizes **corrected 52B/48B → 44B/40B** (connectID @36) in WIRE-FORMAT.md + dissector per protocol.h.
3. `[use]` cgutman dissector → diff vs `flax_enet.lua`, absorb ENet-core coverage.
4. `[study]` BetterSpades + mpgameserver for new attack scenarios (NET-3 flood shapes).
5. `[study]` NetworkSample for NET-3 server-authoritative patterns.

---

## PART E — CASE STUDIES: GAMES KILLED BY CHEATING + AI-ERA THREAT MODEL (verified 2026-08-01)

Full write-up + sources: `reports/RESEARCH-002-killed-by-cheaters-ai-threats.md`.

### E1. The pattern behind every death (APB, H1Z1, The Cycle: Frontier, RYL, SWG, Krunker...)
```
client trusted + weak/no anti-cheat + no server validation
  → legit players leave → revenue dies → shutdown
```
The Cycle: Frontier is the cleanest modern case — Yager officially cited "irreparable damage" from cheaters. RYL (Risk Your Life, ryl.com.my, Youxiland Malaysia, 2005) died the classic way: multihit, dupes, damage edits, WPE Pro packet editing, GameGuard bypass → PvP unplayable + economy flooded → subs quit → shutdown; leaked server files then fed a private-server explosion. r/MMORPG adds nuance: RYL2's subscription swap sealed it (hacking was the enabler).

### E2. Web-game reality (your future web build)
Browser games are 100% exposed — devtools reads your JS/protocol instantly; hacks are Tampermonkey scripts or console pastes (Krunker.io, .io genre) or Lua executors (Roblox: JJSploit 69M+ downloads, 2016 data breach, "datamodel vulns crash game servers" per Roblox's own HackerOne scope). **Server-side validation is everything for web games.**

### E3. AI-era threat model — what changed (2026)
- **Cheat production cost → ~zero** (LLMs write memory hacks/packet tools/injects in minutes).
- **CV aimbots on second PC/capture card** (YOLO on the screen, hardware input emulation) — invisible to client anti-cheat (Vanguard/EAC).
- **"Humanized" cheats** — trained hesitation/missed shots; GAN-Aimbots evaded automatic + human detection.
- **AI everywhere else:** recon, fuzzing, credential stuffing, economy botting, phishing.

### E4. What AI did NOT change (the defense)
- **Every cheat still sends packets through your protocol** — server-side validation cannot be bypassed by AI (GAN-Aimbots paper: behavioral server analysis "cannot be bypassed").
- 2026 defense trend: **server-side AI anomaly detection** — YAACS (arXiv Jul 2026: 88.6% acc / 0.97% FPR), FairFight/VACNet-style telemetry.
- **Defense map:** NET-3 movement validation, NET-1/2 caps, NET-4 rate limits (AI protocol exploits) · packet-timing telemetry (AI bots) · never trust the client (memory hacks) · HMAC ticket auth (web JS exposure) · duplicatePeers=2 + ConnectionsLimit + handshake limits (AI floods) · 2FA + revocable tickets (credentials).

### E5. Reddit firsthand round (2026-08-01) — the 4 lessons
1. **Dupe/exploit death has a rollback window** — New World whack-a-mole + trading shutdowns; WoW ban waves + server rollback; generic AAA dupe: "spread like wildfire, economy wrecked... missed their rollback window." Detect fast server-side or you can never roll back.
2. **Cheaters normalize cheating** — Hypixel Aug 2025: "Everyone is cheating, so I have to cheat"; players stop reporting when nothing happens; Hypixel FAQ admits: "cheater-free is impossible." Behavioral AC (Watchdog) + constant updates is attrition, not victory.
3. **Server validation can't stop CV/humanized bots** — behavior telemetry + server authority is the only unbypassable layer.
4. **Hackers sabotage servers themselves** — Battlefield V "cheaters draining servers"; GTA V teleport/crash; Red Dead Online: modders cited as why Rockstar abandoned updates.

## PART F — HOW PACKET GAMES ARE ACTUALLY BROKEN: THE 5 TECHNIQUES + ENet SURFACE + DEFENSE SPEC (verified 2026-08-01)

Full write-up + sources: `reports/RESEARCH-003-protocol-hacking-mechanics.md`.

### F1. The 5 attack techniques (in order of tool sophistication)
1. **Winsock/LSP interception** — WPE Pro: attach process → sniff send/sendto → filter rewrites/replays. Killed by in-process protections; server validation is the only defense.
2. **In-process hooking** — MapleStory: 5-byte JMP on the Send function (`VirtualProtect` RWX), or call the game's native send with forged packets (MaplePE DLL injection); AoS DLL hacks (offsets.h + dllmain). Undetectable by the server; damage bounded by server validation only.
3. **MITM proxy** — client → local proxy → server; edit/forge/inject (RO packet editor 2009, Pwn Adventure 3 TCP proxy). Same as a bot from the server's view.
4. **Full protocol reimplementation** — OpenKore (RO bot in Perl), openspades/pyspades/BetterSpades (AoS rebuilt from public docs), l2js-client. No client at all → only server authority + secret session state can stop it.
5. **Anti-cheat bypass** — L2 SmartGuard black-boxed via `SendPacket` offsets + per-server decryption DLLs (newxor.dll); MapleStory HackShield CRC patched / EHSvc killed; RYL GameGuard bypass. **Every AC gets bypassed in its lifetime — server-side behavioral analysis is the only layer research calls unbypassable.**

### F2. ENet attack surface (verified against vendored lsalzman/enet source)
- **No encryption, no auth, by design** — plaintext, forgeable, MITM-able handshake (connectID only).
- **`duplicatePeers` defaults to 4095 (= unlimited)** — CONNECT floods from one IP are NOT rejected unless you set it (host.c:103; Flax exposes `duplicatePeers=2`).
- Fragment reassembly state per peer (bitmap + reliable-seq advance by fragmentCount-1) — second-order DoS; bounds enforced in protocol.c.
- Peer timeouts: limit 32, min 5 s, max 30 s (slow-drip keeps dead peers alive).
- **Historical protocol.c remote-DoS CVEs**: CVE-2006-1194 (signedness in `enet_protocol_handle_incoming_commands`, Cube/Sauerbraten/Duke3D), CVE-2006-1195 (send-fragment crash). Exactly the code we fuzz with boofuzz.
- All transport hardening = config: duplicatePeers, ConnectionsLimit, `enet_host_bandwidth_limit`.

### F3. The two canonical case studies
- **Ace of Spades**: public byte-level protocol docs (piqueserver.org) → 3 reimplementations; the docs literally warn "server should verify hits to prevent abuse" + "reasonable limits on chat length and frequency" — our NET-3/NET-4 findings, confirmed in the wild on an ENet game.
- **Pwn Adventure 3** (free, intentionally vulnerable MMO): the canonical training blueprint = differential packet analysis → Wireshark Lua dissector → async proxy → replay/teleport/inject → binary RE. 1:1 matches our lab phases; beaujeant/PwnAdventure3 repo has protocol doc + dissector + proxy as reference implementations.

### F4. 2026 seven-pillar cheat taxonomy (Anybrain) + the tell for each
Pixel AI bots (ms-window consistency) · CV aimbots (input/UI mismatch) · DMA cards (behavioral only) · **state manipulation** (packet bursts at engagement windows — our NET-3 class) · ESP (gaze through walls) · macros (frame-perfect 3h+) · exploits (impossible coords in log). Plus CaaS (Discord/TikTok), private cheats ($200+/mo, auto-update), **humanized AI bots trained to make mistakes**. Market: ~14% cheater rate unprotected FPS lobbies vs Valorant <0.5% (kernel + behavioral ML); new variants appear 4-6 h after a ban wave → **patch cadence beats ban waves**.

### F5. Web-game mechanics (future web build)
WS interception = 5-line `WebSocket.prototype.send` monkey-patch or WebSocket DevTools ext (1.1k★, message simulation); **CSWSH** (cookies sent with handshake regardless of origin — check Origin!); "auth happens once at handshake" pitfall → per-message HMAC/tickets, auth before ANY data, token invalidation on logout.

### F6. Defense-prep spec for the Flax server (L1-L5)
- **L1 transport (config):** `duplicatePeers=2`, ConnectionsLimit 16-32, `enet_host_bandwidth_limit`, per-IP handshake rate limit (CONNECT flood = cheapest attack).
- **L2 application:** server owns ALL state; clients send intent only; movement delta validation per tick; per-session monotonic counters + timestamps kill replay.
- **L3 session integrity:** per-session HMAC key = server secret + client connectID, HMAC critical packets. Kills WPE filters/proxies/replay until binary is reversed (Flax = expensive). Web build: HMAC is anti-accident only (JS extractable).
- **L4 telemetry (mini-Watchdog):** per-session packet rate/size/inter-arrival variance/movement deltas/hit accuracy; alert on anomalies; thresholds + human review (no ML needed at our scale).
- **L5 ops:** fast patch cadence; community report channel; MFA/revocable tickets; never publish protocol docs (AoS lesson).

### F7. Lab mapping
Our fuzz_enet.py/flax_enet.py/fake-server = the attacker F1-F5 describes; NET-1..5 findings = L2/L3; attack-run.ps1 = Pwn3 proxy pattern once Portwarp tunnel is live. Defense acceptance criteria for the NET-* fixes come from this spec.

---

## Immediate next actions (in order)
1. `[use]` Wire the server + fix NET-1/NET-2/NET-4 (game code).
2. `[use]` Write the Wireshark Lua dissector for PacketIds 1-8 + combat 200 (keeps in `tools/`).
3. `[use]` Build rogue client (separate Flax project in this folder).
4. `[study]` Read oomph's movement checks → design your NET-3 validation rules.
5. `[use]` boofuzz + radamsa harnesses against the running server.
6. `[use]` OWASP GSF + awesome-game-security as the ongoing reference index.
7. `[use]` Diff cgutman/wireshark-enet-dissector vs `flax_enet.lua` — absorb ENet-core command coverage.
8. `[use]` Cross-check WIRE-FORMAT.md + boofuzz defs against lsalzman/enet source.
9. `[use]` Build rogue-client codec on ENet-CSharp patterns.
