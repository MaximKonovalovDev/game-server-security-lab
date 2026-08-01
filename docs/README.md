# Game Server Attack Lab — Docs Index

Everything lives in this folder (`C:\Users\me\Desktop\antivirus`). The game
project is never modified — it is only launched and attacked.

## Index

| Doc | What it is |
|---|---|
| **[docs/ARSENAL.md](ARSENAL.md)** | Frameworks & master workflow (server-authoritative), reference repos (OWASP GSF, Certael, oomph, UltimateAntiCheat...), full tool layers, skill roadmap, GitHub sweep PART D (steal-or-move-to: ENet-CSharp, zpl-c/enet, BetterSpades, cgutman dissector...), immediate next actions. GitHub research 2026. |
| **[docs/TOOLCHAIN.md](TOOLCHAIN.md)** | Layer-by-layer tool selection (watch / attack / know-the-enemy / defend / sandbox) with minimum viable kit + hard rules. Curated from the book + GitHub. Sweep additions: cgutman dissector (L1), ENet-CSharp + mpgameserver (L2). || **[docs/BOOK-EXTRACT.md](BOOK-EXTRACT.md)** | Curated picks from `trimstray/the-book-of-secret-knowledge`, organized by phase: capture/craft, pentest arsenal, hardening, daily news, shell one-liners. |
| **[docs/WIRE-FORMAT.md](WIRE-FORMAT.md)** | Reverse-engineered wire format: ENet framing (header/commands/seq rules), Flax NetworkMessage encoding, packet schemas 1-8 + 200, attack notes. |
| **[docs/SERVER-SECURITY.md](SERVER-SECURITY.md)** | Day-one hardening plan (July 2026 research): P0/P1/P2 checklist, ENet tunables, auth design, encryption guidance, server-side cheat detection, rate limits, monitoring, lab test matrix. |
| **[docs/HOSTING.md](HOSTING.md)** | Free hosting strategy (July 2026 research): **no-card plan = home PC + Portwarp Free UDP tunnel** (backup: TunnelThat free), playit.gg demoted to paid fallback (custom UDP now Premium-only), Azure for Students (no card, if student), PayPal $1/mo VPS fallback, card-optional GCP/Oracle, PC-free panels (fps.ms/Gaming4Free/EnderBit/Minehut — pre-defined games only), free-VPS no-card sweep (VPSWala ARM64, Oracle disputed), 2026 IPv4 tax, egress math, hosting-specific security. |
| **[docs/DEPLOY-TUNNEL.md](DEPLOY-TUNNEL.md)** | No-card runbook: Portwarp free (3 TCP+UDP tunnels, no card, unlimited bandwidth) + TunnelThat free (1 UDP tunnel, London edge) → 127.0.0.1:7777, free-tier limits, the tunnel edge-IP security twist, young-service backup plan. |
| **[docs/DEPLOY-GCP.md](DEPLOY-GCP.md)** | Card-optional runbook: GCP signup/upgrade-before-day-90, e2-micro + Standard Tier + static IP, Flax Linux headless cook command, `-headless -mute -null -std` run, systemd service, hardening, cost guardrails. |
| **[docs/WEB-HOSTING.md](WEB-HOSTING.md)** | Web multiplayer game hosting (July 2026 research): free no-card WebSocket hosts (Cloudflare Workers+DO/PartyKit, Render, Deno Deploy, Firebase Spark), pub/sub relays (Apinator/Supabase Realtime/Ably — lobby-tier, message-quota math), Tailscale Funnel verdict (HTTP-only, no WS) & Codespaces public playtest, zero-cost P2P WebRTC (PeerJS + Cloudflare TURN 1TB free), Flax web-export reality (experimental, no C# yet), web security notes. |
| **[reports/FINDINGS-001-initial-audit.md](../reports/FINDINGS-001-initial-audit.md)** | First real security audit of the game's network code: NET-0 (no runnable server), NET-1/2 HIGH (unbounded allocs), NET-3/4/5 MED (validation/rate/range gaps). |

## Map to phases

```
Phase 1 (now, on host):   wire server -> fix NET-1/2/4 -> rogue client
                          -> Wireshark Lua dissector -> boofuzz/radamsa -> floods
                          (docs: ARSENAL.md A3 workflow, TOOLCHAIN.md L1-L2)

Phase 2 (VM):             VirtualBox Windows VM -> dnSpy/Cheat Engine/ReClass
                          -> memory cheat testing (docs: TOOLCHAIN.md L3)

Phase 3 (live prep):      transform validation (NET-3), host hardening,
                          optional client anti-cheat (docs: ARSENAL.md B4, A2)
```

## Lab layout

```
antivirus/
├── docs/            ARSENAL, TOOLCHAIN, BOOK-EXTRACT, WIRE-FORMAT, (this index)
├── reports/         findings & test reports (FINDINGS-001...)
├── tools/
│   ├── raw-client/  flax_enet.py - pure-Python ENet client (handshake,
│   │                crafted payloads, floods, fuzz modes)
│   ├── dissector/   flax_enet.lua - Wireshark dissector for udp.port 7777
│   ├── boofuzz/     fuzz_enet.py + .venv - mutation fuzzer over ENet framing
│   └── wire-probe/  .NET reflection probe (ground-truth extraction)
├── scripts/         attack-run.ps1: spawn server -> attack -> report
└── (future)         pcaps/, results/, vm-images/
```
