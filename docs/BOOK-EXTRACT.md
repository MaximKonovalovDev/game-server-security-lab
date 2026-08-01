# Curated Extract — the-book-of-secret-knowledge

Source: https://github.com/trimstray/the-book-of-secret-knowledge (236k stars, MIT)
Extracted 2026-07-31. NOT a dump — only the picks that matter for **securing a
Flax Engine multiplayer game server**. The full book covers far more (sysadmin
one-liners, every CLI tool in existence); browse the original for anything not
here. Organized by when you'll need it.

---

## 1. CORE — network analysis & crafting (Phase 1, use now)

From **CLI Tools > Network**: capture, craft, and probe on the wire.

| Tool | Why |
|---|---|
| **nmap** | scan what the test host exposes; baseline before/after |
| **masscan / zmap** | fast port discovery when you have many test hosts |
| **hping3** | custom-crafted TCP/UDP packets + flood simulations (SYN flood, etc.) |
| **mtr** | ping + traceroute combined (server-to-player routing checks later) |
| **netcat / socat** | raw UDP/TCP one-liners; socat = bidirectional relays/proxies |
| **tcpdump / tshark / Termshark** | capture loopback/VM traffic; tshark for scripting |
| **ngrep** | grep the network layer — quick pattern checks on live traffic |
| **bmon / vnstat / iptraf-ng** | traffic volume monitoring during load tests |
| **iPerf3 / ethr** | bandwidth measurement for server capacity planning |
| **Scapy** | L3/L4 packet crafting in Python (floods, fragmentation, spoofing) |
| **netsniff-ng** | high-speed capture/analysis kit |
| **Nemesis / packetfu** | packet injection/manipulation |

From **CLI Tools > Network (DNS)**: subfinder, Sublist3r, amass, massdns,
dnstwist — for OSINT on YOUR OWN domains/backend when the game grows a web layer.
DNS tooling matters when you have matchmaking/auth servers.

From **CLI Tools > Network (HTTP)**: curl, HTTPie, wuzz (interactive HTTP),
wrk/hey/vegeta/bombardier (HTTP load testing — for backend APIs), gobuster
(directory busting if you host web assets), Hurl (scriptable HTTP testing).
Burp/ZAP from the pentest chapter are the deeper HTTP tools.

From **CLI Tools > SSL**: testssl.sh, sslyze, sslscan, cipherscan (TLS auditing
for any HTTPS services), certbot + mkcert (certs), ssl-cert-check (expiry
watching). Only needed when backend HTTPS exists.

From **Web Tools > SSL/Security**: SSLLabs, crt.sh, securityheaders.com,
CSP Evaluator, urlscan.io, urlvoid — same: when the backend ships.

## 2. HACKING/PENTESTING arsenal (Phase 1-2, the attack library)

From **Hacking/Penetration Testing > Pentesters arsenal tools**:

| Tool | Why for your lab |
|---|---|
| **Burp Suite / OWASP ZAP / mitmproxy** | HTTP interception/replay — for your future backend APIs (auth, matchmaking, leaderboards) |
| **sqlmap** | SQLi testing on backend |
| **Nikto2** | web server scanning |
| **fuzzdb** | attack-pattern dictionary for fault injection (payload fodder) |
| **AFL++ / syzkaller** | coverage-guided fuzzing — overkill for game UDP; boofuzz/radamsa (ARSENAL.md) are the right size |
| **Ghidra / Cutter / radare2** | reverse engineering (native engine internals; Phase 2 VM) |
| **pwntools** | CTF-style exploit dev library — the mental model for "craft the perfect malicious payload" |
| **john / hashcat** | password cracking — for when you handle player passwords: prove your own hash choices |
| **yara** | pattern matching — scan client for cheat signatures later (Phase 3) |
| **exploitdb** | CVE archive for engine/server dependencies |
| **OWASP Threat Dragon** | threat modeling diagrams — plan the game's trust boundaries on paper |

From **Pentests bookmarks collection** (knowledge stacks):
- **PayloadsAllTheThings** — the payload bible (web)
- **OWASP Cheat Sheet Series** — every hardening topic
- **Cheatsheet-God** — pentest reference bank
- **GTFOBins** — Unix binary privilege escalation
- **Awesome-Hacking (HackWithGithub)** — the meta index
- **h4cker (The-Art-of-Hacking)** — thousands of security resources
- **PENTESTING-BIBLE** — huge resource collection

From **Wordlists and Weak passwords**: SecLists (the standard), Probable-Wordlists
(probability-sorted). Use for: username/login attack testing on your future auth,
and to ensure your own reject-lists reject common passwords.

From **Web Training Apps (local installation)** — skills for free, no risk:
DVWA, OWASP Juice Shop, metasploitable2/3, vulhub, SecurityShepherd. These teach
the web-attack skills you'll reuse on your backend layer. **Pwn Adventure 3**
(ARSENAL.md) is the *game-specific* training ground.

## 3. SYSTEMS/hardening (Phase 3 — hosting)

From **Systems/Services**: Nginx, HAProxy (reverse proxy patterns; HAProxy
fronts a game server for TCP), security/hardening resources (SELinux, AppArmor,
grapheneX, DevSec hardening) — for a Linux VPS deploy.
From **Manuals/Howtos > System hardening**: hardening guides in the book's
manuals chapter (CIS-style) — pair with dedicatedgameservers.net checklist
(ARSENAL.md B4).
From **Containers/Orchestration**: Docker bench / container security if you
containerize matchmaking/backend workers.

## 4. DAILY KNOWLEDGE (ongoing awareness)

From **Your daily knowledge and news > Security**: The Hacker News, DARKReading,
Packet Storm, Security Newsletter (weekly email), Reddit r/hacking,
publiclyDisclosed (twitter). 10 minutes a day keeps you aware of the
engine/server CVEs that matter.

## 5. SHELL ONE-LINERS / TRICKS / FUNCTIONS (the sleeper skill)

The book's **Shell One-liners** section (hundreds of one-liners) + **Shell
Tricks** + **Shell Functions** are the power skill for this whole project:
- every orchestrator script, log-grep, packet-pipeline, and server task gets 10x faster
- includes a massive network-diagnostics one-liner collection (curl flags,
  netcat variants, tcpdump recipes) that directly serve Phase 1 capture/attack work
- source: https://github.com/trimstray/the-book-of-secret-knowledge#shell-one-liners

**Recommendation:** keep a copy of the original book's README in
`tools/book-of-secret-knowledge.md` (download the raw README once) so the
one-liner chapter is searchable offline.

## 6. INSPIRING LISTS (meta-indexes)

From **Inspiring Lists > Security/Pentesting**: awesome-pentest, Awesome-Hacking,
awesome-cyber-skills, awesome-bug-bounty, awesome-ctf — when you need a deeper
rabbit hole, start here. From **Manuals/Howtos > Security & Privacy**: the
book's collected guides.

---

## Not relevant to your stack (skip)
- TOR/IRC/messenger tools, password managers, most Linux sysadmin CLIs (for now)
- Kubernetes/Docker-heavy orchestration (until you host backends)
- Mail/DNS server operations chapters (bookmark for VPS phase)
