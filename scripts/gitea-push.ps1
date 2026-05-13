# Push to Gitea using GITEA_TOKEN from the environment (no token in git remote).
# Usage: .\scripts\gitea-push.ps1 [extra git push args, e.g. main or v1.5.0]
# Env: GITEA_TOKEN (required). GITEA_USER (default: kevyn). GITEA_REMOTE (default: origin).
#      GITEA_HOST (default: git.kevynwatkins.com). GITEA_REPO_PATH (default: kevyn/comfyui-flux2).

$ErrorActionPreference = "Stop"
if (-not $env:GITEA_TOKEN) {
    Write-Error "GITEA_TOKEN is not set. Set it in your user or system environment, then retry."
}
$user = if ($env:GITEA_USER) { $env:GITEA_USER } else { "kevyn" }
$hostName = if ($env:GITEA_HOST) { $env:GITEA_HOST } else { "git.kevynwatkins.com" }
$path = if ($env:GITEA_REPO_PATH) { $env:GITEA_REPO_PATH } else { "kevyn/comfyui-flux2" }

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$pushUrl = "https://${user}:$($env:GITEA_TOKEN)@${hostName}/${path}.git"
$refArgs = @($args)
if ($refArgs.Count -eq 0) {
    $branch = git symbolic-ref --short HEAD 2>$null
    if (-not $branch) { Write-Error "Not on a branch; pass ref(s) explicitly, e.g. .\scripts\gitea-push.ps1 main" }
    $refArgs = @($branch)
}

git push $pushUrl @refArgs
