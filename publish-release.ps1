param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = ""
)

$ErrorActionPreference = "Stop"

$repoRoot   = Split-Path -Parent $MyInvocation.MyCommand.Path
$packageDir = Join-Path $repoRoot "dist"
$package    = Join-Path $packageDir ("MobileTestTool_{0}.zip" -f $Version)
$manifest   = Join-Path $repoRoot "releases/latest.json"

if (-not (Test-Path $package)) {
    throw "Package not found: $package"
}
if (-not (Test-Path $manifest)) {
    throw "Manifest not found: $manifest"
}

Write-Host "=== step 1: add and commit files ==="
git add release.ps1 publish-release.ps1 releases/latest.json config/latest.json.example
if (-not (git diff --cached --quiet)) {
    git commit -m ("Prepare release v{0}" -f $Version)
} else {
    Write-Host "No staged changes. Skip commit."
}

Write-Host "=== step 2: push main ==="
git push origin main

Write-Host "=== step 3: create tag v$Version ==="
if (git rev-parse "refs/tags/v$Version" -q) {
    Write-Host "Tag v$Version exists. Recreate it."
    git tag -d ("v{0}" -f $Version)
    git push origin --delete ("refs/tags/v{0}" -f $Version) 2>$null
}
git tag -a ("v{0}" -f $Version) -m ("Release v{0}" -f $Version)
git push origin ("v{0}" -f $Version)

Write-Host "=== step 4: create GitHub release ==="
$notes = if ($NotesFile -and (Test-Path $NotesFile)) {
    Get-Content $NotesFile -Raw
} else {
    "## Release notes`n- TODO: update notes"
}

gh release create ("v{0}" -f $Version) $package `
    --title ("MobileTestTool v{0}" -f $Version) `
    --notes $notes

Write-Host "=== done ==="