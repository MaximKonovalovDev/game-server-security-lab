# PLAYBOOK-GAME — attack flow for the game server (ENet UDP 7777)

End-to-end flow, phase by phase. Each phase has: goal, exact commands, what a
finding looks like, and the control that should catch it (SECURITY-BY-DESIGN /
WIRE-FORMAT / SECURED-SERVER). Doctrine: lab server only, findings to
`reports/run-<ts>/`, patch → re-run.

## Phase 0 — Recon (what's on the wire)

```
# capture with the lab dissector:
tshark -i <iface> -Y "udp.port==7777" -w reports/run-<ts>/capture.pcap
# or offline analysis with Wireshark + tools/dissector/flax_enet.lua
# baseline handshake to learn the packet flow:
python tools/raw-client/flax_enet.py --mode connect --username Recon
```

Goals: confirm ENet framing (header flags, session, peer id), map packet ids
(1-8, 200), field types (TRICKS A1 heuristics). Outputs feed WIRE-FORMAT.md
corrections + the dissector.

## Phase 1 — Auth / handshake probes (NET-1, NET-2)

```
python tools/raw-client/flax_enet.py --mode connect --username A        # baseline
python tools/raw-client/flax_enet.py --mode craft --username A --payload-hex <hex>  # forged auth token / version field
```

Checks: challenge-response present? (TRICKS A2) forged client version
accepted? token replayable? reserved ids 9-255 tolerated or tripped?

## Phase 2 — Protocol fuzz (NET-5 / robustness)

```
scripts/attack-run.ps1 -Attack fuzz -ServerExe <path>
# or directly:
python tools/boofuzz/fuzz_enet.py --host 127.0.0.1 --port 7777 --cases 2000
python tools/boofuzz/fuzz_enet.py --host 127.0.0.1 --port 7777 --cases 2000 --csv reports/run-<ts>/fuzz.csv
```

Crash oracle built-in (TRICKS A6): clean handshake probe every N cases; CRASH
marker = server died. Also run radamsa mutations over captured seeds.

## Phase 3 — Cheat-class probes (the "what cheaters actually do")

```
python tools/raw-client/flax_enet.py --mode craft  ... # packet edit: speed/teleport (client-authoritative?)
python tools/raw-client/flax_enet.py --mode craft  ... # forged combat packet 200, damage values
python tools/raw-client/flax_enet.py --mode chat-flood --count 100       # rate-limit probe
```

Map each probe to a cheat class (TRICKS A4). Server-authority is the
load-bearing control (SECURITY-BY-DESIGN Rule 1): if a probe succeeds, the
server is trusting the client.

## Phase 4 — DoS / resource abuse (NET-4, MetricsGuard)

```
python tools/raw-client/flax_enet.py --mode flood-connect --count 5000
python tools/raw-client/flax_enet.py --mode packet-soup --count 2000
```

Acceptance: accept loop alive, budgets trip (MetricsGuard), Tripwires fire,
FlagsRouter shadows/quarantines. Crash = finding.

## Phase 5 — Report → patch → re-run (the loop)

1. `scripts/attack-run.ps1` writes `reports/run-<ts>/` (JSON summary + logs).
2. Review; write findings in abuse-template style (facts, expected vs actual,
   severity, control link).
3. Patch in game repo (with user permission) → re-run the failing phase only.
4. `python tools/self-learn/harvest.py` after each cycle → LEARNING-LOG.md.

## Fastest useful first run

```
scripts/attack-run.ps1 -Attack connect -ServerExe <path>   # baseline alive
scripts/attack-run.ps1 -Attack packet-soup -ServerExe <path> --AttackArgs "--count 500"
python tools/boofuzz/fuzz_enet.py --cases 500
```
