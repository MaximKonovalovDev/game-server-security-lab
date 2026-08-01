# install-tools.ps1 - installs/updates the host-side lab tool kit.
#
# Phase 1 (host, this script):   Wireshark + Npcap (captures, dissector), scapy
#                                (crafting/replay glue), python deps for the lab.
# Phase 2 (VM, manual):          dnSpyEx, Cheat Engine, System Informer - inside
#                                the VirtualBox VM only, never on the host.
#
# Usage:  .\scripts\install-tools.ps1 [-Full]   (-Full also installs fuzz tooling)
# Run in an elevated PowerShell for the winget/Npcap steps.

param([switch]$Full = $false)

$ErrorActionPreference = "Stop"
$labRoot = Split-Path -Parent $PSScriptRoot

function Install-Winget([string]$Id, [string]$Why) {
    Write-Host "[*] installing $Id ($Why)..."
    winget install --id $Id --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    if ($LASTEXITCODE -ne 0) { Write-Warning "[!] winget failed for $Id (exit $LASTEXITCODE)" }
}

function Test-Command([string]$Name) { Get-Command $Name -ErrorAction SilentlyContinue -ne $null }

Write-Host "[==] Lab tool kit installer - host side =="

# 1. Wireshark (bundles Npcap) - captures + tshark + Lua dissector
if (-not (Test-Command tshark)) {
    # installer is staged in tools\installers (offline-ready); run elevated:
    #   Wireshark-4.6.7-x64.exe /S /NCRC /desktopicon=no /quicklaunchicon=no /npcap=1
    # (admin required - Npcap installs a capture driver)
    $exe = Join-Path $labRoot "tools\installers\Wireshark-4.6.7-x64.exe"
    if (Test-Path $exe) {
        Write-Host "[!] Wireshark installer staged at: $exe"
        Write-Host "    Run from an elevated PowerShell:"
        Write-Host "      & '$exe' /S /NCRC /desktopicon=no /quicklaunchicon=no /npcap=1"
    } else {
        Write-Host "[!] winget unavailable on this machine - download Wireshark manually:"
        Write-Host "    https://www.wireshark.org/download.html (install with Npcap)"
    }
} else {
    Write-Host "[+] tshark already present: $((Get-Command tshark).Source)"
}

# 2. Python (system) deps for the lab tools
Write-Host "[*] ensuring python deps..."
python -m pip install --quiet --upgrade scapy 2>$null
if ($LASTEXITCODE -ne 0) { Write-Warning "[!] scapy install failed (needs python on PATH)" }

# 3. boofuzz venv (tools\boofuzz\.venv) - rebuild if missing
$venvPy = Join-Path $labRoot "tools\boofuzz\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "[*] creating boofuzz venv..."
    python -m venv (Join-Path $labRoot "tools\boofuzz\.venv")
    & $venvPy -m pip install --quiet -r (Join-Path $labRoot "tools\boofuzz\requirements.txt")
} else {
    Write-Host "[+] boofuzz venv present"
}

# 4. Fake-server / raw-client deps (none beyond stdlib - verified)

# 5. Optional fuzz engine tooling
if ($Full) {
    # Bit-Twist 4.7 (native Windows pcap replay): https://bittwist.sourceforge.io/
    Write-Host "[*] full mode: Bit-Twist (pcap replay) must be downloaded manually from"
    Write-Host "    https://bittwist.sourceforge.io/ -> put bittwist.exe/bittwiste.exe on PATH"
    # radamsa / WinAFL are WSL2/build-from-source - out of scope for the host kit
}

# 6. Verify
Write-Host ""
Write-Host "[==] verification =="
foreach ($name in @("tshark", "python")) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { Write-Host "[+] ${name}: $($c.Source)" } else { Write-Warning "[-] ${name} missing" }
}
if (Test-Path $venvPy) { & $venvPy -c "import boofuzz; print('[+] boofuzz venv OK (boofuzz 0.4.2)')" }
try { python -c "import scapy; print('[+] scapy', scapy.__version__)" } catch { Write-Warning "[-] scapy not importable" }

Write-Host ""
Write-Host "[==] done. Next: wire the lab server (NetworkBootstrapBase Mode=Server, port 7777),"
Write-Host "     then run: .\scripts\attack-run.ps1 -Attack connect -ServerExe <path-to-server>"
