# SERVICES-PLATFORM — turn the lab into a security services business

The repo stops being just your lab: it becomes the **delivery engine** for
security hardening services (servers, services, websites). You already own
the hardest part — an attack lab that knows how these targets break. Now we
productize it: scan → findings → fix → verify, as a repeatable service.

## 1. Service tiers (what you sell)

| Tier | Offer | Engine (already in repo) | Output |
|---|---|---|---|
| T1 Website check | WordPress/store/site security review (the Flatsome case) | `tools/services/scan.py` + nuclei + wpscan + ZAP | findings report (evidence+fix) |
| T2 Server hardening | Linux/Windows server audit + hardening | Lynis (audit) + checklist (BUILD-GAME-SERVER) | audit report + fix plan + rescan |
| T3 Game server hardening | our own game: auth w/ envelope, tripwires, budgets, sentinel | the whole lab (S0 core, PLAYBOOK-GAME) | verified hardened build |
| T4 MCP/AI plugin hardening | the product you sell + buyer hardening | MCP-ATTACK-LAB + BUILD-MCP-PLUGIN + FINDINGS-MCP-001 fix | patch + regression pass |

One engine, four products. T1 = easiest first sale; T4 = differentiator
nobody else offers yet.

## 2. Platform architecture (the "bigger" part)

```
customer ──> (authorized) ──> services API / CLI
                                 │
                    ┌────────────┼──────────────┐
                    ▼            ▼              ▼
             scan agents      fuzz agents    audit agents
             (nuclei, ZAP,   (fuzzd, mcp-    (Lynis, scan.py,
              wpscan,        attacker kit,   headers/TLS/ports)
              scan.py)       boofuzz)
                    │            │              │
                    └──► unified findings JSON (abuse-style: check/sev/
                         evidence/expected/actual/fix)
                              │
                     ┌────────┴─────────┐
                     ▼                  ▼
              DefectDojo/Tracecat    report.md per customer
              (findings mgmt + AI    (prose template)
               agent workflows)
                              │
                     fix-plan (per finding, per service tier)
                              │
                     re-scan → verified (2 clean runs, SELF-LEARN rule)
```

## 3. The fleet + agents + MCP layer (your "stronger fleet / agents / mcps")

- **Agent fleet — agentos (rivet-dev/agentos, 4.4k★, Apache-2.0):** "an
  operating system for agents as a library" — sandboxes agents in WASM/V8
  isolates, no VMs. This is how a scan/fix agent runs per customer WITHOUT
  owning the host. One agent per customer per job; crash = isolated.
- **AI ops bridge — hexstrike-ai (10.9k★, MIT):** MCP server wrapping 150+
  security tools; lets ME (the LLM operator) run the whole pipeline via MCP
  tool calls instead of one-line CLIs. Also `pentest-ai` (vendored) +
  Tracecat (agent SOAR) as the workflow orchestrator.
- **MCP tools we build (service-native, per customer):** `service_scan`
  (run scan.py/nuclei for a target), `service_report` (gen customer report),
  `service_verify` (re-scan a fixed finding), `service_status` (fleet health).
  Modeled on the manage_security mega-tool pattern we already spec'd.
- **Existing assets get absorbed:** our mcp_attack.py modes, injection corpus,
  fuzzd/mcp-fuzzer all become "audit packs" the fleet runs against a customer
  asset on approval.

## 4. The delivery loop (productized SELF-LEARN)

```
1. authorize target (customer signs off - MANDATORY)
2. scan (appropriate tier engine)
3. findings JSON -> DefectDojo/CSV per stage
4. human-reviewed fix plan (evidence-linked, per finding)
5. patch/apply (we only apply what's in the fix plan)
6. re-scan -> verified
7. report.md (customer-facing): summary, sev counts, fixes applied, residual
8. harvest: every engagement feeds LEARNING-LOG + a per-customer baseline
```

## 5. Risks, honestly

- **Authorization is the law.** Only scan what the customer owns/approved —
  blanket scanning gets this business sued. Include a signed scope doc +
  our "authorized targets only" label in every tool.
- **Liability vs value.** We deliver findings + verified fixes on a scope; we
  do NOT guarantee "unhackable". Report residual risk; avoid absolute claims.
- **Credential/secret handling.** Findings can contain secrets (tokens in
  responses). Escalate-not-log on secret material (same scrubbing rule as
  DossierWriter).
- **Tier 3/4 are your own software** — fastest to sell because you control
  the full stack and have the lab proof.
- **Compliance angle** (future): Lynis + CIS benchmarks give you ISO27001/
  PCI-DSS-aligned checklists = enterprise pricing, not freelancer pricing.

## 6. MVP path (do this week)

1. `scan.py` works (done, tested on example.com) — T1 deliverable exists.
2. Wrap nuclei (Docker route — official `projectdiscovery/nuclei` image, no
   native binary per user decision) via `tools/services/nuclei-docker.ps1` +
   `scan.py` + report — one command per customer site on the deploy host.
3. Demo report on a real site you own (or Flatsome staging) to a
   prospective customer.
4. Add T2 Lynis checklist template; T4 = fix FINDINGS-MCP-001 as the first
   paid-form harden job.
5. Fleet (agentos) + MCP bridge = phase 2, once 2-3 customers exist.

## 7. What to build next (in order)

1. `tools/services/service-run.ps1` — one-command site scan+nuclei+report.
2. `tools/services/README.md` — operator doc for the service engine.
3. DefectDojo local instance (docker) — findings tracking for >3 customers.
4. agentos sandboxed scan agent + the 4 service MCP tools above.
5. Lynis port (run on customer Linux hosts; agentless remote or agent).