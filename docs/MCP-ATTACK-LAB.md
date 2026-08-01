# MCP-ATTACK-LAB — attacking the MCP plugin from the outside

**Goal:** treat the user's MCP plugin (FlaxMCP, to be sold one day) as the
target of a lab, exactly like the game server: real attack tooling, a test
matrix, findings reports. Defense map lives in `MCP-SECURITY.md`; this doc is
the attacker side.

**Stance (same doctrine as the game lab):** attacks run against a local test
instance on the lab machine; nothing is done to third parties; findings are
reported to the user's own codebase.

## 1. What "outside" means for an editor-only MCP

The MCP kernel is `#if FLAX_EDITOR` — it only exists in the editor, bound to
`http://localhost:8765/mcp` via `HttpListener` (System.Net). That makes the
threat surface different from the game server:

| Position | Who | Realistic? |
|---|---|---|
| A. External network | anyone on the internet | Only if the user tunnels/opens 8765 (forbidden by MCP-SECURITY B4 — test anyway what a hostile network sees) |
| B. Same-machine process | malware / other users on the dev box | YES — the realistic external-ish case. Token lives in `FLAXMCP_TOKEN` env (any same-user process can read it — TokenValidator.cs documents this). Also: `:9100` Prometheus + OpenAPI on 8765 |
| C. The AI assistant | the LLM connected to the MCP | YES — the most probable real attack: prompt injection through game content → tool calls |
| D. Malicious project content | a game project the plugin opens (mods, downloaded assets, `flaxmcp-plugin.json`, models) | YES — buyer installs a modded project; plugin must not execute its content |
| E. License/thief | someone buying/redistributing the plugin | shipping + assembly-tamper check (MCP-SECURITY surface C) |

## 2. Attack surface map (grounded)

- `http://localhost:8765/mcp` — MCP HTTP/SSE transport (HttpListener)
- OpenAPI generator on the same listener (`OpenApiGenerator.cs`, enumerates tools)
- `:9100` Prometheus metrics + TelemetryDumpService (`FLAXMCP_METRICS_PORT`)
- Auth: `TokenValidator` — `Authorization: Bearer` or `X-FlaxMcp-Token`,
  `FLAXMCP_TOKEN` env, FixedTimeEquals, fail-closed when unset
- `OriginValidator` — origin check
- Tool dispatch: `ToolDispatcherCore` + Policy gates (Safe/Mutating/Destructive)
  + `ToolArgs` validation + `LlmIntentSieve` guardrail + `ProjectPathGuard` +
  `ProviderUrlGuard` + `CSharpDenylist` + description normalizer (ADR-057)
- Boot/plugin loading: `BootOrchestrator.PluginManifestDirs`, `BucketLoader`,
  `DeployManifest`, `install-plugins.ps1`, templates (`FlaxMcp.Templates`)
- Model/receipt loading: MANIFEST + sha256 receipts + `OnnxRuntimeNativeProbe`

## 3. Lab tooling (new, in this repo's `tools/`)

```
tools/mcp-attacker/
├── mcp_attack.py        — raw HTTP/SSE attacker client, modes:
│                          --no-token | --wrong-token | --origin-spoof
│                          --method-fuzz | --arg-bombs | --batch
│                          --flood (parallel conns) | --sse | --openapi
│                          --timing (FixedTimeEquals timing check)
│                          --env-probe (read FLAXMCP_TOKEN from a
│                           sibling process env block — Position B)
├── fuzz_mcp.py          — boofuzz HTTP target for the JSON-RPC endpoint
│                          (reuses tools/boofuzz/.venv)
├── mcp-server-fuzzer/   — vendored Agent-Hellboy/mcp-server-fuzzer (MIT,
│                           §8): automated tool-arg + protocol-type fuzzing
└── injection-corpus.json — prompt-injection strings (Position C), tagged
                            by vector: tool_call / policy_override /
                            token_steal / context_poison / chain_tools /
                            tool_poisoning / rag_injection / memory_exploit
scripts/mcp-attack-run.ps1 — orchestrator: start test instance → run mode
                            groups → capture responses → write
                            reports/FINDINGS-MCP-xxx.md (abuse-template style:
                            facts-only, evidence, expected vs actual)
```

## 4. Test matrix (case / how / expected secure behavior)

### Auth (M-01..M-06)
- M-01 no token → 401 / fail-closed (server refuses requests when `FLAXMCP_TOKEN` unset)
- M-02 wrong token → 401; neither header leaks whether token exists
- M-03 both header forms accepted; `X-FlaxMcp-Token` casing variants rejected (Ordinal)
- M-04 timing: measure response latency over many bad tokens → FixedTimeEquals holds (~flat)
- M-05 token never appears in NDJSON logs / tool results / OpenAPI output
- M-06 same-user env read: sibling process can read `FLAXMCP_TOKEN` (known risk —
  document, and verify a spawned-child process also inherits it: users launch
  editor from shell → token visible; mitigation note: launch-as-different-user)

### Transport (M-10..M-20)
- M-10 wrong Origin / spoofed Origin header → rejected by OriginValidator
- M-11 GET /mcp, HEAD, PUT, DELETE → structured 405, no dispatch
- M-12 malformed JSON-RPC (garbage, wrong types, missing id/jsonrpc) → structured
  error; server survives (no 5xx crash)
- M-13 unknown methods / tool-name typos → error, never dispatches
- M-14 batch JSON-RPC → bounded; each item validated independently
- M-15 giant payload (100MB) / content-length mismatch / chunked weirdness →
  bounded read, error, listener survives (HttpListener DoS check)
- M-16 connection flood → accept loop stays alive; UnloadRegistry port-conflict
  path not triggered
- M-17 SSE: hijack attempt, mid-stream disconnect, replay of session id → no
  cross-session data
- M-18 OpenAPI endpoint → returns tool list (by design) but NO paths, tokens,
  or project data beyond the schema
- M-19 `:9100` metrics → aggregate-only (RoutingTelemetry doctrine); no session
  content, no paths, no tokens
- M-20 idempotency: same request replayed twice → same result, no side effect
  (correlation IDs on logs)

### Tool dispatch (M-30..M-38)
- M-30 arg bombs: giant strings, deep nesting, wrong types, missing required,
  extra unknown args → ToolArgs validation rejects before dispatch
- M-31 path traversal in file tools (`..`, absolute, UNC, junction/symlink) →
  ProjectPathGuard + junction guard reject (repo tests exist — mirror them
  over HTTP)
- M-32 destructive tool without intent → Policy gate blocks (missing-intent);
  `mutation/dry_run` never executes
- M-33 tool-result size bombs (tool that returns huge output) → truncated/bounded
- M-34 self/recursive tool calls, tool-to-tool chains with args from attacker →
  bounded depth, no privilege escalation
- M-35 `ProviderUrlGuard`: attacker-injected `downloadUrl=http://127.0.0.1:8765/...`
  → blocked (guard exists — prove over HTTP)
- M-36 `CSharpDenylist`: script tool attempts `HttpListener`/`Process`/net refs →
  denylist blocks (tests exist; add a remote attempt)
- M-37 prompt-injection corpus (Position C): game-content strings that instruct
  the assistant to call destructive/chain tools → LlmIntentSieve + Policy
  neutralize; tool never fires on content alone
- M-38 context poison: injected content that tries to make the assistant dump
  tool schemas/keys → descriptions redact; token stays out of context

### Supply chain / content (M-40..M-44)
- M-40 malicious `flaxmcp-plugin.json` (bad assembly path, big assemblies list,
  manifest poisoning) → BucketLoader rejects / bounded
- M-41 tampered model files (sha256 mismatch) → receipt verification fails,
  status token = model_load_failed, graceful degrade (ONNX doctrine)
- M-42 malicious template payload via install-plugins → template trust root
  documented; deploy acceptance hash check holds
- M-43 project with hostile `.cs` (modded sample) → compile gate + denylist
  (editor CS errors block, not execute)
- M-44 license/theft: redistributed DLL → assembly hash verify + docs on
  activation; note honestly what DRM cannot do

## 5. Findings format

`reports/FINDINGS-MCP-001.md` per run: case id, command/mode, evidence
(response codes, logs excerpt, timing table), expected vs actual, severity,
link to MCP-SECURITY.md control, recommendation. Facts-only, no red team drama.

## 6. Honest limitations

1. **Cannot fully test Position A externally** — the endpoint binds loopback;
   we test the same code paths via localhost, and document the "never tunnel"
   rule as the real control (B4).
2. **Editor-only**: attacker value of a sold plugin is limited to the buyer's
   dev machine + their AI; game builds ship no MCP at all (`#if FLAX_EDITOR`).
3. **Timing tests** are noisy on shared machines; use repeated runs + medians.
4. Some cases (M-06 env read) are inherent to Windows process env; the fix is
   operational (launch separation), not code.
5. The LLM itself (Position C) lives outside the plugin — we can only harden
   the interface the plugin exposes and the context it feeds.

## 7. Order of work

1. Build `tools/mcp-attacker/mcp_attack.py` + `fuzz_mcp.py` + corpus (lab);
   vendor `mcp-server-fuzzer` (§8) into `tools/mcp-attacker/`.
2. `scripts/mcp-attack-run.ps1` orchestrator.
3. Run Auth + Transport groups against the user's running editor session
   (needs the user's machine, editor open) — first findings.
4. Tool-dispatch group (needs editor + game project loaded).
5. Injection corpus pass against LlmIntentSieve (needs LLM plugin configured).
6. Supply-chain group (repo-only, no editor needed) — incl. `mcp-audit`
   offline scan of the shipped `flaxmcp-plugin.json` + templates.
7. Each finding → patch in flax-mcp repo (with permission) → re-run group.

## 8. External arsenal — researched tools to fold in (verified 2026-08-01)

Second research round: aggressive GitHub tools + the OWASP MCP Top 10, mapped
onto the M-01..M-44 matrix. Nothing here is new code yet — these are the
candidates the tooling section pulls from.

| Tool | Health / license | What it gives us | Maps to |
|---|---|---|---|
| OWASP MCP Top 10 | owasp.org/www-project-mcp-top-10 + nest.owasp.org/projects/mcp-top-10 (2026) | canonical threat list — named items verified: **agentic misbinding** (AI tricked into calling the wrong server) + **context spoofing** | gap-check M-01..M-44; propose new cases (M-45 misbinding — hostile project declaring a lookalike endpoint; M-46 context spoofing depth) |
| mcp-server-fuzzer (Agent-Hellboy) | MIT, 33★/319 commits, active; async, built-in safety system, Docker | automated **tool-arg fuzzing** + **protocol type fuzzing** against `localhost:8765/mcp` — the workhorse of the transport group | M-12..M-16, M-30 |
| mcp-attack-labs (aminrj-labs) | created 2026-02-26, 16★; hands-on lab recipes | attack recipes: **tool poisoning → silent file exfiltration**, DockerDash, RAG injection, agentic memory exploitation — feed `injection-corpus.json` | M-30..M-38 (esp. M-37/M-38) |
| mcpguard (GT-Projects256) | MIT, 7★ | OWASP-MCP-Top-10-mapped scanner/firewall with runtime policies + audit logs — read as a **hardening checklist cross-ref** (MCP-SECURITY), not an attack tool | cross-ref MCP-SECURITY hardening checklist |
| mcp-audit (adudley78) | Apache 2.0, mcp-audit.dev | offline MCP config scanner — run against shipped `flaxmcp-plugin.json` + templates + installer output; no editor needed | M-40..M-44 |
| ai-red-team-toolkit "Fracture" (cinder-security) | MIT, 2★ | autonomous AI red-team engine (fingerprint / extract / memory modules) — automated Position-C campaigns once the LLM plugin is configured | M-37, M-38 |
| practical-devsecops.com/mcp-security-vulnerabilities (2026-01-04) | article | prompt-injection + tool-poisoning prevention technique breakdown → corpus strings + expected-behavior wording | M-37 |
| guardrly.com/blog/mcp-injection-attacks-defense-guide (2026-05-18) | article | tool-poisoning exfiltration walkthrough (attacker crafts a tool description so the assistant hands over user data) → corpus + M-38 redaction checks | M-37, M-38 |

### How each folds into the lab
1. **mcp-server-fuzzer** — vendor into `tools/mcp-attacker/mcp-server-fuzzer/`
   (clone or submodule, MIT). Run against `http://localhost:8765/mcp` with the
   lab token, local editor only (Position B discipline — never against a
   tunneled endpoint). Its built-in safety system + our loopback-only rule is
   the guardrail.
2. **mcp-attack-labs** — technique library, not a dependency: extract the
   recipes into `injection-corpus.json` with new tags (`tool_poisoning`,
   `rag_injection`, `memory_exploit`) so M-37/M-38 have real attacker strings.
3. **mcp-audit** — offline run in the supply-chain group (no editor needed):
   point it at `flaxmcp-plugin.json` + `FlaxMcp.Templates` output, treat its
   findings as M-40..M-44 evidence.
4. **Fracture** — optional Position-C automation; defer until the LLM plugin
   is configured and the manual corpus pass (step 5) has run once.
5. **OWASP MCP Top 10** — gap-check after the first findings: propose new
   M-cases (M-45 misbinding, M-46 context spoofing) rather than assuming the
   matrix is complete.
