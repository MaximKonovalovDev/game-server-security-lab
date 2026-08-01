# SECURITYPACK-PLUGIN — Building the Security Pack Into the FlaxMCP Repo (deep spec)

**Verdict: yes, and the repo is 80% ready.** This spec maps every security
control we designed (SECURITY-BY-DESIGN, AI-SENTINEL, ATTACKER-INTEL,
USER-DOSSIER) onto REAL files, conventions, and hooks in `C:\flax\flax-mcp`,
with the exact registration checklist, tool surface, and build order. Based
on a full repo audit (2026-08-01, three deep passes).

**The one architectural decision that shapes everything:** the MCP boot chain
(`FlaxMcpBoot.cs`, `KernelLoader.cs`, `McpHttpServer.cs`) is `#if FLAX_EDITOR`
and plugin bridges are `#if FLAX_AVAILABLE` — **shipped standalone builds
contain no MCP**. So the security pack is TWO layers:

```
Layer 1  SecurityPack.Runtime  — game-side source in the GAME assembly
   (ships in every build, no MCP, no editor): the enforcement itself.
   Hook points: PacketRegistry, LobbyScaffold subclass, event loop.
Layer 2  SecurityPack.Ops      — plugins/security/ plugin DLL (editor-side)
   (manage_security MCP tools): the ops console — flag queue, dossier
   view, wave orders, model path. Talks to Runtime by reflection bridge
   (exactly the existing GameSystemsLiveBridge pattern).
   Fleet note: on the 1000+ headless fleet, Ops runs on the dev box
   against exported dossier files + signed wave-order file drops —
   preserving "never tunnel 8765" (MCP-SECURITY B4).
```

---

## 1. What the repo already gives us (audit result)

| Need | Found in repo | Where |
|---|---|---|
| Real UDP transport + peer state | `TransportManager` (real `UdpClient`), `transport_*` tools | `plugins/gameplay/src/Core/FlaxMcp.Gameplay.Multiplayer.Core/Packs/Network/Network.Transport.cs:19-137` |
| Anti-cheat engine precedent | `AntiCheatEngine` (speed-hack tracker, resource bounds, fog-of-war) + `network/anticheat_speed_register` tool | `Network.AntiCheat.cs:110-128` — **extend, don't reinvent** |
| Auth gate override point | `LobbyScaffold.ResolveAuthenticatedPlayerId` (virtual, line 256); `AuthTokenRequired=true` fail-closed; **no subclass exists today → every connection rejected** | `samples/game-project/Source/Game/Shared/Network/LobbyScaffold.cs` |
| Chat hardening | 24-char username, 256-char chat clamp, 5/s rate limit, server-stamped SenderID | `LobbyScaffold.cs:196-231,306-315` |
| Packet ID space for us | IDs 9-199 free; **129+ reserved "for add-on scripts"**; 200 combat; 250/251-255 free → envelope 250, tripwires 251-255 | `NetworkPackets.cs:11-21`; `NetworkCombatSync.cs:56-58` |
| Privacy precedent | `SessionMetadataRedaction` (credential-class keys) | `Shared/Network/SessionMetadataRedaction.cs` |
| MCP endpoint auth | 256-bit bearer token, auto-minted `%LocalAppData%\flaxmcp`, fail-closed | `src/FlaxMcp.Kernel/Core/Security/TokenValidator.cs:120-183` — **MCP-SECURITY B1 is already done** |
| Loopback CSRF/DNS-rebind guard | `OriginValidator` | `plugins/Plugins.Common/src/Core/Security/OriginValidator.cs:166` |
| ONNX in-process providers | `QueryRouterProvider` pattern: lazy singleton, env-var path, graceful degrade, status tokens, `ResetForTests` | `src/FlaxMcp.Kernel/Core/Embedding/QueryRouterProvider.cs` + `QueryRouter.cs` |
| Model ops loop | receipts w/ gates (sha256, dry-run, integration tests, restart+health, live probes, `PROMOTED`), MANIFEST.md, runbook | `external/models/receipts/routing-v2g-promotion-20260731.receipt.json`; `docs/reference/onnx-routing-runbook.md` |
| Input-sieve precedent (AI-bait/sanitize) | `LlmIntentSieve` — 15 compiled regex rules, Severity Clean/Suspicious/Hostile | `plugins/llm/src/Core/FlaxMcp.Llm.Core/Guardrails/LlmIntentSieve.cs` |
| Logging substrate for dossier | Serilog NDJSON rolling per-day, `correlation_id` | `docs/reference/logging.md` |
| Tool policy enforcement | `Policy.Safe/Mutating/Destructive` — kernel auto-gates intent + dry-run + receipts; agent-group allowlist; rate limits | `src/FlaxMcp.Core/Core/Policy.cs`; `ToolDispatcherCore.cs:555-608` |

## 2. What's missing (the gaps the pack fills — exact spots)

| Gap | Exact spot | Fix |
|---|---|---|
| **Receive event loop is unwired** — `PacketRegistry.Receive` is dead code | `LobbyScaffold.ProcessRawPeerEvent` (lines 400-407) never called; `TODO(network-verify)` comments `LobbyScaffold.cs:392-399`, `NetworkCombatSync.cs:416-421` | **Step 0:** game-side `Peer.PopEvent` loop → `ProcessRawPeerEvent` (engine API: `NetworkManager.Peer`; verify PopEvent surface in Flax 1.12 docs) |
| NET-1 unbounded allocations | `PlayerListPacket.Deserialize` `NetworkPackets.cs:135-144` (`count` = ReadInt32 loop); `PlayersTransformPacket.Deserialize` `:212-222`; `NetworkCombatSync._incoming` queue `:447` | PacketGuard: count caps (64 players / 256 transforms) BEFORE allocation; queue cap |
| NET-2 no string caps at codec | `PlayerConnectedPacket.cs:164`, `ChatMessagePacket.cs:244` (`ReadString` uncapped) | caps in codec (24/256) — mirror `MaxTokenBytes=1024` pattern (`NetworkPackets.cs:47`) |
| NET-3 movement: zero validation, **no consumer of PlayersTransform at all** | no `RegisterHandler(PacketIds.PlayersTransform)` anywhere | MovementGuard handler: count cap, ownership (sender.ConnectionId vs entry Guids), NaN/plausibility, speed clamp |
| NET-5 enum range checks NOT implemented | `NetworkCombatSync.cs:461,465` (`rawEventType`, `CombatHitKind` cast unchecked); no damage clamp | range reject + clamp; sender-ownership (attackerId must map to sender) |
| No per-connection packet rate/handshake budget | only chat rate limit | MetricsGuard: per-conn PPS/bytes buckets + handshake budget |
| No HMAC envelope, no per-session identity on wire | id 250 free | Envelope250 (SECURITY-BY-DESIGN Rule 2), key from config/env `FLAXMCP_GAME_HMAC_KEY` + per-release rotation |
| Tripwire = LogWarning only | `PacketRegistry.cs:82` default case; **id 6 silently swallowed** (`:72-74`) | Tripwires: counters + dossier event for unknown/251-255; also catch id 6 |
| No disconnect reasons / kick packet | `KickClient` is in-memory only (`LobbyControllerBase.Extensions.cs:112-146`, teardown TODO) | new packet id (e.g. 252) `KickNotice` w/ reason enum |
| No ENet tunables from managed code | only `MaxClients` via `Network Settings.json` asset (100), `NetworkFPS 60`, `Port 7777`, ENetDriver | verify Flax 1.12 API for `duplicatePeers`/limits; where unavailable: document as ops-layer (engine default) + session budgets in MetricsGuard |
| Boot/ops surfaces `#if FLAX_EDITOR` | `FlaxMcpBoot.cs:1`, kernel refs `Game.Build.cs:54` | Runtime layer is plain game source (ships); Ops layer editor-only by design |

## 3. Layer 1 — SecurityPack.Runtime (game-side source, ships in builds)

New files under `samples/game-project/Source/Game/Shared/Security/` (game
assembly → first-class access to `PacketRegistry`/`LobbyScaffold`, no
reflection needed for the hot path):

```
Shared/Security/
├── SecurityPackRuntime.cs        — singleton bootstrap: config read, wiring,
│                                    shutdown; <flax-capability tag="security">
├── PacketGuard.cs                — NET-1/2/5: pre-scan msg length, count caps,
│                                    string caps, enum range checks (pure-CLR)
├── Envelope250.cs                — HMAC envelope: packet class (Serialize/
│                                    Deserialize per NetworkPackets contract),
│                                    verify-before-dispatch, sessionKey
│                                    derivation, seq/replay window (pure-CLR)
├── Tripwires.cs                  — unknown-ID + 251-255 counters, dossier
│                                    events, id-6 blind-spot fix
├── MovementGuard.cs              — RegisterHandler(PlayersTransform): ownership,
│                                    speed clamp (NET-3), NaN reject
├── MetricsGuard.cs               — SessionMetrics counters (SECURITY-BY-DESIGN
│                                    Rule 4 schema verbatim) + per-conn budgets
├── DossierWriter.cs              — USER-DOSSIER ledger (JSONL, per-day rolling
│                                    per logging.md precedent), SessionMetadata
│                                    Redaction reuse, coarse for clean / full
│                                    for flagged
├── FlagRouter.cs                 — T0 thresholds, flag→shadow, quarantine
│                                    routing at reconnect, wave-order ingestion
│                                    (signed file-drop), FleetMode flag
├── SentinelT1.cs                 — ONNX IsolationForest: lazy load, env-var
│                                    model path, graceful degrade, status
│                                    tokens (mirrors QueryRouterProvider)
└── SecurityPackLobby.cs          — LobbyScaffold subclass: override
                                    ResolveAuthenticatedPlayerId (:256) →
                                    token/username → playerId + HMAC sessionKey;
                                    connect/disconnect → dossier open/close
```

Plus Step 0 (event loop) lands as a change in the existing
`LobbyScaffold.ProcessRawPeerEvent` region — the pack owns that wiring.

**Boot:** `FlaxMcpBoot.cs`-style: a small `SecurityPackBoot.cs` in
`Source/Game/` calls `SecurityPackRuntime.Initialize()` on server start
(`NetworkStartMode.Host/Server`), teardown on stop. No MCP dependency —
shipped builds get enforcement; editor gets it too.

## 4. Layer 2 — SecurityPack.Ops (plugins/security/ plugin DLL)

```
plugins/security/
├── flaxmcp-plugin.json           — name "security", capability "security",
│                                    assemblies ["FlaxMcp.Plugins.Security"]
├── FlaxMcp.Plugins.Security.csproj  — refs FlaxMcp.Core + Plugins.Common;
│                                    glob src/Core/** + src/Live/**;
│                                    RestorePackagesWithLockFile
├── src/Core/FlaxMcp.Security.Core/
│   ├── SecurityOps.cs            — [MegaTool("manage_security")] + routes
│   ├── SecurityOps.Flags.cs      — flag queue read/review
│   ├── SecurityOps.Dossier.cs    — dossier query (identity, timeline, links)
│   ├── SecurityOps.Waves.cs      — wave order creation (signed file-drop out)
│   ├── SecurityOps.Model.cs      — sentinel model status/switch (receipts)
│   └── SecurityOps.Fleet.cs      — fleet-mode: sync/export dossier snapshots
├── src/Live/SecurityLiveBridge.cs   — reflection bridge to Runtime
│                                    (GameSystemsLiveBridge pattern: ResolveType)
└── tests/FlaxMcp.Plugins.Security.Tests/
    └── … xUnit, Ctx() fake context, ResetForTests, CollectionDefinition for
        serial tests; naming <Method>_<Condition>_<Expectation>
```

### manage_security action surface (Policy-gated honestly)

| Action | Policy | Notes |
|---|---|---|
| `status` | Safe | runtime config, model status tokens, counters — no data |
| `flag_list` | Safe | shadow queue summary (IDs, reason tags — no raw content) |
| `flag_detail` | Safe | one session's metrics + dossier event list |
| `dossier` | Safe | identity/timeline/links for a session/machine ID |
| `flag_review_confirm` | Mutating | intent required; writes confirmed label → sentinel labels |
| `flag_review_clear` | Mutating | intent required; logs clear reason |
| `wave_create` | **Destructive** | intent + `dryRunId` from `mutation/dry_run`; writes signed wave-order file (never direct kill) |
| `quarantine_route` | Mutating | route flagged session at reconnect (batched) |
| `model_set` | Mutating | switch `FLAXMCP_SECURITYPACK_MODEL_PATH` + receipt validate |
| `fleet_sync` | Safe | dev-box export of dossier snapshots (big-fleet mode) |

Descriptions end with `Keywords: security, anti-cheat, ...` (ADR-057
normalization appends policy text automatically). Never expose raw chat/
packet payloads in tool output — dossier goes through
`SessionMetadataRedaction`-style scrubbing.

## 5. Sentinel T1 — ONNX integration (copy the proven pipeline)

- **Provider:** `SentinelT1.cs` mirrors `QueryRouterProvider`/`QueryRouter`:
  lazy singleton, `FLAXMCP_SECURITYPACK_MODEL_PATH` → dir check → model.onnx
  + `normalizer.json` (feature min/max or z params) + `config.json` →
  `OnnxRuntimeNativeProbe.IsAvailable` → `InferenceSession` (CPU EP) → input
  metadata verify (float32 `[1,N]` features) → status tokens:
  `not_configured / model_missing / onnx_runtime_unavailable /
  model_input_mismatch / model_load_failed / enabled`. Failure → T0-only
  (advisory, graceful — repo doctrine).
- **Model:** IsolationForest (sklearn → ONNX via skl2onnx, self-contained,
  `export_params=True`, **float32 only** — dynamic int8 is known-broken for
  classifiers in this repo, MANIFEST quantization notes).
- **Training:** `scripts/training/build-sentinel-dataset.py` +
  `train-sentinel-isolation-forest.py` (new, same conventions: receipts,
  `--dry-run`, fixture validation, provenance sha256) → artifacts under
  `external/models/security-pack/v1/` + `MANIFEST.md` rows (Active/Rollback/
  Inventory tables) + runbook section.
- **Ops loop:** candidate → model_artifact_verification (sha256, self-
  contained, logits shape, quant dry-run) → integration-test gate
  (`test-fast.ps1 -Plugin security`, self-skipping when env unset) →
  restart-and-health (tool health + `wiring_self_test` ExpectedExtensions
  resync) → live probes → `PROMOTED (active)` receipt + rollback row.
- **Telemetry:** RoutingTelemetry pattern — aggregate-only (no session data
  in telemetry), fixed histograms, `reportOnly:true`,
  `autoThresholdAdjust:false` (thresholds are manual operator decisions).

## 6. Registration checklist (4 places — do not skip)

1. `src/FlaxMcp.Kernel/Core/Boot/BootOrchestrator.cs:140-153` —
   `PluginManifestDirs` += `"security"`.
2. `samples/game-project/Source/Game/DeployManifest.cs:20-33` — `Buckets`
   row `FlaxMcpSecurity → FlaxMcp.Plugins.Security.dll`.
3. `plugins/security/flaxmcp-plugin.json` — `assemblies` + `dependencies`
   (Plugins.Common; gameplay optional for AntiCheatEngine reuse).
4. `tool/wiring_self_test` — resync `ExpectedExtensions` with the new
   bridge (repo convention on any plugin add/remove).
5. Build: `scripts/build/build-plugin.ps1` auto-discovers
   `FlaxMcp.Plugins.Security.csproj` (deploy table is name-based); commit
   `packages.lock.json`; `TreatWarningsAsErrors` + `FlaxMcp.Analyzers`
   (missing-intent on mutating tools fails analysis).

## 7. New env vars (document in docs/reference/security-model.md §5 map)

| Var | Purpose |
|---|---|
| `FLAXMCP_SECURITYPACK_MODEL_PATH` | sentinel ONNX dir (process-immutable, one resolve) |
| `FLAXMCP_SECURITYPACK_DOSSIER_DIR` | ledger/dossier root (default LocalAppData) |
| `FLAXMCP_SECURITYPACK_ROLE` | `live \| quarantine \| decoy \| fleet` (SECURED-SERVER §1.3) |
| `FLAXMCP_SECURITYPACK_FLEET_ID` | shard id for fleet-mode dossiers |
| `FLAXMCP_GAME_HMAC_KEY` | per-release HMAC key (key ceremony, never committed) |
| `FLAXMCP_SECURITYPACK_WAVES_DIR` | signed wave-order drop dir (fleet) |
| `FLAXMCP_SECURITYPACK_THRESHOLDS` | T0 threshold overrides (operator-only) |

## 8. Build order S0-S3 (each shippable, test matrix reused from the specs)

- **S0 — runtime core:** Step-0 event loop wired; PacketGuard caps; MetricsGuard
  counters + dossier writer; tripwires. *Accept: every lab attack from
  attack-run.ps1 produces counters + dossier events; clean walkthroughs produce
  coarse-only records (USER-DOSSIER test matrix).*
- **S1 — identity:** Envelope250 + `SecurityPackLobby` (ResolveAuthenticatedPlayerId
  override) + MovementGuard. *Accept: forged/teleport packets rejected; bad-MAC/
  replay-seq counted; speed clamp fires; HMAC key rotation test.*
- **S2 — sentinel + ops:** SentinelT1 ONNX + manage_security tools + flag queue
  + wave orders. *Accept: FPR < 1% gate on clean data; every lab attack flags;
  flag_review_confirm exports sentinel labels; wave_create requires dry-run.*
- **S3 — intel:** dossier identity/linkage queries, fleet-sync, quarantine role
  wiring, honey-docs/tripwire rotation (ATTACKER-INTEL L1.2/L7.4). *Accept:
  machine-ID persistence across accounts/IPs; quarantine quit-rate metric.*

## 9. Honest risks (design around them, don't ignore)

1. **Event-loop gap is step 0 and needs engine verification** — Flax 1.12's
   `NetworkManager.Peer` PopEvent surface must be confirmed (engine types
   aren't in the repo); fallback: hook at the `LobbyScaffold` packet methods
   if `Receive` can't be reached directly.
2. **ENet tunables** (`duplicatePeers`) not reachable from managed code —
   engine defaults; mitigate with MetricsGuard session budgets; document in
   ops layer.
3. **Ships-without-MCP doctrine** — Runtime is game source by design; Ops is
   editor-only; the fleet console talks to the fleet via file-drops +
   exports, never a tunneled endpoint (MCP-SECURITY B4 holds).
4. **Key ceremony discipline** — `FLAXMCP_GAME_HMAC_KEY` rotation cadence is
   the envelope's whole value; the lab test matrix must include a rotation
   drill.
5. **Intents are the human gate** — approval popups were deliberately removed
   from the kernel (ToolDispatcherCore.cs:629); destructive wave actions
   MUST stay `Destructive`+dry-run, never relaxed to Mutating.

*References: SECURITY-BY-DESIGN (envelope 250, metrics, ops), AI-SENTINEL
(ONNX tiers, receipts), ATTACKER-INTEL (tripwires, waves, quarantine),
USER-DOSSIER (ledger schema), MCP-SECURITY (ops tiers), SECURED-SERVER
(roles, fleet), plus repo docs: docs/reference/onnx-routing-runbook.md,
docs/guides/recipes/plugin-getting-started.md, docs/SAFETY.md.*
