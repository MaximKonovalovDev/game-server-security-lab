# Scope Agreement — Security Engagement (template)

> **TEMPLATE — NOT LEGAL ADVICE.** Get this reviewed by a lawyer in your
> jurisdiction before first use with a paying client. It implements the rules
> in docs/PEER-INTEL.md §1-3 (authorization-first, neutral report tone,
> contractual re-scope, liability wording). Do NOT scan anything not on this
> form. Do NOT change the tone of any report.

## Engagement identification

- Client (legal entity): _________________________________________
- Engaged party (firm): _________________________________________
- Engagement date: ______________  Test window (start → end): ______________
- Service tier (from pricing questionnaire): [ ] T1 site check  [ ] T2 server
  hardening  [ ] T3 game netcode review  [ ] T4 MCP/AI plugin audit
  [ ] Recurring/monitoring plan (specify) _______________________________

## 1. Authorized scope (THE list — nothing else is in scope)

| # | Asset | Type (URL/IP/hostname/repo) | Owner confirmed? | Notes |
|---|---|---|---|---|
| 1 | | | [ ] | |
| 2 | | | [ ] | |
| 3 | | | [ ] | |
| 4 | | | [ ] | |

Binding rule: the engagement party will test **only** the assets listed above.
Any asset not on this table is out of scope. If the client later wants an
asset added, it requires a written addendum (optional §10) BEFORE any testing
begins on it — never retroactively.

## 2. What will be done (per-tool, per-asset)

- [ ] Passive/active web scan (scan.py / nuclei): headers, TLS, ports, CMS,
      common sensitive paths — LOW impact (no payloads that alter data).
- [ ] Authenticated/unauthenticated checks: (list tools per service tier)
  _______________________________________________________________________
- [ ] Active exploit / DoS / credential attacks: (list) ___________________
- [ ] Game proto fuzzing / MCP dispatch tests — HIGH impact, may cause log
      noise or transient errors; greenlit here: [ ] yes  [ ] no
- [ ] Re-scan after fixes to verify (post-engagement, same scope): [ ] yes

Impact waiver clause: client is informed that authorized testing may cause
noise and transient effects; engaged party will stop any test on client
request within 1 business hour of notice.

## 3. Written authorization (the legal floor)

The client confirms, by signing this form:
- [ ] They own or are authorized by the owner to test every asset in §1.
- [ ] They have informed relevant third parties (hosting/SaaS/whoever hosts
      the assets) that testing will occur — cross-owner authorization is the
      client's responsibility.
- [ ] This document is the written authorization required by applicable
      computer-misuse / unauthorized-access law [enter local statute names:
      CFAA (US) / Computer Misuse Act (UK) / equivalent].

## 4. Report + tone policy (PEER-INTEL §1 legality of tone)

The engaged party will:
- Deliver findings report **neutral and factual**: evidence, expected vs
  actual, severity, fix. No sarcasm, no threats (implied or explicit), no
  "you got owned" language — in writing or verbally.
- Mark the report "findings as of test date; not a guarantee of security."
- Escalate-not-log any credential material found (secrets go in a protected
  annex, never in the standard report).
- Publish nothing about the client without a signed disclosure addendum.

Client confirms they understand: findings text may not always be flattering,
but the engaged party will never write or act in a way that can be read as a
demand or threat. A disagreement is handled through this engagement, not in a
report.

## 5. Liability wording (findings, not guarantees)

- Deliverable = findings + fix recommendations + re-scan verification **within
  the scope and window above**.
- The engaged party does not guarantee the assets are or will remain
  "unhackable"; residual risk is explicitly the client's to accept or reduce.
- Engaged party liability limited to fees paid for this engagement; no
  consequential damages. (Have a lawyer tune this for your jurisdiction.)
- Both parties keep each other's non-public information confidential.

## 6. Payment

- Quote: $____________ (from the pricing questionnaire tier table; fixed for
  the scope in §1).
- Payment terms: [ ] 50% on signing, 50% on delivery  [ ] net-30
  [ ] other: _______________
- **Re-scope clause (PEER-INTEL §2):** if test-time discovery shows the asset
  count / surface is materially beyond §1 (e.g., double the hosts, unbounded
  API endpoints), the engaged party will pause, notify, and quote the delta
  per the tier table — and will not exceed the agreed scope or time without a
  written addendum (§10).

## 7. Duration + stop rights

- Test window: §0 above. Report due within N business days of window end: ____.
- Either party may stop testing early with written notice; prorated fee for
  completed work.

## 8. Insurance / firm info (once applicable — PEER-INTEL §3)

- Business liability / professional indemnity policy #: _____________________
  (add once seeking enterprise clients; keep this field in every template)

## 9. Contact + emergency stop

- Client contact (1 business hour response): _______________________________
- Engaged party contact: __________________________________________________
- Emergency stop: any client reply "stop" halts testing immediately.

## 10. Addendum / amendments

Any change to scope, window, or price requires both signatures below.
(Future asset additions go here, BEFORE that asset is touched.)

| Date | Change | Client | Firm |
|---|---|---|---|
| | | | |

## Signatures

- Client: ______________________  Date: ______________
- Engaged party: ______________  Date: ______________

Quote attached: **pricing-questionnaire.md** (signed copy returned with this form).