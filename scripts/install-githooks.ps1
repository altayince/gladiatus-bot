param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

git -C $RepoRoot config core.hooksPath .githooks
Write-Host "Configured git hooks path to .githooks for $RepoRoot"
