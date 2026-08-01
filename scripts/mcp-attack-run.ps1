# mcp-attack-run.ps1 - orchestrator for MCP attack runs against the FlaxMCP
# plugin's local editor endpoint (http://localhost:8765/mcp).
#
# Doctrine: local editor instance ONLY (docs/MCP-ATTACK-LAB.md). The plugin
# runs inside the editor process, so this script never launches a server -
# it attacks whatever is listening on the MCP port.
#
# Usage:
#   .\mcp-attack-run.ps1 -Group auth                # no token needed
#   .\mcp-attack-run.ps1 -Group transport -Token $env:FLAXMCP_TOKEN
#   .\mcp-attack-run.ps1 -Group dispatch -Token $env:FLAXMCP_TOKEN
#   .\mcp-attack-run.ps1 -Group supply-chain         # offline, no endpoint
#   .\mcp-attack-run.ps1 -Group all -Token $env:FLAXMCP_TOKEN
#
# Writes reports\FINDINGS-MCP-<timestamp>\ per findings format
# (docs/MCP-ATTACK-LAB.md section 5): facts-only JSON lines + summary.

param(
    [ValidateSet("auth", "transport", "dispatch", "supply-chain", "all")]
    [string]$Group = "auth",
    [string]$Token = "",
    [string]$Url = "http://localhost:8765/mcp",
    [int]$Count = 8,
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$labRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $labRoot "reports" }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $OutDir "FINDINGS-MCP-$stamp"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$py = Join-Path $labRoot "tools\mcp-attacker\.venv\Scripts\python.exe"
$attack = Join-Path $labRoot "tools\mcp-attacker\mcp_attack.py"

function Invoke-Mode {
    param([string]$Mode, [string[]]$Extra)
    $args = @($attack, "--mode", $Mode, "--url", $Url, "--count", $Count) + $Extra
    if ($Token) { $args += @("--token", $Token) }
    $jsonLines = & $py @args 2>&1
    $jsonLines | Where-Object { $_ -match '^\{' } | Set-Content -Path (Join-Path $runDir "mode-$Mode.jsonl")
    $n = ($jsonLines | Where-Object { $_ -match '^\{' }).Count
    Write-Host "[*] $Mode -> $n result line(s) -> mode-$Mode.jsonl"
}

function Test-EndpointAlive {
    try {
        $r = Invoke-WebRequest -Uri "$Url" -Method Get -TimeoutSec 3 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

$alive = Test-EndpointAlive
if (-not $alive -and $Group -ne "supply-chain") {
    Write-Warning "MCP endpoint $Url not answering. Start the Flax editor with the plugin first (localhost:8765)."
    Write-Warning "Supply-chain group can still run offline."
}

switch ($Group) {
    "auth" {
        Invoke-Mode "no-token" @("--count", [string]$Count)
        Invoke-Mode "wrong-token" @("--count", [string]($Count * 2))
        Invoke-Mode "env-probe"
        if ($Token) { Invoke-Mode "timing" @("--count", [string]($Count * 10)) }
    }
    "transport" {
        Invoke-Mode "origin-spoof"
        Invoke-Mode "method-fuzz"
        Invoke-Mode "batch"
        Invoke-Mode "openapi"
        Invoke-Mode "endpoints"
        if ($Token) {
            Invoke-Mode "flood" @("--concurrency", "64", "--count", "64")
            Invoke-Mode "sse"
        }
    }
    "dispatch" {
        if (-not $Token) { throw "dispatch group needs -Token (policy gates require auth)" }
        Invoke-Mode "baseline"
        Invoke-Mode "arg-bombs"
    }
    "supply-chain" {
        # offline: metadata/poisoning audits against repo config + templates.
        # NOTE: vendored mcpwn spawns MCP servers via command (stdio) - it cannot
        # point at the editor's HTTP listener; use it against any MCP server we
        # build ourselves (e.g. a test server). Docs: TRICKS.md B9-B12.
        $pluginJson = "C:\flax\flax-mcp\plugins\security\flaxmcp-plugin.json"
        if (Test-Path $pluginJson) {
            Write-Host "[*] manual audit -> $pluginJson (checklist: docs/TRICKS.md B9-B12, docs/BUILD-MCP-PLUGIN.md section 6)"
        } else {
            Write-Host "[!] $pluginJson not found - supply-chain scan skipped (game repo not synced?)"
        }
        Write-Host "[*] optional (needs uv): uvx snyk-agent-scan@latest --json  (scans MCP configs on machine)"
        Write-Host "[*] optional (mcpwn, stdio-spawned servers only):"
        Write-Host "    tools/mcp-attacker/.venv/Scripts/python.exe tools/mcp-attacker/mcpwn/mcpwn.py --safe-mode <server-command>"
    }
    "all" {
        Invoke-Mode "no-token" @("--count", [string]$Count)
        Invoke-Mode "wrong-token" @("--count", [string]($Count * 2))
        Invoke-Mode "env-probe"
        Invoke-Mode "origin-spoof"
        Invoke-Mode "method-fuzz"
        Invoke-Mode "batch"
        Invoke-Mode "openapi"
        Invoke-Mode "endpoints"
        if ($Token) {
            Invoke-Mode "baseline"
            Invoke-Mode "timing" @("--count", [string]($Count * 10))
            Invoke-Mode "flood" @("--concurrency", "64", "--count", "64")
            Invoke-Mode "sse"
            Invoke-Mode "arg-bombs"
        }
    }
}

Write-Host ""
Write-Host "[*] done -> $runDir"
Write-Host "[*] next: review mode-*.jsonl, then write FINDINGS-MCP-001.md per docs/MCP-ATTACK-LAB.md section 5"
