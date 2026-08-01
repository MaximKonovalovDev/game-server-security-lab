# SELF-LEARN — the lab's learning loop

Every attack run feeds the next one. No wasted runs: evidence is harvested,
rules are updated, and the next test set is suggested automatically.

## The loop

```
attack run (game or MCP)
   -> reports/run-<ts>/  or  reports/FINDINGS-MCP-<nnn>/
   -> python tools/self-learn/harvest.py
   -> docs/LEARNING-LOG.md (append-only) + "next suggested tests"
   -> next run does the suggested tests
   -> findings become patches (with user permission)
   -> patches become regressions (re-run the group)
```

## Harvest details

`tools/self-learn/harvest.py`:

- scans `reports/` for run dirs (JSONL evidence + findings md)
- counts cases per run, groups by case prefix (`M-` MCP / `G-` game)
- flags cases whose status is outside the expected set (200/401/403/405/404)
- appends a dated entry to `docs/LEARNING-LOG.md` with coverage + suggestions
- `--since N` = only runs younger than N days; `--dry-run` prints without writing

Suggested tests are derived from gaps: uncovered groups (e.g. flood/SSE
missing), unexpected statuses (re-run + hand-inspect), and a fallback to
"raise severity" when everything is clean.

## Rules the loop maintains

1. **Facts only.** Evidence JSONL + response excerpts; findings reports carry
   status, expected vs actual, severity, control link (abuse-report style).
2. **Re-run after every patch.** A fixed group regression set (auth →
   transport → dispatch) runs after each code change in the game repo.
3. **Severity escalates.** A clean group gets deeper probes next cycle
   (bigger floods, longer fuzz cases, more corpus entries) rather than
   repeating the same run.
4. **Triple-check mode**: never report a "pass" from one run; a group only
   graduates after 2 clean runs.
5. **New surface = new group.** Any newly discovered endpoint (Phase 0
   endpoints/openapi) spawns its own mini-group before being trusted.

## Cadence

- After every session with attacks: run harvest.py (2 min).
- Weekly: read LEARNING-LOG.md; fold recurring themes into TRICKS.md.
- Monthly: review ARSENAL.md research parts for new tools to vendor.

## Log format

Append-only `docs/LEARNING-LOG.md`:

```
## Harvest 2026-08-01 — 64 cases in 3 run(s)
- `run-20260731-093000`: 40 cases, groups ['G'], 2 with unexpected status: [...]
- `FINDINGS-MCP-001`: 24 cases, groups ['M'], 1 with unexpected status: [...]
### Group coverage
- G:40 M:24
### Next suggested tests
- re-run group `M` and hand-inspect: unexpected status on M-01-no-token-0
- flood + sse group not covered yet - run transport group fully
```
