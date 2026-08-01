# Deploy Runbook — No-Card UDP Tunnels: Portwarp + TunnelThat (July 2026)

Locked-in no-card plan. Research summary: playit.gg (the old champion) restricted
custom UDP/TCP tunnels to Premium in early 2026; two newer services now fill the
gap for free. Verified from their own sites + docs, July 2026.

- **Portwarp** (`portwarp.com`) — Free: **3 tunnels, TCP+UDP, unlimited bandwidth,
  end-to-end encryption, no credit card**. Clients: Windows (Microsoft Store),
  Linux (Snap), CLI. PRO $2.99/mo (PayPal via Stripe) adds firewall rules, GeoIP,
  analytics, custom domains.
- **TunnelThat** (`tunnelthat.xyz`) — Free: **1 tunnel, TCP+UDP, "free forever, no
  card, no trial countdown"**. London (Telehouse) edge, DDoS-filtered (Corero),
  <1 ms claimed overhead. CLI only: `tunnelthat connect localhost:7777`.

Both are young 2026 services — that's the tradeoff for $0. **Run both** (one
primary, one backup) plus direct port-forwarding if your ISP allows it.

## What you get

A public `IP:port` (or hostname) players connect to. Your Flax/ENet server listens
on `127.0.0.1:7777`; the agent dials out to their edge and proxies players back.
No router changes, no CGNAT problems, no home-IP exposure. Works with the
**Windows cooked build** — no Linux cook needed.

## 1. Portwarp (primary)

1. Sign up at `portwarp.com` — username/email, **no card** ("Free to use · No
   credit card required").
2. Install — pick one:
   - **Windows (GUI):** Microsoft Store (`9P70NMQ39SBK`) or direct installer
     `https://get.microsoft.com/installer/download/9P70NMQ39SBK`.
   - **Windows (CLI, verified 2026-07):** the `curl | bash` installer is
     Linux/macOS-only — use the manual zip instead:
     ```
     Invoke-WebRequest https://portwarp.com/download/pwrp-0.3.2-windows-amd64.zip -OutFile pwrp.zip
     (Get-FileHash pwrp.zip).Hash  # compare vs https://portwarp.com/download/checksums.txt
     Expand-Archive pwrp.zip -DestinationPath tools\portwarp\bin
     .\tools\portwarp\bin\pwrp.exe login        # device-flow: opens browser, no password stored
     ```
   - **Linux:** `snap install portwarp` (GUI) or `curl -fsSL https://portwarp.com/install | bash` (CLI).
3. **Create the tunnel in the web dashboard** (the CLI has no create command —
   `connect` only starts existing tunnels): local address `127.0.0.1`, local
   port `7777`, protocol **UDP**.
4. Back in the CLI, start it as a persistent background daemon:
   ```
   .\tools\portwarp\bin\pwrp.exe connect <tunnel-id> -d -s   # -d detach, -s auto-reconnect on boot
   .\tools\portwarp\bin\pwrp.exe status                       # shows your public address
   ```
   The daemon keeps the tunnel alive after the terminal closes; `service` makes
   it start on login.
5. Portwarp gives you a public address (e.g. `play.mc.pwrp.cc:port` or an IP:port).
   Players use that. Share the IP:port form for Flax/ENet (no DNS needed).

## 2. TunnelThat (backup)

1. Sign up at `tunnelthat.xyz` (no card, no trial timer).
2. Install the CLI, then:
   ```
   tunnelthat connect localhost:7777
   ```
   It prints your public address (`play.tunnelthat.xyz:PORT` and an IP:port).
3. Keep this tunnel as the backup address; if Portwarp has an outage, share this
   one instead. (London-only edge — best latency for EU players.)

## 3. Test it

- Local test first: `tools\raw-client\flax_enet.py 127.0.0.1 7777` — handshake +
  a few messages against the local server.
- Then through the tunnel: same tool against the Portwarp address.
- Then a real friend join. Watch the server log: all players will appear to come
  from the tunnel edge IP — expected, see security note below.

## 4. Free-tier limits (verified)

| | Portwarp Free | TunnelThat Free |
|---|---|---|
| Tunnels | 3 | 1 |
| Protocols | TCP + UDP | TCP + UDP |
| Bandwidth | unlimited | not stated (fair use; DDoS-filtered) |
| Card | none | none |
| Region | anycast edges (claimed; verify ping) | London only |
| Automation/API | docs + CLI | API requires paid plan |

You need 1 tunnel; the extras are free insurance.

## 5. Security: the proxy twist + young-service risks

- **All players appear to come from the tunnel edge IP.** Per-IP rate limiting and
  duplicate-peer checks from `SERVER-SECURITY.md` must become **per-player-identity**
  limits (auth token/guid, per-session message rates).
- **Home IP stays hidden** — DDoS hits their edge, not your router.
- **ToS:** hosting your own game server is the intended use on all three services;
  they all ban C2/RAT/scanning traffic — our lab attacks stay local (hard rule),
  never through the tunnels.
- **Backup plan:** young services can vanish or change terms (playit did in 2026!).
  Tunnel config is trivial — keep the server binary + config in the private GitHub
  repo, and keep the second tunnel address ready.

## 6. When the playerbase grows

- Upgrade path: Portwarp PRO ($2.99/mo, PayPal) → Azure for Students (if student)
  → PayPal $1/mo VPS → GCP/Oracle (if you ever have a card). All in `HOSTING.md`.

## Verified sources

- portwarp.com + /pricing (2026-07): free plan $0/forever, 3 tunnels, TCP+UDP,
  unlimited bandwidth, no credit card; PRO $2.99/mo; PayPal accepted.
- tunnelthat.xyz + /docs (2026-07): one tunnel free forever, TCP+UDP, no card;
  API above Free only.
- playit.gg pricing + support docs: UDP badge under "Requires Playit Premium";
  GitHub issue playit-cloud/playit-agent#127 (Jan 2026): manual TCP/TCP+UDP on
  free → Premium required; community post (Jan 2026): UDP disabled for free.
