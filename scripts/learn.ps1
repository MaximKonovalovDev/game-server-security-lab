# learn.ps1 - run the self-learning harvest (docs/SELF-LEARN.md).
#
# Usage:
#   .\learn.ps1              # harvest everything -> docs/LEARNING-LOG.md
#   .\learn.ps1 -Since 7     # only runs younger than 7 days
#   .\learn.ps1 -DryRun      # preview without writing

param(
    [int]$Since = 0,
    [switch]$DryRun = $false
)

$labRoot = Split-Path -Parent $PSScriptRoot
$harvest = Join-Path $labRoot "tools\self-learn\harvest.py"

& python $harvest $(if ($Since) { @("--since", $Since) }) $(if ($DryRun) { @("--dry-run") })
