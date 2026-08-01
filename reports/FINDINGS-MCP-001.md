# FINDINGS-MCP-001 — MCP endpoint accepts requests with NO token (auth bypass)

**Date:** 2026-08-01 (21:05–21:06 local)
**Target:** `http://localhost:8765/mcp` — the user's live Flax editor MCP instance
**Test group:** Auth (M-01, M-02) — accidental live hit while validating lab tooling
**Severity:** HIGH (Position B — any same-user process can enumerate and invoke tools)
**Status:** OPEN

## Summary

The MCP HTTP endpoint processed JSON-RPC requests — including `tools/list` AND
`tools/call` dispatch-path requests — with **no `Authorization` header and no
`X-FlaxMcp-Token` header at all**. Expected behavior per `docs/MCP-SECURITY.md`
B1 + `TokenValidator.cs` doctrine: fail-closed 401 when token is absent/mismatched.

## Evidence (facts only)

All requests: `POST http://localhost:8765/mcp`, `Content-Type: application/json`,
NO auth headers. Server: `Microsoft-HTTPAPI/2.0` (HttpListener).

| # | Request | Status | Response (excerpt) |
|---|---|---|---|
| 1 | `tools/list` (no auth) | **200** | `{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"tool/activation_hint",...` — full 6-tool list returned (17062 bytes) |
| 2 | `tools/list` (wrong token `wrong`) | **200** | same full tools list |
| 3 | `tools/list` (wrong token `AAA...32x`) | **200** | same full tools list |
| 4 | `tools/call` name=`zz_no_such_tool` (no auth) | **200** | dispatch pipeline ran: `{"result":{"isError":true,"structuredContent":{"error":{"code":"unknown_tool",...` — proves tools/call reaches the dispatcher pre-auth |
| 5 | `tools/call` name=`tool/inspect` args=`{name:...}` (no auth) | **200** | argument validation ran: `"invalid_arguments", 2 validation error(s): 'key' is required...` — proves argument-validation layer is pre-auth too |
| 6 | `GET /openapi.json` (no auth) | **500** | `{"error":"generation_failed"}` — endpoint reachable without auth; also unhandled failure |
| 7 | `GET /health` (no auth) | 200 | `{"name":"flax-mcp","kernelLoaded":true}` (by-design public health — fine) |
| 8 | `GET /mcp` (no auth, no SSE accept) | 404 | `"Mcp-Session-Id missing or unknown; call initialize first."` |

Control checks (same session): spoofed `Origin` (7 variants, incl. `https://evil.example`)
→ all **403** (OriginValidator works). Bad HTTP methods (HEAD/PUT/PATCH/OPTIONS) → 405.

Tools exposed without auth (from evidence file `noauth-tools-list.json`):
`tool/activation_hint`, `tool/by_capability`, `tool/get_relevant_tools`,
`tool/health`, `tool/inspect`, `tool/recent`.

## Expected vs actual

- Expected (M-01): no token → 401 / fail-closed. **Actual: 200 + full tools list.**
- Expected (M-02): wrong token → 401, no existence oracle. **Actual: 200 + full tools list.**
- Expected (M-18): OpenAPI 200-schema-only or 404. **Actual: 500 `generation_failed`** (secondary issue: unhandled error path).

## Analysis (hypotheses, unverified)

1. `FLAXMCP_TOKEN` is unset in the editor's environment AND the HTTP layer does
   not enforce the documented fail-closed rule (TokenValidator may be wired to
   a different surface, or the /mcp listener has an auth bypass — e.g. auth
   only on some paths, or the token check short-circuits when unset).
2. `FLAXMCP_TOKEN` is set but the token check is not attached to the
   `HttpListener` request pipeline (e.g. checked only for certain methods).

Distinguishing test: `--env-probe` (child inherits token?) + asking the user to
confirm whether `FLAXMCP_TOKEN` is set in the editor's launch environment.

## Impact (Position B reality check)

Any same-user process on the dev box (or malware running as the same user)
can, today: enumerate all tools, read schemas/descriptions, and issue
`tools/call` requests. Whether dangerous actions are still blocked downstream
(Policy gates, intent, dry-run) is a second layer — the auth layer is
currently bypassed entirely. Same-user env reads are inherent to Windows, so
auth is the load-bearing control here.

## Recommendation

1. Patch `McpHttpServer.cs` / request pipeline: enforce `TokenValidator`
   (Bearer or X-FlaxMcp-Token, FixedTimeEquals) at the top of the listener
   handler for ALL methods and ALL paths under the listener (not just /mcp
   POST), fail-closed 401 when unset. (User repo — needs user approval to edit.)
2. `/openapi.json` generation failure should return a structured 4xx/5xx
   without `generation_failed` body leakage — or the endpoint should 401/404
   pre-auth.
3. Re-run Auth group after patch (regression: M-01..M-06 must pass).

## Control linkage

- `docs/MCP-SECURITY.md` B1 (loopback endpoint auth — "already good: ... [check] gaps" — this finding closes the check)
- `docs/MCP-ATTACK-LAB.md` M-01, M-02, M-18

## Evidence files

- `reports/FINDINGS-MCP-001/noauth-tools-list.json`
- `reports/FINDINGS-MCP-001/noauth-call-unknown-tool.json`
- `reports/FINDINGS-MCP-001/noauth-call-validation-error.json`
