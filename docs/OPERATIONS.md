# OPERATIONS — the lab's operating model (flows, toolchain, cadence)

This repo is an operations center for two targets. Everything below is the
day-to-day loop; details live in the linked docs.

## The two attack flows

| | Game server (ENet UDP 7777) | MCP plugin (localhost:8765) |
|---|---|---|
| Runbook | `docs/PLAYBOOK-GAME.md` | `docs/PLAYBOOK-MCP.md` |
| Orchestrator | `scripts/attack-run.ps1` | `scripts/mcp-attack-run.ps1` |
| Attack client | `tools/raw-client/flax_enet.py` | `tools/mcp-attacker/mcp_attack.py` |
| Fuzzer | `tools/boofuzz/fuzz_enet.py` (+radamsa) | `tools/mcp-attacker/fuzz_mcp.py` + vendored `mcp-fuzzer` |
| Dissector/scan | `tools/dissector/flax_enet.lua` (Wireshark) | `tools/mcp-attacker/mcpwn/`, corpus, snyk-agent-scan |
| Findings | `reports/run-<ts>/` | `reports/FINDINGS-MCP-<nnn>/` |
| Status | S0 core built; fuzz/attack phases pending live server | Auth group FAILS live (FINDINGS-MCP-001) |

## Phases per target (full detail in the playbooks)

Game: **0 recon → 1 auth probes → 2 protocol fuzz → 3 cheat-class probes →
4 DoS → 5 report/patch/rerun**
MCP: **0 surface map → 1 auth → 2 transport → 3 dispatch → 4 Position C →
5 supply chain → 6 report/patch/rerun**

## Toolchain map

```
tools/raw-client/       ENet wire client (stdlib, zero engine deps)
tools/boofuzz/          boofuzz venv + fuzz_enet.py (game) ; fuzz_mcp.py runs from mcp-attacker
tools/mcp-attacker/     mcp_attack.py (13 modes) · fuzz_mcp.py · injection-corpus.json
                        fake_mcp_server.py (kit validation mirror)
                        vendored: mcp-server-fuzzer/ · mcp-poisoning-poc/ · mcpwn/
tools/dissector/        flax_enet.lua Wireshark dissector
tools/self-learn/       harvest.py (the learning loop)
scripts/                attack-run.ps1 · mcp-attack-run.ps1 · learn.ps1
reports/                run-<ts>/ (game) · FINDINGS-MCP-<nnn>/ (MCP) · evidence JSON
docs/                   specs · playbooks · tricks · build guides (index: README.md)
```

## Cadence (the loop that makes this work)

1. **Run** a phase from a playbook (always against the lab instance).
2. **Report** — facts-only findings, evidence files, severity, control link
   (template: `reports/FINDINGS-MCP-001.md`).
3. **Learn** — `python tools/self-learn/harvest.py` → `docs/LEARNING-LOG.md`
   (coverage + next suggested tests).
4. **Patch** (with user permission, in the game repo) → **re-run the failing
   group** → 2 clean runs graduates it (SELF-LEARN rule 4).
5. **Keep the arsenal fresh** — new research rounds fold into `docs/ARSENAL.md`
   parts + `docs/TRICKS.md` (sourced entries only, no fluff).

## Self-learning system

`docs/SELF-LEARN.md` — harvest reports → LEARNING-LOG → next-test suggestions;
rules: facts-only, re-run after patch, escalate severity on clean groups,
never trust a single run, new surface = new group.

## Building better (the defensive half)

- `docs/BUILD-GAME-SERVER.md` — authoritative server, hardened wire, budgets,
  layered detection, ops topology.
- `docs/BUILD-MCP-PLUGIN.md` — listener-wide fail-closed auth, description
  hygiene, dispatch gates, session model, least-surface endpoints.
- Every build guide section starts from a real attack technique (TRICKS.md)
  and an acceptance test in the M/G matrix.

## Next actions (in order)

1. **MCP**: user opens editor (it IS running) → run full Auth group re-check +
   Transport group (`scripts/mcp-attack-run.ps1 -Group all`) — FINDINGS-MCP-001
   is the first patch candidate in the user repo (with permission).
2. **MCP**: decide the auth fix with the user (TokenValidator wiring) →
   re-run auth group → FINDINGS-MCP-002.
3. **Game**: start the lab server → Phase 0/1 recon → first game findings.
4. **Learn**: harvest after every run; monthly ARSENAL review.
