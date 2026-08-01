# Abuse Report Template (facts only — providers act on evidence, not opinions)

> Save as `reports/abuse/<provider>-<date>-<target>.md`. Fill every field you
> have; omit nothing, invent nothing. Attach the evidence PCAP (sha256).
> Legal frame: reporting abuse of OUR servers to the provider of the
> offending IP/service. Never demand action — state facts.

## Subject
- Provider / platform: (Discord, hosting company, VPN service, tunnel service, cheat repo host)
- Attacker IP(s): 
- Reported entity: (IP, Discord server/account, domain, repo, tunnel id)

## Facts (all from our own logs)
- Incident timestamps (UTC): start / end
- Target service: (our game server, IP:port, server name)
- Attack type: (UDP flood / forged packets / login abuse / harassment)
- Peak rate observed: (packets/s, bytes/s — from our per-server agent)
- Duration: 
- Evidence: `evidence/<case>/<pcap files>` — sha256 hash(es):
- Replay/parse notes: (dissector version, how the PCAP was captured)

## Attacker-observed detail
- Distinct source IPs / ports: 
- IP geolocation / ASN (if resolved via public lookup): 
- Tool signatures (protocol DNA, mutation grammar, UA strings if web): 
- Linked identities observed (accounts, Discord handles, tokens) — only
  what WE observed, never speculating:
- Pattern/notes: (repeat visits, behavior evolution, post-ban return)

## Policy / rule references (quote or link the provider rule broken)

## Consent + contact
- Reporter: (operator of the target server)
- Contact: (email/Discord for provider follow-up)
- Date:

## Checklist before sending
- [ ] Facts only: no opinions, no demands, no "please ban forever"
- [ ] No third-party data in the report (only our observations + public lookups)
- [ ] PCAP hashes match the files attached
- [ ] No retaliatory framing — this is a provider-rule abuse report
