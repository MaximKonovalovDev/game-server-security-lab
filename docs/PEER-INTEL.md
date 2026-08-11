# PEER-INTEL — what solo security practitioners actually do (Reddit research, 2026-08-01)

Research round: r/AskNetsec + r/cybersecurity threads on running a solo/boutique
security business. Every section = a practitioner's hard-won rule, with source.
This doc corrects and sharpens FIRM-PROPOSAL.

## 1. THE cautionary tale — report tone can be criminalized

**Source: r/cybersecurity AMA "I went to prison for internet piracy and
hacking" (2 months old, 1,600+ pts, ~300 comments).**

The HeheStreams case (SDNY, 2021): operator charged with CFAA + wire fraud +
"illicit digital transmission". Served 18 months in federal prison. The
detail that matters for us: he was ALSO charged with **extortion and
interstate threats based on his bug-report writing style** ("my autistic-ass
replying on brand when making a bug report"). The way he wrote reports became
charges.

**Rules extracted:**
- The "report weakness to admin, offer fix" model is legal ONLY with prior
  authorization. This AMA is the counter-example: gray-area hunting + a
  snarky report = federal case. FIRM-PROPOSAL's "acceptance before scanning"
  rule is now backed by a 1,600-pt firsthand prison story.
- Customer-facing report tone is a legal surface: neutral, factual,
  "findings as of date on scope", zero sarcasm, zero threats (even implied).
- Never report vulnerabilities on systems you weren't asked to test. Ever.

## 2. Scoping + pricing — the peer playbook (boutique shop owner, 11 days old)

**Source: r/AskNetsec "How do you currently scope and price a pentest
engagement before testing even starts?"** — solo boutique owner asked; peers
answered:

- "Everyone reuses a template. The ones who say they don't are retyping last
  quarter's proposal." → **Build ONE master template; never start from scratch.**
- "Build a scoping questionnaire that the price depends on, so when the asset
  count turns out to be double what the client told you, the re-scope is
  contractual instead of a fight." → **Price = f(scope questionnaire). Asset
  count in writing; re-scope clause automatic.**
- Tiered pricing observed in the wild:
  - Web app only → Price A
  - Web + API → Price B (LOE on API size)
  - Web + API + Network → Price C (CIDR ranges)
  - + Mobile → Price D
  → Our FIRM-PROPOSAL prices become **tier tables**, not flat prices:
  T1 site scan (A), +server hardening (B), +game/MCP deep (C/D).

## 3. The legal + insurance floor (recurring peer wisdom)

- "Pentesting contracts and the law" (11y old thread, still cited): written
  authorization + consult an attorney, always. Same rule today.
- "Pentesting insurance" thread: incorporate + general business liability
  insurance. **Add to FIRM-PROPOSAL section 6: insurance is not optional
  before enterprise clients.**
- "Starting up an Own Pentesting firm as a freelancer" — solo start is normal;
  branch out after.

## 4. Business reality — the 10-lessons thread (2,000+ pts)

**Source: r/cybersecurity "My thoughts on a decade of Cyber Security: 10
Lessons" (4y old, still top-of-subreddit).** Lessons that change how we sell:

- **Lesson 1-2 — speak money, not stats.** CFOs don't care about "firewall
  blocks"; they care about $ saved per incident. Our customer reports must
  translate findings into $ (e.g., "this hole = card fraud exposure + PCI
  fines, ~$X/yr at risk").
- **Lesson 9 — "don't write to be understood, write so you can't possibly be
  misunderstood."** Reports get read by CEOs. Simple language, established
  terms, evidence-linked. Our abuse-style findings already fit; the customer
  summary needs plain-language $ framing.
- **Lesson 10 — marketing/design is a legit weapon.** Single image beats
  23-page report for execs. Reports need a 1-page executive graphic.
- **Lesson 5 — know the news before the boss does.** Monthly retainer should
  include "this month's CVEs affecting YOUR stack" — that's a sellable
  retainer line item, and it's what keeps retainers renewed.

## 5. AI in security — what practitioners think (5 months old)

**Source: r/AskNetsec "AI-powered security testing in production—what's
actually working vs hype?"** — practitioners are skeptical of AI claims; the
things that hold: automated vuln discovery for business logic/API, false
positive rates matter, runtime validation, CI/CD integration. → Our AI
offering (agentos fleet + MCP service tools) should be pitched as
**automation of the repetitive 80%** (recon, re-scan, report assembly) with a
human on the deep findings — that's exactly what practitioners say works.

## 6. MCP security is live on Reddit RIGHT NOW

**Source: r/AskNetsec "For MCP servers, what can the config actually prove
about stability? 'Remote vs local' turned out backwards" (11 days old).**
MCP config security questions are being asked on AskNetsec TODAY — confirms
the T4 niche timing. First-mover content (writeup, test pack) is this
quarter, not next year.

## 7. Burnout warning (legit, repeated)

**Source: "Pentest Burnout — looking for advice" (66 pts).** Overlapping
clients + report writing after hours = the #1 solo burnout. → FIRM-PROPOSAL
must include: batch deliveries, capped concurrent engagements (2-3 max
solo), template-driven reports (section 2), and the weekly content block.

## What this changes in FIRM-PROPOSAL

1. Legal section gets the prison AMA as the standing example — tone policy
   becomes a written rule in the scope template.
2. Pricing becomes tier tables driven by a scoping questionnaire (contractual
   re-scope on asset-count growth).
3. Reports get: 1-page exec summary with $-framing + graphic; plain language
   for CEO readers.
4. Retainers include monthly "CVEs affecting your stack" brief.
5. Insurance + incorporation moved into the launch checklist (before first
   enterprise client).
6. Solo capacity: max 3 concurrent engagements; template-first reporting.
