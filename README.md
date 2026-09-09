# Game Server Security Lab

Adversarial test lab for my own Flax Engine game server and MCP plugin:
break it in the lab, fix it in the build, prove the fix. Attack tooling +
defense specs + real findings, all in one place.

> **Authorized testing only.** Everything here is built to test systems I own
> (my Flax game server, my MCP plugin) or systems I am explicitly authorized
> to test. Do not point any of these tools at third-party servers.

## Why it exists

Small multiplayer games ship with the client in charge — speed hacks,
teleports, duped items, dead economies. Fixing that after launch costs far
more than building it right. This lab is the practice behind that belief:
a place where attacks are rehearsed against my own server so the defenses
are proven, not assumed. Its defense-only sibling is
[server-security-research](https://github.com/MaximKonovalovDev/server-security-research).

## What's inside

| Area | Contents |
|---|---|
| `docs/` | 30+ research and build specs (see index below) |
| `tools/raw-client/` | Pure-Python ENet client: handshake, crafted payloads, floods, fuzz modes |
| `tools/dissector/` | Wireshark Lua dissector for the game port |
| `tools/boofuzz/` + `tools/radamsa/` | Mutation fuzzing over ENet framing |
| `tools/wire-probe/` | .NET reflection probe (ground-truth extraction) |
| `tools/mcp-attacker/` | Attack tooling for the MCP plugin surface |
| `tools/self-learn/` | Learning loop: every run feeds the next test plan |
| `scripts/` | `attack-run.ps1`: spawn server → attack → report |
| `reports/` | Findings and test reports, including two live ones |

Key docs (`docs/`): `ARSENAL.md` (framework + workflow), `TOOLCHAIN.md`
(tool selection per layer), `WIRE-FORMAT.md` (reverse-engineered ENet/Flax
framing), `SECURITY-BY-DESIGN.md` (day-one hardening rules),
`AI-SENTINEL.md` (server watchdog spec), `ATTACKER-INTEL.md`,
`MCP-SECURITY.md` (MCP endpoint + supply-chain hardening),
`USER-DOSSIER.md`, `SECURED-SERVER.md` (hosted-build blueprint),
`PLAYBOOK-GAME.md` + `PLAYBOOK-MCP.md` (attack runbooks with exact
commands), `TRICKS.md` (sourced techniques DB), plus hosting/deploy
runbooks. Full map: [`docs/README.md`](docs/README.md).

## Live findings (not theories)

- **`reports/FINDINGS-MCP-001.md`** — my own running MCP plugin answered
  `tools/list` AND `tools/call` with **no token** (expected 401
  fail-closed). Origin spoofing correctly 403'd. Finding → fix → verify.
- **`reports/FINDINGS-001-initial-audit.md`** — first real audit of the
  game's network code: NET-1/2 HIGH (unbounded allocations), NET-3/4/5
  MEDIUM (validation/rate/range gaps), each tied to a lab probe.
- **`reports/RESEARCH-002/003`** — case studies (games killed by cheaters;
  how packet games get broken) mapped to concrete defenses.
- S0 slice: 6 runtime game-side files + plugin, **57 green tests**,
  verified in both dotnet and Flax game builds.

## Honest limits

- A lab is not production: findings are point-in-time against my own builds.
- Some lanes need setup (VM for memory-cheat testing, tunnel for hosted
  playtests) — the docs say which, per lane.
- No zero-days, no third-party targets, no bypass kits. Attack code exists
  so defenses can be tested, nothing here is packaged for abuse.

## License

MIT — see `LICENSE`.
