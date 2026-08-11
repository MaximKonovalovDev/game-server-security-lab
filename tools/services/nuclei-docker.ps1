# nuclei-docker.ps1 - run nuclei (official image) against an authorized target.
#
# Docker route (user decision 2026-08-01): no native nuclei binary on the
# lab machine (Defender flags the official build as HackTool - hash-verified
# false positive). Scanner runs container-isolated on the deploy host.
#
# Usage (deploy host with Docker):
#   .\nuclei-docker.ps1 -Target https://customer-site.com -OutDir .\results
#   .\nuclei-docker.ps1 -Target https://site -Severity high,critical -OutDir .\results
#
# Requires: docker (Windows: Docker Desktop with WSL2 backend, or Linux host).

param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$Severity = "low,medium,high,critical",
    [string]$OutDir = "results",
    [string]$Templates = "templates",
    [switch]$UpdateTemplates = $true
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker not found. Install Docker Desktop (WSL2 backend) or run on a Linux deploy host."
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $Templates | Out-Null

$mounts = @(
    "-v", "${PWD}:/work",
    "-v", "${PWD}\templates:/root/nuclei-templates"
)

if ($UpdateTemplates) {
    & docker run --rm @mounts projectdiscovery/nuclei:latest -update-templates 2>&1 | Select-Object -Last 2
}

& docker run --rm @mounts projectdiscovery/nuclei:latest `
    -u $Target `
    -severity $Severity `
    -jsonl -output "/work/nuclei-findings.jsonl" `
    -silent 2>&1 | Select-Object -First 30

Write-Host ""
Write-Host "[*] findings: $OutDir\nuclei-findings.jsonl"
Write-Host "[*] merge with scan.py findings -> triage -> fix plan (docs/SERVICES-PLATFORM.md)"
