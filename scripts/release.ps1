param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = "",
    [switch]$SkipPublish,
    [switch]$SkipPackage,
    [string]$GiteeOwner = "",
    [string]$GiteeRepo = "",
    [string]$GiteeToken = ""
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

    # Check if GitHub CLI is authenticated
    $authStatus = & $ghPath auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: GitHub CLI is not authenticated." -ForegroundColor Red
        Write-Host "Please run: gh auth login" -ForegroundColor Yellow
        Write-Host "Or set the GH_TOKEN environment variable with a GitHub API token." -ForegroundColor Yellow
        throw "GitHub CLI authentication required. Run 'gh auth login' or set GH_TOKEN environment variable."
    }

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

    # Write notes to temp file to properly handle multi-line text and special characters
    $tempNotesFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempNotesFile, $Notes, (New-Object System.Text.UTF8Encoding($false)))
        & $ghPath release create ("v{0}" -f $Version) $Package --title ("MobileTestTool v{0}" -f $Version) --notes-file $tempNotesFile
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: GitHub release creation failed." -ForegroundColor Red
            Write-Host "Please check:" -ForegroundColor Yellow
            Write-Host "  1. GitHub CLI is authenticated (run: gh auth login)" -ForegroundColor Yellow
            Write-Host "  2. You have permission to create releases in this repository" -ForegroundColor Yellow
            Write-Host "  3. Network connection is working" -ForegroundColor Yellow
            throw "gh release create failed. Check authentication and permissions."
        }
    } finally {
        if (Test-Path $tempNotesFile) {
            Remove-Item $tempNotesFile -Force
        }
    }
}

function Invoke-GiteeReleaseCreate {
    param(
        [string]$Version,
        [string]$Package,
        [string]$Notes,
        [string]$Owner,
        [string]$Repo,
        [string]$Token
    )

    if (-not $Owner -or -not $Repo -or -not $Token) {
        Write-Warning "Gitee release skipped: Missing Owner, Repo, or Token. Please provide -GiteeOwner, -GiteeRepo, and -GiteeToken parameters."
        return
    }

    Write-Host "Creating Gitee release for v$Version..."

    # Gitee API endpoint (access_token as query parameter)
    $apiBaseUrl = "https://gitee.com/api/v5/repos/$Owner/$Repo"
    $apiUrl = "$apiBaseUrl/releases?access_token=$Token"
    
    # Check if release exists
    $checkUrl = "$apiBaseUrl/releases/tags/v$Version?access_token=$Token"
    $headers = @{
        "Content-Type" = "application/json"
    }

    try {
        $response = Invoke-RestMethod -Uri $checkUrl -Method Get -Headers $headers -ErrorAction SilentlyContinue
        if ($response -and $response.id) {
            Write-Host "Release v$Version exists. Deleting before recreating..."
            $deleteUrl = "$apiBaseUrl/releases/$($response.id)?access_token=$Token"
            Invoke-RestMethod -Uri $deleteUrl -Method Delete -Headers $headers
        }
    } catch {
        # Release doesn't exist, continue
    }

    # Create release
    $releaseBody = @{
        tag_name = "v$Version"
        name = "MobileTestTool v$Version"
        body = $Notes
        prerelease = $false
    } | ConvertTo-Json -Depth 3

    try {
        $releaseResponse = Invoke-RestMethod -Uri $apiUrl -Method Post -Headers $headers -Body $releaseBody -ContentType "application/json"
        Write-Host "Gitee release created: $($releaseResponse.html_url)" -ForegroundColor Green
        
        # Gitee API file upload is complex, so we'll prompt for manual upload
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host "Gitee Release created successfully!" -ForegroundColor Green
        Write-Host "Release URL: $($releaseResponse.html_url)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Please manually upload the package file:" -ForegroundColor Yellow
        Write-Host "  1. Open: $($releaseResponse.html_url)" -ForegroundColor Cyan
        Write-Host "  2. Click 'Upload Attachment' button" -ForegroundColor Cyan
        Write-Host "  3. Select file: $Package" -ForegroundColor Cyan
        Write-Host "  4. Wait for upload to complete" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Package file location: $Package" -ForegroundColor White
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host ""
    } catch {
        Write-Error "Failed to create Gitee release: $_"
        throw
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

    # Try as absolute path, if not then relative to project root
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

$repoRoot    = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$buildDir    = Join-Path $repoRoot "dist/MobileTestTool"
$packageDir  = Join-Path $repoRoot "dist"
$packageName = "MobileTestTool_$Version.zip"
$packagePath = Join-Path $packageDir $packageName
$manifestDir = Join-Path $repoRoot "releases"
$manifestPath = Join-Path $manifestDir "latest.json"
$versionFile = Join-Path $repoRoot "core\version.py"

# Update version number
Write-Host "=== step 0: update version.py ==="
if (-not (Test-Path $versionFile)) {
    throw "Version file not found: $versionFile"
}

$versionContent = Get-Content $versionFile -Raw -Encoding UTF8

# Use single quotes for regex to avoid escaping issues
$oldVersion = $null
if ($versionContent -match 'APP_VERSION = "([^"]+)"') {
    $oldVersion = $matches[1]
}

if ($oldVersion -and $oldVersion -ne $Version) {
    Write-Host "Updating version from $oldVersion to $Version"

    $versionPattern     = 'APP_VERSION = "[^"]+"'
    $versionReplacement = 'APP_VERSION = "' + $Version + '"'

    $versionContent = $versionContent -replace $versionPattern, $versionReplacement
    [System.IO.File]::WriteAllText(
        $versionFile,
        $versionContent,
        (New-Object System.Text.UTF8Encoding($false))
    )
    Write-Host "Version updated successfully"
} elseif ($oldVersion -eq $Version) {
    Write-Host "Version already matches: $Version"
} else {
    Write-Host "Warning: Could not find APP_VERSION in version.py, skipping update"
}

if (-not $SkipPackage) {
    Write-Host "=== step 1: run build_pyqt.bat ==="
    $buildScript = Join-Path $repoRoot "scripts\build_pyqt.bat"
    & $buildScript

    Write-Host "=== step 2: compress onedir folder ==="
    if (-not (Test-Path $buildDir)) {
        throw ("Build directory not found: {0}" -f $buildDir)
    }
    if (Test-Path $packagePath) {
        Remove-Item $packagePath
    }
    $buildItems = Get-ChildItem -Path $buildDir
    $buildPaths = @()
    foreach ($item in $buildItems) {
        $buildPaths += $item.FullName
    }
    Compress-Archive -Path $buildPaths -DestinationPath $packagePath
    Write-Host ("Created package: {0}" -f $packagePath)
} else {
    Write-Host "=== step 1 and 2 skipped (SkipPackage enabled) ==="
    if (-not (Test-Path $packagePath)) {
        throw ("Existing package not found: {0}. Cannot continue with -SkipPackage." -f $packagePath)
    }
}

Write-Host "=== step 3: compute SHA256 ==="
$hashObj = Get-FileHash -Path $packagePath -Algorithm SHA256
$hashStr = $hashObj.Hash
$sha256 = $hashStr.ToLower()
Write-Host ("SHA256: {0}" -f $sha256)

if ($SkipPublish) {
    Write-Host "=== step 4: SKIPPED (SkipPublish enabled) ==="
    Write-Host "Warning: latest.json will not be generated because -SkipPublish is used"
    Write-Host "Reason: latest.json download links require corresponding GitHub Release to work properly"
    Write-Host "If you need to publish this version later, run the full release process without -SkipPublish"
    Write-Host ""
    Write-Host "SkipPublish enabled. Packaging complete."
    Write-Host ("Package: {0}" -f $packagePath)
    Write-Host ("SHA256: {0}" -f $sha256)
    return
}

Write-Host "=== step 4: generate latest.json ==="
if (-not (Test-Path $manifestDir)) {
    New-Item -ItemType Directory -Path $manifestDir | Out-Null
}

$githubDownloadUrl = "https://github.com/pranvil/MobileTestTool/releases/download/v$Version/$packageName"
# Read release notes once to ensure latest.json and releases use the same content
$releaseNotes = Get-ReleaseNotes -NotesFile $NotesFile -RepoRoot $repoRoot -DefaultNotes "- Add release notes here" -Trim

# Build download_urls array
$downloadUrls = @()

# GitHub source (US and default)
$downloadUrls += @{
    url = $githubDownloadUrl
    region = "us"
    platform = "windows"
    priority = 10
}

# Gitee source (CN) - if configured
if ($GiteeOwner -and $GiteeRepo) {
    $giteeDownloadUrl = "https://gitee.com/$GiteeOwner/$GiteeRepo/releases/download/v$Version/$packageName"
    $downloadUrls += @{
        url = $giteeDownloadUrl
        region = "cn"
        platform = "windows"
        priority = 20
    }
}

# Default source (for other countries)
$downloadUrls += @{
    url = $githubDownloadUrl
    region = "default"
    platform = "all"
    priority = 5
}

$manifest = [ordered]@{
    version       = $Version
    download_url  = $githubDownloadUrl  # Default fallback
    sha256        = $sha256
    file_name     = $packageName
    file_size     = (Get-Item $packagePath).Length
    release_notes = $releaseNotes
    published_at  = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    mandatory     = $false
    download_urls = $downloadUrls
}

$manifestJson = $manifest | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($manifestPath, $manifestJson + "`n", (New-Object System.Text.UTF8Encoding($false)))
Write-Host ("Manifest written to: {0}" -f $manifestPath)

Write-Host "=== step 5: summary ==="
Get-Content $manifestPath
Write-Host ""

Write-Host "=== step 6: git commit and push ==="
$filesToStage = @(
    "scripts/release.ps1",
    "config/latest.json.example",
    "releases/latest.json",
    "core/version.py"
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

Write-Host "=== step 7: tags and GitHub release ==="
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

# Reuse previously read release notes to ensure consistency with latest.json content
$notesForRelease = $releaseNotes

Write-Host "=== step 7a: GitHub release ==="
$ghCmd = Get-Command gh -ErrorAction SilentlyContinue
if ($ghCmd) {
    Invoke-GhReleaseCreate -Version $Version -Package $packagePath -Notes $notesForRelease
} else {
    Write-Host "Warning: GitHub CLI (gh) not found in PATH. Skipping GitHub release."
    Write-Host "To publish to GitHub, install GitHub CLI or add it to PATH."
    Write-Host "You can install it from: https://cli.github.com/"
}

if ($GiteeOwner -and $GiteeRepo -and $GiteeToken) {
    Write-Host "=== step 7b: Gitee release ==="
    Invoke-GiteeReleaseCreate -Version $Version -Package $packagePath -Notes $notesForRelease -Owner $GiteeOwner -Repo $GiteeRepo -Token $GiteeToken
} else {
    Write-Host "=== step 7b: Gitee release skipped (not configured) ==="
    Write-Host "To enable Gitee release, provide: -GiteeOwner [owner] -GiteeRepo [repo] -GiteeToken [token]"
}

Write-Host "=== all done ==="