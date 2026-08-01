# Game Server Attack Lab — Toolchain

Curated from `trimstray/the-book-of-secret-knowledge` + GitHub research (2026).
Everything is filtered for one target: **a Flax Engine (C#) multiplayer game,
custom packet protocol over Flax's built-in network layer, port 7777, Windows.**

Legend: `[book]` = from the-book-of-secret-knowledge · `[git]` = GitHub research · `[build]` = we build it ourselves

---

## Layer 1 — WATCH (capture & analysis)

What the server actually sends/receives. Required before any attack makes sense.

| Tool | Source | Why it matters here |
|---|---|---|
| **Wireshark** + **tshark** | [book] | Capture loopback UDP on 7777, watch your handshake/transform packets on the wire. tshark = scriptable version for the orchestrator. |
| **Termshark** | [book] | TUI for tshark — quick captures without the GUI. |
| **Npcap** (Wireshark driver) | [book] | Loopback capture on Windows requires Npcap with loopback support enabled. |
| **Zeek / netsniff-ng** | [book] | Later: long-running traffic logging on a dedicated test host. Optional. |
| **wireshark-enet-dissector** (cgutman) | [git] | Pre-existing ENet dissector — diff against our `flax_enet.lua` and absorb its ENet-core command coverage (verified Aug 2026). |
| Game log + MCP bridge health | your repo | Your server already has the FlaxMcp HTTP bridge + log files — the orchestrator uses these to detect crashes (simpler than Wireshark for "is it alive"). |

## Layer 2 — ATTACK (crafting & injection)

The realistic hacker = modified client, not raw sockets. Order matters:

| Tool | Source | Why it matters here |
|---|---|---|
| **Rogue client** (custom) | [build] | THE main weapon. A Flax project that connects like a real client and sends forged packets through your own codec: fake transforms (teleport/speed-hack sim), spoofed SenderID, oversized list counts, floods, fuzz. This is what real cheaters build. |
| **Packet Sender** | [book] | Quick manual UDP/TCP send-receive against 7777 to sanity-check a theory without writing code. |
| **netcat (ncat) / socat** | [book] | Raw UDP one-liners: `echo garbage \| ncat -u 127.0.0.1 7777`. Tests how the server handles non-protocol bytes. |
| **Scapy** | [book] | Python packet crafting — useful for L3/L4-level tests (UDP floods, fragmentation, source-spoofing on LAN). Flax's app-layer framing is engine-internal, so Scapy stays at transport level. |
| **boofuzz** | [git] | Network protocol fuzzing framework (successor of Sulley). Define your packet structures (packet ID + fields) once, and it systematically mutates every field, including length fields — exactly what finds your unbounded-count bugs. |
| **ENet-CSharp** (nxrighthere) | [git] | C# ENet binding (MIT) — reference codec for the rogue client, same language as the game (verified Aug 2026). |
| **mpgameserver** (nsetzer) | [git] | Python UDP game server, security-focused (LGPL-2.1) — rate-limit/validation patterns for the fake-server + NET-3 flood shapes (verified Aug 2026). |
| **radamsa** | [git] | Mutation fuzzer: take a captured real packet (PCAP from Layer 1) and generate thousands of mutated variants. |
| **hping3** | [book] | Custom-crafted TCP/UDP packets and floods at IP level. |
| **nmap / masscan** | [book] | Verify the server's exposed surface: which ports answer, what else is listening on the test machine. |
| **Ostinato** | [book] | High-volume traffic generation when you want to stress the network path itself. |

## Layer 3 — KNOW THE ENEMY (reverse engineering & memory) — Phase 2, VM ONLY

**Critical insight for your game: your game logic is C#.** Anyone with dnSpy
can read your networking code like a book. Test as they would.

| Tool | Source | Why it matters here |
|---|---|---|
| **dnSpy** | [git] | .NET decompiler + debugger + assembly editor. Will decompile `Game.CSharp.dll` in seconds — your packet handlers, auth logic, everything. #1 tool an attacker uses on a Flax game. |
| **ILSpy** | [git] | Alternative .NET decompiler (good CLI, better for automation). |
| **Cheat Engine** | [book]+[git] | Memory scanner: speed hacks, health/ammo edits, float scanning. Supports Mono/.NET dissection. The classic. |
| **Squalr** | [git] | Cheat Engine alternative written in C#. |
| **ReClass.NET** | [git] | Reconstruct data structures in the native engine memory (player objects, etc.). |
| **Process Hacker** | [git] | Inspect the running game: modules, handles, threads, memory. What a cheat dev opens first. |
| **Frida** | [git] | Dynamic instrumentation — hook .NET/native functions at runtime without a debugger. |
| **Ghidra / Cutter** | [book] | Reverse engineering the *native* Flax engine internals if you ever go deeper (transport framing lives in native code). |
| **HxD** | [git] | Hex editor for poking at save files / config / local state — data lying attacks. |

## Layer 4 — DEFEND (what to read & borrow from)

| Resource | Source | Why it matters here |
|---|---|---|
| **OWASP Game Security Framework (OGSF)** | [git] | The game-security playbook (threat models, requirements). Public review draft is out — read the multiplayer trust / abuse chapters. |
| **The-X.ploit.-Files** (AlSch092) | [git] | 15 years of REAL online-game exploits, mostly outbound packet crafting/manipulation, with root causes + remediations. Gold for someone new to this. |
| **UltimateAntiCheat** (AlSch092) | [git] | Open-source usermode anti-cheat (memory-edit detection, injection detection, integrity checks). AGPL — study the *concepts*, don't copy into a closed game. |
| **gamehacking-cheatsheet** | [git] | Attack-side cheat sheet: tells you what attackers will try so you can defend it. |
| **hacking-online-games** (dsasmblr) | [git] | Tutorial repo specifically about hacking ONLINE games — the exact threat. |
| **Pwn Adventure 3** | [git] | A free MMOFPS designed to BE hacked. Practice your skills in a legit playground before touching your own game. |
| **Valve/EAC/BattlEye GDC talks** | [git] | Mindset: server authority, trust boundaries, why client anti-cheat is an arms race. |
| **Steamworks anti-cheat docs** | [git] | If you ever ship on Steam — VAC integration, secure networking expectations. |
| **Flax Networking docs** | [git] | Know exactly what the engine guarantees (reliability, ordering) vs what you must validate yourself. |
| **cheatsheetseries.owasp.org** | [book] | General web/API hardening for any backend services. |

## Layer 5 — SANDBOX (where the attacks run)

| Tool | Source | Why it matters here |
|---|---|---|
| **VirtualBox** | research | **Your machine is Windows 10 Home → no Hyper-V, no Windows Sandbox.** VirtualBox (free) is the VM layer for Phase 2: cheat tools + a copy of your client run inside the VM, isolated from your dev machine. |
| **Windows Defender + Controlled Folder Access** | research | Keep Cheat Engine etc. inside the VM only; never on your host. |
| **Isolated LAN / host-only network** | research | VM on host-only network; server on host. Nothing touches the internet during tests. |
| **Your repo's sidecar/port tooling** | your repo | `scripts/_lib/Clear-Port.ps1`, health checks etc. — reuse for lab orchestration. |

---

## Minimum viable kit (start here, in order)

1. **tshark/Wireshark** — see the protocol on the wire (Layer 1)
2. **Rogue client [build]** — forged transforms, spoofed sender, floods (Layer 2)
3. **boofuzz + radamsa** — automated malformed-packet attacks (Layer 2)
4. **dnSpy** — see your own game the way an attacker does (Layer 3)
5. **OWASP GSF + The-X.ploit.-Files** — 2 evenings of reading = more defense than 6 months of trial-and-error (Layer 4)

## Hard rules

- Every attack runs against a **throwaway server process** on `127.0.0.1:7777` or a VM host-only network. Never against a live/player server.
- Cheat tools (Cheat Engine, dnSpy-on-binary, etc.) live in the **VM only**.
- A scenario is only "fixed" when it survives the same test twice after the code change.

---

## 2026 tooling status (verified July 2026 — versions move fast, re-check before installing)

| Tool | Latest verified | Status | Our lab use |
|---|---|---|---|
| Wireshark / tshark | 4.6.7 (Jul 2026) | active | capture + Lua dissector (`tools/dissector/flax_enet.lua`) — API unchanged in 4.6 |
| Npcap | 1.88 (May 2026) | active | bundled with Wireshark installer |
| Scapy | 2.7.0 (Dec 2025) | very active | raw UDP crafting/replay glue |
| Bit-Twist | 4.7 (Nov 2024) | active | native-Windows pcap replay at line rate (tcpreplay is Cygwin-only) |
| boofuzz | 0.4.2 (Oct 2023, last release) | semi — pin Python 3.8–3.11 | our harness is built on it |
| radamsa | 0.7 | active | mutation engine (WSL2/Cygwin) |
| WinAFL | master (Mar 2025) | semi (author → Jackalope) | Windows coverage fuzzing of native ENet parse (TinyInst mode) |
| dnSpy | 6.1.8 (2020) | **dead, archived** | use **dnSpyEx v6.6.0** (Jun 2026, .NET 10) instead — VM only |
| ILSpy | 10.1.1 (Jul 2026) | very active | fast decompile fallback |
| Cheat Engine | 7.7 (May 2026) | active | memory-cheat simulation — VM only |
| System Informer | 3.2.25011 (May 2025) | active | handle/module/.NET forensics (VM) |
| OWASP GSF | public review draft | stable target Q4 2026 | framework checklist to adopt |
| UltimateAntiCheat / Korvayne | current | indie-budget open source | optional client-side AC layer (later phase) |

Skip: tcpreplay (Cygwin-only), honggfuzz (no Windows), original dnSpy (dead), ReClass.NET (dormant since 2019).

Winget: `WiresharkFoundation.Wireshark` (verify ID at install time). Phase-2 tools (dnSpyEx, CE, System Informer) install inside the VM, not the host.
