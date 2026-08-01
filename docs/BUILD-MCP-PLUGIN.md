# BUILD-MCP-PLUGIN — how to build a better MCP plugin (defense cookbook)

Written from the attack side: every section starts from a technique in
TRICKS.md / an M-case, then the fix. First live finding this applies to:
**FINDINGS-MCP-001 — /mcp answers tools/list + tools/call with NO auth.**

## 1. Auth at the listener, for everything, fail-closed

(FINDINGS-MCP-001; TRICKS B13.) One check at the top of the HTTP handler:
Bearer or X-FlaxMcp-Token, FixedTimeEquals, 401 when missing OR mismatched —
for ALL methods (POST/GET/HEAD...) and ALL paths under the listener. Auth on
a middleware for "tools/list only" is a bypass. When `FLAXMCP_TOKEN` is
unset: refuse (fail-closed), never serve open.

## 2. Descriptions are model input — treat them as hostile

(Tool poisoning, TRICKS B9-B12; OWASP MCP Top 10; invariantlabs.) The
description field of a tool is read by the LLM with near-instruction weight.
- Scan every tool name/description/param doc for injection patterns:
  imperative overrides ("ignore", "always", "priority message"), base64
  blobs (`[A-Za-z0-9+/]{20,}={0,2}`), hidden instruction markers after
  `\n\n`, references to secrets/sensitive paths.
- Normalize descriptions (ADR-057 description normalizer) — strip anything
  that isn't a plain capability statement.
- Pin + re-verify descriptions at install and periodically (rug-pull
  defense; snyk-agent-scan / mcp-audit do this offline).
- **Tool shadowing**: reject tool names that collide with built-ins or each
  other (AgentDefenders/mcp-scan "shadowing" analyzer).

## 3. Dispatch gates, not just auth

(Our M-30..M-38; Policy gate design.) After auth: ToolArgs validation
(schema, types, depth, size) → Policy tiers (Safe/Mutating/Destructive,
intent required, dry-run for destructive) → path guards (ProjectPathGuard:
no `..`, absolute, UNC, junction/symlink escape) → URL guards (ProviderUrlGuard:
no loopback/private/metadata endpoints 169.254.169.254) → code denylist
(CSharpDenylist) for script tools. Every layer rejects before any side effect.

## 4. The session model

(Our M-17.) Sessions must: be issued via initialize only, be bound to one
client (id + transport), expire, and never be forgeable (server-side random,
not client-chosen). Session id missing/unknown → JSON-RPC error, never a
fallback to anonymous. (GET /mcp currently returns a JSON-RPC error for
missing session — good; but the POST path bypasses sessions entirely today.)

## 5. Endpoints: least surface, structured errors

- `/health` public OK (that's the point), but: no version details that help
  attackers pick exploits.
- `/openapi.json` (or whatever the generator mounts): auth-gated, schema-only
  (no paths beyond /mcp, no tokens, no project data), and failures return
  structured 4xx — never raw `{"error":"generation_failed"}` (FINDINGS-MCP-001).
- Metrics (`:9100`): aggregate-only (RoutingTelemetry doctrine), no session
  content, no paths, no tokens.
- Never tunnel the MCP port (MCP-SECURITY B4) — the whole auth discussion is
  academic if a tunnel exposes Position A.

## 6. Supply chain (buyers download the plugin)

- Hash-verified loads: assemblies + models with sha256 receipts (MANIFEST),
  graceful degrade on mismatch (model_load_failed status token).
- `flaxmcp-plugin.json`: validate assembly paths (no absolute/UNC/..),
  bound assembly list size, reject manifest poisoning (M-40..M-44).
- Templates: trust root documented, deploy acceptance hash check.
- Watch out: scan-path hygiene (don't glob user dirs for plugins).

## 7. Test every release with the lab

The M-matrix (M-01..M-46) is the regression suite: auth group must fail
closed, transport group must survive fuzz (boofuzz probe oracle), dispatch
group must reject all bomb payloads, corpus pass must not move the assistant
(M-37/38), supply-chain scans must be clean. Two consecutive clean runs
graduate a group (SELF-LEARN rule 4).
