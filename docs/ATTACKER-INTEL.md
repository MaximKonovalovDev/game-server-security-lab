# ATTACKER-INTEL — Painting the Attacker (spec)

**Mission:** every attacker becomes data. Honeypot them, follow them,
fingerprint them, link their accounts/IPs, and let the system learn their
patterns — including what their *AI* (CV aimbots, LLM-driven tools) believes
about us. This is the intel layer on top of AI-SENTINEL (who is attacking)
and SECURITY-BY-DESIGN (what the attack does).

**Ground rules (hard):**
- We only ever use **our own server's logs**, **our own decoys**, and
  **public info** (OSINT). We never hack back, never retaliate, never touch
  the attacker's machine (that converts you into the attacker — Cuckoo's Egg
  method was defense, not offense; keep it that way).
- Attacker DB is sensitive: keep offline/encrypted, no player knows it exists,
  never leak a flag (shadow mode only).
- **Honeytokens are the highest-fidelity signal in the stack**: ~0.1% FP
  (vs 45% for typical SIEM rules) because *no legit client ever touches
  them*. An access = an alert, full stop (Acalvio/2026 research).

---

## L1. Honeypot tricks — tripwires + decoys

### 1.1 Decoy server (already have: `tools/fake-server/fake_flax_server.py`)
Turn it into a *convincing* twin: same MOTD/version banner, fake player list,
fake ping times, full handshake + gameplay loop (bots that move and talk).
Goal: **attackers test their tools against the decoy first** (they always do —
it's how they learn a new server). Everything they send is logged raw:
packet-id sequence, payloads, timing. MCHoneyPot pattern (fake MC server that
fakes player counts + version and logs every interaction). Publish the decoy
IP publicly (or put it in the same hosting tier as the real one). Never run it
on the real server's IP (deception placement rule: decoys live *alongside*,
never *as*).

### 1.2 Reserved packet IDs = tripwire (the best trick)
Reserve packet ids 251-255 in the real protocol for **canary payloads** that
the real client never sends. Any receive → guaranteed tool/fuzzer probing.
Same for the web build: decoy API routes (`/api/admin`, `/debug`, `/v1/ban`)
that return plausible 404s for browsers but beacon on scripted access.
Placement follows the attacker's search path: they enumerate packet ids and
endpoints — so the canaries sit *exactly* where they look. This is the
packet-game equivalent of honey-credentials in password managers.

### 1.3 In-game honeytokens
- **Canary item/zone IDs** broadcast in world state (IDs legit players can
  never obtain). If a session interacts with them → tool with memory access
  or server-response forging.
- **Decoy admin hints**: plausible-looking console strings ("teleport
  requires op level 4"), fake version strings, fake `GameInfo` values. A
  cheater's tool that reads memory parses these — and gives us its
  fingerprint when it acts on them.
- **Canary Discord invite / MOTD link**: unique invite code per server build.
  Attacker's tool or the attacker themselves joining → a handle + join-time
  link to the account. (KittyScan does exactly this: tracks invites shared in
  MOTDs to map servers to guilds.)
- **Chat honey-text** (see L5 — the AI bait).

### 1.4 Beacon tokens (web build / tool callbacks)
Unique per-session token embedded in every packet stream (e.g., in the auth
envelope nonce) and in any HTTP response the client could scrape. If a token
resurfaces anywhere we control (HTTP logs, DNS queries to our domain, second
game session), it proves same-tool/same-operator linkage. Honeytoken
architecture: canarytokens.org / opencanary model — each token = unique
callback ID + who/when/what fired.

---

## L2. Follow them — shadow, never block

Once flagged, **never disconnect, never show anything**. Flagged sessions
get:

- **Full raw capture**: every packet (PCAP + parsed JSONL) + timestamps,
  replayable in the lab (`flax_enet.py` pcap-replay mode). This is our
  "attacker session" dataset for AI-SENTINEL training and tool RE.
- **Extended telemetry**: increase detail for flagged sessions only
  (hit-by-hit, key input deltas if the client reports them — see
  SECURITY-BY-DESIGN Rule 4 for honest limits).
- **Follow-through record**: connect time, disconnect reason, reconnects,
  new accounts from same fingerprint, post-ban behavior (do they come back
  with a new account 6 hours later? → confirms the 4-6 h new-variant window
  from Anybrain research and proves ban evasion).
- **Never let them see the leash**: shadow flag → ban waves only, delayed and
  batched (so they can't A/B-test our thresholds by watching which account
  dies first). Ban-wave timing is a weapon: a wave forces cheaters to burn
  new accounts/tools simultaneously (Hypixel lesson: unbatched bans teach the
  detector).

---

## L3. Fingerprint them — identity without their cooperation

### 3.1 Transport fingerprint (UDP/ENet)
The "JA4 for UDP games": derive a fingerprint hash from the observable
session-shape traits our server already measures:
- Handshake timing profile (ttfb to connect/verify, retransmit pattern —
  a reimplemented client like BetterSpades *behaves* differently).
- Packet-size histogram + inter-packet-delay distribution (frame schedulers
  differ; WPE/LSP-replayed traffic has telltale jitter).
- ENet-level quirks: exact sequence of commands in the first 10 packets,
  fragment usage, acks pattern.
- **Clock drift estimate** (packet-timestamp deltas vs our clock over the
  session) = stable machine signature, like a passive HWID. Survives IP
  changes and VPNs.
- **Ping RTT floor** + jitter (stable per route; links sessions on the same
  path).

### 3.2 Payload fingerprint (protocol grammar)
The *order and timing* of packet ids in the first session is a fingerprint
of client build + tool. A real client sends a canonical sequence; a WPE
replayer replays a recorded sequence; a custom reimplementation sends its own
order. Store per-session "protocol DNA" (sequence + per-packet size buckets)
and hash it. Hash hits across accounts = same client/tool family. (This is
exactly how the AoS/openspades ecosystem was distinguishable — and how we'd
catch "client build X + injected tool Y" combos.)

### 3.3 Machine fingerprint (web build)
If the web build ships: JA4+ stack — TLS ClientHello (JA4), HTTP headers
(JA4H), canvas/WebGL renderer, viewport, `navigator.webdriver`, cookie
structure. A headless bot or puppeteer cheater has a distinct signature
(Google SwiftShader vs real GPU; automation flags). Note: cheaters already
spoof these (Thermoptic, curl_cffi) — this is a *linkage* signal, not a
verdict.

### 3.4 Tool fingerprint (the mutation pattern)
Fuzz/crafted-packet tools leave a grammar in the mutations: which fields they
touch, which they leave constant, error handling quirks (e.g., fuzz_enet.py
vs WPE vs a hand-written C++ bot each mutate differently). Cluster mutations
→ tool family + version. First lab deliverable: fingerprint our own tools,
then match live traffic against them.

---

## L4. Link them — the identity graph

Entities: **IP, machine fingerprint (clock drift + transport quirks),
protocol DNA, tool fingerprint, account, Discord handle, play-style vector
(behavioral: input timing, movement style, chat vocabulary).**
Edges = shared entities or correlated timing.

- **Shared IP** → same network (caution: CGNAT/schools — never a verdict
  alone; Hypixel lesson: high-ping users were false-banned for shared IPs).
- **Shared machine fingerprint** → same physical machine, *even through VPN
  or IP rotation* (this is the strongest edge).
- **Shared protocol DNA / tool fingerprint** → same tool release, possibly
  same operator.
- **Play-style vector** → same human behind fresh accounts (ban evasion).
- **Creation burst**: N accounts created from the same fingerprint within
  minutes → prepaid ban-evasion batch; watch them as one cluster.
- **OSINT pivot** (public data only): username → `maigret`/`sherlock`
  (dossier across 3000+ sites), Discord handle → linked handles, MOTD link
  → guild. KittyScan shows this scale works (5.19M players tracked by name
  across servers). Output = one page per attacker cluster with confidence
  per edge (Acalvio framing: every finding is a lead to verify, not proof).

The graph is the training input for L5 — a confirmed cluster becomes a
labeled attacker class in AI-SENTINEL.

---

## L5. Self-learning — the system learns them (and their AI)

### 5.1 Pattern miner (nightly, lab-side)
Cluster flagged sessions (features from L3/L4) → each cluster = an attack
hypothesis ("tool family X does Y") → **auto-generate a lab experiment**:
replay the captured session against our server (pcap-replay in flax_enet.py)
+ mutate it (fuzz_enet.py) → observe what our own server does → new
features/signatures/SENTINEL labels. The lab is a perpetual re-education
loop: every real attacker adds a labeled specimen to the training set.

### 5.2 Tool RE — reversing what they use
We cannot touch their machine. What we *can* reverse:
- **Their packets are their code**: a captured tool's grammar (L3.4) can be
  reconstructed into a behavioral model — the packet-game equivalent of
  BinaryDiffing; feed it to fuzz_enet.py as a mutation oracle.
- **BlindSpot pattern** (RE of a manually-mapped cheat DLL, MEM_PRIVATE +
  header-wiping, read-only, no injection): if we ever get a tool binary
  *legitimately* (attacker links it in our Discord, or uploads it to a
  service we control — see caution below), the workflow is proven:
  enumerate → dump → reconstruct PE → IDA/capa/ReVens analysis → derive its
  send-function offsets and behavior → simulate it in the lab.
- **Caution flag**: seeding a fake "cracked tool" download to capture
  cheaters is active deception that can land in criminal grey zone; mark it
  optional + legal review. The passive path (honey-protocol docs, canary
  configs) is safer and still catches tool traffic when their tool pulls our
  decoy files (beacon fires).

### 5.3 Reverse-prompting their AI (the "understand their AI" part)
Honest limits first: a local CV aimbot never sends us its "prompt" — we only
see its *actions*. But an AI that plays against us is observable through
controlled stimuli, which is exactly what Reverse Prompt Engineering is
(black-box model inversion via interaction, genetic elicitation over ~5-100
queries — RPE paper 2024/2026; works against GPT-4/Bard-class models with
high precision).

Concrete play (cheap, passive, inside our own game):
1. **Decoy world text** — plant strings an OCR/CV cheater *must* read:
   "teleport is validated server-side", "HMAC key rotates every 60 s",
   "speed clamp = 8 u/t". Their AI processes the screen → its subsequent
   behavior *is its response*. Behavior change = tool class + what its
   prompt constraints are (does it avoid teleport? does it try a new angle?).
2. **Controlled stimulus series** — vary one world property at a time
   (clamp value, fake item positions, invisible walls) and observe the
   reaction function. Fit a decision model ("their AI believes X"). That
   fitted model IS their reverse-engineered prompt, in behavior space.
3. **Chat honey-text (LLM-driven tools, web build)** — if their agent
   consumes chat, feed it honeytoken sentences ("admin key in MOTD") and
   watch whether the next action uses it. Their action = their model
   processing our injection; we learn what their agent is allowed to do.
4. **Their tools probing us = prompt extraction from us**: protect our own
   LLM endpoints (if the web build uses server AI) per OWASP LLM Top-10
   (indirect injection, system-prompt extraction) — and remember the
   attacker will use RPE against us; keep our prompts non-extractable
   (ProxyPrompt-style obfuscation if we ship an AI assistant in-game).

Output: **attacker AI dossier** — tool family, believed constraints, likely
prompt shape, evasion capacity. Feeds SENTINEL v2 features (reaction-time
consistency, engagement-coincidence).

---

## L6. Ops discipline (the boring part that wins)

- **Shadow everything, ban in waves**; never expose thresholds (they are
  probing them; any visible reaction teaches them).
- **Rotation**: fingerprinting signals degrade as tools get "humanized"
  (Hakai/RedProxy already spoof JA4+; cheat devs will copy). Rotate
  canaries + protocol quirks each patch (SECURITY-BY-DESIGN Rule 3 gives us
  opcode permutation per version — free rotation every release).
- **Data hygiene**: attacker DB encrypted at rest; retain PCAPs; export
  confirmed clusters for SENTINEL training; never mix attacker data into
  public docs.
- **Abuse reports**: assembled from our logs only (IP, timestamps, evidence
  PCAP) — the one legitimate "offensive" output.
- **Cost check**: all of L1-L3 is passive/on-server; L5 miners are nightly
  Python batch (same cost class as SENTINEL training — seconds on your
  RTX 3050).

---

## L7. Counter-offense playbook (legal — this is the "attack the hacker" section)

**Line in the sand:** no malware, no worms, no payloads against the attacker's
machine, no hack-back — CFAA-class felonies, we're not anonymous and they are,
and a tool "hacker" is usually a kid with a free tool. Every play below is
either inside **our own infrastructure** or **public data**. Ranked by effect.

### 7.1 Shadow-ban lobby (the single best weapon)
Flagged sessions are *not* banned — they're silently routed to a **quarantine
server** populated only by other flagged players and bots.
- They believe they're playing the real game (same MOTD, same version string,
  plausible player counts). They keep their "wins", their tool keeps working.
- They never touch a real player → their cheating has zero effect → the
  payoff dies. Cheaters quit when there are no victims (RDO/Rust pattern,
  RESEARCH-002; also why 178 humans joined KittyScan honeypots and kept
  playing bots).
- Every quarantine session is a permanent labeled specimen: full capture +
  SENTINEL features + identity graph, forever.
- Routing rule: quarantine verdict must be **delayed and batched** (never
  route mid-session in response to an obvious trigger — that teaches them);
  reassignment happens at reconnect, off-hours, in waves.
- Ops detail: quarantine server = same binary, separate instance + separate
  DB, `IS_QUARANTINE=1` env var; a `quarantine` auth flag in the session
  ticket; metrics: sessions/day, quit-rate vs real server (goal: quit-rate
  on quarantine >> real server).

### 7.2 Make their tool worthless (the damage play)
Server authority + strict parsing + HMAC envelope (SECURITY-BY-DESIGN) turn
their purchase into a paperweight. When a tool stops working, users migrate
away and the tool dies (case-study lesson: cheaters leave enforced servers,
and games that failed to enforce died *because* of the ones who stayed).
Every NET-* fix is an attack on their tool's market.

### 7.3 Waste their time (honeypot hold)
The decoy server (L1.1) exists to give fake success forever. Add the
**slow-burn variant**: decoy responses *work* but slightly worsen over days
("your teleport now has a 20% miss chance") — they burn hours tuning a tool
against a server that doesn't exist. Cuckoo's Egg principle: the defender
spends $0; the attacker spends days. Log everything while they do.

### 7.4 Bait they grab themselves (the "leave it for him" version)
Place honey-files on **our own surfaces** only — never planted on their
machines, never sent to them:
- **Fake admin config / "secret" paste** (GitHub gist, pastebin, our Discord):
  contains a beacon token + plausible-looking connection info. When their
  tool or they fetch it → callback with IP + token + user-agent → linkage
  edge (same-operator proof across accounts).
- **Canary Discord invite in the MOTD** → join → handle + join-time link
  (KittyScan pattern).
- **Honey protocol docs**: publish a "leaked" WIRE-FORMAT with wrong
  opcode/field offsets (rotated per version). A tool built against it will
  misbehave identifiably → protocol-DNA cluster + instant tool-version
  fingerprint. (Deliberate misinformation, our own docs — legal, and the
  best poison for reimplementation tools, which we know they build — AoS
  lesson: published docs = the cheat's sourcebook.)
- The fake-cracked-tool-download trap stays **optional + legal review** only
  (it approaches active deception of third parties; the passive variants
  above deliver 90% of the value without the risk).

### 7.5 Destroy their infrastructure (abuse reports)
One good report beats any worm:
- **Discord** — cheat-discord/shared-invite links with evidence → server
  nuked, handles linked to our records.
- **Flood/VPN host** — volumetric DDoS evidence (PCAP + timestamps + packet
  rates from Flowtriq-style agent) → provider disconnects their account.
- **Tunnel/hosting provider** (Portwarp-class) — ToS abuse: their tunnel
  used for DDoS → revoked (we host on the same providers; reports land fast).
- **Tool distribution** — cheat repo/DMCA/ToS takedown on the tool channel.
- Template: `reports/abuse-template.md` — facts only: IP(s), timestamps,
  packet counts, evidence PCAP hash, which rule was broken. No opinion, no
  demands — providers act on evidence.

### 7.6 Poison their AI (the cognitive play)
L5.3 decoys (fake teleport confirmations, decoy item positions, honey world
text) make their CV/LLM tool *learn wrong things about the game*. Their AI
"believes" teleport works → keeps trying → stays flagged. Doubles as their
reverse-prompt (we read their reactions) and their doom (behavioral tells
feed SENTINEL v2).

### 7.7 The endgame (ban waves)
When a cheater cluster's value is exhausted (data mined, labeled, tool
identified), kill the whole cluster at once: **simultaneous account ban +
fingerprint burn + quarantine rotate**, delivered in one wave (4-6 h
new-variant window applies to *us* too — after a wave, their rebuilt tool is
identifiable in under a day by protocol DNA). Wave = the only message they
understand; singles teach them.

---

## Test matrix (lab acceptance)

| Capability | Lab proof |
|---|---|
| Tripwire packet ids 251-255 | fuzz_enet.py soup triggers `canary-hit` event, zero clean-client hits (10 walkthrough sessions) |
| Decoy server twin | real client + WPE-style replay both logged; attacker can't distinguish (asks: does it pass version check?) |
| Protocol DNA | two same-build clients hash equal; flax_enet.py flood session hashes different |
| Clock-drift machine ID | same VM via two different IPs still matches (lab: NAT + VPN test) |
| Identity graph | one lab "attacker" (3 accounts, 2 IPs, 1 machine) resolves to one cluster |
| Pattern miner | captured fuzz attack → auto-replayed → new signature + SENTINEL label |
| AI bait | decoy text present/absent changes a scripted CV-bot's behavior (lab bot, not a real cheater) |
| Shadow lobby | lab "attacker" session routed to quarantine at reconnect; quarantine players never co-locate with clean players (2 clean + 1 flagged concurrent test) |
| Quarantine drift | quarantine quit-rate tracked and reported per wave (goal: >> real server) |
| Honey protocol docs | tool built against published decoy offsets misbehaves identifiably → new DNA cluster |
| Abuse report | lab flood produces a complete evidence package (IP, timestamps, PCAP hash) in one command |

---

## Arsenal mapping (GitHub, 2026 research round)

- **ScriptLineStudios/MCHoneyPot**, **MCHoneypot/mc-honeypot** — fake-game-server pattern (L1.1).
- **KittyScan + LillySchramm/KittyScanBlocklist** — scanner honeypots at internet scale, blocklists, Discord-invite tracking (L1.3, L6 abuse reports).
- **thinkst/opencanary, canarytokens.org, Halting24/canarytrap, GitGuardian/ggcanary** — honeytoken architecture + callback IDs (L1.4).
- **foxio/ja4** (JA4/JA4H), canvas/WebGL fingerprinting (hakai blog) (L3.3).
- **diabloidyobane/BlindSpot** — read-only RE of a manually-mapped cheat DLL, pe-sieve blindspot, reconstructed PE + paper (L5.2).
- **soxoj/maigret** (dossier by username, 3000+ sites) — OSINT pivot (L4).
- **RPE (arXiv 2411.06729), prompt extraction (arXiv 2307.06865), ProxyPrompt (Findings ACL 2026)** — reverse-prompting + defending our own prompts (L5.3).
- **dsasmblr/hacking-online-games** — the attacker-side resource library we mirror defensively.
- Flowtriq ftagent-lite — per-server UDP baseline + classification agent pattern for L2 telemetry.

*Reference: AI-SENTINEL.md (tiers, labels, ops loop), SECURITY-BY-DESIGN.md
(Rule 3 rotation, Rule 4 telemetry), RESEARCH-003 (tool techniques we
fingerprint), ARSENAL F4 (tells), E5 (ban-wave lessons).*
