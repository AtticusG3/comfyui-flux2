# Prune GHCR versions and GitHub releases (dry run by default).
# Requires: gh auth with read:packages, delete:packages, repo scope.
# Usage:
#   .\scripts\cleanup-registry.ps1              # dry run
#   .\scripts\cleanup-registry.ps1 -Apply       # delete

param(
    [switch]$Apply,
    [int]$MinDownloads = 2,
    [switch]$SkipGhcr,
    [switch]$SkipReleases
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$args = @(
    "scripts/registry_cleanup.py",
    "--min-downloads", "$MinDownloads"
)
if ($Apply) { $args += "--apply" }
if ($SkipGhcr) { $args += "--skip-ghcr" }
if ($SkipReleases) { $args += "--skip-releases" }

Push-Location $root
try {
    python @args
} finally {
    Pop-Location
}
