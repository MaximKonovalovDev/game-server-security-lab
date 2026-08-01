# attack-run.ps1 - orchestrator for a single attack run against the lab server.
#
# Usage:
#   .\attack-run.ps1 -Attack connect -ServerExe <path-to-server> [common params]
#
#   -Attack       mode passed to tools\raw-client\flax_enet.py
#                 (connect, craft, packet-soup, flood-connect, flood-request,
#                  chat-flood, fuzz)
#   -ServerExe    path to the game server executable (optional; if given the
#                 script launches it, waits for the port to open, attacks,
#                 then stops it)
#   -ServerArgs   extra args for the server (default: -stdout -log)
#   -Port         server UDP port (default 7777)
#   -AttackArgs   extra args forwarded to flax_enet.py
#   -Capture      capture traffic with tshark if available ($true/$false)
#   -OutDir       where reports/pcaps go (default ..\reports)
#
# The script always writes a JSON summary + the server's stdout/log tail to
# reports\run-<timestamp>\.

param(
    [Parameter(Mandatory = $true)][ValidateSet("connect", "craft", "packet-soup", "flood-connect", "flood-request", "chat-flood", "fuzz")]
    [string]$Attack,
    [string]$ServerExe = "",
    [string]$ServerArgs = "-stdout -log",
    [int]$Port = 7777,
    [string]$AttackArgs = "",
    [switch]$Capture = $false,
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$labRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $labRoot "reports" }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $OutDir "run-$stamp"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$summary = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    attack    = $Attack
    port      = $Port
    server    = $ServerExe
}

$serverProc = $null
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "python not found on PATH" }
try {
    # ---- 1. start server ---------------------------------------------------
    if ($ServerExe) {
        Write-Host "[*] starting server: $ServerExe $ServerArgs"
        $serverProc = Start-Process -FilePath $ServerExe -ArgumentList $ServerArgs `
            -RedirectStandardOutput (Join-Path $runDir "server-stdout.log") `
            -RedirectStandardError (Join-Path $runDir "server-stderr.log") `
            -WindowStyle Hidden -PassThru
        $summary.server_pid = $serverProc.Id

        $ready = $false
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep -Milliseconds 500
            if ($serverProc.HasExited) { break }
            # UDP readiness probe: a real ENet handshake beats Test-NetConnection (TCP-only)
            $probe = & $py.Source -c "import sys; sys.path.insert(0, r'$labRoot\tools\raw-client'); import flax_enet as f; c = f.EnetClient('127.0.0.1', $Port, timeout=1.0); sys.exit(0 if c.connect() else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        }
        if (-not $ready) {
            Write-Warning "[!] server did not open port $Port in 30s"
            if ($serverProc.HasExited) { Write-Warning "[!] server exited early" }
        } else {
            Write-Host "[+] server is listening on UDP $Port"
        }
        $summary.server_ready = $ready
    }

    # ---- 2. optional capture -----------------------------------------------
    $tshark = Get-Command tshark -ErrorAction SilentlyContinue
    $pcap = Join-Path $runDir "capture.pcapng"
    $tsharkProc = $null
    if ($Capture -and $tshark) {
        Write-Host "[*] capturing via tshark"
        $tsharkProc = Start-Process -FilePath $tshark.Source -ArgumentList @(
            "-i", "loopback", "-f", "udp port $Port", "-w", $pcap) -WindowStyle Hidden -PassThru
        Start-Sleep -Milliseconds 800
    }

    # ---- 3. run the attack --------------------------------------------------
    $clientArgs = @("$labRoot\tools\raw-client\flax_enet.py", "--mode", $Attack, "--port", $Port)
    if ($AttackArgs) { $clientArgs += ($AttackArgs -split " ") }
    $attackLog = Join-Path $runDir "attack-stdout.log"

    Write-Host "[*] running attack: $($clientArgs -join ' ')"
    $attackProc = Start-Process -FilePath $py.Source -ArgumentList $clientArgs `
        -RedirectStandardOutput $attackLog -RedirectStandardError "$runDir\attack-stderr.log" `
        -NoNewWindow -Wait -PassThru
    $summary.attack_exit_code = $attackProc.ExitCode
    $summary.attack_output = Get-Content -LiteralPath $attackLog -Raw

    # ---- 4. drain server logs ------------------------------------------------
    if ($serverProc) {
        Start-Sleep -Milliseconds 500
        $summary.server_stdout_tail = (Get-Content -LiteralPath (Join-Path $runDir "server-stdout.log") -ErrorAction SilentlyContinue | Select-Object -Last 80) -join "`n"
    }

    # ---- 5. save summary -----------------------------------------------------
    $summaryJson = Join-Path $runDir "summary.json"
    $summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $summaryJson -Encoding utf8
    Write-Host ""
    Write-Host "[+] run complete -> $runDir"
    Write-Host "    summary: $summaryJson"
    if ($Capture -and $tshark) {
        Write-Host "    pcap:    $pcap"
    }
}
finally {
    if ($tsharkProc -and -not $tsharkProc.HasExited) { Stop-Process -Id $tsharkProc.Id -Force -ErrorAction SilentlyContinue }
    if ($serverProc -and -not $serverProc.HasExited) {
        Write-Host "[*] stopping server (pid $($serverProc.Id))"
        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    }
}
