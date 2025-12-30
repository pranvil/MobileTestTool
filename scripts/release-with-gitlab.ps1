<#
.SYNOPSIS
    发布脚本（包含 GitLab 支持）

.DESCRIPTION
    这是一个便捷脚本，自动加载 GitLab 配置并调用 release.ps1

.PARAMETER Version
    版本号，例如 "0.9.6.5.4"

.PARAMETER NotesFile
    可选的发布说明文件路径，例如 "docs\notes.md"

.EXAMPLE
    .\scripts\release-with-gitlab.ps1 -Version "0.9.6.5.4"

.EXAMPLE
    .\scripts\release-with-gitlab.ps1 -Version "0.9.6.5.4" -NotesFile "docs\notes.md"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = ""
)

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
    Write-Host "Or create .gitlab-config.ps1 file in project root:" -ForegroundColor Yellow
    Write-Host "   `$GitLabUrl = `"http://10.129.93.67`""
    Write-Host "   `$GitLabOwner = `"hao.lin`""
    Write-Host "   `$GitLabRepo = `"mobiletesttool`""
    Write-Host "   `$GitLabToken = `"your_token`""
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "GitLab Configuration:" -ForegroundColor Green
Write-Host "  URL:   $gitlabUrl" -ForegroundColor Cyan
Write-Host "  Owner: $gitlabOwner" -ForegroundColor Cyan
Write-Host "  Repo:  $gitlabRepo" -ForegroundColor Cyan
Write-Host "  Token: $($gitlabToken.Substring(0, [Math]::Min(8, $gitlabToken.Length)))..." -ForegroundColor Cyan
Write-Host ""

# 调用主发布脚本
& .\scripts\release.ps1 -Version $Version -NotesFile $NotesFile `
    -GitLabUrl $gitlabUrl `
    -GitLabOwner $gitlabOwner `
    -GitLabRepo $gitlabRepo `
    -GitLabToken $gitlabToken

