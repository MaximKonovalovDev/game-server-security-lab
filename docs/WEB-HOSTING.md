# Web Multiplayer Game — Free Hosting Research (July 2026)

Deep-researched, verified current. Two architectures for a browser multiplayer
game, both achievable at **$0 with no credit card**:

- **A. Server-authoritative WebSocket backend** — players connect to a hosted
  server. Best for competitive/fair play (server validates everything).
- **B. P2P WebRTC (zero server)** — players connect browser-to-browser; you only
  need tiny free signaling + free STUN/TURN. Best for small co-op groups, 0ms
  latency potential, and literally zero hosting.

Your existing Flax game is ENet/UDP — browsers can't speak raw UDP (see "Flax web
export" at the bottom), so a web game means either a separate JS/TS game or Flax's
new experimental web build.

## Architecture A — free WebSocket hosts (verified 2026)

| Host | Free tier | Card? | WebSocket? | Sleep behavior | Verdict |
|---|---|---|---|---|---|
| **Cloudflare Workers + Durable Objects** | 100K requests/day, 10ms CPU/req, 128MB; DO on free plan (April 2025+); WebSocket Hibernation API (idle = not billed); KV 100K reads/1K writes/day; Queues now free (Feb 2026) | No | **Yes, native + hibernation** | None — stays awake | **#1 for web games** |
| **PartyKit** (open source, runs on Cloudflare) | Individual free: 10 live projects, global edge, storage cleared every 24h | No | Yes (room server model) | None | Fastest to build |
| **Render Free** | 750 h/mo, 512MB, 0.1 CPU, 100GB/mo bandwidth, 500 build min | No | Yes — **active WS messages count as traffic and prevent sleep** | Spins down after 15 min idle; 30-60s cold start | **#2 — keep-alive while playing; joins lag ~1 min after a gap** |
| **Deno Deploy Free** | 1M requests/mo, 100GB egress, 1GiB KV, 50ms CPU/req | No | Yes (raw WS + socket.io confirmed) | None | #3 (WS duration limits unverified — test) |
| Firebase **Spark** | Firestore 50K reads/20K writes/20K deletes per day, 1GiB; RTDB 1GB stored/10GB/mo; Functions 2M/mo; Hosting 10GB | No | RTDB = realtime sync (not raw WS) | None | Good for signaling/state, not a game tick loop |
| Vercel Hobby / Netlify Free | 100GB bandwidth | No | **No** long-lived WS on serverless | — | **Not for games** |
| Fly.io / Railway / Glitch | — | **Card required** / credit-only / **sunsetting** | — | — | Dead for you |

**Recommended stack A (all free, no card):**
1. Frontend: static HTML/JS/TS on **Cloudflare Pages** (unlimited sites, 500 builds/mo) or GitHub Pages.
2. Game server: **Workers + Durable Objects** with WebSocket Hibernation (one DO = one match room; idle rooms cost nothing; SQLite storage inside each DO since 2025). 100K req/day covers thousands of small matches.
   - Prefer plain code over a framework? Use **PartyKit** (`pk` CLI, `partykit dev` → `partykit deploy`) — same free Cloudflare foundation, less boilerplate.
3. Backup/fallback: **Render** Node app (`ws`/socket.io) — deploy from Git, no card, WebSockets keep it awake while anyone plays; accept the 30-60s cold start between sessions.
4. Optional persistence: Cloudflare D1 or KV (free tier) / Firebase Firestore (Spark, no card).

## Relay/pub-sub "WebSocket" services — lobby tier only (verified July 2026)

Pusher-style hosted WebSocket services (channels + presence + webhooks). They
look perfect for games — but free message quotas kill continuous simulation.
10 players at 30 Hz × 1 broadcast per tick = 300 msg/s:

| Service | Free tier (verified) | Card? | Message math | Verdict |
|---|---|---|---|---|
| **Apinator** (apinator.io) | 500 concurrent conns, **500K msgs/day**, 100 channels, 500 presence members/channel, 500 client events/s, **256 KB max msg**; Pusher-compatible protocol (drop-in), EU+US regions, webhooks, HMAC auth; community project — "no paid tier above it, no card" | No | 500K/day ≈ **5.8 msg/s sustained** → a 10-player 30 Hz sim exhausts the daily quota in **~28 min** | Lobby / presence / chat only |
| **Supabase Realtime** | 200 peak concurrent, **2M msgs/mo**, 256 KB broadcast payload, presence 20 msg/s, broadcast replay 72 h; broadcast latency <50 ms (server-mediated); **free projects pause after 7 days of inactivity** (policy tightened Feb 2026 — cron-ping workaround) | No | 2M/mo ≈ **0.77 msg/s sustained** | Signaling / matchmaking, not the tick loop |
| **Ably** | 6M msgs/mo, 200 concurrent, 200 channels, stable (long-running product) | No | 6M/mo ≈ **2.3 msg/s sustained** | Same verdict |

All three are fine as **lobby/matchmaking/presence** layers under a real game
server, or for low-rate turn-based games. Any continuous simulation needs the
dedicated hosts above (Cloudflare DO / Render / Deno) — those have no
per-message quotas.

## Long shots that nearly work — Tailscale Funnel & GitHub Codespaces (verified 2026)

- **Tailscale Funnel — ❌ for game WebSockets, ✅ for plain HTTP.** Free public
  HTTPS URLs to a service on your own machine (ports **443/8443/10000 only**,
  TLS-only, non-configurable bandwidth caps). Two verified blockers for games:
  1. **HTTP/2-only proxy without RFC 8441 (Extended CONNECT)** — browser
     WebSockets fail through it (open GitHub issue, Mar 2026; workaround = use
     Tailscale direct, not Funnel).
  2. HTTPS-oriented **idle reaper kills long-lived WebSocket upgrades** —
     reports of connections reset after ~9 s (issue, May 2026); plus community
     Funnel outage reports (r/Tailscale, 2026).
  → Fine for a lobby page/webhooks; do not build the game socket on it.
- **GitHub Codespaces — ✅ temporary public playtest server.** Free personal
  tier: **120 core-hours/mo = 60 h on a 2-core machine**, 15 GB storage
  (stopped codespaces still consume storage — delete unused). Forwarded ports
  can be set **Public**: anyone with the `https://<codespace>-<port>.app.github.dev`
  URL connects without auth. Caveats: codespace stops on idle (30-min default)
  → scheduled playtest sessions only, never always-on; org accounts get no free
  tier.

## Architecture B — P2P WebRTC, zero hosting (verified 2026)

No game server at all: browsers connect directly via WebRTC data channels.
Needed pieces — all free:

| Piece | Free option (verified) | Limits |
|---|---|---|
| Signaling | **PeerJS Cloud** (alive, 100% uptime status July 2026, no account, donate-funded) — or self-host PeerServer (any free host, incl. Render) — or **Firebase RTDB Spark** (no card) | PeerJS Cloud: shared IDs can collide; fine for small groups |
| STUN | Google (`stun.l.google.com:19302`) or Twilio — both free, no account | Unlimited binding requests |
| TURN (relay fallback) | **Cloudflare Calls TURN — 1,000 GB/month free**, then $0.05/GB; per-allocation caps ~50-100 Mbps (fine for games) | The best deal by ~10x |
| TURN alts | **ExpressTURN 100 GB/mo free** (TCP+UDP, ports 3478/80/443); Metered 0.5-50 GB/mo (varies by source — tiny); Turnix 10 GB/mo; Xirsys 0.5 GB/mo | Small but usable |
| NAT reality | Chrome UMA: **~75-80% connect with STUN-only**; 20-25% need TURN. US-only data: ~10% need relay (appear.in). IPv6 avoids NAT entirely | With Cloudflare TURN configured, effectively 100% connect |

**Why it's cheap:** only the 10-25% of players who can't hole-punch burn TURN
bandwidth. A 4-player 20-min match at ~100 KB/s/game ≈ ~1-3 GB relayed worst-case —
free Cloudflare TURN alone covers roughly 300-1000 matches/month.

**Recommended stack B:**
1. Game code: any WebRTC data-channel lib (PeerJS for easy signaling integration, or raw `RTCPeerConnection` for full control). See also Geckos.io (game-optimized WebRTC).
2. ICE config: Google STUN + Cloudflare TURN (credentials via their API) + Twilio STUN.
3. Matchmaking/lobby: PeerJS Cloud room IDs or a Firebase RTDB "lobby" doc.
4. Authoritative-cheat note: P2P = every client is host-capable → **cheating is harder to prevent** (a host player sees all state). For anti-cheat-sensitive games, prefer A.

## Flax web export — the honest picture (verified)

- **Flax 1.12 (May 2026) added experimental Web builds** via WebGPU (playable in
  browsers; official `FlaxWebRacing` sample open-sourced).
- **BUT: C# scripting is not yet implemented in web builds** ("such as C# support"
  — official release notes). Your game's networking is C# on ENet/UDP, so **the
  current Flax game cannot run in a browser yet**, and browsers can't do raw UDP
  anyway (would need a WebSocket/WebTransport bridge layer in-engine).
- Conclusion: build the web multiplayer game as a **separate JS/TS game** (reuse
  your packet design + wire-format docs — same schema, JSON/binary over WS), and
  revisit Flax web export when C# support lands.

## Security notes (web version)

- Same proxy rule as desktop: players behind Cloudflare edge or tunnels share
  edge IPs → rate-limit and ban by **player identity/token**, not IP.
- Cloudflare free tier includes WAF + DDoS protection for your Workers/Pages —
  free extra for a game with public lobbies.
- Free hosts enforce abuse terms: keep our lab attacks **local** (hard rule),
  never against Cloudflare/Render/Firebase.
- Auth: use a short signed token per match (cookie/localStorage) before accepting
  WS; validate every message server-side (same P0 list as SERVER-SECURITY.md).
- Browsers auto-terminate WS on tab close — handle reconnect + rejoin gracefully.

## Sources (verified July 2026)

- Cloudflare: Workers limits (docs, July 2026), DO free-tier changelog (2025-04-07),
  WebSocket Hibernation GA, Realtime TURN pricing (1,000 GB free, $0.05/GB, Apr 2026).
- PartyKit: partykit.io pricing (10 live projects free), acquisition post (2024).
- Render: render.com/docs/free (15-min spin-down; WS messages count as traffic),
  free tier guides (no card, 750h).
- Deno: deno.com/deploy/pricing (1M req/mo free); community WebSocket tests (2025).
- Firebase: pricing docs + Q1 2026 report (Storage removed from Spark Feb 2026).
- PeerJS: peerjs.com (cloud alive, status page 100%, July 2026).
- WebRTC: Chrome UMA (getstream.io), appear.in ~20% global / ~10% US TURN rates
  (Philipp Hancke, SO).
- Flax: flaxengine.com blog 1.12 release (Web support experimental, no C#), docs
  platforms page.
- TURN free tiers: Cloudflare Realtime docs, expressturn.com, metered.ca,
  itch.io community roundup (Mar 2026).
- Apinator: apinator.io (free-tier table: 500 conns / 500K msgs/day / 256 KB /
  100 channels / 500 events/s), sysdesai.com build writeup (Redis pub/sub
  fan-out, Apr 2026).
- Supabase: docs/guides/realtime/limits (presence 20 msg/s, 256 KB broadcast,
  replay 72 h), pricing (200 peak conns / 2M msgs; 7-day pause change 2026-02).
- Tailscale Funnel: docs (ports 443/8443/10000, TLS-only, bandwidth caps); GitHub
  issues — WS reset ~9 s idle reaper (May 2026), missing RFC 8441 Extended
  CONNECT (Mar 2026).
- Codespaces: docs.github.com forwarding-ports (public visibility,
  app.github.dev URLs), features page (120 core-h / 15 GB free personal tier).
