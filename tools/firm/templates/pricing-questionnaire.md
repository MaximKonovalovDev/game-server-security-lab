# Pricing Questionnaire + Tier Table (template)

> Fill this BEFORE quoting. Price = f(this form) — PEER-INTEL §2 rule: when
> the answers change after signing, the re-scope is contractual, not a fight.
> Every answer here must match the scope-agreement §1 table.

## Client / job

- Client: ____________________  Date: ____________
- Purpose of engagement: [ ] one-time audit  [ ] fix + re-verify
  [ ] recurring/monitoring  [ ] pre-launch review  [ ] post-incident

## A. Web / site surface (T1)

1. Site URL(s): ________________________________________________
2. CMS/platform: [ ] WordPress  [ ] WooCommerce  [ ] Joomla  [ ] Drupal
   [ ] Shopify  [ ] custom  [ ] unknown
3. Theme used (if WP, e.g. Flatsome): _______________________________
4. Plugins/extensions count: [ ] <10  [ ] 10-30  [ ] 30+ (list majors)
5. Admin/backoffice exposed on the internet? [ ] yes [ ] no
6. eCommerce/payments on site? [ ] yes [ ] no  (PCI-relevant surface)
7. Subdomains / related sites in scope: ________________________________
8. Staging/preprod copies in scope? [ ] yes [ ] no

## B. Server / infra surface (T2)

9. OS: [ ] Linux (distro: ____) [ ] Windows  [ ] containerized (Docker/K8s)
10. Hosting: [ ] VPS (provider: ____)  [ ] shared host  [ ] on-prem  [ ] cloud
11. Public ports expected (firewall list): ______________________________
12. Services: web/Nginx/Apache, DB, mail, SSH — list: _____________________
13. Existing hardening done? [ ] none  [ ] partial  [ ] audit reports exist
14. Compliance target: [ ] none  [ ] ISO27001  [ ] PCI-DSS  [ ] SOC2  [ ] other

## C. Game / netcode surface (T3)

15. Engine + version (e.g. Flax 1.12, Unity, Godot): ______________________
16. Transport: [ ] UDP/ENet  [ ] TCP  [ ] WebSocket  [ ] Steamworks
17. Auth model: [ ] none/trust-client  [ ] token  [ ] challenge-response
18. Server authority: clients send [ ] inputs+tick  [ ] raw positions/state
19. Live population: [ ] not live  [ ] <100  [ ] 100-1000  [ ] 1000+
20. Cheat exposure so far (speed/dupe/aim reports): _______________________

## D. MCP / AI surface (T4)

21. Plugin/package + version: ___________________________________________
22. Transport: [ ] stdio  [ ] HTTP/SSE  [ ] Streamable HTTP  [ ] other
23. Auth on endpoint: [ ] none  [ ] token/env  [ ] OAuth  [ ] other
24. Tools exposed (count + categories): _________________________________
25. Who loads it: [ ] editor  [ ] agent/assistant  [ ] server daemon
26. Any LLM reads tool descriptions from content (prompt-injection surface)?

## E. Recurring plan (for retainer pricing)

27. Assets to re-scan monthly: A / B / C / D sections above (circle)
28. CVE-brief wants "CVEs affecting your stack" monthly? [ ] yes [ ] no
29. On-call response: [ ] none  [ ] business-hours  [ ] 24/7 (premium)
30. Incident response retainer slot? [ ] yes [ ] no

---

## Tier table (quote from here; prices = template default, tune to market)

| Tier | Scope (questionnaire sections) | Default price |
|---|---|---|
| T1-A | Site check: A only (scan.py + nuclei report) | $100-250 |
| T1-B | A + fix + re-scan verified | $300-800 |
| T2-A | Server hardening audit: B, report only (Lynis + checklist) | $400-800 |
| T2-B | B + applied hardening + re-audit verified | $800-1200 |
| T3 | Game netcode review: C (fuzz + cheat-class probes + fixes) | $800-2500 |
| T4 | MCP/AI audit: D (endpoint + dispatch + prompt-injection pass + fixes) | $500-1500 |
| IR | Post-incident cleanup: (breach scope) | $500-3000+ |
| R1 | Retainer: monthly re-scan (A/B/C/D per E27) + report | $50-100/mo |
| R2 | R1 + monthly CVE brief (E28) + config review | $150-300/mo |
| R3 | R2 + response window (E29) + quarterly deep audit | $500-1000/mo |

**LOE adjustments** (PEER-INTEL §2 tiering): +API surface → +25-50% (T1/T4);
+network CIDR ranges → +25% (T2); +mobile → +50%. Document EVERY adjustment
here before signing:

- Adjustment notes: ______________________________________________________
- Final quote: $____________ (fixed against scope-agreement §1)

## Signature block

- Quote valid 30 days. Client: ____________  Firm: ____________