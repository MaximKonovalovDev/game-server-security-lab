# HANDOFF — SecurityPack S0 delivered (2026-08-01)

**Purpose:** resume point for any new opencode session. Read this first, then
the docs it links. Everything below is either on disk (lab repo git) or in the
target repo (`C:\flax\flax-mcp`). Nothing lives only in a chat.

## 1. What the lab is

A security lab for the user's Flax multiplayer game (ENet/UDP 7777). The lab
repo (`C:\Users\me\Desktop\antivirus`) holds all planning, tools and reports;
the game repo (`C:\flax\flax-mcp`) is the user's real project where the
security pack now ships. Lab discipline: attacks stay in the lab; the game
repo is edited only with explicit permission (trust was burned once — see §5).

## 2. Doc map (lab repo `docs/` — read the ones marked ★)

| Doc | What it is |
|---|---|
| ★ `SECURITYPACK-PLUGIN.md` | The build spec for the plugin work. Grounded in a 3-pass audit of flax-mcp. Layers, file lists, hook-point lines, env vars, S0-S3 order, honest risks. **THE reference for continuing.** |
| ★ `SECURITY-BY-DESIGN.md` | Day-one hardening doctrine (Rules 1-5, incl. Rule 4 = the SessionMetrics counter schema DossierWriter uses). |
| ★ `USER-DOSSIER.md` | JSONL session ledger spec + test matrix (coarse for clean / full for flagged). |
| ★ `ARSENAL.md` | Index of everything, parts A-L + test matrix. Part M = this delivery. |
| `ATTACKER-INTEL.md` | L1-L7 intel doctrine (honeypots, tripwires 251-255, fingerprints, counter-offense). |
| `AI-SENTINEL.md` | 3-tier ONNX watchdog (T0 thresholds / T1 IsolationForest / T2 MLP), FPR < 1% gate. |
| `MCP-SECURITY.md` | MCP-surface security (prompt injection, endpoint, assembly loading). |
| `SECURED-SERVER.md` | Hosting blueprint + §7 1000-player shard fleet. |
| `WIRE-FORMAT.md`, `TOOLCHAIN.md`, `BOOK-EXTRACT.md` | Wire format notes, toolchain, research. |
| `reports/` | Findings + abuse-template. `tools/` + `scripts/attack-run.ps1` = lab kit. |

## 3. What is DONE (S0, verified)

In `C:\flax\flax-mcp` (user's repo):

- `samples/game-project/Source/Game/Shared/Security/` — 6 **pure-CLR** runtime
  files, namespace `Game.Shared.Security`: `PacketGuard` (NET-1/2/5 pre-scan,
  packet-id classification, reserved 251-255), `Envelope250` (HMAC-SHA256
  envelope + IPSec-style replay window + session key derivation + EnvelopeSession),
  `Tripwires` (251-255 + unknown-id + id-6 blind-spot counters), `MetricsGuard`
  (SessionMetrics schema + per-conn rate/byte budgets), `DossierWriter`
  (JSONL per-day rolling, coarse/full detail, credential-key scrubbing),
  `FlagRouter` (T0 thresholds → MALFORMED_PACKETS / ENVELOPE_FAILURE / TRIPWIRE /
  GUARD_REJECTS with ShadowRoute/Quarantine actions).
- `plugins/security/` — `FlaxMcp.Plugins.Security.csproj` (links the canonical
  files into the plugin asm), `flaxmcp-plugin.json` (capability "security").
  Installer auto-discovers it by csproj name — no deploy-table edit needed.
- `plugins/security/tests/FlaxMcp.Plugins.Security.Tests/` — 57 xUnit tests,
  ALL GREEN. Run: `dotnet test plugins\security\tests\FlaxMcp.Plugins.Security.Tests\FlaxMcp.Plugins.Security.Tests.csproj`
- Game build verified clean: `Flax.Build.exe -build -buildtargets=GameEditorTarget
  -skiptargets=FlaxEditor -platform=Windows -arch=x64 -configuration=Development` (run from `samples/game-project`).

## 4. What is NEXT

**S0 completion (engine-gated, needs the user's Flax 1.12 API verification):**
1. `SecurityPackRuntime.cs` (bootstrap: env-var config — `FLAXMCP_SECURITYPACK_DOSSIER_DIR`,
   `FLAXMCP_GAME_HMAC_KEY`, `FLAXMCP_SECURITYPACK_THRESHOLDS`; wiring; shutdown)
   + `SecurityPackBoot.cs` (FlaxMcpBoot.cs-style shim in `Source/Game/`).
2. **Step 0 event loop**: `LobbyScaffold.ProcessRawPeerEvent` (samples/game-project/
   Source/Game/Shared/Network/LobbyScaffold.cs:400-407) is unwired;
   `PacketRegistry.Receive` (:40-103) is dead code; id 6 is swallowed
   (NetworkPackets.cs:72-74). Verify the Flax 1.12 `NetworkManager.Peer` event
   surface; fallback = hook the LobbyScaffold packet methods.
3. Acceptance: every lab attack in `scripts/attack-run.ps1` produces counters +
   dossier events; clean walkthroughs produce coarse-only records (USER-DOSSIER matrix).

**Then S1:** Envelope250 game packet class (packet id 250, verify-before-dispatch),
`SecurityPackLobby` (subclass `LobbyScaffold`, override `ResolveAuthenticatedPlayerId`
:256 → playerId + HMAC sessionKey), `MovementGuard` (NET-3 speed clamp, NaN reject).
Accept: forged/teleport rejected, bad-MAC/replay counted, HMAC key rotation drill.

**Then S2:** SentinelT1 ONNX provider (copy `QueryRouterProvider` pattern,
float32 only, status tokens, receipts+MANIFEST, `FLAXMCP_SECURITYPACK_MODEL_PATH`),
`manage_security` mega-tool (Safe: status/flag_list/flag_detail/dossier; Mutating:
flag_review_*; Destructive+dry-run: wave_create), training scripts.

**Then S3:** dossier identity/linkage queries, fleet-sync, quarantine role wiring,
honey-docs/tripwire rotation.

## 5. Hard-won rules (violating these burned trust once — respect them)

1. **The Flax game build does NOT reference System.Text.Json.** Game-side code
   must be dependency-free or use only what the game already references
   (System, System.Collections.Generic, System.Text, System.Security.Cryptography
   are known-good). Verify against the real game build, not just `dotnet test` —
   the first version of DossierWriter compiled in tests and broke the editor.
2. Repo conventions: canonical game-side code lives in `samples/game-project/
   Source/Game/Shared/<Domain>/` (GOAP/QA/Combat precedent); plugin csproj links
   those files; tests get types via the plugin asm. TreatWarningsAsErrors +
   FlaxMcp.Analyzers on in-repo projects. Sealed classes, XML docs,
   `<flax-capability tag="security">` tags on Shared types.
3. **Ask before touching the game repo.** Lab-repo docs/edits are free; user's
   repo needs a go-ahead. Never commit in either repo without being asked.
4. Keep the pure-CLR boundary: everything testable stays Flax-free; engine-
   touching pieces (LobbyScaffold hooks, MovementGuard, boot) are one small
   adapter layer, gated/compiled in the game build only.
5. `Envelope250` HMAC key comes from `FLAXMCP_GAME_HMAC_KEY` (key ceremony,
   rotation drill is part of the test matrix — never commit a key).

## 6. How to continue in a new chat

```
Read C:\Users\me\Desktop\antivirus\docs\HANDOFF-S0.md and the docs it links
(especially SECURITYPACK-PLUGIN.md). Then continue the SecurityPack build in
C:\flax\flax-mcp per §4 (S0 completion → S1 → S2 → S3) with the rules in §5.
Ask before touching the game repo; verify with dotnet test AND the
GameEditorTarget build; confirm with the user before any commit.
```
