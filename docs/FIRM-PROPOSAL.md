# FIRM-PROPOSAL — the solo security firm (full capture plan, 2026)

You, solo, running a **boutique security firm** — not a freelancer. A firm has
a brand, a site, content that sells for you 24/7, recurring revenue, and a
scope that scales when you're ready. This is the whole proposition.

## 1. Positioning

Boutique solo firm, 3 verticals — each bigger than the last:

| Vertical | Audience | Moat |
|---|---|---|
| **Web & server security** (T1/T2) | small shops, WordPress stores, e-commerce | many competitors, but they're agencies; solo = cheap + fast |
| **Game netcode security** (T3) | indie multiplayer devs | almost NO ONE offers this; your lab is purpose-built |
| **MCP/AI plugin security** (T4) | MCP server authors, AI tool builders | the 2026 gold rush; you have the attack lab + a real bug |

Engines already exist for all four (scan.py, nuclei/Docker, MCP attack kit,
game lab). You are 80% of the way to a real firm's capability.

## 2. The disclosure model — YOUR idea, done legally

"Expose weakness → report to admin → fix for charge" is a real business model
(called vulnerability-adjacent sales / white-hat research-to-remediation). But
unsolicited SCANNING of third parties is a crime in most countries (CFAA /
Computer Misuse Act class laws), even with good intent. So the firm runs the
model in **three legal shapes**:

1. **Free authorized assessment** (the sales engine): a cold-prospect gets a
   no-obligation entry scan (T1) — but ONLY after they accept a one-line
   scope form ("may I scan example.com?") . Acceptance = authorization.
   This is standard practice (every pentest firm's "free security check").
   Objection-killer: "Most shops take the same day."
2. **Responsible disclosure** (no scanning allowed, no contact from you first):
   ONLY if a weakness is visible WITHOUT attacking (publicly exposed config
   file, open admin page, no-auth endpoint you found passively/homepage-only).
   Publish per disclosure guidelines, offer fix AFTER they reply. Never
   brute force, never intrusion, never without the owner initiating.
3. **Paid authorized engagements** (your lab as PROOF): full T3/T4 audits
   with signed scope + liability wording. The lab runs the same playbook that
   produced FINDINGS-MCP-001 — against the customer's own relaxed targets
   with their blessing.

Rule engraved above the door: **acceptance before scanning, always.**
The firm's brand = "the ex-attacker who now fixes your game/MCP/website". That
story sells itself; never poison it with one unethical scan.

## 3. Service catalog + pricing (solo rates, honest for a solo firm)

### One-time
| Service | Deliverable | Price |
|---|---|---|
| T1 Website security check | scan.py + nuclei report, findings + fixes | $100-250 |
| T1 + fix ("secure my site") | scan + apply fixes + re-scan verified | $300-800 |
| T2 Server hardening | Lynis audit + checklist + applied hardening | $400-1200/server |
| T3 Game netcode review | protocol fuzz + cheat-class probes + fixes | $800-2500 |
| T4 MCP/AI plugin audit | endpoint + dispatch + prompt-injection pass + fixes | $500-1500 |
| Breach cleanup (post-incident) | remove malware, lock down, recovery plan | $500-3000 |

### Monthly retainer (the RECURRING engine — the real business)
| Plan | What | Price/mo |
|---|---|---|
| Watchdog-lite | monthly site scan + report + priority email | $50-100 |
| Watchdog+ | + server audit + WAF/CDN config check + monthly hardening | $150-300 |
| Embedded (up to a few) | retainer above + on-call response days + quarterly deep audit | $500-1000 |

Retainer math: 5 clients x $200/mo = $1,000/mo passive-ish recurring. 10 at
$300 = $3,000/mo. That's the firm surviving without hunting every month.

## 4. Capturing the whole field — the content engine

### The site stack (3 properties, one brand)
1. **Firm site** (main) — services, pricing, results (anonymized), scope/
   T&C template downloads (lead-gen content), contact.
2. **Niche hub #1: MCP security** (the differentiator) — attack lab writeups
   (FINDINGS-MCP-001 format), corpus downloads, free "MCP test pack",
   nuclei templates. Search-to-lead magnet for T4.
3. **Niche hub #2: game/server hardening** — the netcode lab content, ENet
   tips, free checklists. Magnet for T3 + T2.
   (Cheap: static/CMS, one shared design, run on your free hosting research.)

### YouTube — the capture multiplier
Three show formats, ~2/week, all from work you ALREADY do:
- **"Breaking my own server"** — live lab runs (game fuzz, MCP auth bypass).
  This is your differentiator: real footage of real bugs you then FIX.
- **"Harden this server"** — the T1/T2 checklist applied to a target
  (with owner's permission on camera), showing before/after scans.
- **MCP security short-form** — tool poisoning, description hygiene, the
  3% refusal stat, "your MCP server is open" — short, viral-able.
Content-to-contract funnel: YouTube/site → free checklist (email capture) →
free authorized T1 scan → paid audit/retainer.

### Reputation stack (compounds)
- GitHub: publish the MCP test pack + nuclei templates (you planned this in
  MONETIZE #6). Stars = trust signals on the firm site.
- Hacker profiles (Intigriti/HTB) with MCP flavor for credibility.
- Guest posts on AI/security newsletters.

## 5. Brand & assets to build (lightweight)

- Name (pick after discussion; 6-8 candidates), logo (simple), domain +
  email (name@firm). Everything static, $0-10/mo to run.
- Templates: **scope agreement** (THE legal artifact — you scan only what it
  lists), **proposal**, **report skeleton** (reconmap/APTRS style), **invoice**,
  **disclosure policy page**.
- A demo target (your own game server + a deliberately weak MCP server in
  Docker) for the "free check" sales call and videos — never demo on a
  stranger's box.

## 6. Firm backend (solo ops)

- **APTRS** (1.1k★, MIT) self-hosted — pentest reporting + client dashboard:
  tracks engagement → report → invoice state. The firm's backbone.
- **DefectDojo** later: vuln DB so repeat clients see "same finding fixed →
  recheck historical baseline" (retainer up-sell story).
- **AgentOS fleet + service MCP tools** (SERVICES-PLATFORM phase 2) — the
  "one customer = one sandboxed scan agent" scale lever once retainers stack.
- Legal hygiene day one (solo-firm reality): scope template (the big one),
  liability-limiting T&Cs (report wording = findings, not guarantee), later
  professional indemnity insurance before enterprise clients.
- Payments: invoices + a payment link (the FREE/no-card hosting research
  applies to your own stack too — keep firm costs near zero until revenue).

## 7. 90-day launch plan

```
Weeks 1-2:  brand (name/domain/email) + scope template + firm site skeleton
            + APTRS self-hosted. Publish FINDINGS-MCP-001 writeup (rep).
Weeks 3-4:  YouTube channel live (3-4 launch videos: MCP auth bypass demo,
            game fuzz run, "harden this server" ep 1 on YOUR server).
            Site content: 1 landing page per service + pricing.
Weeks 5-6:  Free authorized T1 scan offer (form = authorization). 2-3 free
            audits done for portfolio. Publish capsules of results (anonymized).
Weeks 7-8:  First paid engagement + first retainer sold (watchdog-lite).
            Set the "verified" re-scan loop into the delivery (SELF-LEARN).
Weeks 9-12: publish MCP test pack + nuclei templates (repo rep), 8 more
            videos, second niche site live. Review: what converts, kill what
            doesn't; aim: $500-1000/mo revenue + 1 committed retainer.
```

## 8. KPIs (what "it's working" means)

- 5 free scans offered/week, 2 accepted → 1 paid (25%+ conversion = real product)
- 2 retainers by day 90; $500-1000/mo recurring by month 4
- YouTube: 10 videos, 100+ subs, 3 "contact us" from viewers
- GitHub MCP test pack: 50+ stars (rep signal)
- Zero unauthorized-scan incidents (the only non-negotiable)

## 9. Honest risks (state them so they stay true)

1. **Legal line is absolute** — one unauthorized scan ends the firm. The
   scope-form discipline is operational, not optional.
2. **Solo capacity ceiling** — audits + content + sales is a lot; protect a
   weekly content block and batch deliveries. Hiring = only after retainers
   pay for it.
3. **Niche flooding** — MCP tooling commoditizes the *shallow* scan; the
   moat is manual deep audit + fixes + game netcode (they don't commoditize).
4. **Liability** — reports say "findings as of date on scope", always.
5. **Revenue timing** — disclose/rep takes weeks; burn-in content phase must
   not starve the delivery pipeline (do free audits WHILE content grows).

## 10. What to build next (in order)

1. ~~Scope-agreement + disclosure-policy templates~~ **DONE**
   (`tools/firm/templates/scope-agreement.md` + `pricing-questionnaire.md` —
   authorization-first, contractual re-scope, tone policy, liability wording;
   lawyer review before first paying client).
2. APTRS self-hosted instance (reporting backend).
3. Firm site skeleton (`tools/firm/site/` — static, one-page-per-service).
4. The 3 launch YouTube scripts (from existing lab footage/evidence).
5. MCP test pack + 3 nuclei MCP templates (open-source rep asset).
6. Free-scan sales one-pager (authorization form inside).