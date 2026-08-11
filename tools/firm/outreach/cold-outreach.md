# Cold outreach templates — copy, personalize 1 line, send

## 1. Indie multiplayer devs (game netcode reviews, $800-2500)

Subject: Free 20-min look at your netcode security (no strings)

```
Hi {dev},

I audit multiplayer game servers — specifically netcode that trusts the
client. I noticed {game} uses {ENet/UDP/WebSocket + engine}. A quick story:
cheaters killed real games (APB, H1Z1, The Cycle: Frontier), and the usual
first holes are: client-authoritative movement (speedhack/teleport by packet
edit), forged combat packets, unbounded connect floods.

I'll spend 20 minutes on a free, authorized look at your server — you'll get
whatever I find, no charge, whether or not you hire me. If you want, a full
review is a fixed-price scope (you approve the asset list first — nothing
scanned without your sign-off).

Want me to take that first look?
```

## 2. MCP server / AI plugin authors ($500-1500)

Subject: Your MCP server is probably answering unauthenticated calls

```
Hi {author},

Quick one: I audited a live MCP endpoint this week and it answered
tools/list AND tools/call with no token — 200 + full tool list, expected 401.
Your {plugin/server} is {transport + auth model}.

If you're selling or publishing an MCP server, an audit report is a sales
weapon: buyers are starting to ask for them, and the ones with evidence win.

Fixed-price audit: endpoint auth, dispatch validation, prompt-injection
corpus pass, written report. Your asset list, your sign-off first. Free
first-look if you want.

Proof of work: {link to writeup once published}
```

## 3. Local WordPress/e-commerce shops (T1 scans, $100-250)

Subject: {Shop} — quick security check, 10 minutes

```
Hi {owner},

I audit small business websites. {Shop} runs {WordPress/WooCommerce — found
by visiting}. Most shops in your area have: no HSTS, admin exposed, old
plugins. One checkout breach costs more than a year of scans.

Offer: I'll run a free authorized check of {yourdomain} — you get a short
report of what I found. If you want fixes applied + verified re-scan, that's
a fixed price you approve first.

Want the free check?
```

## Rules (non-negotiable — docs/PEER-INTEL.md)
- Send ONLY after checking the target is theirs/authorized (for devs: they
  own the repo/server; for shops: they own the domain).
- Free look = still needs their "yes" in writing (email reply is fine).
- Never attach scans to the outreach; never scan before the yes.
- Tone: neutral, helpful, zero "your site is garbage" energy.
