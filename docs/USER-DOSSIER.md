# USER-DOSSIER — Paint Every Player, Observe Every Attacker (spec)

**Purpose:** one persistent, per-user dossier for *every* player — identity
signals, behavior breadcrumbs, verdict history, cross-session memory — and a
live-shadow observation mode for attackers. Attacker = a user whose dossier
accumulates flags. No "us vs them" split, one ledger.

**Place in the stack:** dossier is the write-side of everything else —
AI-SENTINEL reads dossier features, ATTACKER-INTEL L4 reads dossier edges,
SECURITY-BY-DESIGN Rule 4 defines the raw counters. This doc defines the
record format, the streams, and the observation console.

---

## 1. Session ledger (the record)

One append-only record per session (JSONL: `dossier/sessions/<yyyy-mm>/<sessionId>.jsonl`).

```json
{
  "sessionId": "s-<uuid>", "userId": "u-<hash of strongest id>",
  "tsStart": "...", "tsEnd": "...", "durationS": 0,
  "verdict": "clean | flagged | shadow | quarantine",
  "reasonTags": ["canary-251", "speed-exceeded", "clock-drift-match"],
  "identity": {
    "ip": "...", "port": 0, "tunnelEdge": true,
    "machineId": "m-<hash(clock-drift+transport quirks)>",
    "protocolDna": "p-<hash(first-session sequence)>",
    "toolFp": "t-<hash(mutation grammar)>|none",
    "clientBuild": "1.2.3"
  },
  "behavior": [
    {"t": 0.0, "type": "zone", "z": "spawn"},
    {"t": 1.2, "type": "item", "i": "canary-007", "ok": false},
    {"t": 3.0, "type": "cmd", "c": "teleport", "ok": false},
    {"t": 4.5, "type": "chat", "s": "<sanitized text, never raw>"}
  ],
  "metrics": { "pps": {"mean": 0, "p95": 0, "max": 0}, "bytesPerS": 0,
    "sizeVar": 0, "maxMoveDelta": 0, "speedExceeded": 0, "badMac": 0,
    "replaySeq": 0, "unknownId": 0, "hitAcc": 0, "burstiness": 0, "jitter": 0 },
  "links": ["m-...", "p-...", "t-...", "a-<account>", "d-<discord>?"]
}
```

**Painting rules:**
- **Identity = strongest signal wins.** Machine ID (clock-drift + transport
  quirks, ATTACKER-INTEL L3.1) beats IP; protocol DNA beats client build;
  tool fingerprint beats claim. IP is only a *weak* edge (CGNAT/tunnel edge).
- **Behavior breadcrumbs are whitelisted events, not a raw dump:** zone
  changes, item pickups (esp. canaries), command attempts, chat (sanitized
  + hashed, never stored raw for privacy), disconnects. Raw packet detail is
  for flagged sessions only (L2 full capture).
- **Metrics = SessionMetrics counters verbatim** (SECURITY-BY-DESIGN Rule 4),
  so sentinel T0/T1 can recompute/validate offline.

---

## 2. Breadcrumb stream (the "who goes where, does what" feed)

Append-only event stream, per session, written by the server kernel at every
hook point (PacketRegistry receive, NET-3 movement check, auth-envelope
drop, combat path). Two consumers:
- **Live tail (ops console):** an observer (you) watches a flagged session
  stream in real time.
- **Offline replay:** flagged sessions replay frame-by-frame from PCAP
  (flax_enet.py pcap-replay) with breadcrumbs overlaid — the "VHS" of the
  attack.

Storage: clean sessions = summarized breadcrumbs (coarse, e.g. zone-level,
1/s max) to keep the ledger cheap; **flagged sessions = full detail**.

---

## 3. Dashboard (the "know everyone" console)

`dashboard/` — a local web/CLI tool (or MCP tools — scoped read-only, see
MCP-SECURITY A2):

| View | Shows |
|---|---|
| Live board | all current sessions: verdict, machine ID, DNA, pps, jitter, flags live |
| Dossier page | one user: full timeline, verdict history, linked accounts (L4 graph), recidivism count |
| Flag queue | shadow-flagged sessions awaiting human review → confirm/clear (feeds sentinel labels) |
| Watch | live breadcrumb tail of any shadow/flagged session + PCAP replay |
| Cluster view | L4 graph rendered per machine/tool/account |
| Quarantine | who's in the lobby, quit-rates vs real server |

Every review action (confirm flag / clear / quarantine) is logged into the
dossier + exported to `sentinel/labels/confirmed.jsonl`.

---

## 4. Cross-session memory (the "he's back" machine)

- On connect: compute machine ID + DNA → lookup dossier DB → if a prior
  dossier exists (even under a different account/IP), **attach** this
  session to it and emit `recidivism` event.
- Recidivism rules: machine match + flag history ⇒ auto-shadow on connect
  (never auto-ban); machine match + clean history ⇒ normal, but `note`.
- New-account bursts from one machine ID = ban-evasion batch → whole cluster
  marked (ATTACKER-INTEL L4 creation-burst edge).
- Dossier DB: SQLite (encrypted at rest), retention: full detail 90 days,
  summaries 1 year, machine IDs kept indefinitely (they're hashes, not PII).

---

## 5. Live-shadow operations (observing an attacker right now)

Playbook (from ATTACKER-INTEL L2):
1. Flag fires → session enters **shadow** (nothing changes for them).
2. You open **Watch** — live breadcrumb tail + metrics + raw packet stats.
3. You may escalate to **full capture** (PCAP) — automatic for flagged.
4. You may route them to the **quarantine lobby** — but only at reconnect,
   batched, in a wave (never mid-session; that teaches the detector).
5. You may **test them in the decoy**: point them (or a copy of their
   traffic via pcap-replay) at the decoy twin — their tool exercises the
   fake world, we record the whole tool behavior (Cuckoo's Egg method).
6. Endgame: cluster-wide wave (account ban + fingerprint burn + quarantine
   rotate) once the dossier is mined (ATTACKER-INTEL L7.7).
- **OPSEC:** nothing the observer does is visible to the target; console
  access itself is restricted (MCP-SECURITY tiers apply — the dossier
  console is read-only, approval-gated, never reachable via game content).

---

## 6. Honest limits (state once, design around them)

- We observe **what touches our server**: packets, actions, timing. Not
  their screen, not their processes, not their other apps (client telemetry
  is an opt-in trust question, never a guarantee).
- **Behind a tunnel edge, IPs lie**: Portwarp-class UDP tunnels NAT everyone
  to the edge IP (DEPLOY-TUNNEL "edge-IP twist") — per-IP logic breaks, so
  machine ID + DNA + auth-envelope session identity are the primary edges
  (this is *why* the dossier stores them on every session).
- **Behind a VPN, identity hides** — we see the fingerprint cluster, not
  the face. OSINT (maigret-style) works only on public handles they reuse.
- **Clean players are human too**: privacy-minimal by design — chat
  sanitized, metrics summarized, full detail only under flag. This is also
  what keeps us legal (own-logs-only doctrine, ATTACKER-INTEL ground rules).

---

## 7. Lab test matrix

| Test | Method | Pass criterion |
|---|---|---|
| Dossier created per session | walkthrough session → record exists | ledger row + identity computed |
| Breadcrumbs flow | clean walkthrough: zone/item/chat events | coarse events, ≤1/s, no raw chat |
| Machine ID persistence | same VM, 2 IPs, 2 accounts | both sessions attach to one dossier (recidivism=1) |
| Auto-shadow on return | flagged machine reconnects | verdict=shadow at connect, no ban |
| Full capture on flag | fuzz attack flags | PCAP + full-detail breadcrumbs stored |
| Review loop | flag → confirm → label exported | `sentinel/labels/confirmed.jsonl` row + dossier verdict |
| Replay | pcap-replay of flagged session | timeline renders; attacker behavior visible |
| Dashboard isolation | dossier console via MCP tool | read-only, approval-gated, no game-content reach (MCP-SECURITY tests) |

*Reference: SECURITY-BY-DESIGN Rule 4 (counters), AI-SENTINEL (features +
labels), ATTACKER-INTEL L2/L3/L4/L7 (shadow, fingerprints, graph, endgame),
MCP-SECURITY (console access tiers), DEPLOY-TUNNEL (edge-IP twist).*
