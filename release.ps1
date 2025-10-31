param(
    [string]$Version = "0.9.3"
)

$ErrorActionPreference = "Stop"

$repoRoot    = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildDir    = Join-Path $repoRoot "dist/MobileTestTool_PyQt5"
$packageDir  = Join-Path $repoRoot "dist"
$packageName = "MobileTestTool_$Version.zip"
$packagePath = Join-Path $packageDir $packageName
$manifestDir = Join-Path $repoRoot "releases"
$manifestPath = Join-Path $manifestDir "latest.json"

Write-Host "=== step 1: run build_pyqt.bat ==="
& (Join-Path $repoRoot "build_pyqt.bat")

Write-Host "=== step 2: compress onedir folder ==="
if (-not (Test-Path $buildDir)) {
    throw ("Build directory not found: {0}" -f $buildDir)
}
if (Test-Path $packagePath) {
    Remove-Item $packagePath
}
Compress-Archive -Path (Join-Path $buildDir "*") -DestinationPath $packagePath
Write-Host ("Created package: {0}" -f $packagePath)

Write-Host "=== step 3: compute SHA256 ==="
$sha256 = (Get-FileHash $packagePath -Algorithm SHA256).Hash.ToLower()
Write-Host ("SHA256: {0}" -f $sha256)

Write-Host "=== step 4: generate latest.json ==="
if (-not (Test-Path $manifestDir)) {
    New-Item -ItemType Directory -Path $manifestDir | Out-Null
}

$downloadUrl = "https://github.com/pranvil/MobileTestTool/releases/download/v$Version/$packageName"
$releaseNotes = @"
- Add your release notes here
"@

$manifest = [ordered]@{
    version       = $Version
    download_url  = $downloadUrl
    sha256        = $sha256
    file_name     = $packageName
    file_size     = (Get-Item $packagePath).Length
    release_notes = $releaseNotes.Trim()
    published_at  = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    mandatory     = $false
}

$manifest | ConvertTo-Json -Depth 3 | Out-File $manifestPath -Encoding UTF8
Write-Host ("Manifest written to: {0}" -f $manifestPath)

Write-Host "=== step 5: summary ==="
Get-Content $manifestPath
Write-Host ""
git status -sb