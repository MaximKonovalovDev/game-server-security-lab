# Deploy Runbook — GCP e2-micro, Flax Linux Headless (July 2026)

Locked-in plan: **GCP e2-micro** (safe, no-reclamation always-free VM). Everything
below verified against official docs (GCP free-tier page updated 2026-07-21, GCP
network pricing page, Flax docs command-line-access).

Cost reality (before you start): the VM is $0 forever, but GCP now charges
**~$3.65/mo for the external IPv4** ($0.005/h; free tier covers only 1 h/mo) and
egress over **200 GiB/mo** (Standard Tier) at $0.085/GiB. A small game server:
**~$4–8/mo total**. Budget alert (step 8) keeps this visible.

---

## 0. Prereqs

- Your Flax project cookable (any platform) — server gameplay logic exists.
- You will do the cook + VM console steps yourself (console + SSH). This runbook
  is the exact recipe; paste blocks in order.

---

## 1. GCP account (10 min)

1. Go to `console.cloud.google.com/freetrial` → sign up (card required; $0–1 hold,
   not a charge). You get a $300 Welcome credit (90 days) + Free Tier access.
2. **Before day 90: upgrade to a Paid billing account** (Billing → Activate).
   - You keep the remaining credit and the Free Tier forever.
   - If you DON'T upgrade, the trial account auto-closes at day 90/credit end and
     your VM is **permanently deleted** (30-day grace, then gone). This is the
     #1 reason people "lose" their free GCP VM.
3. Free e2-micro is only free in **us-west1 (Oregon)**, **us-central1 (Iowa)**,
   **us-east1 (South Carolina)** — pick one (Oregon is fine for NA/EU mix).

## 2. Create the VM (console)

VM instances → Create instance:

- Name: `flax-server`
- Region/zone: one of the three above (e.g. `us-west1`)
- Machine type: **e2-micro** (always-free shape; 1 GB RAM — fine ≤ 32 players)
- Boot disk: **Ubuntu 24.04 LTS**, size **30 GB** (standard disk, free tier),
  untick the "increase size" trap
- Networking:
  - **Network tier: Standard** (⚠️ must pick Standard — Premium's free egress is
    only 1 GiB/mo; Standard's is 200 GiB/mo)
  - External IPv4: **Reserve a static IP** (≈$3.65/mo, stable address players use).
    Ephemeral IP is also billed now and changes on restart — don't.
- Firewall: create the VM (SSH 22 will be auto-allowed); add **UDP 7777** in step 3.

## 3. Firewall rules

VPC Network → Firewall → Create rule `allow-game-udp`:

- Targets: tagged instances (tag your VM `game-server`), or all
- IP ranges: `0.0.0.0/0`
- Protocols: **UDP, port 7777**
- (Leave SSH allowed for admin; everything else denied by default.)

## 4. Cook the Flax Linux headless build (on your Windows machine)

1. In Flax Editor: **Game Cooker** (Ctrl+Shift+B) → Platforms → enable **Linux**
   (if not already). Check the build preset has a Linux target, e.g. `Development.Linux`.
2. CLI cook (same thing, scriptable — works from cmd/PowerShell):
   ```
   "C:\Program Files (x86)\Flax\Flax_1.12\Binaries\Editor\Win64\Development\FlaxEditor.exe" -project "C:\flax\flax-mcp\samples\game-project" -headless -mute -null -std -build "Development.Linux"
   ```
   (Substitute your project path and preset/target name — `-build "Development.Linux"`
   means preset `Development`, target `Linux`.)
3. Output lands in `Output\Linux\x64\` (or your configured output dir) as a
   standalone folder with the game binary + `Data` + managed DLLs.
4. Smoke-test locally? Flax Linux builds run on Linux only — skip local test,
   test on the VM (step 6).

> Cross-cook note: Flax supports building Linux from Windows (native x64 binary,
> Mono runtime bundled). If the cook fails on missing Linux toolchain, install the
> Linux target via Game Cooker → it fetches the toolchain once.

## 5. Upload the build to the VM

```
scp -r "C:\flax\flax-mcp\samples\game-project\Output\Linux\x64\*" me@<VM_IP>:/home/me/flaxserver/
```

## 6. First run — the exact headless server command

SSH in (`gcloud compute ssh flax-server --zone=us-west1-a`), then:

```bash
cd ~/flaxserver
chmod +x ./GameProject_Linux_x64        # exact binary name varies
./GameProject_Linux_x64 -headless -mute -null -std
```

Flags (from Flax docs, verified):
- `-headless` — no windows; works in cooked desktop builds
- `-null` — Null render backend; **"highly recommended for headless server builds
  for multiplayer games"** (official wording)
- `-mute` — Null audio backend (no OpenAL needed)
- `-std` — logs to stdout (visible in SSH/journal)

First-run checklist:
- Logs show your server code starting (bind to UDP 7777; `NetworkBootstrapBase`
  in server mode — whatever mode flag your game uses must be passed too, e.g. a
  `-server` arg if you built one).
- If the binary won't start: `ldd ./GameProject_Linux_x64` and install missing
  libs (`sudo apt install` the names shown with "not found"). Headless needs none
  of X11/OpenGL/OpenAL when using `-null -mute`, but libc/libstdc++ must match —
  Ubuntu 24.04 + Flax 1.12 is a current pair.
- Test from your PC: `tools\raw-client\flax_enet.py 35.1xx.xx.xx` — handshake
  should complete against the real server.

## 7. Make it a service (survives reboot, restarts on crash)

`sudo nano /etc/systemd/system/flax-server.service`:

```ini
[Unit]
Description=Flax game server
After=network-online.target

[Service]
User=me
WorkingDirectory=/home/me/flaxserver
ExecStart=/home/me/flaxserver/GameProject_Linux_x64 -headless -mute -null -std -server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now flax-server
sudo journalctl -u flax-server -f     # live logs
```

## 8. Harden (fast path; full plan in SERVER-SECURITY.md)

```bash
sudo apt update && sudo apt install -y ufw fail2ban
sudo ufw allow 7777/udp && sudo ufw allow OpenSSH && sudo ufw enable
sudo ssh-keygen -A && sudo nano /etc/ssh/sshd_config   # PasswordAuthentication no
sudo systemctl restart ssh && sudo systemctl enable --now fail2ban
```

- Server runs as non-root (`User=me`) — done above.
- Apply the P0/P1 checklist from `SERVER-SECURITY.md` (ENet caps, rate limits,
  fail-closed handlers, connection limits) — same code runs on Linux.
- Budget alerts: Billing → Budgets → alert at $5/mo (catches IP+egress surprises).

## 9. Day-1 operations

- Redeploy: re-cook + `scp` over the new build + `sudo systemctl restart flax-server`.
- Backups: keep the cooked output + config in the private GitHub repo → fresh VM in
  ~10 min (steps 2–7).
- IP change: if you ever delete the static IP, reserve a new one and re-share.
- Scaling: >32 players or >200 GiB/mo → see HOSTING.md Phase 3 (VPS) or Oracle.

## 10. Kill switch / cost guardrails

- Stop VM anytime (billing for the IP continues — the IPv4 tax applies while the
  address is reserved even if the VM is stopped; release the static IP if you
  decommission).
- Watch `gcloud compute addresses list` (status `RESERVED` = still billed).
- Worst case to expect: 64-player full-broadcast ≈ 970 GiB/mo ≈ $65 egress —
  that's the signal to move to Oracle (10 TB free) or a cheap VPS.

## Verified sources

- GCP free tier limits (official, updated 2026-07-21): 1 non-preemptible e2-micro
  in us-west1/us-central1/us-east1; 30 GB disk; 1 GiB/mo egress (Premium).
- GCP network pricing (official, current): Standard Tier 200 GiB/mo free then
  $0.085/GiB; external IPv4 static+ephemeral $0.005/h (~$3.65/mo), free tier 1 h/mo.
- Flax docs "Command line access": `-headless`, `-mute`, `-null`, `-std`, `-build
  "Development.<Platform>"`, cross-cook pattern `-project <path> ... -build`.
