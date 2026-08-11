# tools/services — the security-service engine

Sellable security checks. Every tool here emits the SAME findings format so
one report pipeline serves all customers:

    {"check": "id", "severity": "critical|high|med|low|info",
     "evidence": "...", "expected": "...", "actual": "...", "fix": "..."}

Authorization rule (legal): scan ONLY targets the customer owns / approved in
the signed scope. Nothing else.

## 1. scan.py — the core primitive (stdlib, zero install)

```powershell
python scan.py --url https://customer-site.com --json findings.json --report report.md
python scan.py --host 1.2.3.4 --ports 22,80,443,3306
```

Checks: HTTP status + banner leak, CMS detect, security headers (HSTS/CSP/
XFO/nosniff/Referrer-Policy/Permissions-Policy), common sensitive paths
(.git/config, .env, phpinfo, backups), TLS version + cert expiry, TCP port
scan with high-risk port flags (21/23/25/445/2375/3306/5432/6379/9200/27017).
Output: findings JSON + severity-sorted markdown report with fixes.

## 2. nuclei — the deep scanner (Docker route, chosen 2026-08-01)

The Windows binary (v3.11.1) was downloaded, then quarantined by Defender as
"HackTool" — a known false positive: our SHA256 matched the official release
checksum exactly (bb6cb9ff8939b753f6fcab06fd30a15f5bc61d8382a597871334c007a85ff9d2).
Per user decision, no native binary: **nuclei runs via the official Docker
image** (`projectdiscovery/nuclei`). This machine has no Docker yet — the
wrapper is ready for the service deployment host (VPS/server):

```powershell
# on the deploy host (Docker installed):
.\nuclei-docker.ps1 -Target https://customer-site.com -OutDir .\results
```

Wrapper mounts `templates/` + writes `results/` locally; scanner itself is
container-isolated (no host AV friction, per-customer isolation).

## 3. Pipeline (how a customer engagement runs)

```powershell
# T1 website check:
python scan.py --url https://site --json findings.json --report report.md
.\nuclei-docker.ps1 -Target https://site -OutDir .\results      # deploy host
# wpscan (if WordPress): wpscan --url https://site --enumerate vp,vt,u --api-token <t>
# then: review findings -> fix plan -> re-scan -> verified (2 clean runs)
```

## 4. Findings → report flow (docs/SERVICES-PLATFORM.md)

1. scan → findings JSON
2. triage (dedup, false positives, severity)
3. fix plan: one fix per finding (linked evidence)
4. apply fixes on approved scope only
5. re-scan → verified
6. customer report.md: summary, severity counts, fixes applied, residual risk

## 5. Tool notes

- `scan.py`: stdlib only, runs anywhere (this machine included) — the
  instant T1 deliverable.
- nuclei: Docker only per decision above; templates update via
  `nuclei -update-templates` inside the container.
- Lynis (T2 server audits): Linux-only, runs on the customer server
  (agentless), not on this Windows box.
- ZAP: optional deep web scan (OWASP ZAP, installed on demand).
- Secret hygiene: findings may contain secrets (tokens in responses) —
  escalate-not-log on credential material (DossierWriter scrubbing rule).
