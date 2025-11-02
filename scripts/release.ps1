param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = "",
    [switch]$SkipPublish,
    [switch]$SkipPackage
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [Parameter(Position = 0, Mandatory = $true, ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    & git @Args
    if ($LASTEXITCODE -ne 0) {
        $joined = $Args -join ' '
        throw "git command failed: git $joined"
    }
}

function Invoke-GhReleaseCreate {
    param(
        [string]$Version,
        [string]$Package,
        [string]$Notes
    )

    $ghCmd = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $ghCmd) {
        throw "GitHub CLI (gh) not found in PATH. Install or add to PATH, or run with -SkipPublish."
    }
    $ghPath = $ghCmd.Source

    $releaseExists = $false
    try {
        & $ghPath release view ("v{0}" -f $Version) 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) { $releaseExists = $true }
    } catch {
        $releaseExists = $false
    }

    if ($releaseExists) {
        Write-Host "Release v$Version exists. Deleting before recreating..."
        & $ghPath release delete ("v{0}" -f $Version) --yes
    }

    & $ghPath release create ("v{0}" -f $Version) $Package `
        --title ("MobileTestTool v{0}" -f $Version) `
        --notes $Notes
    if ($LASTEXITCODE -ne 0) {
        throw "gh release create failed"
    }
}

function Get-ReleaseNotes {
    param(
        [string]$NotesFile,
        [string]$RepoRoot,
        [string]$DefaultNotes = "- Add release notes here",
        [switch]$Trim
    )

    if (-not $NotesFile) {
        return $DefaultNotes
    }

    # 尝试作为绝对路径，如果不是则相对于项目根目录
    $notesPath = if ([System.IO.Path]::IsPathRooted($NotesFile)) {
        $NotesFile
    } else {
        $possiblePath = Join-Path $RepoRoot $NotesFile
        if (Test-Path $possiblePath) {
            $possiblePath
        } elseif (Test-Path $NotesFile) {
            $NotesFile
        } else {
            $null
        }
    }

    if ($notesPath) {
        $content = Get-Content $notesPath -Raw -Encoding UTF8
        if ($Trim) {
            return $content.Trim()
        } else {
            return $content
        }
    } else {
        return $DefaultNotes
    }
}

$repoRoot    = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$buildDir    = Join-Path $repoRoot "dist/MobileTestTool"
$packageDir  = Join-Path $repoRoot "dist"
$packageName = "MobileTestTool_$Version.zip"
$packagePath = Join-Path $packageDir $packageName
$manifestDir = Join-Path $repoRoot "releases"
$manifestPath = Join-Path $manifestDir "latest.json"

if (-not $SkipPackage) {
    Write-Host "=== step 1: run build_pyqt.bat ==="
    & (Join-Path $repoRoot "scripts\build_pyqt.bat")

    Write-Host "=== step 2: compress onedir folder ==="
    if (-not (Test-Path $buildDir)) {
        throw ("Build directory not found: {0}" -f $buildDir)
    }
    if (Test-Path $packagePath) {
        Remove-Item $packagePath
    }
    Compress-Archive -Path (Join-Path $buildDir "*") -DestinationPath $packagePath
    Write-Host ("Created package: {0}" -f $packagePath)
} else {
    Write-Host "=== step 1 & 2 skipped (SkipPackage enabled) ==="
    if (-not (Test-Path $packagePath)) {
        throw ("Existing package not found: {0}. Cannot continue with -SkipPackage." -f $packagePath)
    }
}

Write-Host "=== step 3: compute SHA256 ==="
$sha256 = (Get-FileHash $packagePath -Algorithm SHA256).Hash.ToLower()
Write-Host ("SHA256: {0}" -f $sha256)

Write-Host "=== step 4: generate latest.json ==="
if (-not (Test-Path $manifestDir)) {
    New-Item -ItemType Directory -Path $manifestDir | Out-Null
}

$downloadUrl = "https://github.com/pranvil/MobileTestTool/releases/download/v$Version/$packageName"
$releaseNotes = Get-ReleaseNotes -NotesFile $NotesFile -RepoRoot $repoRoot -DefaultNotes "- Add release notes here" -Trim

$manifest = [ordered]@{
    version       = $Version
    download_url  = $downloadUrl
    sha256        = $sha256
    file_name     = $packageName
    file_size     = (Get-Item $packagePath).Length
    release_notes = $releaseNotes
    published_at  = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    mandatory     = $false
}

$manifestJson = $manifest | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($manifestPath, $manifestJson + "`n", (New-Object System.Text.UTF8Encoding($false)))
Write-Host ("Manifest written to: {0}" -f $manifestPath)

Write-Host "=== step 5: summary ==="
Get-Content $manifestPath
Write-Host ""

if ($SkipPublish) {
    Write-Host "SkipPublish enabled. Packaging complete."
    return
}

Write-Host "=== step 6: git commit & push ==="
$filesToStage = @(
    "scripts/release.ps1",
    "config/latest.json.example",
    "releases/latest.json"
)

foreach ($file in $filesToStage) {
    $fullPath = Join-Path $repoRoot $file
    if (Test-Path $fullPath) {
        Invoke-Git "add" $file
    }
}

git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    Invoke-Git "commit" "-m" ("Prepare release v{0}" -f $Version)
} else {
    Write-Host "No staged changes. Skip commit."
}

Invoke-Git "push" "origin" "main"

Write-Host "=== step 7: tags & GitHub release ==="
$tagExists = $false
try {
    git rev-parse --verify ("refs/tags/v{0}" -f $Version) --quiet | Out-Null
    if ($LASTEXITCODE -eq 0) { $tagExists = $true }
} catch {
    $tagExists = $false
}

if ($tagExists) {
    Write-Host "Tag v$Version exists. Recreating..."
    Invoke-Git "tag" "-d" ("v{0}" -f $Version)
}

Invoke-Git "tag" "-a" ("v{0}" -f $Version) "-m" ("Release v{0}" -f $Version)
Invoke-Git "push" "origin" ("v{0}" -f $Version)

$notesForRelease = Get-ReleaseNotes -NotesFile $NotesFile -RepoRoot $repoRoot -DefaultNotes "## Release notes`n- TODO: update notes"

Invoke-GhReleaseCreate -Version $Version -Package $packagePath -Notes $notesForRelease

Write-Host "=== all done ==="