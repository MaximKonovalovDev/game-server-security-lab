# Security scan report — https://example.com

Generated: 2026-08-11T09:23:28+00:00
Findings: 10

## HIGH (1)
- **header-strict-transport-security** — header absent
  - expected: present | actual: absent
  - fix: HSTS missing - enables SSL-stripping. Fix: `Strict-Transport-Security: max-age=31536000; includeSubDomains`

## MED (2)
- **header-content-security-policy** — header absent
  - expected: present | actual: absent
  - fix: CSP missing - XSS impact grows. Fix: add a CSP header (start strict, relax as needed)
- **header-x-frame-options** — header absent
  - expected: present | actual: absent
  - fix: Clickjacking risk. Fix: `X-Frame-Options: DENY` (or CSP frame-ancestors)

## LOW (3)
- **server-banner** — cloudflare
  - expected: no version-disclosing banner | actual: cloudflare
  - fix: hide version: `ServerTokens Prod` / remove header via proxy
- **header-x-content-type-options** — header absent
  - expected: present | actual: absent
  - fix: MIME sniffing risk. Fix: `X-Content-Type-Options: nosniff`
- **header-referrer-policy** — header absent
  - expected: present | actual: absent
  - fix: Referrer leaks URLs. Fix: `Referrer-Policy: strict-origin-when-cross-origin`

## INFO (4)
- **http-status** — GET / -> 200
  - expected: any | actual: 200
  - fix: -
- **header-permissions-policy** — header absent
  - expected: present | actual: absent
  - fix: No Permissions-Policy - browser features unrestricted
- **tls-version** — TLSv1.3
  - expected: TLS1.2+ | actual: TLSv1.3
  - fix: disable TLS1.0/1.1 if shown
- **ports-open** — open: [80, 8080, 8443]
  - expected: - | actual: 80,8080,8443
  - fix: close unused; expose only required ports
