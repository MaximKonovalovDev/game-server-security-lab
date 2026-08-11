# CASH-SPRINT — your exact moves this week (no theory)

You're tired and want cash — here's the order of operations. ~2 hours of
your time total this week. Everything referenced already exists in this repo.

## Day 1 (1 hour)

1. **Create Fiverr + Upwork accounts** with the copy in
   `tools/firm/outreach/freelance-listings.md` (profile + 3 gigs).
   - Fiverr: publish gigs at the LOW end ($60 scan, $250 MCP audit).
   - Upwork: set fixed price $50 scan, $150 MCP audit.
2. **Portfolio proof** (attach to both):
   - `tools/firm/portfolio/sample-T1-report.md` — a real scan report
   - `reports/FINDINGS-MCP-001.md` — your flagship: "found a live MCP endpoint
     with NO auth" (this is the strongest proof in your pocket; it's a real
     bug found on a real running server)
3. **Price to close:** first 2 gigs = cheap, for reviews. After 2 reviews:
   double the prices.

## Day 2 (30 min)

4. **Send 10 cold emails** using `tools/firm/outreach/cold-outreach.md`:
   - 4 to indie multiplayer devs (find them: itch.io multiplayer games,
     Godot/Unity/Flax discords, itch game jam boards)
   - 3 to MCP server authors (GitHub: search "mcp-server" + recently pushed,
     npm "mcp" packages with an author email)
   - 3 to local shops (walk through your town's business directory, find
     WordPress sites, use template #3)
   - Personalize ONE line each. The free 20-min look converts best.

## Day 3-7 (30 min total)

5. **Every reply → send the scope-agreement** (`tools/firm/templates/`) —
   their "yes" email + signed scope = you're authorized. Scan, report,
   invoice. Use the engagement flow: scan → findings → fix plan → fix →
   re-scan → report (the SELF-LEARN loop, productized).
6. **Every delivery → ask for the retainer**: "monthly re-scan + CVE brief,
   $50-100/mo?" One retainer = the first recurring dollar.

## What NOT to do
- No scanning anything without the signed scope / yes-email. EVER.
  (PEER-INTEL §1 — the prison story is real.)
- No unpaid "portfolio building" beyond the 2 free first-looks.
- No waiting for the perfect site/name — sell from this repo today.

## Realistic numbers (be honest with yourself)
- Week 1: 0-2 small gigs ($60-250) if outreach converts.
- Month 1: 3-6 gigs, $300-1000 total, if you post listings + send emails.
- Month 2-3: 2 retainers ($150-300/mo) = the foundation.
- The MCP audit niche (your real edge) pays when the writeup is public —
  that's `reports/FINDINGS-MCP-001.md` sanitized → publish on the blog/reddit
  r/cybersecurity + r/netsec. Do it when you have 2 spare hours.

## Your #1 leverage right now
Your plugin fix (FINDINGS-MCP-001 → auth patch) turns a hole into a story:
"my own product, found open, fixed it" — that's the credibility the MCP
audits sell on. The fix needs your OK to touch `C:\flax\flax-mcp`. Say go
and I'll write the patch this week.
