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

    # Ensure Notes is not empty (Gitee API requires non-empty body)
    if ([string]::IsNullOrWhiteSpace($Notes)) {
        $Notes = "Release v$Version"
        Write-Host "Warning: Release notes are empty, using default description" -ForegroundColor Yellow
    }

    # Get current commit SHA for target_commitish
    $targetCommitish = "main"  # Default to main branch
    try {
        $currentBranch = git rev-parse --abbrev-ref HEAD
        if ($LASTEXITCODE -eq 0 -and $currentBranch) {
            $targetCommitish = $currentBranch
        }
        # Try to get the commit SHA instead
        $commitSha = git rev-parse HEAD
        if ($LASTEXITCODE -eq 0 -and $commitSha) {
            $targetCommitish = $commitSha.Trim()
        }
    } catch {
        Write-Host "Warning: Could not determine target commit, using 'main' branch" -ForegroundColor Yellow
    }

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
        target_commitish = $targetCommitish
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

# 需要一起提交到 Git 的文件（按你原来的习惯保留）
$filesToStage = @(
    "scripts/release.ps1",
    "config/latest.json.example",
    "releases/latest.json",
    "core/version.py"
)

foreach ($file in $filesToStage) {
    $fullPath = Join-Path $repoRoot $file
    if (Test-Path $fullPath) {
        Write-Host "Staging $file"
        Invoke-Git "add" $file
    }
    else {
        Write-Host "Skip missing file: $file"
    }
}

# 如果有暂存修改，就提交一次版本
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    $commitMessage = "chore: release v$Version"
    Write-Host "Committing release changes: $commitMessage"
    Invoke-Git "commit" "-m" $commitMessage
}
else {
    Write-Host "No staged changes detected. Skipping commit."
}

# 推送主分支到 GitHub（origin）
Write-Host "Pushing 'main' to 'origin' (GitHub)..."
Invoke-Git "push" "origin" "main"

# 检查是否配置了 gitee 这个 remote，如果有就同步过去
$remotes = (git remote) -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
if ($remotes -contains "gitee") {
    Write-Host "Pushing 'main' to 'gitee'..."
    Invoke-Git "push" "gitee" "main"
}
else {
    Write-Host "No 'gitee' remote configured. Skipping push of 'main' to Gitee."
}

Write-Host "=== step 7: tags and GitHub release ==="

# 版本号对应的 tag 名
$tagName = "v$Version"

# 如果本地已有同名 tag，先删掉再重建，避免冲突
$existingTag = git tag --list $tagName
if ($existingTag) {
    Write-Host "Tag $tagName already exists locally. Deleting and recreating..."
    Invoke-Git "tag" "-d" $tagName
}

Write-Host "Creating tag $tagName..."
Invoke-Git "tag" "-a" $tagName "-m" ("Release {0}" -f $Version)

# 把 tag 推到 GitHub（origin）
Write-Host "Pushing tag $tagName to 'origin' (GitHub)..."
Invoke-Git "push" "origin" $tagName

# 如果有 gitee 远程，把 tag 同步到 Gitee
if ($remotes -contains "gitee") {
    Write-Host "Pushing tag $tagName to 'gitee'..."
    Invoke-Git "push" "gitee" $tagName
}
else {
    Write-Host "No 'gitee' remote configured. Skipping push of tag to Gitee."
}

Write-Host "=== step 7a: GitHub release ==="

try {
    # 这里沿用你原来的 GitHub Release 函数和变量
    Invoke-GhReleaseCreate -Version $Version -Package $packagePath -Notes $releaseNotes
}
catch {
    Write-Error "Failed to create GitHub release: $_"
    throw
}

Write-Host "=== step 7b: Gitee release ==="

if ($GiteeOwner -and $GiteeRepo -and $GiteeToken) {
    try {
        Invoke-GiteeReleaseCreate `
            -Version $Version `
            -Package $packagePath `
            -Notes $releaseNotes `
            -Owner $GiteeOwner `
            -Repo $GiteeRepo `
            -Token $GiteeToken

        Write-Host "Gitee release created successfully."
    }
    catch {
        Write-Error "Failed to create Gitee release: $_"
    }
}
else {
    Write-Host "Gitee config not set. Skipping Gitee release creation."
}

Write-Host "Code and tags have been pushed to the 'gitee' remote (if configured)."
Write-Host "=== all done ==="
