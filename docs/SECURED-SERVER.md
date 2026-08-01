# SECURED-SERVER — Building the Top-Secured Hosted Server (integration blueprint)

**Purpose:** the build plan that fuses every doc in this lab into ONE
hosted deployment. If you read one doc to build the server, read this; the
rest are the component specs.

```
internet
   │  UDP 7777 (game only)
   ▼
Portwarp edge (free tier) ──NAT──► home PC  (tunnel edge-IP twist:
                                    everyone looks like the edge IP → identity
        FLAX SERVER PROCESS        must come from fingerprints + auth envelope)
   ┌──────────────────────────────────────────────┐
   │ ENet host (duplicatePeers=2, ConnectionsLimit│
   │ 16-32, handshake budget, timeouts)           │
   │   ├─ strict parse  NET-1/2/5 (bounded allocs,│
   │   │   enum/string/range checks)              │
   │   ├─ server authority NET-3 (movement:       │
   │   │   ownership, speed clamp, no-clip)       │
   │   ├─ HMAC envelope id=250 (Rule 2: session   │
   │   │   key, seq, 4-byte MAC; versioned keys)  │
   │   ├─ SessionMetrics (Rule 4 counters)        │
   │   ├─ SENTINEL T0 thresholds ──► flag ──►     │
   │   ├─ SENTINEL T1 ONNX (env-var model path,   │
   │   │   advisory only, graceful degrade)       │
   │   ├─ DOSSIER ledger + breadcrumbs            │
   │   └─ routers: clean lobby | quarantine lobby │
   └───────┬───────────────┬──────────────┬───────┘
           │ reconnect,    │  flagged     │  unknown tools
           │ batched waves │  sessions    │  & probes
           ▼               ▼              ▼
   QUARANTINE INSTANCE   DOSSIER DB    DECOY TWIN (honeypot)
   (same binary,         (SQLite,      (fake world, full capture,
   IS_QUARANTINE=1,      encrypted,    fake success forever)
   cheaters only+bots)   + PCAP store)
           │                │
           ▼                ▼
   abuse-report packager   NIGHTLY BATCH (RTX 3050)
   (reports/abuse-         pattern miner + sentinel retrain
   template.md)            → receipts → model vN → restart
```

---

## 1. Host topology (hard rules)

1. **One public port: UDP 7777 via Portwarp edge.** Nothing else reaches the
   internet. No TCP tunnels, no game ports on the LAN-facing IP, no
   port-forwards to the editor.
2. **MCP port (8765) never leaves the machine** (MCP-SECURITY B4). Dev/editing
   happens on the LAN/loopback only; if remote dev is ever needed: stdio
   over SSH with token auth, still never the game box.
3. **Three processes, one machine:** real server, quarantine lobby, decoy
   twin — same binary, env-var role (`ROLE=live|quarantine|decoy`), separate
   DBs. Decoy advertises where cheaters look (public server list), never on
   the real IP (deception placement rule).
4. **Edge-IP twist handled:** since the tunnel NATs all players to the edge
   IP, per-IP budgets (handshake, ConnectionsLimit) are *session* budgets
   (auth-envelope session IDs + machine fingerprints, USER-DOSSIER 6), not
   IP budgets. IP-based logic only feeds the weak edge of the L4 graph.

## 2. Server process hardening (the box)

- Run under a **low-privilege Windows account**, no admin, no network share
  access; headless flags (`-headless -mute -null -std`, DEPLOY-GCP pattern
  adapted to Windows).
- **Firewall:** allow UDP 7777 from the tunnel edge only; block everything
  else inbound on the host; no remote desktop public.
- **Windows Defender:** scoped exclusions (game dir) only — never blanket;
  Defender on for the rest of the box.
- **Load gates:** `ConnectionsLimit` 16-32, `duplicatePeers=2`, per-session
  handshake budget (NET-4), ENet bandwidth limits, peer timeouts.
- **Patch cadence + rotation** (SECURITY-BY-DESIGN Rule 3/5): version byte +
  opcode permutation per release; HMAC `sharedVersionKey` rotated per
  release with a key ceremony (generate → ship in server build → client
  build; never in docs, never in game content).
- **No protocol docs public** (AoS lesson) — honey docs with wrong offsets
  are the *only* docs "public" (ATTACKER-INTEL L7.4).
- **Backups:** world state + dossier DB (encrypted) to a separate drive /
  cold location, daily.

## 3. Data (the prize the attacker wants)

- Dossier DB + PCAP store + sentinel labels: **encrypted at rest**, offline
  backups, retention per USER-DOSSIER 4. Machine IDs are hashes (not PII).
- Attacker DB and game world never share credentials; secrets via env vars
  only (SecretStore doctrine).
- Privacy/legality: own-logs-only; chat sanitized; full detail only under
  flag (USER-DOSSIER 6).

## 4. The operational loop (24/7)

```
always-on:  T0 thresholds → flags → shadow → (wave: quarantine/ban)
every 60 s: T1 ONNX on session end → flags → dossier
nightly:    pattern miner + sentinel retrain + receipts → model vN → restart
on wave:    cluster kill (accounts + fingerprint burn + quarantine rotate)
on event:   abuse-report packager (PCAP hash + facts) → provider
```

Human in the loop: you review flags (dossier dashboard), confirm/clear,
authorize waves. Nothing auto-bans (AI-SENTINEL advisory rule).

## 5. Build order (phases — each is shippable)

- **P0 — baseline:** NET-1/2/4 fixes, strict parsing, SessionMetrics T0
  wired, ENet gates. Lab: attack-run.ps1 green.
- **P1 — identity:** auth envelope (id=250) + version byte + opcode
  permutation; machine fingerprint + protocol DNA computed; dossier ledger
  written for all sessions. Lab: fingerprints stable across IP change.
- **P2 — sentinel shadow:** T1 Isolation Forest ONNX (lab-generated data),
  shadow queue + dashboard, no actions yet. Lab: FPR < 1% gate.
- **P3 — public:** live server via Portwarp; quarantine lobby live; ban
  waves authorized; decoy twin advertised.
- **P4 — intel ops:** nightly miner, tool fingerprinting, abuse reports,
  honey docs rotation, attacker-AI dossier (L5.3) when combat stats exist.
- **P5 — MCP hardening** (parallel, dev machine, not the game box): the
  MCP-SECURITY checklist + lab tests.

## 6. Acceptance (what "top-secured" means, measurably)

- Every lab attack from the suite is detected (ARSENAL F7 matrix) and no
  clean walkthrough flags (FPR < 1%, 10-session baseline).
- Identity survives IP change; account hop attaches to the same dossier.
- Quarantine quit-rate >> real-server quit-rate (cheaters leave).
- Abuse report package generated in one command from any live attack.
- MCP endpoint fails every lab probe (no-Origin, rebind, tokenless, CORS).
- Zero attacker-reachable paths to: dossier DB, keys, sentinel model
  decisions, MCP tools (game content can never invoke them).

*References — component specs: SECURITY-BY-DESIGN (authority, envelope,
versioning, metrics, ops), AI-SENTINEL (watchdog), ATTACKER-INTEL
(honeypots, fingerprints, graph, counter-offense), USER-DOSSIER
(observability), MCP-SECURITY (dev-tool surface), HOSTING/DEPLOY-TUNNEL
(edge + twist), ARSENAL F6/F7 (defense spec + acceptance).*
