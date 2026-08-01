#!/usr/bin/env python3
"""
harvest.py - the lab's self-learning loop.

Scans reports/ (findings + mode-*.jsonl evidence), turns every observed case
into a row, maintains docs/LEARNING-LOG.md, and proposes next tests based on
which attack groups produced non-expected behavior.

The loop (docs/SELF-LEARN.md):
  attack run -> reports/FINDINGS-MCP-<ts>/ + reports/run-<ts>/
  harvest.py  -> docs/LEARNING-LOG.md (append-only) + "next tests" suggestion
  next run    -> does the suggested test; repeat

Usage:
  python harvest.py                    # scan everything
  python harvest.py --since 7          # only runs younger than 7 days
  python harvest.py --dry-run          # print, don't write the log
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

LAB = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS = os.path.join(LAB, "reports")
LOG = os.path.join(LAB, "docs", "LEARNING-LOG.md")

CASE_RE = re.compile(r"\b([MG]-\d{2,3}[-\w]*)")

INTERESTING = {
    "expected-but-actually": "out-of-spec behavior (verify + patch)",
    "401": "auth gap",
    "200": "unexpected success (access without auth!)",
    "500": "unhandled exception path",
    "403": "rejection behaved",
    "CRASH": "server survived-check: verify",
}


def runs_younger(age_days):
    out = []
    for name in sorted(os.listdir(REPORTS)):
        d = os.path.join(REPORTS, name)
        if not os.path.isdir(d):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(d))
        except OSError:
            continue
        if (datetime.now() - mtime).days <= age_days:
            out.append(d)
    return out


def scan_run(rdir):
    cases = {}
    for fn in os.listdir(rdir):
        if not fn.endswith(".jsonl") and not fn.endswith(".md"):
            continue
        path = os.path.join(rdir, fn)
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                cid = rec.get("case") or fn
                cases[cid] = {
                    "status": rec.get("status"),
                    "body": (rec.get("body") or "")[:120],
                    "expected": rec.get("expected"),
                }
    return cases


def is_unexpected(cid, rec):
    """A case is suspicious when its status disagrees with its expectation."""
    status = rec.get("status")
    if status is None:
        return False
    if status not in (200, 401, 403, 405, 404):
        return True
    exp = (rec.get("expected") or "").lower()
    if "401" in exp and status == 200:
        return True
    if ("200" in exp or "result" in exp) and status in (401, 403):
        return True
    if "405" in exp and status == 404:
        return True
    return False


def classify(cases):
    by_group = defaultdict(list)
    for cid, rec in cases.items():
        prefix = cid.split("-")[0] if cid else "?"
        by_group[prefix].append((cid, rec))
    return by_group


def propose_next(by_group, log_rows):
    """Fails: cases whose status disagrees with expectation -> suggest re-run."""
    suggestions = []
    for group, items in sorted(by_group.items()):
        suspicious = [cid for cid, rec in items if is_unexpected(cid, rec)]
        if suspicious:
            suggestions.append(
                f"- re-run group `{group}` and hand-inspect: unexpected status on {', '.join(suspicious[:4])}"
            )
    last = log_rows[-3:] if log_rows else []
    joined = " ".join(last).lower()
    if "m-" in joined and "flood" not in joined:
        suggestions.append("- flood + sse group not covered yet - run transport group fully")
    if "g-" in joined and "fuzz" not in joined:
        suggestions.append("- boofuzz protocol fuzz not in the log - run fuzz_enet.py/fuzz_mcp.py")
    if not suggestions:
        suggestions.append("- all clean: raise severity on one group (deeper arg-bombs, bigger flood)")
    return suggestions


def main():
    p = argparse.ArgumentParser(description="self-learning harvester for the lab")
    p.add_argument("--since", type=int, default=0, help="only runs <= N days old")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not os.path.isdir(REPORTS):
        print(f"[!] no reports dir: {REPORTS}", file=sys.stderr)
        sys.exit(1)

    dirs = runs_younger(args.since) if args.since else sorted(os.listdir(REPORTS))
    dirs = [d if os.path.isabs(d) else os.path.join(REPORTS, d) for d in dirs]
    dirs = [d for d in dirs if os.path.isdir(d)]

    total_cases = 0
    all_groups = Counter()
    merged = {}
    entries = []
    for d in dirs:
        cases = scan_run(d)
        if not cases:
            continue
        total_cases += len(cases)
        merged.update(cases)
        groups = classify(cases)
        for g, items in groups.items():
            all_groups[g] += len(items)
        bad = [cid for cid, rec in cases.items() if is_unexpected(cid, rec)]
        entries.append(f"- `{os.path.basename(d)}`: {len(cases)} cases, groups {sorted(groups)}, "
                       f"{len(bad)} with unexpected status: {bad[:5]}")

    log_rows = []
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as f:
            log_rows = [l for l in f.read().splitlines() if l.startswith("- `")]

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"## Harvest {stamp} — {total_cases} cases in {len(dirs)} run(s)"
    block = [header, ""] + (entries or ["- no runs captured"]) + [
        "",
        "### Group coverage",
        f"- {', '.join(f'{g}:{n}' for g, n in sorted(all_groups.items())) or 'none'}",
        "",
        "### Next suggested tests",
    ] + propose_next(classify(merged), log_rows)

    if not args.dry_run:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\n".join(block) + "\n")
        print(f"[*] wrote {LOG}")
    else:
        print("\n".join(block))


if __name__ == "__main__":
    main()
