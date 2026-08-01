# Hosting Strategy — Free Options for Your Server (July 2026)

Research date: July 2026 (official docs + forums + Reddit/HN verified). Your server:
C#/.NET 8, Flax 1.12, ENet, **UDP 7777 inbound**, server-authoritative, < 64 players.

## Your constraint: always free + no credit card (verified July 2026)

**The short answer:** no major cloud gives you a permanent free VPS without a card
(Oracle/GCP/AWS all demand one). But 2026 brought two *new* free tunnel services
that support **custom UDP** — the exact thing your ENet game needs. playit.gg, the
old champion, restricted custom UDP/TCP to Premium in early 2026 (details below).

| Option | Always free? | No card? | UDP 7777? | 24/7? | Verdict |
|---|---|---|---|---|---|
| **Portwarp Free** | ✅ $0/forever | ✅ ("no credit card required") | ✅ 3 tunnels, TCP+UDP, unlimited bandwidth | ⚠️ your PC must run | **#1 — new winner** |
| **TunnelThat Free** | ✅ 1 tunnel free forever | ✅ | ✅ TCP+UDP, London edge | ⚠️ your PC must run | #2 — EU-optimized backup |
| **Azure for Students** (only if student) | ✅ renews yearly while enrolled | ✅ | ✅ any port (B1s VM, Windows or Linux, 750 h/mo) | ✅ | N/A for you (not a student) |
| Direct home hosting (port-forward/IPv6) | ✅ | ✅ | ✅ | ⚠️ PC must run | #4 — no middleman |
| RackNerd & budget VPSes (PayPal/crypto) | ❌ but ~$1/mo ($11/yr) | ✅ PayPal/crypto | ✅ | ✅ | the "$1/mo escape hatch" |
| playit.gg | ❌ **custom UDP/TCP now Premium-only** (2026 change) | ✅ free signup | ❌ free plan | ⚠️ | dead for custom games on free |
| hax.co.id / woiden.id free VPS | ✅ (renew ≥3 days before expiry via panel; Telegram signup) | ✅ | ⚠️ NAT VPS = shared IPv4 + per-user ports (some plans IPv6-only), tiny resources, UDP unverified | ~ | sketchy "shitty" tier, not for production |
| Oracle / GCP / AWS free tiers | ✅ | ❌ **card required** | ✅ | ✅ | blocked for you |

### What happened to playit.gg (the previous #1) — 2026 change, verified

Three independent confirmations:
1. playit's own pricing page now lists **UDP** under "Requires Playit Premium"
   (alongside SSH/HTTPS); free tier = pre-defined game tunnels only (Minecraft,
   Terraria, ... — no custom game support).
2. Official GitHub issue `playit-cloud/playit-agent#127` (Jan 2026, closed):
   manual TCP/TCP+UDP tunnel creation on free → "Premium is required".
3. Community post (Jan 2026): "Playit.GG has disabled UDP ports for free accounts";
   Premium is $3/mo (or $30/yr).

For a **custom** game on a custom UDP port, playit free no longer works. Their free
tier only auto-creates tunnels for their supported game list. Keep playit Premium
($3/mo) in mind only as a paid fallback.

### The new winners, verified (their sites, July 2026)

**Portwarp** (`portwarp.com`): free plan = **3 active tunnels, TCP and UDP,
unlimited bandwidth, end-to-end encryption, no credit card**. Clients: Windows
(Microsoft Store), Linux (Snap), CLI (`curl -fsSL https://portwarp.com/install`).
PRO $2.99/mo adds firewall rules, GeoIP blocking, analytics, custom domains
(PayPal accepted). Claims anycast edge routing for low ping. ⚠️ Young service
(2026-era) — homepage edge counter shows 0, reliability unproven vs playit's 1M
users. Keep a second tunnel as backup.

**TunnelThat** (`tunnelthat.xyz`): free = **1 tunnel, TCP & UDP, "free forever, no
card, no trial countdown"**. London Docklands (Telehouse) edge, DDoS-filtered
(Corero), <1 ms overhead claimed. CLI: `tunnelthat connect localhost:7777` → public
`play.tunnelthat.xyz:port`. ⚠️ Single London location (best for EU players), very
young service. Fine as the backup tunnel.

**Both are proxy models like playit:** agent on your PC dials out; players connect
to their public `IP:port`. No port forwarding, home IP stays hidden, DDoS hits
their edge not your router.

## Full sweep results (July 2026) — who's alive, who's dead

Deep-researched every "free tunnel/VPS" candidate, including the sketchy ones:

| Service | Free tier, verified | UDP? | Verdict for a game server |
|---|---|---|---|
| **Portwarp** | 3 tunnels, TCP+UDP, unlimited BW, no card | ✅ | #1 (primary tunnel) |
| **TunnelThat** | 1 tunnel, TCP+UDP, no card, London edge | ✅ | #2 (backup tunnel) |
| **Localtonet** | 1 TCP/UDP tunnel, **1 GB/mo** | ✅ | tiny cap — test-play only |
| **fxTunnel** | HTTP+TCP free, **UDP paid** (their own pricing page contradicts their blog) | ❌ free | dead for us on free |
| **Serveo** | 3 SSH tunnels, TCP, no account, no card | ❌ | WebSocket testing only; Nov 2025 4-day outage |
| **localhost.run** | SSH tunnel, no account | ❌ | WebSocket testing only |
| **ngrok** | 1 GB/mo, 20K req/mo; **TCP requires card verification**; **no UDP on any tier** (Feb 2026 tightening) | ❌ | dead for games |
| **LocalXpose** | free = 2 HTTP tunnels; TCP/UDP = Pro $8/mo | ❌ free | dead for us on free |
| **Cloudflare Tunnel** | free HTTP; TCP/UDP = Spectrum (paid); clients must install cloudflared | ❌ | dead for public players |
| **bore.pub** | free, open source | ❌ TCP only | WebSocket testing only |
| **woiden.id / hax.co.id** | NAT VPS: shared IPv4 + per-user ports, Telegram signup, renew ≥3 days before expiry; some plans IPv6-only; UDP through their NAT unverified | ❓ | sketchy; not for production |
| **Trials** (Kamatera 30d, VPSServer 30d, $100 credit plans) | real VPS, real IPv4 | ✅ | **temporary** — vanish after 30 days, then require card |
| **Firebase Spark / Render / Cloudflare Workers** | see `WEB-HOSTING.md` — web multiplayer hosts, no card | — | web game backends |

**Bottom line for the desktop ENet game:** the free, no-card, *permanent*, custom-UDP
set is exactly two: **Portwarp (primary) + TunnelThat (backup)**. Everything else is
trial-based, TCP-only, or dead. "Even shitty ones" exists (Localtonet 1GB, woiden
NAT VPS) but isn't worth running a server on — keep them as test toys only.

**PC-free bottom line:** permanent free *custom-game* hosting without your PC
still doesn't exist — panels (fps.ms/Gaming4Free/EnderBit/Minehut) host
pre-defined games only, and the no-card free-VPS claims (VPSWala ARM64, Oracle)
are unverified, ARM-only, or disputed. Your PC running Portwarp remains the only
real free path; everything else is playtest-grade (Codespaces public ports,
Render, panels).

## PC-free options: free game-server panels (pre-defined games only, verified 2026)

These host game servers in their datacenters — **no PC of yours required**. But
they only serve *their* game list (Minecraft, Terraria, ...), **no custom
game/EXE upload** — your Flax game can't go here yet (except by voting, see
Gaming4Free):

| Panel | Free tier (verified) | Catch | Custom game? |
|---|---|---|---|
| **fps.ms** | Minecraft/Terraria/Discord & Telegram bots, no card, smart hibernation (sleeps when empty, wakes on play), US+EU | pre-defined list | ❌ |
| **Gaming4Free** (G4F.GG) | 9 games (MC, Unturned, FiveM, Terraria, Factorio, Rust, ARK, Valheim), EU/US/Asia, DDoS-protected, file manager/SFTP, auto-backups; **server runs 24 h then needs 1-click renewal — world kept 7 days**; $2.50/mo Premium removes the nag | renewal nag + ads; since 2024 | ❌ (new games via Discord vote — the only theoretical path) |
| **EnderBit** | MC, CS2, Rust, ARK, Garry's Mod, Discord bots, TeamSpeak/Mumble, MariaDB/MongoDB, no card | pre-defined list | ❌ |
| **Minehut** | Minecraft only: 10 slots, 1 GB RAM, no playtime limits, sleeps empty & wakes on join | MC-only; 24/7 online = paid | ❌ |

## Free VPS without a card — the 2026 sweep (verified)

| Service | Claimed free tier | Card? | Reality check |
|---|---|---|---|
| **VPSWala** (vpswala.org) | Starter: 1 vCPU **ARM64**, 2 GB RAM, **500 MB NVMe**, **10 GB/mo bandwidth**, Linux only, SSH root — "free forever, no expiry, no card"; verify with .edu/GitHub/company email, 60-s deploy | ✅ claimed | ⚠️ obscure 2026-era site (SEO-heavy), no backups; tiny disk/bandwidth; **ARM64 cannot run your Flax x64 Linux build** — usable only for a Node/WS web game. Signup-verify before trusting |
| **Oracle Cloud Always Free** | up to 4 ARM OCPU / 24 GB, 200 GB disk, 10 TB egress | ❓ **disputed** — 1vps.com (Feb 2026) calls it "the only truly free no-card VPS"; long-standing community reports say card/verification at signup | treat as card-required until proven otherwise |
| **woiden.id / hax.co.id** | NAT VPS, Telegram signup, per-user ports, renew ≥3 days before expiry | ✅ | sketchy tier (sweep table above) |
| Trials (Kamatera 30d, VPSServer 30d, Tencent Lighthouse 3-mo, Legion 48-h) | real VPS | varies | **temporary** — expires, then card |

**Red-flag rule (techbloat, Apr 2026):** avoid any "free VPS" that asks for a
deposit, crypto payment, Telegram-only registration (→ woiden/hax warning), or
ID documents. Legit no-card options are few, and they say so in plain text.

## The three hard truths

1. **Permanent free hosting means Linux.** There is no permanent free *Windows* VM in
   2026. Azure B1s (Windows) is free for 12 months only. Oracle/GCP free tiers are
   Linux-only. → **Plan the Linux headless build now.** Flax supports it: cook a
   standalone Linux build, run with `-headless -mute -null -std` (no GPU needed).
   ⚠️ Flax Linux builds are **x64** — treat Oracle's ARM Ampere shape as experimental
   (only the AMD E2.1.Micro x64 free shape is a sure fit).
2. **Almost every free PaaS is useless for games:** Render/Railway/Koyeb/Northflank/
   HuggingFace have **no inbound UDP** and/or spin down after 15 min idle. Cloudflare
   Tunnel (free) and Tailscale Funnel are TCP-only. Skip them all for the socket
   (fine for a lobby/matchmaking HTTPS endpoint later).
3. **AWS free tier is dead for new accounts** (July 2025 change: $200 credits, 6 months,
   then account closes). Fly.io's free tier is gone (~$4–5/mo now).
4. **The 2026 IPv4 tax (verified on GCP pricing pages, 2026-07):** Google now bills
   external IPv4s — static AND ephemeral — at $0.005/h (~**$3.65/mo**), free tier
   covers only 1 hour/month. Oracle does not charge for IPv4. Factor ~$3.65/mo into
   any GCP plan. (Same story on most clouds in 2026; IPv6 is free but player
   coverage still isn't universal.)

## Candidate table (verified)

| Provider | Free specs | UDP 7777? | 24/7? | Verdict |
|---|---|---|---|---|
| **Oracle Cloud Always Free** | 2× AMD E2.1.Micro (x64, 1 GB) + Ampere A1 ARM (2 OCPU/12 GB per docs; 3rd-party says 4/24); 200 GB disk; **10 TB/mo egress**; no expiry; no IPv4 charge | ✅ any port | ✅ no sleep (but idle-reclamation risk) | **#1 money pick** — $0 forever, only real free 24/7 UDP host |
| **GCP e2-micro** | 1 vCPU/1 GB, 30 GB disk, no expiry; **egress: 1 GiB/mo always-free, 200 GiB/mo free on Standard Tier**, then $0.085/GiB; **external IPv4 ~$3.65/mo** (2025+ IPv4 tax) | ✅ | ✅ truly always-on, no reclamation | **chosen plan** — safe/no-drama, costs ~$4/mo + egress when live |
| Azure B1s | 1 vCPU/1 GB, **Windows included**, 12 months | ✅ | ❌ expires, then ~$15/mo | Windows staging only |
| AWS EC2 | dead for new accounts | — | — | skip |
| Fly.io | free tier gone | ✅ (paid) | ❌ | skip (would be best if paid) |
| Render / Railway / Koyeb / Northflank / HF Spaces | free tiers exist | ❌ no UDP | mostly sleep | skip |
| Home PC + WireGuard relay | your hardware | ✅ via relay | ⚠️ your PC must run | #2 strategy (below) |
| Player-hosted (listen server) | $0 forever | ✅ (their network) | ❌ dies with host | #3 strategy (below) |

## Real cost check: GCP e2-micro when your game goes live (2026 pricing, verified)

| Scenario | Egress/mo | Egress cost | IPv4 | Total |
|---|---|---|---|---|
| Tiny/co-op (≤8 players, throttled) | ≤ 50 GiB | $0 | $3.65 | **~$4/mo** |
| 16 players, relevance culling (realistic) | ~200–250 GiB | $0–4 | $3.65 | **~$4–8/mo** |
| 64 players, full broadcast (worst case) | ~970 GiB | ~$65 | $3.65 | **~$70/mo** |

Numbers: Standard Tier egress free to 200 GiB then $0.085/GiB; Premium Tier free to
1 GiB then $0.12/GiB. Always use Standard Tier. Oracle's 10 TB free egress never
charges this — Oracle stays $0 no matter the traffic. GCP is the *safe* choice, not
the *cheapest* choice; the difference only shows at scale or with a big playerbase.

## Bandwidth reality check

Full-broadcast math: 64 players × 30 Hz × 200 B ≈ 1.35 GB/h — but that's worst case.
With relevance culling, a realistic 16-player server burns **~0.15–0.35 GB/h** →
**10–30 GB/month** for a small game (fits GCP's 200 GiB Standard-Tier free egress
with huge headroom). Bandwidth is not the constraint — *uptime policy and UDP* are.

## Recommended strategy (phased, $0 → ~$4/mo)

### Phase 0 — now: lab + friends on your network
Keep attacking/testing locally (lab hard rules unchanged). For playing with a few
friends, a player-hosted listen server or LAN works; no hosting cost, no exposure.

### Phase 1 — first public server: home PC + Portwarp Free (no-card plan, chosen)
1. Create a Portwarp account (`portwarp.com` — **no credit card**) and install the
   client (Windows app, Linux snap, or CLI).
2. Add a **UDP tunnel** pointing at `127.0.0.1:7777` (free plan: 3 tunnels).
3. Portwarp gives you a public address — give players that (Flax/ENet connects
   directly; no port forwarding, no home-IP exposure).
4. **Add a backup tunnel on TunnelThat** (`tunnelthat connect localhost:7777`) —
   both are young 2026 services, so a second free tunnel means if one dies, you
   re-share the other address. Also keep direct port-forwarding (if your ISP
   allows) as a third fallback.
5. Harden per `SERVER-SECURITY.md` — **with the proxy twist: all players share the
   tunnel edge IP, so swap per-IP rate limits for per-player-identity limits**.
6. Exact steps: `DEPLOY-TUNNEL.md`. Cost: **$0.00**. Caveat: your PC must stay on.

### Phase 1b — Azure for Students: NOT applicable (you're not a student)
Skipped — Azure for Students requires an enrolled-student school email. For a real
always-on VPS later, jump to Phase 2 ($1/mo PayPal VPS).

### Phase 2 — the $1/mo escape hatch: PayPal budget VPS
No card, ~$11/yr (RackNerd-style yearly deals, PayPal/crypto), real datacenter IP,
10+ TB bandwidth. This is what "no card but willing to pay $1/mo" gets you. Same
Linux headless deploy as `DEPLOY-GCP.md`.

### Phase 3 — card-optional upgrades (only if you ever get a card)
GCP e2-micro (~$4/mo all-in, safe/no-drama — full runbook `DEPLOY-GCP.md`),
Oracle Always Free ($0 forever, 10 TB egress, termination risk), or playit Premium
($3/mo, established network, regional tunnels). The build and hardening are
identical — only the console changes.

## Alternatives worth knowing (free, but different tradeoffs)

- **Home PC + WireGuard relay on a $1–2 VPS**: your hardware does the compute, the
  VPS relays UDP — works under CGNAT, hides your home IP. playit.gg does this for
  $0 with no VPS at all — only pick WireGuard if you want the tunnel to be
  fully self-controlled.
- **Player-hosted server binaries** (Valheim/Palworld model): ship a free server
  binary, players host. $0 forever, scales with players — but: host-machine trust
  issues, no always-online world, and "who hosts tonight" friction. Great for
  co-op games, wrong fit for competitive/ranked.
- **EOS (Epic Online Services) free P2P + relays**: free NAT traversal without any
  server — but P2P changes your whole architecture (and your security model).
  Revisit only if you ever want to drop the central server.

## Security notes specific to hosting (from research)

- Free-tier cloud IPs are **scanner magnets** (Oracle/AWS ranges are constantly
  port-scanned): UFW allow UDP 7777 only, disable password SSH, fail2ban, never
  expose the server on a Windows box without the P0 hardening.
- If you home-host: never expose the home IP directly — always through the
  Portwarp/TunnelThat/playit relay or a WireGuard tunnel. Real anecdotes of
  ~1 Gbps attacks on home IPs exist. The free tunnel proxies give you this hiding
  for $0.
- **Proxy tunnel twist (Portwarp/TunnelThat/playit alike):** every player's packets
  come from the tunnel edge IP → per-IP rate limits and duplicate-peer detection
  must key on per-player identity instead (session token/guid), not the socket
  address.
- Backups: server binary + config live in your private GitHub repo → instant redeploy.
- Keep lab attacks local (hard rule) — don't attack through tunnel proxies, your
  home net, or any free VPS.

## Decisions (status 2026-07)

1. **No-card hosting plan: home PC + Portwarp Free (UDP tunnel) — locked in.**
   $0.00, no card, 3 free UDP/TCP tunnels, unlimited bandwidth. Backup tunnel on
   TunnelThat (1 free UDP tunnel). Runbook: `DEPLOY-TUNNEL.md`.
2. **playit.gg demoted** — custom UDP/TCP now Premium-only (2026 change, verified
   via their pricing page, GitHub issue #127, and community reports). $3/mo fallback
   only.
3. **Azure for Students: dropped** — you're not a student (asked 2026-07). The
   always-on no-card upgrade path is now: TunnelThat backup tunnel + direct
   port-forwarding → PayPal $1/mo VPS.
4. **Card-optional fallbacks** (GCP/Oracle) documented in `DEPLOY-GCP.md` +
   HOSTING.md if you ever have a card; PayPal VPS (~$1/mo) if you have PayPal.
5. **Linux build steps — written** in `DEPLOY-GCP.md` (Flax CLI cook command,
   `-headless -mute -null -std` run, systemd, Ubuntu deps). Note: tunnel hosting
   on your Windows PC needs **no Linux build at all** — just run the cooked
   Windows build.
6. **Player-hosted model** — still open; depends on whether your game is co-op
   (works great) or competitive/ranked (needs the central server).
7. **Web multiplayer game (separate project):** free no-card stack researched —
   Cloudflare Workers + Durable Objects (or PartyKit) as primary WebSocket host,
   Render as fallback, or fully P2P WebRTC with free Cloudflare TURN (1 TB/mo) +
   PeerJS signaling at $0. Flax web export exists but has no C# yet — see
   `WEB-HOSTING.md`.
8. **Reddit round 2 (July 2026) verified:** Apinator (500K msgs/day) & Supabase
   Realtime (2M msgs/mo) are lobby/presence-only for games — quota math kills
   continuous sim (WEB-HOSTING.md). Tailscale Funnel = HTTP-only for games (no
   WS: HTTP/2 without RFC 8441 + ~9 s idle reaper). Codespaces free = temporary
   public playtest (public ports, 60 h/mo, dies on idle). PC-free panels
   (fps.ms/Gaming4Free/EnderBit/Minehut) = pre-defined games only, no custom
   game. VPSWala = free-forever ARM64 VPS claim (no card) — unverified, ARM-only,
   tiny (500 MB / 10 GB), fine only for a Node web game. Oracle no-card status:
   disputed.
