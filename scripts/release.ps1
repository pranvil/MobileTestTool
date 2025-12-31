<#
.SYNOPSIS
    统一的发布脚本，支持发布到 GitHub、Gitee、GitLab

.DESCRIPTION
    自动从配置文件加载平台配置，支持选择发布到单个或多个平台

.PARAMETER Version
    版本号（必需），例如 "0.9.6.5.5"

.PARAMETER Platform
    发布平台（可选），可选值：all|github|gitee|gitlab，默认 "all"

.PARAMETER NotesFile
    发布说明文件路径（可选），例如 "docs\notes.md"

.PARAMETER SkipPublish
    跳过发布步骤（仅打包）

.PARAMETER SkipPackage
    跳过打包步骤（使用已有包）

.EXAMPLE
    .\scripts\release.ps1 -Version "0.9.6.5.5"
    发布到所有已配置的平台

.EXAMPLE
    .\scripts\release.ps1 -Version "0.9.6.5.5" -Platform github
    仅发布到 GitHub

.EXAMPLE
    .\scripts\release.ps1 -Version "0.9.6.5.5" -Platform gitee
    仅发布到 Gitee

.EXAMPLE
    .\scripts\release.ps1 -Version "0.9.6.5.5" -Platform gitlab
    仅发布到 GitLab
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [ValidateSet("all", "github", "gitee", "gitlab")]
    [string]$Platform = "all",
    [string]$NotesFile = "",
    [switch]$SkipPublish,
    [switch]$SkipPackage
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Helper Functions
# ============================================================================

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

function Load-ReleaseConfig {
    <#
    .SYNOPSIS
        加载发布配置，优先从环境变量读取，然后从配置文件读取
    #>
    
    $config = @{
        GiteeOwner = $null
        GiteeRepo = $null
        GiteeToken = $null
        GitLabUrl = $null
        GitLabOwner = $null
        GitLabRepo = $null
        GitLabToken = $null
    }
    
    # 1. 优先从环境变量读取
    $config.GiteeOwner = $env:GITEE_OWNER
    $config.GiteeRepo = $env:GITEE_REPO
    $config.GiteeToken = $env:GITEE_TOKEN
    $config.GitLabUrl = $env:GITLAB_URL
    $config.GitLabOwner = $env:GITLAB_OWNER
    $config.GitLabRepo = $env:GITLAB_REPO
    $config.GitLabToken = $env:GITLAB_TOKEN
    
    # 2. 如果环境变量未设置，从配置文件读取
    $configFile = Join-Path $PSScriptRoot "..\.release-config.ps1"
    if (Test-Path $configFile) {
        Write-Host "Loading configuration from .release-config.ps1..." -ForegroundColor Cyan
        . $configFile
        
        if (-not $config.GiteeOwner) { $config.GiteeOwner = $GiteeOwner }
        if (-not $config.GiteeRepo) { $config.GiteeRepo = $GiteeRepo }
        if (-not $config.GiteeToken) { $config.GiteeToken = $GiteeToken }
        if (-not $config.GitLabUrl) { $config.GitLabUrl = $GitLabUrl }
        if (-not $config.GitLabOwner) { $config.GitLabOwner = $GitLabOwner }
        if (-not $config.GitLabRepo) { $config.GitLabRepo = $GitLabRepo }
        if (-not $config.GitLabToken) { $config.GitLabToken = $GitLabToken }
    }
    
    return $config
}

function Get-PlatformsToPublish {
    <#
    .SYNOPSIS
        根据 Platform 参数和配置情况，确定要发布的平台列表
    #>
    param(
        [string]$Platform,
        [hashtable]$Config
    )
    
    $platforms = @()
    
    switch ($Platform.ToLower()) {
        "all" {
            # 检查所有平台的配置
            # GitHub 总是可用（使用 gh CLI）
            $platforms += "github"
            
            # 检查 Gitee 配置
            if ($Config.GiteeOwner -and $Config.GiteeRepo -and $Config.GiteeToken) {
                $platforms += "gitee"
            }
            
            # 检查 GitLab 配置
            if ($Config.GitLabUrl -and $Config.GitLabOwner -and $Config.GitLabRepo -and $Config.GitLabToken) {
                $platforms += "gitlab"
            }
        }
        "github" {
            $platforms = @("github")
        }
        "gitee" {
            if (-not ($Config.GiteeOwner -and $Config.GiteeRepo -and $Config.GiteeToken)) {
                throw "Gitee configuration not found! Please configure Gitee in .release-config.ps1 or environment variables."
            }
            $platforms = @("gitee")
        }
        "gitlab" {
            if (-not ($Config.GitLabUrl -and $Config.GitLabOwner -and $Config.GitLabRepo -and $Config.GitLabToken)) {
                throw "GitLab configuration not found! Please configure GitLab in .release-config.ps1 or environment variables."
            }
            $platforms = @("gitlab")
        }
    }
    
    return $platforms
}

# ============================================================================
# Release Creation Functions
# ============================================================================

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
    $projectPath = "$Owner/$Repo"
    $encodedPath = $projectPath -replace '/', '%2F'
    $apiBaseUrl = "$Url/api/v4/projects/$encodedPath"
    $releasesUrl = "$apiBaseUrl/releases"
    
    Write-Host "GitLab API URL: $apiBaseUrl" -ForegroundColor Cyan

    $headers = @{
        "PRIVATE-TOKEN" = $Token
        "Content-Type" = "application/json"
    }

    # 检查是否已存在该 tag 的 Release
    try {
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

    # 验证 tag 是否存在，如果不存在则自动创建并推送
    Write-Host "Checking if tag exists in GitLab..." -ForegroundColor Cyan
    $tagsUrl = "$apiBaseUrl/repository/tags/v$Version"
    $tagExists = $false
    $maxRetries = 5
    $retryDelay = 2
    
    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            $tagInfo = Invoke-RestMethod -Uri $tagsUrl -Method Get -Headers $headers -ErrorAction Stop
            if ($tagInfo -and $tagInfo.name) {
                Write-Host "Tag found: $($tagInfo.name) (commit: $($tagInfo.commit.id))" -ForegroundColor Green
                $tagExists = $true
                break
            }
        } catch {
            $errorResponse = $_.Exception.Response
            if ($errorResponse -and $errorResponse.StatusCode -eq 404) {
                $tagExists = $false
                break
            } else {
                if ($i -lt $maxRetries) {
                    Write-Host "Error checking tag, retrying in $retryDelay seconds... (attempt $i/$maxRetries)" -ForegroundColor Yellow
                    Start-Sleep -Seconds $retryDelay
                } else {
                    Write-Host "Warning: Could not verify tag status. Will attempt to create tag anyway." -ForegroundColor Yellow
                    $tagExists = $false
                }
            }
        }
    }
    
    # 如果 tag 不存在，自动创建并推送
    if (-not $tagExists) {
        Write-Host "Tag 'v$Version' does not exist in GitLab. Creating and pushing tag..." -ForegroundColor Yellow
        
        $remotes = (git remote) -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
        if (-not ($remotes -contains "gitlab")) {
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Red
            Write-Host "ERROR: Cannot create tag automatically!" -ForegroundColor Red
            Write-Host "========================================" -ForegroundColor Red
            Write-Host ""
            Write-Host "Tag 'v$Version' does not exist in GitLab, and 'gitlab' remote is not configured." -ForegroundColor Yellow
            Write-Host "Please configure the gitlab remote first:" -ForegroundColor Cyan
            Write-Host "  git remote add gitlab $Url/$Owner/$Repo.git" -ForegroundColor White
            Write-Host ""
            Write-Host "Or manually push the tag:" -ForegroundColor Cyan
            Write-Host "  git tag -a v$Version -m 'Release $Version'" -ForegroundColor White
            Write-Host "  git push gitlab v$Version --force" -ForegroundColor White
            Write-Host ""
            throw "Tag 'v$Version' not found in GitLab and cannot create automatically (no gitlab remote)."
        }
        
        $localTag = git tag --list "v$Version" 2>$null
        if ($localTag) {
            Write-Host "Local tag 'v$Version' exists. Using existing tag." -ForegroundColor Cyan
        } else {
            Write-Host "Creating local tag 'v$Version'..." -ForegroundColor Cyan
            try {
                Invoke-Git "tag" "-a" "v$Version" "-m" ("Release {0}" -f $Version)
                Write-Host "Local tag created successfully." -ForegroundColor Green
            } catch {
                Write-Host "Warning: Failed to create local tag: $_" -ForegroundColor Yellow
                throw "Failed to create tag: $_"
            }
        }
        
        Write-Host "Pushing tag 'v$Version' to GitLab..." -ForegroundColor Cyan
        try {
            $gitlabRemoteUrl = (git remote get-url gitlab)
            if ($gitlabRemoteUrl -match "^http://") {
                Write-Host "GitLab remote uses HTTP. Configuring Git to allow insecure connections..." -ForegroundColor Yellow
                $gitlabHost = ([System.Uri]$gitlabRemoteUrl).Host
                git config --local "http.$gitlabRemoteUrl.sslVerify" false 2>$null
                if ($LASTEXITCODE -ne 0) {
                    git config --global "http.$gitlabHost.sslVerify" false 2>$null
                }
            }
            
            Invoke-Git "push" "gitlab" "v$Version" "--force"
            Write-Host "Tag pushed to GitLab successfully." -ForegroundColor Green
            
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
            throw "Failed to push tag to GitLab: $_"
        }
    }

    # 创建 Release 的请求体
    $bodyObj = @{
        tag_name = "v$Version"
        name = "MobileTestTool v$Version"
        description = $Notes
    }
    
    if ($targetCommitish -and $targetCommitish -ne "main" -and $targetCommitish -ne "master") {
        $bodyObj.ref = $targetCommitish
    }

    $bodyJson = $bodyObj | ConvertTo-Json -Depth 3 -Compress

    try {
        Write-Host "Calling GitLab API: POST $releasesUrl" -ForegroundColor Cyan
        Write-Host "Request body: $bodyJson" -ForegroundColor Gray
        Write-Host ""
        
        $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($bodyJson)
        $resp = Invoke-RestMethod -Uri $releasesUrl -Method Post -Headers $headers -Body $bodyBytes -ContentType "application/json; charset=utf-8" -ErrorAction Stop
        
        # 调试：打印完整响应
        Write-Host "GitLab API Response:" -ForegroundColor Gray
        $resp | ConvertTo-Json -Depth 5 | Write-Host -ForegroundColor Gray
        Write-Host ""
        
        Write-Host "GitLab release created successfully!" -ForegroundColor Green
        
        # 尝试多种可能的属性名
        $releaseId = $resp.id
        $releaseUrl = $resp.web_url
        if (-not $releaseUrl) {
            $releaseUrl = $resp.url
        }
        if (-not $releaseUrl) {
            # 构建 URL
            $releaseUrl = "$Url/$Owner/$Repo/-/releases/v$Version"
        }
        
        Write-Host "Release ID: $releaseId" -ForegroundColor Cyan
        Write-Host "Release URL: $releaseUrl" -ForegroundColor Cyan
        
        # 上传文件到 GitLab
        Write-Host "Uploading package file to GitLab..." -ForegroundColor Cyan
        
        if (-not (Test-Path $Package)) {
            Write-Host "Warning: Package file not found: $Package" -ForegroundColor Yellow
            Write-Host "Release created but file upload skipped." -ForegroundColor Yellow
        } else {
            $fileName = Split-Path -Leaf $Package
            $fileSize = (Get-Item $Package).Length
            $fileSizeMB = [math]::Round($fileSize / 1MB, 2)
            $maxUploadSizeMB = 50  # GitLab uploads API 限制为 50MB
            
            Write-Host "File size: $fileSizeMB MB" -ForegroundColor Cyan
            
            # 检查文件大小是否超过 GitLab uploads API 限制
            if ($fileSizeMB -gt $maxUploadSizeMB) {
                Write-Host ""
                Write-Host "========================================" -ForegroundColor Yellow
                Write-Host "Warning: File exceeds GitLab upload limit" -ForegroundColor Yellow
                Write-Host "========================================" -ForegroundColor Yellow
                Write-Host ""
                Write-Host "File size ($fileSizeMB MB) exceeds GitLab uploads API limit ($maxUploadSizeMB MB)." -ForegroundColor Yellow
                Write-Host "GitLab uploads API cannot handle files larger than $maxUploadSizeMB MB." -ForegroundColor Yellow
                Write-Host ""
                Write-Host "Alternative solutions:" -ForegroundColor Cyan
                Write-Host "  1. Use external storage (GitHub/Gitee) and add as external link" -ForegroundColor White
                Write-Host "  2. Contact GitLab admin to increase upload limit" -ForegroundColor White
                Write-Host "  3. Use GitLab Package Registry (if available)" -ForegroundColor White
                Write-Host "  4. Manually upload via GitLab Web UI" -ForegroundColor White
                Write-Host ""
                
                # 尝试从其他平台获取下载链接并添加为外部 asset link
                $externalUrl = $null
                
                # 优先使用 GitHub 下载链接（通常最可靠）
                $githubUrl = "https://github.com/pranvil/MobileTestTool/releases/download/v$Version/$fileName"
                Write-Host "Attempting to add GitHub download link as external asset..." -ForegroundColor Cyan
                Write-Host "GitHub URL: $githubUrl" -ForegroundColor Gray
                $externalUrl = $githubUrl
                
                # 如果没有 GitHub，尝试 Gitee
                if (-not $externalUrl -and $config.GiteeOwner -and $config.GiteeRepo) {
                    $giteeUrl = "https://gitee.com/$($config.GiteeOwner)/$($config.GiteeRepo)/releases/download/v$Version/$fileName"
                    Write-Host "Attempting to add Gitee download link as external asset..." -ForegroundColor Cyan
                    Write-Host "Gitee URL: $giteeUrl" -ForegroundColor Gray
                    $externalUrl = $giteeUrl
                }
                
                if ($externalUrl) {
                    try {
                        $assetUrl = "$apiBaseUrl/releases/v$Version/assets/links"
                        $assetBody = @{
                            name = $fileName
                            url = $externalUrl
                            link_type = "package"
                        } | ConvertTo-Json -Depth 3 -Compress
                        
                        Write-Host "Adding external download link to release assets..." -ForegroundColor Cyan
                        $assetBodyBytes = [System.Text.Encoding]::UTF8.GetBytes($assetBody)
                        $assetResp = Invoke-RestMethod -Uri $assetUrl -Method Post -Headers $headers -Body $assetBodyBytes -ContentType "application/json; charset=utf-8" -ErrorAction Stop
                        
                        Write-Host "External download link added successfully!" -ForegroundColor Green
                        Write-Host "Download URL: $externalUrl" -ForegroundColor Cyan
                    } catch {
                        Write-Host "Warning: Failed to add external link: $_" -ForegroundColor Yellow
                        Write-Host "Please manually add the download link in GitLab Web UI" -ForegroundColor Yellow
                    }
                } else {
                    Write-Host "No external download URL available. Please manually upload the file." -ForegroundColor Yellow
                }
                
                Write-Host ""
                Write-Host "Manual upload instructions:" -ForegroundColor Cyan
                Write-Host "  1. Go to: $releaseUrl" -ForegroundColor White
                Write-Host "  2. Click 'Edit' button" -ForegroundColor White
                Write-Host "  3. Upload the file manually or add external download link" -ForegroundColor White
                Write-Host ""
            } else {
                # 文件小于 50MB，可以正常上传
                try {
                    $uploadsUrl = "$apiBaseUrl/uploads"
                    
                    Write-Host "Uploading file: $fileName ($fileSizeMB MB)..." -ForegroundColor Cyan
                    Write-Host "This may take a while for large files..." -ForegroundColor Yellow
                
                # 使用 System.Net.Http.HttpClient 但改用更简单的方法
                try {
                    Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
                } catch {
                    throw "Failed to load System.Net.Http assembly. Please ensure .NET Framework 4.5+ is installed."
                }
                
                $httpClient = New-Object System.Net.Http.HttpClient
                $httpClient.Timeout = [System.TimeSpan]::FromMinutes(30)
                
                try {
                    $httpClient.DefaultRequestHeaders.Add("PRIVATE-TOKEN", $Token)
                    
                    # 使用 MultipartFormDataContent
                    $multipartContent = New-Object System.Net.Http.MultipartFormDataContent
                    
                    # 读取文件内容为字节数组
                    Write-Host "Reading file into memory..." -ForegroundColor Gray
                    $fileBytes = [System.IO.File]::ReadAllBytes($Package)
                    $fileContent = New-Object System.Net.Http.ByteArrayContent($fileBytes)
                    $fileContent.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue("application/zip")
                    $multipartContent.Add($fileContent, "file", $fileName)
                    
                    Write-Host "Sending POST request to: $uploadsUrl" -ForegroundColor Gray
                    
                    try {
                        # 使用异步方法但同步等待
                        $task = $httpClient.PostAsync($uploadsUrl, $multipartContent)
                        $response = $task.GetAwaiter().GetResult()
                        
                        if ($null -eq $response) {
                            if ($task.IsFaulted) {
                                throw $task.Exception.InnerException
                            }
                            throw "Response is null"
                        }
                        
                        Write-Host "Response status: $($response.StatusCode)" -ForegroundColor Gray
                        
                        if ($response.IsSuccessStatusCode) {
                            $responseContent = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                            Write-Host "Upload API Response:" -ForegroundColor Gray
                            Write-Host $responseContent -ForegroundColor Gray
                            
                            $uploadResp = $responseContent | ConvertFrom-Json
                            
                            $uploadedUrl = $null
                            if ($uploadResp.PSObject.Properties.Name -contains "url") {
                                $uploadedUrl = $uploadResp.url
                            }
                            
                            if ([string]::IsNullOrWhiteSpace($uploadedUrl) -and ($uploadResp.PSObject.Properties.Name -contains "markdown")) {
                                $markdown = $uploadResp.markdown
                                if (-not [string]::IsNullOrWhiteSpace($markdown)) {
                                    $uploadedUrl = $markdown -replace '\[.*?\]\((.*?)\)', '$1'
                                }
                            }
                            
                            if ([string]::IsNullOrWhiteSpace($uploadedUrl)) {
                                Write-Host "Upload response object:" -ForegroundColor Yellow
                                $uploadResp | ConvertTo-Json -Depth 5 | Write-Host -ForegroundColor Yellow
                                throw "Could not extract URL from upload response"
                            }
                            
                            if (-not $uploadedUrl.StartsWith("http")) {
                                $uploadedUrl = "$Url$uploadedUrl"
                            }
                            
                            # 使用正确的 API 端点添加 asset link
                            $assetUrl = "$apiBaseUrl/releases/v$Version/assets/links"
                            $assetBody = @{
                                name = $fileName
                                url = $uploadedUrl
                                link_type = "package"
                            } | ConvertTo-Json -Depth 3 -Compress
                            
                            Write-Host "Adding file to release assets..." -ForegroundColor Cyan
                            Write-Host "Asset URL: $assetUrl" -ForegroundColor Gray
                            
                            try {
                                $assetBodyBytes = [System.Text.Encoding]::UTF8.GetBytes($assetBody)
                                $assetResp = Invoke-RestMethod -Uri $assetUrl -Method Post -Headers $headers -Body $assetBodyBytes -ContentType "application/json; charset=utf-8" -ErrorAction Stop
                                
                                Write-Host "File uploaded and added to release successfully!" -ForegroundColor Green
                                Write-Host "Download URL: $uploadedUrl" -ForegroundColor Cyan
                            } catch {
                                Write-Host "Warning: Failed to add file link to release: $_" -ForegroundColor Yellow
                                Write-Host "File uploaded to: $uploadedUrl" -ForegroundColor Cyan
                                Write-Host "You may need to manually add the file link to the release." -ForegroundColor Yellow
                            }
                        } else {
                            $errorContent = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                            throw "Upload failed with status $($response.StatusCode): $errorContent"
                        }
                    } catch {
                        Write-Host "Error during file upload: $_" -ForegroundColor Red
                        Write-Host "Exception type: $($_.Exception.GetType().FullName)" -ForegroundColor Red
                        if ($_.Exception.InnerException) {
                            Write-Host "Inner exception: $($_.Exception.InnerException.Message)" -ForegroundColor Red
                        }
                        throw
                    } finally {
                        $fileContent.Dispose()
                        $multipartContent.Dispose()
                    }
                } finally {
                    $httpClient.Dispose()
                }
                } catch {
                    Write-Host "Warning: File upload failed: $_" -ForegroundColor Yellow
                    Write-Host "Release created but file upload failed. You may need to upload manually." -ForegroundColor Yellow
                    if ($releaseUrl) {
                        Write-Host "You can upload the file manually at: $releaseUrl" -ForegroundColor Yellow
                    } else {
                        Write-Host "Release URL: $Url/$Owner/$Repo/-/releases/v$Version" -ForegroundColor Yellow
                    }
                }
            }
        }
        
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host "GitLab Release 创建成功！" -ForegroundColor Green
        Write-Host "==========================================" -ForegroundColor Yellow
        Write-Host ""
        if ($releaseUrl) {
            Write-Host "Release 地址: $releaseUrl" -ForegroundColor Cyan
        } else {
            Write-Host "Release 地址: $Url/$Owner/$Repo/-/releases/v$Version" -ForegroundColor Cyan
        }
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

# ============================================================================
# Main Script
# ============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MobileTestTool Release Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Version: $Version" -ForegroundColor Green
Write-Host "Platform: $Platform" -ForegroundColor Green
Write-Host ""

# Load configuration
$config = Load-ReleaseConfig

# Determine platforms to publish
$platformsToPublish = Get-PlatformsToPublish -Platform $Platform -Config $config

Write-Host "Platforms to publish:" -ForegroundColor Cyan
foreach ($p in $platformsToPublish) {
    Write-Host "  - $p" -ForegroundColor Yellow
}
Write-Host ""

# Validate configurations for selected platforms
if ($platformsToPublish -contains "gitee") {
    if (-not ($config.GiteeOwner -and $config.GiteeRepo -and $config.GiteeToken)) {
        throw "Gitee configuration incomplete. Please check .release-config.ps1 or environment variables."
    }
}

if ($platformsToPublish -contains "gitlab") {
    if (-not ($config.GitLabUrl -and $config.GitLabOwner -and $config.GitLabRepo -and $config.GitLabToken)) {
        throw "GitLab configuration incomplete. Please check .release-config.ps1 or environment variables."
    }
}

# Set up paths
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

# Build package
if (-not $SkipPackage) {
    Write-Host "=== step 1: run build.bat ==="
    $buildScript = Join-Path $repoRoot "scripts\build.bat"
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
    Write-Host "Reason: latest.json download links require corresponding Release to work properly"
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
if ($config.GiteeOwner -and $config.GiteeRepo) {
    $giteeDownloadUrl = "https://gitee.com/$($config.GiteeOwner)/$($config.GiteeRepo)/releases/download/v$Version/$packageName"
    $downloadUrls += @{
        url = $giteeDownloadUrl
        region = "cn"
        platform = "windows"
        priority = 20
    }
}

# GitLab source (Internal) - if configured
if ($config.GitLabUrl -and $config.GitLabOwner -and $config.GitLabRepo) {
    $gitlabDownloadUrl = "$($config.GitLabUrl)/$($config.GitLabOwner)/$($config.GitLabRepo)/-/releases/v$Version/downloads/$packageName"
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
    download_url  = $githubDownloadUrl
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
        Write-Host "Staging $file"
        Invoke-Git "add" $file
    }
    else {
        Write-Host "Skip missing file: $file"
    }
}

git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    $commitMessage = "chore: release v$Version"
    Write-Host "Committing release changes: $commitMessage"
    Invoke-Git "commit" "-m" $commitMessage
}
else {
    Write-Host "No staged changes detected. Skipping commit."
}

# Push to remotes based on platforms to publish
$remotes = (git remote) -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }

# Always push to GitHub (origin)
Write-Host "Pushing 'main' to 'origin' (GitHub)..."
Invoke-Git "push" "origin" "main"

# Push to Gitee if configured and selected
if ($remotes -contains "gitee" -and ($platformsToPublish -contains "gitee" -or $Platform -eq "all")) {
    Write-Host "Pushing 'main' to 'gitee'..."
    Write-Host "Fetching latest from 'gitee'..."
    Invoke-Git "fetch" "gitee"
    
    $canFastForward = $true
    try {
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
        Write-Host "Using '--force-with-lease' to push to 'gitee'..." -ForegroundColor Yellow
        Invoke-Git "push" "gitee" "main" "--force-with-lease"
    }
}
else {
    if ($platformsToPublish -contains "gitee") {
        Write-Host "Warning: Gitee remote not configured, but Gitee release is requested." -ForegroundColor Yellow
    }
}

# Push to GitLab if configured and selected
if ($remotes -contains "gitlab" -and ($platformsToPublish -contains "gitlab" -or $Platform -eq "all")) {
    Write-Host "Pushing 'main' to 'gitlab'..."
    
    $gitlabUrl = (git remote get-url gitlab)
    if ($gitlabUrl -match "^http://") {
        Write-Host "GitLab remote uses HTTP. Configuring Git to allow insecure connections..." -ForegroundColor Yellow
        $gitlabHost = ([System.Uri]$gitlabUrl).Host
        git config --global "http.https://$gitlabHost/.sslVerify" false 2>$null
        git config --global "http.$gitlabHost.sslVerify" false 2>$null
        git config "http.sslVerify" false 2>$null
        Write-Host "Git configured to allow HTTP connections to GitLab." -ForegroundColor Green
    }
    
    Write-Host "Fetching latest from 'gitlab'..."
    Invoke-Git "fetch" "gitlab"
    
    $canFastForward = $true
    try {
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
        Write-Host "Using '--force-with-lease' to push to 'gitlab'..." -ForegroundColor Yellow
        Invoke-Git "push" "gitlab" "main" "--force-with-lease"
    }
}
else {
    if ($platformsToPublish -contains "gitlab") {
        Write-Host "Warning: GitLab remote not configured, but GitLab release is requested." -ForegroundColor Yellow
    }
}

Write-Host "=== step 7: tags and releases ==="

$tagName = "v$Version"

$existingTag = git tag --list $tagName
if ($existingTag) {
    Write-Host "Tag $tagName already exists locally. Deleting and recreating..."
    Invoke-Git "tag" "-d" $tagName
}

Write-Host "Creating tag $tagName..."
Invoke-Git "tag" "-a" $tagName "-m" ("Release {0}" -f $Version)

# Push tags to remotes
Write-Host "Pushing tag $tagName to 'origin' (GitHub)..."
Invoke-Git "push" "origin" $tagName "--force"

if ($remotes -contains "gitee" -and ($platformsToPublish -contains "gitee" -or $Platform -eq "all")) {
    Write-Host "Pushing tag $tagName to 'gitee'..."
    Invoke-Git "push" "gitee" $tagName "--force"
}

if ($remotes -contains "gitlab" -and ($platformsToPublish -contains "gitlab" -or $Platform -eq "all")) {
    Write-Host "Pushing tag $tagName to 'gitlab'..."
    Invoke-Git "push" "gitlab" $tagName "--force"
}

# Create releases
if ($platformsToPublish -contains "github") {
    Write-Host "=== step 7a: GitHub release ==="
    try {
        Invoke-GhReleaseCreate -Version $Version -Package $packagePath -Notes $releaseNotes
    }
    catch {
        Write-Error "Failed to create GitHub release: $_"
        throw
    }
}

if ($platformsToPublish -contains "gitee") {
    Write-Host "=== step 7b: Gitee release ==="
    try {
        Invoke-GiteeReleaseCreate `
            -Version $Version `
            -Package $packagePath `
            -Notes $releaseNotes `
            -Owner $config.GiteeOwner `
            -Repo $config.GiteeRepo `
            -Token $config.GiteeToken
    }
    catch {
        Write-Host "Gitee release creation failed. Please check the error message above." -ForegroundColor Red
    }
}

if ($platformsToPublish -contains "gitlab") {
    Write-Host "=== step 7c: GitLab release ==="
    try {
        Invoke-GitLabReleaseCreate `
            -Version $Version `
            -Package $packagePath `
            -Notes $releaseNotes `
            -Url $config.GitLabUrl `
            -Owner $config.GitLabOwner `
            -Repo $config.GitLabRepo `
            -Token $config.GitLabToken
    }
    catch {
        $errorMsg = $_.Exception.Message
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            $reader.Close()
            Write-Host "GitLab API Error Response: $responseBody" -ForegroundColor Red
        }
        Write-Host "GitLab release creation failed: $errorMsg" -ForegroundColor Red
        Write-Host "Please check:" -ForegroundColor Yellow
        Write-Host "  1. GitLab URL is correct: $($config.GitLabUrl)" -ForegroundColor Yellow
        Write-Host "  2. Owner and Repo are correct: $($config.GitLabOwner)/$($config.GitLabRepo)" -ForegroundColor Yellow
        Write-Host "  3. Token has 'api' and 'write_repository' permissions" -ForegroundColor Yellow
        Write-Host "  4. Tag 'v$Version' exists in GitLab" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Code and tags have been pushed to configured remotes."
Write-Host "=== all done ==="

