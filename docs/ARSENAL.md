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

## Immediate next actions (in order)
1. `[use]` Wire the server + fix NET-1/NET-2/NET-4 (game code).
2. `[use]` Write the Wireshark Lua dissector for PacketIds 1-8 + combat 200 (keeps in `tools/`).
3. `[use]` Build rogue client (separate Flax project in this folder).
4. `[study]` Read oomph's movement checks → design your NET-3 validation rules.
5. `[use]` boofuzz + radamsa harnesses against the running server.
6. `[use]` OWASP GSF + awesome-game-security as the ongoing reference index.
