param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = "",
    [switch]$SkipPublish,
    [switch]$SkipPackage,
    [string]$GiteeOwner = "",
    [string]$GiteeRepo = "",
    [string]$GiteeToken = "",
    [string]$GitLabUrl = "",
    [string]$GitLabOwner = "",
    [string]$GitLabRepo = "",
    [string]$GitLabToken = ""
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

    Write-Host "Creating Gitee release for v$Version..."

    # 确保描述不为空，否则 Gitee 会报 "发行版的描述不能为空"
    if ([string]::IsNullOrWhiteSpace($Notes)) {
        $Notes = "MobileTestTool v$Version"
    }

    # 尝试确定 target_commitish（提交 SHA 优先，其次分支名）
    $targetCommitish = "main"
    try {
        $currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $currentBranch) {
            $targetCommitish = $currentBranch.Trim()
        }

        $commitSha = git rev-parse HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $commitSha) {
            $targetCommitish = $commitSha.Trim()
        }
    } catch {
        Write-Host "Warning: could not determine target commit, using '$targetCommitish'"
    }

    $apiBaseUrl = "https://gitee.com/api/v5/repos/$Owner/$Repo"
    $checkUrl   = "$apiBaseUrl/releases/tags/v$Version?access_token=$Token"
    $createUrl  = "$apiBaseUrl/releases?access_token=$Token"

    $headers = @{ Accept = "application/json" }

    # 如果已有同 tag 的 Release，先删掉，避免重复
    try {
        $existing = Invoke-RestMethod -Uri $checkUrl -Method Get -Headers $headers -ErrorAction SilentlyContinue
        if ($existing -and $existing.id) {
            Write-Host "Gitee release v$Version already exists. Deleting..."
            $deleteUrl = "$apiBaseUrl/releases/$($existing.id)?access_token=$Token"
            Invoke-RestMethod -Uri $deleteUrl -Method Delete -Headers $headers -ErrorAction Stop | Out-Null
        }
    } catch {
        Write-Host "No existing Gitee release for tag v$Version, continue to create."
    }

    # 创建 Release 的请求体
    $bodyObj = @{
        tag_name         = "v$Version"
        name             = "MobileTestTool v$Version"
        body             = $Notes
        target_commitish = $targetCommitish
        prerelease       = $false
    }

    $bodyJson = $bodyObj | ConvertTo-Json -Depth 3

    try {
        $resp = Invoke-RestMethod -Uri $createUrl -Method Post -Headers $headers -Body $bodyJson -ContentType "application/json" -ErrorAction Stop
        Write-Host "Gitee release created successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host "Gitee Release 创建成功！" -ForegroundColor Green
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Release 地址: $($resp.html_url)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "请手动上传 ZIP 文件:" -ForegroundColor Yellow
        Write-Host "  1. 打开上述 Release 地址" -ForegroundColor White
        Write-Host "  2. 点击 '上传附件' 或 'Upload Attachment' 按钮" -ForegroundColor White
        Write-Host "  3. 选择文件: $Package" -ForegroundColor White
        Write-Host "  4. 等待上传完成" -ForegroundColor White
        Write-Host ""
        Write-Host "需要上传的文件路径:" -ForegroundColor Cyan
        Write-Host "  $Package" -ForegroundColor White
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host ""
    } catch {
        Write-Error "Failed to create Gitee release: $_"
        throw
    }
}

function Invoke-GitLabReleaseCreate {
    param(
        [string]$Version,
        [string]$Package,
        [string]$Notes,
        [string]$Url,
        [string]$Owner,
        [string]$Repo,
        [string]$Token
    )

    Write-Host "Creating GitLab release for v$Version..."

    # 确保描述不为空
    if ([string]::IsNullOrWhiteSpace($Notes)) {
        $Notes = "MobileTestTool v$Version"
    }

    # 确定 target_commitish
    $targetCommitish = "main"
    try {
        $currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $currentBranch) {
            $targetCommitish = $currentBranch.Trim()
        }

        $commitSha = git rev-parse HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $commitSha) {
            $targetCommitish = $commitSha.Trim()
        }
    } catch {
        Write-Host "Warning: could not determine target commit, using '$targetCommitish'"
    }

    # GitLab API URL - 使用项目路径编码
    # 注意：GitLab API 需要 URL 编码的项目路径，格式为 owner%2Frepo
    $projectPath = "$Owner/$Repo"
    # 使用 PowerShell 内置方法进行 URL 编码
    $encodedPath = [System.Uri]::EscapeDataString($projectPath)
    $apiBaseUrl = "$Url/api/v4/projects/$encodedPath"
    $releasesUrl = "$apiBaseUrl/releases"

    $headers = @{
        "PRIVATE-TOKEN" = $Token
        "Content-Type" = "application/json"
    }

    # 检查是否已存在该 tag 的 Release
    try {
        # GitLab API 需要获取所有 releases 然后查找匹配的 tag
        $allReleases = Invoke-RestMethod -Uri $releasesUrl -Method Get -Headers $headers -ErrorAction SilentlyContinue
        if ($allReleases) {
            $existingRelease = $allReleases | Where-Object { $_.tag_name -eq "v$Version" } | Select-Object -First 1
            if ($existingRelease) {
                Write-Host "GitLab release v$Version already exists. Deleting..."
                $releaseId = $existingRelease.id
                $deleteUrl = "$releasesUrl/$releaseId"
                Invoke-RestMethod -Uri $deleteUrl -Method Delete -Headers $headers -ErrorAction Stop | Out-Null
            }
        }
    } catch {
        Write-Host "No existing GitLab release for tag v$Version, continue to create."
    }

    # 创建 Release 的请求体
    $bodyObj = @{
        name = "MobileTestTool v$Version"
        tag_name = "v$Version"
        description = $Notes
        ref = $targetCommitish
    }

    $bodyJson = $bodyObj | ConvertTo-Json -Depth 3

    try {
        # 1. 创建 Release
        $resp = Invoke-RestMethod -Uri $releasesUrl -Method Post -Headers $headers -Body $bodyJson -ErrorAction Stop
        Write-Host "GitLab release created successfully!" -ForegroundColor Green
        
        # 2. 上传文件到 GitLab
        Write-Host "Uploading package file to GitLab..." -ForegroundColor Cyan
        
        if (-not (Test-Path $Package)) {
            Write-Host "Warning: Package file not found: $Package" -ForegroundColor Yellow
            Write-Host "Release created but file upload skipped." -ForegroundColor Yellow
        } else {
            try {
                # 使用 GitLab Uploads API 上传文件
                $uploadsUrl = "$apiBaseUrl/uploads"
                $fileName = Split-Path -Leaf $Package
                $fileSize = (Get-Item $Package).Length
                $fileSizeMB = [math]::Round($fileSize / 1MB, 2)
                
                Write-Host "Uploading file: $fileName ($fileSizeMB MB)..." -ForegroundColor Cyan
                
                # 使用 .NET HttpClient 进行 multipart/form-data 上传
                try {
                    Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
                } catch {
                    throw "Failed to load System.Net.Http assembly. Please ensure .NET Framework 4.5+ is installed."
                }
                
                $httpClient = New-Object System.Net.Http.HttpClient
                try {
                    $httpClient.DefaultRequestHeaders.Add("PRIVATE-TOKEN", $Token)
                    
                    $multipartContent = New-Object System.Net.Http.MultipartFormDataContent
                    $fileStream = [System.IO.File]::OpenRead($Package)
                    try {
                        $streamContent = New-Object System.Net.Http.StreamContent($fileStream)
                        $streamContent.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue("application/zip")
                        $multipartContent.Add($streamContent, "file", $fileName)
                        
                        $response = $httpClient.PostAsync($uploadsUrl, $multipartContent).Result
                        
                        if ($response.IsSuccessStatusCode) {
                            $responseContent = $response.Content.ReadAsStringAsync().Result
                            $uploadResp = $responseContent | ConvertFrom-Json
                            
                            # GitLab Uploads API 返回的格式可能是 { "alt": "...", "url": "...", "markdown": "..." }
                            $uploadedUrl = $uploadResp.url
                            if (-not $uploadedUrl) {
                                # 尝试其他可能的字段名
                                $uploadedUrl = $uploadResp.markdown -replace '\[.*?\]\((.*?)\)', '$1'
                            }
                            
                            if ($uploadedUrl) {
                                # 确保 URL 是完整的
                                if (-not $uploadedUrl.StartsWith("http")) {
                                    $uploadedUrl = "$Url$uploadedUrl"
                                }
                                
                                # 3. 将上传的文件添加到 Release 的 assets
                                $assetUrl = "$releasesUrl/v$Version/assets/links"
                                $assetBody = @{
                                    name = $fileName
                                    url = $uploadedUrl
                                } | ConvertTo-Json -Depth 3
                                
                                Write-Host "Adding file to release assets..." -ForegroundColor Cyan
                                $assetResp = Invoke-RestMethod -Uri $assetUrl -Method Post -Headers $headers -Body $assetBody -ErrorAction Stop
                                
                                Write-Host "File uploaded successfully!" -ForegroundColor Green
                                Write-Host "Download URL: $uploadedUrl" -ForegroundColor Cyan
                            } else {
                                throw "Upload succeeded but could not parse response URL"
                            }
                        } else {
                            $errorContent = $response.Content.ReadAsStringAsync().Result
                            throw "Upload failed with status $($response.StatusCode): $errorContent"
                        }
                    } finally {
                        $fileStream.Close()
                    }
                } finally {
                    $httpClient.Dispose()
                }
            } catch {
                Write-Host "Warning: File upload failed: $_" -ForegroundColor Yellow
                Write-Host "Release created but file upload failed. You may need to upload manually." -ForegroundColor Yellow
                Write-Host "You can upload the file manually at: $($resp.web_url)" -ForegroundColor Yellow
            }
        }
        
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host "GitLab Release 创建成功！" -ForegroundColor Green
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Release 地址: $($resp.web_url)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host ""
    } catch {
        Write-Error "Failed to create GitLab release: $_"
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

# GitLab source (Internal) - if configured
if ($GitLabUrl -and $GitLabOwner -and $GitLabRepo) {
    $gitlabDownloadUrl = "$GitLabUrl/$GitLabOwner/$GitLabRepo/-/releases/v$Version/downloads/$packageName"
    $downloadUrls += @{
        url = $gitlabDownloadUrl
        region = "internal"
        platform = "windows"
        priority = 15
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
    
    # 先 fetch gitee 的最新状态
    Write-Host "Fetching latest from 'gitee'..."
    Invoke-Git "fetch" "gitee"
    
    # 检查是否可以快进推送
    $canFastForward = $true
    try {
        # 检查 gitee/main 是否在本地 main 的历史中
        $mergeBase = git merge-base main gitee/main 2>$null
        $giteeMainCommit = git rev-parse gitee/main 2>$null
        if ($LASTEXITCODE -eq 0 -and $mergeBase -and $giteeMainCommit) {
            if ($mergeBase -ne $giteeMainCommit) {
                $canFastForward = $false
                Write-Host "Warning: 'gitee/main' has diverged from local 'main'. Using force-with-lease to push." -ForegroundColor Yellow
            }
        }
    } catch {
        $canFastForward = $false
        Write-Host "Warning: Could not determine merge base. Using force-with-lease to push." -ForegroundColor Yellow
    }
    
    if ($canFastForward) {
        Invoke-Git "push" "gitee" "main"
    } else {
        # 使用 --force-with-lease 进行安全强制推送
        # 这比 --force 更安全，只有在远程没有被其他人更新时才会推送
        Write-Host "Using '--force-with-lease' to push to 'gitee'..." -ForegroundColor Yellow
        Invoke-Git "push" "gitee" "main" "--force-with-lease"
    }
}
else {
    Write-Host "No 'gitee' remote configured. Skipping push of 'main' to Gitee."
}

# 检查是否配置了 gitlab 这个 remote，如果有就同步过去
if ($remotes -contains "gitlab") {
    Write-Host "Pushing 'main' to 'gitlab'..."
    
    # 先 fetch gitlab 的最新状态
    Write-Host "Fetching latest from 'gitlab'..."
    Invoke-Git "fetch" "gitlab"
    
    # 检查是否可以快进推送
    $canFastForward = $true
    try {
        # 检查 gitlab/main 是否在本地 main 的历史中
        $mergeBase = git merge-base main gitlab/main 2>$null
        $gitlabMainCommit = git rev-parse gitlab/main 2>$null
        if ($LASTEXITCODE -eq 0 -and $mergeBase -and $gitlabMainCommit) {
            if ($mergeBase -ne $gitlabMainCommit) {
                $canFastForward = $false
                Write-Host "Warning: 'gitlab/main' has diverged from local 'main'. Using force-with-lease to push." -ForegroundColor Yellow
            }
        }
    } catch {
        $canFastForward = $false
        Write-Host "Warning: Could not determine merge base. Using force-with-lease to push." -ForegroundColor Yellow
    }
    
    if ($canFastForward) {
        Invoke-Git "push" "gitlab" "main"
    } else {
        # 使用 --force-with-lease 进行安全强制推送
        Write-Host "Using '--force-with-lease' to push to 'gitlab'..." -ForegroundColor Yellow
        Invoke-Git "push" "gitlab" "main" "--force-with-lease"
    }
}
else {
    Write-Host "No 'gitlab' remote configured. Skipping push of 'main' to GitLab."
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
    # Tag 推送使用 --force，因为同一个 tag 可能在不同提交上
    Invoke-Git "push" "gitee" $tagName "--force"
}
else {
    Write-Host "No 'gitee' remote configured. Skipping push of tag to Gitee."
}

# 如果有 gitlab 远程，把 tag 同步到 GitLab
if ($remotes -contains "gitlab") {
    Write-Host "Pushing tag $tagName to 'gitlab'..."
    # Tag 推送使用 --force，因为同一个 tag 可能在不同提交上
    Invoke-Git "push" "gitlab" $tagName "--force"
}
else {
    Write-Host "No 'gitlab' remote configured. Skipping push of tag to GitLab."
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
    }
    catch {
        Write-Host "Gitee release creation failed. Please check the error message above." -ForegroundColor Red
        # 不抛出异常，允许脚本继续执行完成
    }
}
else {
    Write-Host "Gitee config not set. Skipping Gitee release creation."
}

Write-Host "=== step 7c: GitLab release ==="

if ($GitLabUrl -and $GitLabOwner -and $GitLabRepo -and $GitLabToken) {
    try {
        Invoke-GitLabReleaseCreate `
            -Version $Version `
            -Package $packagePath `
            -Notes $releaseNotes `
            -Url $GitLabUrl `
            -Owner $GitLabOwner `
            -Repo $GitLabRepo `
            -Token $GitLabToken
    }
    catch {
        Write-Host "GitLab release creation failed. Please check the error message above." -ForegroundColor Red
        # 不抛出异常，允许脚本继续执行完成
    }
}
else {
    Write-Host "GitLab config not set. Skipping GitLab release creation."
}

Write-Host "Code and tags have been pushed to the 'gitee' and 'gitlab' remotes (if configured)."
Write-Host "=== all done ==="
