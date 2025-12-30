<#
.SYNOPSIS
    测试 GitLab Release 创建功能

.DESCRIPTION
    仅测试 GitLab Release 创建，不进行完整发布流程

.PARAMETER Version
    版本号，例如 "0.9.6.5.5"

.PARAMETER NotesFile
    可选的发布说明文件路径
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = ""
)

$ErrorActionPreference = "Stop"

# 从环境变量读取 GitLab 配置
$gitlabUrl = $env:GITLAB_URL
$gitlabOwner = $env:GITLAB_OWNER
$gitlabRepo = $env:GITLAB_REPO
$gitlabToken = $env:GITLAB_TOKEN

# 如果环境变量未设置，尝试从配置文件读取
if ((-not $gitlabUrl -or -not $gitlabOwner -or -not $gitlabRepo -or -not $gitlabToken) -and (Test-Path ".\.gitlab-config.ps1")) {
    Write-Host "Loading GitLab configuration from .gitlab-config.ps1..." -ForegroundColor Cyan
    . .\.gitlab-config.ps1
    
    if ($GitLabUrl) { $gitlabUrl = $GitLabUrl }
    if ($GitLabOwner) { $gitlabOwner = $GitLabOwner }
    if ($GitLabRepo) { $gitlabRepo = $GitLabRepo }
    if ($GitLabToken) { $gitlabToken = $GitLabToken }
}

if (-not $gitlabUrl -or -not $gitlabOwner -or -not $gitlabRepo -or -not $gitlabToken) {
    Write-Host ""
    Write-Host "GitLab configuration not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please set environment variables:" -ForegroundColor Yellow
    Write-Host "   `$env:GITLAB_URL = `"http://10.129.93.67`""
    Write-Host "   `$env:GITLAB_OWNER = `"hao.lin`""
    Write-Host "   `$env:GITLAB_REPO = `"mobiletesttool`""
    Write-Host "   `$env:GITLAB_TOKEN = `"your_token`""
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing GitLab Release Creation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "GitLab Configuration:" -ForegroundColor Green
Write-Host "  URL:   $gitlabUrl" -ForegroundColor Cyan
Write-Host "  Owner: $gitlabOwner" -ForegroundColor Cyan
Write-Host "  Repo:  $gitlabRepo" -ForegroundColor Cyan
Write-Host "  Token: $($gitlabToken.Substring(0, [Math]::Min(8, $gitlabToken.Length)))..." -ForegroundColor Cyan
Write-Host "  Version: $Version" -ForegroundColor Cyan
Write-Host ""

# 读取发布说明
$releaseNotes = "- Test release for GitLab API"
if ($NotesFile -and (Test-Path $NotesFile)) {
    $releaseNotes = Get-Content $NotesFile -Raw -Encoding UTF8
    Write-Host "Loaded release notes from: $NotesFile" -ForegroundColor Green
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

Write-Host "Target commit: $targetCommitish" -ForegroundColor Cyan
Write-Host ""

# GitLab API URL
$projectPath = "$gitlabOwner/$gitlabRepo"
# GitLab API 需要 owner%2Frepo 格式
$encodedPath = $projectPath -replace '/', '%2F'
$apiBaseUrl = "$gitlabUrl/api/v4/projects/$encodedPath"
$releasesUrl = "$apiBaseUrl/releases"

Write-Host "GitLab API URL: $apiBaseUrl" -ForegroundColor Cyan
Write-Host "Releases URL: $releasesUrl" -ForegroundColor Cyan
Write-Host ""

$headers = @{
    "PRIVATE-TOKEN" = $gitlabToken
    "Content-Type" = "application/json"
}

# 检查是否已存在该 tag 的 Release
Write-Host "Checking for existing release..." -ForegroundColor Cyan
try {
    $allReleases = Invoke-RestMethod -Uri $releasesUrl -Method Get -Headers $headers -ErrorAction SilentlyContinue
    if ($allReleases) {
        $existingRelease = $allReleases | Where-Object { $_.tag_name -eq "v$Version" } | Select-Object -First 1
        if ($existingRelease) {
            Write-Host "Existing release found (ID: $($existingRelease.id))" -ForegroundColor Yellow
            Write-Host "  Name: $($existingRelease.name)" -ForegroundColor Yellow
            Write-Host "  URL: $($existingRelease.web_url)" -ForegroundColor Yellow
            Write-Host ""
            $delete = Read-Host "Delete existing release? (y/n)"
            if ($delete -eq 'y' -or $delete -eq 'Y') {
                Write-Host "Deleting existing release..." -ForegroundColor Yellow
                $deleteUrl = "$releasesUrl/$($existingRelease.id)"
                Invoke-RestMethod -Uri $deleteUrl -Method Delete -Headers $headers -ErrorAction Stop | Out-Null
                Write-Host "Release deleted successfully" -ForegroundColor Green
            } else {
                Write-Host "Skipping release creation (existing release kept)" -ForegroundColor Yellow
                exit 0
            }
        } else {
            Write-Host "No existing release found for tag v$Version" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "Error checking existing releases: $_" -ForegroundColor Red
    Write-Host "Continuing with release creation..." -ForegroundColor Yellow
}

# 验证 tag 是否存在，如果不存在则自动创建并推送
Write-Host "Checking if tag exists in GitLab..." -ForegroundColor Cyan
$tagsUrl = "$apiBaseUrl/repository/tags/v$Version"
$tagExists = $false

try {
    $tagInfo = Invoke-RestMethod -Uri $tagsUrl -Method Get -Headers $headers -ErrorAction Stop
    if ($tagInfo -and $tagInfo.name) {
        Write-Host "Tag found: $($tagInfo.name) (commit: $($tagInfo.commit.id))" -ForegroundColor Green
        $tagExists = $true
    }
} catch {
    $errorResponse = $_.Exception.Response
    if ($errorResponse -and $errorResponse.StatusCode -eq 404) {
        # Tag 不存在，准备创建
        $tagExists = $false
    } else {
        Write-Host "Error checking tag: $_" -ForegroundColor Red
        Write-Host "Will attempt to create tag anyway..." -ForegroundColor Yellow
        $tagExists = $false
    }
}

# 如果 tag 不存在，自动创建并推送
if (-not $tagExists) {
    Write-Host "Tag 'v$Version' does not exist in GitLab. Creating and pushing tag..." -ForegroundColor Yellow
    
    # 检查是否有 gitlab remote
    $remotes = (git remote) -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    if (-not ($remotes -contains "gitlab")) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "ERROR: Cannot create tag automatically!" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Tag 'v$Version' does not exist in GitLab, and 'gitlab' remote is not configured." -ForegroundColor Yellow
        Write-Host "Please configure the gitlab remote first:" -ForegroundColor Cyan
        Write-Host "  git remote add gitlab $gitlabUrl/$gitlabOwner/$gitlabRepo.git" -ForegroundColor White
        Write-Host ""
        Write-Host "Or manually push the tag:" -ForegroundColor Cyan
        Write-Host "  git tag -a v$Version -m 'Release $Version'" -ForegroundColor White
        Write-Host "  git push gitlab v$Version --force" -ForegroundColor White
        Write-Host ""
        exit 1
    }
    
    # 检查本地是否已有 tag
    $localTag = git tag --list "v$Version" 2>$null
    if ($localTag) {
        Write-Host "Local tag 'v$Version' exists. Using existing tag." -ForegroundColor Cyan
    } else {
        Write-Host "Creating local tag 'v$Version'..." -ForegroundColor Cyan
        try {
            git tag -a "v$Version" -m "Release $Version"
            if ($LASTEXITCODE -ne 0) {
                throw "git tag command failed"
            }
            Write-Host "Local tag created successfully." -ForegroundColor Green
        } catch {
            Write-Host "Error: Failed to create local tag: $_" -ForegroundColor Red
            exit 1
        }
    }
    
    # 推送 tag 到 GitLab
    Write-Host "Pushing tag 'v$Version' to GitLab..." -ForegroundColor Cyan
    try {
        # 检查 GitLab remote URL 是否为 HTTP，如果是则配置允许不安全连接
        $gitlabRemoteUrl = (git remote get-url gitlab)
        if ($gitlabRemoteUrl -match "^http://") {
            Write-Host "GitLab remote uses HTTP. Configuring Git to allow insecure connections..." -ForegroundColor Yellow
            $gitlabHost = ([System.Uri]$gitlabRemoteUrl).Host
            git config --local "http.$gitlabRemoteUrl.sslVerify" false 2>$null
            if ($LASTEXITCODE -ne 0) {
                git config --global "http.$gitlabHost.sslVerify" false 2>$null
            }
        }
        
        git push gitlab "v$Version" --force
        if ($LASTEXITCODE -ne 0) {
            throw "git push command failed"
        }
        Write-Host "Tag pushed to GitLab successfully." -ForegroundColor Green
        
        # 等待 GitLab API 同步（最多等待 10 秒）
        Write-Host "Waiting for GitLab API to sync the tag..." -ForegroundColor Cyan
        $syncRetries = 5
        $syncDelay = 2
        $tagSynced = $false
        
        for ($j = 1; $j -le $syncRetries; $j++) {
            Start-Sleep -Seconds $syncDelay
            try {
                $tagInfo = Invoke-RestMethod -Uri $tagsUrl -Method Get -Headers $headers -ErrorAction Stop
                if ($tagInfo -and $tagInfo.name) {
                    Write-Host "Tag synced to GitLab API: $($tagInfo.name)" -ForegroundColor Green
                    $tagSynced = $true
                    break
                }
            } catch {
                if ($j -lt $syncRetries) {
                    Write-Host "Tag not synced yet, waiting... (attempt $j/$syncRetries)" -ForegroundColor Yellow
                }
            }
        }
        
        if (-not $tagSynced) {
            Write-Host "Warning: Tag pushed but GitLab API hasn't synced yet. Continuing anyway..." -ForegroundColor Yellow
        }
    } catch {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "ERROR: Failed to push tag to GitLab!" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please push the tag manually:" -ForegroundColor Cyan
        Write-Host "  git push gitlab v$Version --force" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}

# 创建 Release 的请求体
# GitLab API 要求：tag_name 是必需的，name 和 description 是可选的
# 确保 description 不为空且是字符串
if ([string]::IsNullOrWhiteSpace($releaseNotes)) {
    $releaseNotes = "MobileTestTool v$Version"
}

$bodyObj = @{
    tag_name = "v$Version"
    name = "MobileTestTool v$Version"
    description = $releaseNotes.Trim()
}

# 如果 ref 不是默认分支，可以添加（但通常不需要）
if ($targetCommitish -and $targetCommitish -ne "main" -and $targetCommitish -ne "master") {
    $bodyObj.ref = $targetCommitish
}

# 使用 -Compress 避免换行问题，但保持可读性用于调试
$bodyJson = $bodyObj | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "Creating GitLab release..." -ForegroundColor Cyan
Write-Host "API URL: $releasesUrl" -ForegroundColor Gray
Write-Host "Request body:" -ForegroundColor Gray
Write-Host $bodyJson -ForegroundColor Gray
Write-Host ""

try {
    # 确保使用 UTF-8 编码发送 JSON
    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($bodyJson)
    $resp = Invoke-RestMethod -Uri $releasesUrl -Method Post -Headers $headers -Body $bodyBytes -ContentType "application/json; charset=utf-8" -ErrorAction Stop
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "GitLab Release created successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Release ID: $($resp.id)" -ForegroundColor Cyan
    Write-Host "Release Name: $($resp.name)" -ForegroundColor Cyan
    Write-Host "Tag Name: $($resp.tag_name)" -ForegroundColor Cyan
    Write-Host "Release URL: $($resp.web_url)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can open the URL above in browser to view the Release" -ForegroundColor Yellow
    Write-Host ""
}
catch {
    $errorMsg = $_.Exception.Message
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "GitLab Release creation failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error message: $errorMsg" -ForegroundColor Red
    Write-Host ""
    
    # 尝试读取详细的错误响应
    $responseBody = $null
    if ($_.Exception -is [System.Net.WebException]) {
        $webException = $_.Exception
        if ($null -ne $webException.Response) {
            $stream = $null
            $reader = $null
            try {
                $stream = $webException.Response.GetResponseStream()
                if ($null -ne $stream) {
                    $reader = New-Object System.IO.StreamReader($stream)
                    $responseBody = $reader.ReadToEnd()
                    Write-Host "API Error Response:" -ForegroundColor Yellow
                    Write-Host $responseBody -ForegroundColor Red
                    Write-Host ""
                    
                    # 尝试解析 JSON 错误响应
                    try {
                        $errorObj = $responseBody | ConvertFrom-Json
                        if ($errorObj.message) {
                            Write-Host "Error details: $($errorObj.message)" -ForegroundColor Red
                        }
                        if ($errorObj.error) {
                            Write-Host "Error: $($errorObj.error)" -ForegroundColor Red
                        }
                    } catch {
                        # 不是 JSON 格式，忽略
                    }
                }
            }
            catch {
                Write-Host "Could not read error response: $_" -ForegroundColor Yellow
            }
            finally {
                if ($null -ne $reader) { $reader.Close() }
                if ($null -ne $stream) { $stream.Close() }
            }
        }
    }
    
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. GitLab URL is correct: $gitlabUrl" -ForegroundColor Yellow
    Write-Host "  2. Owner and Repo are correct: $gitlabOwner/$gitlabRepo" -ForegroundColor Yellow
    Write-Host "  3. Token has 'api' and 'write_repository' permissions" -ForegroundColor Yellow
    Write-Host "  4. Tag 'v$Version' exists in GitLab" -ForegroundColor Yellow
    Write-Host "  5. Network connection is normal" -ForegroundColor Yellow
    Write-Host ""
    
    exit 1
}

