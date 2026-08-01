# PLAYBOOK-MCP — attack flow for the MCP plugin (localhost:8765)

End-to-end flow for the plugin (the product-to-be-sold). Doctrine: local
editor instance ONLY; never a tunneled endpoint; probe-before-dispatch
(TRICKS C22) — read-only and non-dispatchable payloads until explicit
authorization. Findings: `reports/FINDINGS-MCP-<nnn>/`. First live finding
already exists: **FINDINGS-MCP-001 (no-auth tools/list + tools/call reachable)**.

## Phase 0 — Alive + surface map (read-only)

```
python tools/mcp-attacker/mcp_attack.py --mode endpoints    # what else serves on 8765
python tools/mcp-attacker/mcp_attack.py --mode openapi      # OpenAPI probe (note: /openapi.json = 500 generation_failed)
python tools/mcp-attacker/mcp_attack.py --mode sse --token $env:FLAXMCP_TOKEN   # SSE behavior + session id
```

Output: endpoint inventory, OpenAPI status, SSE/session shape. This is where
new live servers are discovered — the first run is always this.

## Phase 1 — Auth group (M-01..M-06)

```
python tools/mcp-attacker/mcp_attack.py --mode no-token --count 8
python tools/mcp-attacker/mcp_attack.py --mode wrong-token --count 16
python tools/mcp-attacker/mcp_attack.py --mode timing --token $env:FLAXMCP_TOKEN --count 80
python tools/mcp-attacker/mcp_attack.py --mode env-probe
```

Expected: 401 fail-closed on no/wrong token; flat timing; env-probe documents
the inherent Windows same-user env read. **Current status: FAILS (see
FINDINGS-MCP-001).**

## Phase 2 — Transport group (M-10..M-20)

```
python tools/mcp-attacker/mcp_attack.py --mode origin-spoof          # M-10/11 (currently PASSES: 403)
python tools/mcp-attacker/mcp_attack.py --mode method-fuzz           # M-11
python tools/mcp-attacker/mcp_attack.py --mode batch --token $env:FLAXMCP_TOKEN
python tools/mcp-attacker/mcp_attack.py --mode flood --token $env:FLAXMCP_TOKEN --concurrency 64
python tools/mcp-attacker/mcp_attack.py --mode sse --token $env:FLAXMCP_TOKEN
# deeper protocol fuzz:
..\boofuzz\.venv\Scripts\python.exe tools/mcp-attacker/fuzz_mcp.py --port 8765 --cases 800
# vendored heavy fuzzer (HTTP mode):
tools/mcp-attacker/.venv/Scripts/mcp-fuzzer.exe --mode all --phase both --protocol http --endpoint http://localhost:8765/mcp --enable-safety-system
```

Boofuzz has a built-in liveness probe (CRASH oracle). `mcp-fuzzer` writes
`findings.json` using the canonical taxonomy (TRICKS B15) — map its categories
onto M-cases in the report.

## Phase 3 — Tool dispatch (M-30..M-38)

```
python tools/mcp-attacker/mcp_attack.py --mode arg-bombs --token $env:FLAXMCP_TOKEN
python tools/mcp-attacker/mcp_attack.py --mode arg-bombs --token $env:FLAXMCP_TOKEN --tools tool/inspect,tool/health
```

Dispatch probes use validation-rejectable payloads first (unknown tool,
invalid args — safe), then authorized full-dispatch tests for Policy-gate
checks (M-32 destructive intent, M-35 ProviderUrlGuard, M-36 denylist).

## Phase 4 — Position C (AI assistant) — corpus pass

Corpus: `tools/mcp-attacker/injection-corpus.json` (C01-C15, tagged vectors).
Method: feed corpus strings into the assistant via game-content channels
(modded sample project content, model/asset text) and observe whether
LlmIntentSieve + Policy gates + description hygiene hold (M-37/M-38). Requires
the LLM plugin configured; manual pass first, then optional automation
(cinder Fracture-style).

## Phase 5 — Supply chain (offline, no editor needed)

```
# vendored mcpwn scanner (M-40..M-44):
cd tools/mcp-attacker/mcpwn && pip install -r requirements.txt   # once
python mcpwn.py <config-or-endpoint>                             # per its README
# metadata poisoning scan (snyk-agent-scan, run via uvx when available):
uvx snyk-agent-scan@latest --json --format sarif .  # scans MCP configs on machine
```

Also: audit `flaxmcp-plugin.json` + `FlaxMcp.Templates` output by hand
(checklist in TRICKS B9-B12), model receipts (sha256), assembly hashes (M-41).

## Phase 6 — Report → patch → re-run (the loop)

1. Each run: `scripts/mcp-attack-run.ps1 -Group <auth|transport|dispatch|supply-chain|all> -Token $env:FLAXMCP_TOKEN` → `reports/FINDINGS-MCP-<ts>/mode-*.jsonl`.
2. Write `FINDINGS-MCP-<nnn>.md` (evidence files alongside, FINDINGS-MCP-001 as the template).
3. Patch in flax-mcp repo (with user permission) → re-run the failing group.
4. `python tools/self-learn/harvest.py` → LEARNING-LOG.md (M-group coverage + next tests).

## Current status board

| Group | Status | Evidence |
|---|---|---|
| Auth (M-01/02) | FAIL — no-token/wrong-token → 200 + full tools list | FINDINGS-MCP-001 |
| Origin (M-10/11) | PASS — 403 on all spoofed origins | FINDINGS-MCP-001 control checks |
| OpenAPI (M-18) | WEAK — /openapi.json → 500 generation_failed (no auth) | FINDINGS-MCP-001 |
| Health (discovery) | open by design | FINDINGS-MCP-001 |
| Transport fuzz / dispatch / corpus / supply chain | not yet run | — |
