# MONETIZE — earning from the lab (directions + research, 2026-08-01)

Everything here starts from assets you already own: an attack lab that breaks
game servers + MCP/AI plugins, a working scan engine (`tools/services/scan.py`),
a real finding (FINDINGS-MCP-001), and a product (FlaxMCP) with a security
pack spec'd and half-built. This doc ranks directions by fit / time-to-first-
dollar / ceiling. Facts marked [R] = researched GitHub/market, [K] = general
knowledge, be skeptical.

## The 8 directions

### 1. MCP / AI-plugin security audits — THE niche (T4) [R]
- Market fact: MCP is exploding (Claude Desktop, Cursor, opencode, Copilot all
  load MCP servers; anyone can publish one). Security tooling for it is a
  crowded GOLD RUSH: `getagentseal/agentseal` (audit live MCP servers for tool
  poisoning), `HarmonicSecurity/claudit-sec` (audit Claude Desktop MCP configs),
  `luckyPipewrench/pipelock` (AI agent firewall, Apache), `snyk/agent-scan`
  (2.8k★) — all young, all small teams, all charging money.
- Your edge: you've ALREADY built the MCP attack lab + found a real vuln in
  your own plugin (no-auth tools/list+call). Almost nobody offers a *manual*
  MCP security audit by someone who breaks MCP servers for fun.
- Offer: "MCP server / plugin security audit" — config review + live endpoint
  tests + report. Price: $300-1500/audit (niche, little competition).
- Reputation play: publish a public writeup of FINDINGS-MCP-001 (your own
  plugin, anonymized) — instant credibility in a niche where content is thin.

### 2. Game server / netcode security audit (T3) [K]
- Indie multiplayer games (Godot/Unity/Flax, ENet/Steamworks/Photon) ship with
  zero netcode security. Servers trust the client, no envelopes, no budgets.
- Your lab is purpose-built for this (flax_enet.py, boofuzz, envelope spec).
  Offer: "game netcode security review" — protocol fuzz + cheat-class probes +
  fixes. Price: $500-2500/game. Demand channel: indie dev Discord/forums,
  GameDev.net, itch.io multiplayer jams.
- Differentiator vs generic pentesters: you speak game protocol (packet ids,
  ENet, server-authority), they don't.

### 3. Bug bounty — direct cash for attack skill [K]
- Platforms: HackerOne, Bugcrowd, Intigriti (weekly challenges = free practice +
  rep), yesWeHack, HackTheBox ProLabs (skill gate).
- Honest reality [K]: web bug bounty is saturated; beginners earn little;
  it's lottery-ish. BUT the MCP/AI-assistant corner is new and under-hunted —
  your MCP skills land there. Targets: MCP server implementations, AI agent
  frameworks, tool-poisoning cases in popular MCP servers.
- Treat as: reputation + occasional payout, NOT the main income. The main
  income is #1/#2 where you control the price.

### 4. Productized website scans (T1) — fastest first sale [R]
- Engine already exists: `scan.py` (headers/TLS/ports/CMS/paths) + nuclei
  (Docker, deploy host). Fixed price: $50-150 per site scan, $30-60/mo
  re-scan retainer ("your site checked monthly, report each time").
- Research: `APTRS` (1.1k★, MIT) — self-hosted automated pentest reporting
  with customer dashboard + client management: exactly the delivery backend
  for this. `reconmap/pentest-reports` — report templates from top companies;
  `noraj/OSCP-Exam-Report-Template-Markdown` (4.2k★) — pro markdown report
  skeleton. Steal all three.
- Channel: local businesses, WordPress/WooCommerce shops (the Flatsome case),
  Fiverr/Upwork as a portfolio seed.

### 5. Plugin licensing + security pack upsell (your product) [K]
- Sell FlaxMCP plugin: base license + "SecurityPack" premium tier (S0 core:
  envelope, tripwires, budgets, sentinel — already half-built). Buyers of a
  game MCP plugin are exactly the T3/T4 audience — the services become lead
  gen for the plugin and vice versa. License via plain email + license file
  (DRM honest limits documented in MCP-SECURITY surface C).

### 6. Nuclei templates + MCP CVE content [R]
- Nuclei templates are the industry's VulnDB (30k★, MIT, YAML). Writing
  templates for MCP/auth gaps (e.g., "MCP endpoint without token") gets you:
  GitHub stars, community rep, and sponsor buttons. Small money, big
  compounding for #1/#2/#3. Also: your injection-corpus + fuzzd corpora can
  become a published MCP security test pack (MIT) — the ecosystem lacks one.

### 7. Education/content [K]
- Hot topic, almost no courses: "MCP security for developers" / "harden your
  game server". Your docs ARE the curriculum (TRICKS, BUILD-*, playbooks).
  Udemy/YouTube + a paid workshop. Slow burn; compounds everything else.
  Gate: needs you on camera; decide if that's you.

### 8. Affiliates (trivial, don't build a plan around it) [K]
- Hosting affiliates (from HOSTING.md research), Cloudflare, security tools.
  Pennies; only add once a site/blog exists for #7.

## Recommended path (phased, $0 start)

```
Phase 1 (this month, $0):
  - Publish the FINDINGS-MCP-001 writeup (anonymized) -> niche reputation
  - Join Intigriti + HackerOne MCP-adjacent programs (practice + rep)
  - Offer ONE free MCP audit + ONE free game netcode review (portfolio)
Phase 2 (1-2 months):
  - Productize T1: scan.py + nuclei(Docker) + APTRS backend -> $50-150/site
  - T3 offer on indie dev channels; T4 offer on MCP/AI dev channels
Phase 3 (3-6 months):
  - Recurring monitoring retainers (T1/T4 monthly)
  - SecurityPack premium tier live in FlaxMCP (upsell into T3/T4 leads)
  - agentos fleet + service MCP tools -> scale without hiring
Phase 4 (later):
  - Course/content if the personal brand works; publish nuclei MCP templates
```

## Honest risks (don't skip)

1. **Authorization is the law.** Every engagement needs a signed scope.
   One unauthorized scan = the business dies (and worse). The lab doctrine
   "authorized targets only" is now a business rule.
2. **Liability.** Deliver findings + verified fixes, never "unhackable"
   guarantees. Residual-risk section in every report (report.md already has
   the shape).
3. **Time-to-first-dollar.** Bug bounty = slow; services = weeks. Don't quit
   anything for this until Phase 2 has a paying customer.
4. **The niche could flood** (see the gold rush above) — but manual deep
   audits by someone who can also FIX the code (you have both repos) hold
   value even when scanners commoditize the shallow part.
5. **Secrets hygiene** in customer scans (escalate-not-log; DossierWriter
   scrubbing rule already spec'd).

## Research notes (sources)

- [R] GitHub verified 2026-08-01: APTRS (1.1k★ MIT, pentest reporting + client
  portal), reconmap/pentest-reports, noraj/OSCP report templates (4.2k★),
  agentseal (MCP audit), claudit-sec (Claude Desktop audit, 293★),
  pipelock (agent firewall, 792★), snyk/agent-scan (2.8k★) — MCP security is
  an active commercial space already.
- [K] Platform knowledge (HackerOne/Bugcrowd/Intigriti mechanics, indie dev
  market, WP service pricing) — verify locally before acting.
- Next research round: actual MCP audit pricing on the market (fiverr/upwork/
  specialist firms), game netcode audit demand on indie forums, Intigriti
  earnings reality.
