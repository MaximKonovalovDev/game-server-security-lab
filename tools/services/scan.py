#!/usr/bin/env python3
"""
scan.py - the security-service primitive: scan a website or server and emit
a findings report (abuse-report style: facts, evidence, fix).

This is the core of the "security services" business - each finding is a
sellable line item: evidence + severity + concrete fix, then re-scan to
verify. Designed to wrap/absorb heavier scanners later (nuclei, wpscan,
Lynis, ZAP) - every external scanner emits the SAME findings format:

    {"check": "id", "severity": "critical|high|med|low|info",
     "target": "...", "evidence": "...", "expected": "...",
     "actual": "...", "fix": "..."}

Usage:
  python scan.py --url https://example.com          # website scan
  python scan.py --host 1.2.3.4 --ports 22,80,443   # server port scan + banner
  python scan.py --url http://localhost:8765/mcp    # any HTTP service works
  python scan.py --url https://x --json out.json --report out.md

Stdlib only. Authorized targets only.
"""

import argparse
import concurrent.futures
import http.client
import json
import re
import socket
import ssl
import sys
from datetime import datetime, timezone

FINDINGS = []
SEV_ORDER = {"critical": 0, "high": 1, "med": 2, "low": 3, "info": 4}
COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995,
                1433, 1521, 2049, 2222, 2375, 3306, 3389, 5432, 6379,
                8080, 8443, 8888, 9090, 9200, 27017]
WEB_PORTS = [80, 443, 8080, 8443, 8888]
COMMON_PATHS = ["/wp-login.php", "/wp-content/", "/xmlrpc.php", "/administrator/",
                "/admin/", "/.git/config", "/.env", "/phpinfo.php", "/backup.zip",
                "/db.sql", "/.htaccess", "/.DS_Store", "/server-status"]
CMS_MARKERS = [("WordPress", re.compile(r"wp-content|wp-includes|wp-json", re.I)),
               ("Joomla", re.compile(r"/media/system|com_content", re.I)),
               ("Drupal", re.compile(r"/sites/default|drupal", re.I)),
               ("Shopify", re.compile(r"cdn.shopify|myshopify", re.I)),
               ("WooCommerce", re.compile(r"woocommerce", re.I)),
               ("Moodle", re.compile(r"/moodle|moodle", re.I))]
SECURITY_HEADERS = [
    ("strict-transport-security", "high", "HSTS missing - enables SSL-stripping. Fix: `Strict-Transport-Security: max-age=31536000; includeSubDomains`"),
    ("content-security-policy", "med", "CSP missing - XSS impact grows. Fix: add a CSP header (start strict, relax as needed)"),
    ("x-frame-options", "med", "Clickjacking risk. Fix: `X-Frame-Options: DENY` (or CSP frame-ancestors)"),
    ("x-content-type-options", "low", "MIME sniffing risk. Fix: `X-Content-Type-Options: nosniff`"),
    ("referrer-policy", "low", "Referrer leaks URLs. Fix: `Referrer-Policy: strict-origin-when-cross-origin`"),
    ("permissions-policy", "info", "No Permissions-Policy - browser features unrestricted"),
]


def add(check, severity, evidence, expected, actual, fix):
    FINDINGS.append({"check": check, "severity": severity, "evidence": evidence,
                     "expected": expected, "actual": actual, "fix": fix})


def http_probe(host, port, path="/", method="GET", timeout=6.0):
    """Return (status, headers dict, body head, err)."""
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request(method, path)
        r = conn.getresponse()
        body = r.read(4096)
        return r.status, {k.lower(): v for k, v in r.getheaders()}, body, None
    except Exception as e:
        return None, {}, b"", f"{type(e).__name__}: {e}"
    finally:
        conn.close()


def https_probe(host, port, path="/", timeout=6.0):
    import ssl as _ssl
    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read(4096)
        return r.status, {k.lower(): v for k, v in r.getheaders()}, body, None
    except Exception as e:
        return None, {}, b"", f"{type(e).__name__}: {e}"
    finally:
        conn.close()


def scan_website(url, timeout):
    m = re.match(r"https?://([^/:]+)(?::(\d+))?(/.*)?$", url)
    if not m:
        add("url-parse", "high", url, "valid http(s) URL", "unparseable", "fix the --url argument")
        return
    host, port, path = m.group(1), int(m.group(2) or 443 if url.startswith("https") else 80), m.group(3) or "/"
    use_https = url.startswith("https")
    probe = https_probe if use_https else http_probe
    status, hdrs, body, err = probe(host, port, path, timeout)
    if err:
        add("connect", "high", f"{url}", "reachable", f"{err}",
            "confirm DNS + firewall; if service is up, TLS/port issue")
        return
    add("http-status", "info", f"GET {path} -> {status}", "any", str(status), "-")
    server = hdrs.get("server", "")
    if server:
        add("server-banner", "low", server, "no version-disclosing banner",
            server, "hide version: `ServerTokens Prod` / remove header via proxy")
    if "x-powered-by" in hdrs:
        add("x-powered-by", "low", hdrs["x-powered-by"], "header absent", "present",
            "remove X-Powered-By (PHP/ASP version disclosure)")

    cms = next((n for n, rx in CMS_MARKERS if rx.search(body.decode("utf-8", "replace"))), None)
    if cms:
        add("cms-detect", "info", cms, "unknown", f"detected: {cms}",
            "keep CMS + plugins updated; disable unneeded endpoints")

    for hname, sev, fix in SECURITY_HEADERS:
        if hname not in hdrs:
            add(f"header-{hname}", sev, "header absent", "present", "absent", fix)

    for p in COMMON_PATHS:
        if p in ("/wp-login.php", "/xmlrpc.php", "/administrator/") and cms != "WordPress" and p != "/xmlrpc.php":
            continue
        st, h, b, e = probe(host, port, p, timeout=timeout)
        if st and st < 400:
            sev = "high" if p in ("/.git/config", "/.env", "/phpinfo.php", "/backup.zip", "/db.sql") else "info"
            add(f"path-{p}", sev, f"GET {p} -> {st}", f"{p} not exposed", f"{p} reachable ({st})",
                f"block {p} (403/404); remove file if backup/secret")


def scan_tls(host, port, timeout):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            with ctx.wrap_socket(s, server_hostname=host) as t:
                cert = t.getpeercert()
                ver = t.version()
                add("tls-version", "info", ver, "TLS1.2+", ver,
                    "disable TLS1.0/1.1 if shown")
                if cert:
                    exp = cert.get("notAfter", "")
                    add("tls-cert-expiry", "low", exp, "valid > 30 days", exp,
                        "renew before expiry; automate with certbot")
    except ssl.SSLError as e:
        add("tls", "high", str(e), "valid TLS", "handshake failed", "fix cert/SSL config")
    except OSError as e:
        add("tls", "info", str(e), "-", "not TLS on this port", "-")


def scan_ports(host, ports, timeout):
    open_ports = []

    def chk(p):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((host, p))
            open_ports.append(p)
            return True
        except OSError:
            return False
        finally:
            s.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
        ex.map(chk, ports)
    open_ports.sort()
    add("ports-open", "info", f"open: {open_ports or 'none'}", "-", ",".join(map(str, open_ports)),
        "close unused; expose only required ports")
    for p in open_ports:
        if p in (21, 23, 25, 445, 2375, 3306, 5432, 6379, 9200, 27017):
            add(f"port-{p}", "high", f"port {p} open", "not exposed to internet",
                "open", "close/firewall; if needed, restrict by IP + strong auth")
        elif p not in (22, 80, 443, 8080, 8443, 8888):
            add(f"port-{p}", "low", f"port {p} open", "-", "open", "verify it's intentional")
    return open_ports


def report_md(target):
    lines = [f"# Security scan report — {target}", "",
             f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
             f"Findings: {len(FINDINGS)}", ""]
    for sev in SEV_ORDER:
        items = [f for f in FINDINGS if f["severity"] == sev]
        if not items:
            continue
        lines.append(f"## {sev.upper()} ({len(items)})")
        for f in items:
            lines.append(f"- **{f['check']}** — {f['evidence']}")
            lines.append(f"  - expected: {f['expected']} | actual: {f['actual']}")
            lines.append(f"  - fix: {f['fix']}")
        lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="security-service scan primitive")
    p.add_argument("--url", default="")
    p.add_argument("--host", default="")
    p.add_argument("--ports", default=",".join(map(str, COMMON_PORTS)))
    p.add_argument("--timeout", type=float, default=6.0)
    p.add_argument("--json", default="", help="write findings JSON")
    p.add_argument("--report", default="", help="write markdown report")
    args = p.parse_args()

    target = args.url or args.host
    if not target:
        print("need --url or --host", file=sys.stderr)
        sys.exit(2)

    if args.url:
        scan_website(args.url, args.timeout)
        m = re.match(r"https?://([^/:]+)(?::(\d+))?", args.url)
        if m:
            host = m.group(1)
            port = int(m.group(2) or (443 if args.url.startswith("https") else 80))
            if args.url.startswith("https"):
                scan_tls(host, port, args.timeout)
            scan_ports(host, [p for p in WEB_PORTS if p != port], args.timeout)
    if args.host:
        ports = [int(x) for x in args.ports.split(",") if x]
        scan_ports(args.host, ports, args.timeout)

    FINDINGS.sort(key=lambda f: SEV_ORDER[f["severity"]])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"target": target, "findings": FINDINGS}, f, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report_md(target))
    print(json.dumps({"target": target, "findings": FINDINGS}, indent=2))


if __name__ == "__main__":
    main()
