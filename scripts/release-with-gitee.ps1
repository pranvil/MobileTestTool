#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    发布脚本（包含 Gitee 支持）

.DESCRIPTION
    这是一个便捷脚本，自动加载 Gitee 配置并调用 release.ps1

.PARAMETER Version
    版本号（必需）

.PARAMETER NotesFile
    发布说明文件路径（可选）

.PARAMETER SkipPublish
    跳过发布步骤（仅打包）

.PARAMETER SkipPackage
    跳过打包步骤（使用已有包）

.EXAMPLE
    .\scripts\release-with-gitee.ps1 -Version "0.9.6.4.4"

.EXAMPLE
    .\scripts\release-with-gitee.ps1 -Version "0.9.6.4.4" -NotesFile "docs\notes.md"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = "",
    [switch]$SkipPublish,
    [switch]$SkipPackage
)

$ErrorActionPreference = "Stop"

# 从环境变量读取 Gitee 配置
$giteeOwner = $env:GITEE_OWNER
$giteeRepo = $env:GITEE_REPO
$giteeToken = $env:GITEE_TOKEN

# 如果环境变量未设置，尝试从配置文件读取
if ((-not $giteeOwner -or -not $giteeRepo -or -not $giteeToken) -and (Test-Path ".\.gitee-config.ps1")) {
    Write-Host "Loading Gitee configuration from .gitee-config.ps1..." -ForegroundColor Cyan
    . .\.gitee-config.ps1
    
    if ($GiteeOwner) { $giteeOwner = $GiteeOwner }
    if ($GiteeRepo) { $giteeRepo = $GiteeRepo }
    if ($GiteeToken) { $giteeToken = $GiteeToken }
}

# 检查配置
if (-not $giteeOwner -or -not $giteeRepo -or -not $giteeToken) {
    Write-Error @"
Gitee configuration not found!

Please do one of the following:

1. Set environment variables:
   `$env:GITEE_OWNER = "your_username"
   `$env:GITEE_REPO = "MobileTestTool"
   `$env:GITEE_TOKEN = "your_token"

2. Create .gitee-config.ps1 file in project root:
   `$GiteeOwner = "your_username"
   `$GiteeRepo = "MobileTestTool"
   `$GiteeToken = "your_token"

See docs/Gitee发布配置指南.md for details.
"@
    exit 1
}

Write-Host "Gitee Configuration:" -ForegroundColor Green
Write-Host "  Owner: $giteeOwner" -ForegroundColor Cyan
Write-Host "  Repo:  $giteeRepo" -ForegroundColor Cyan
Write-Host "  Token: $($giteeToken.Substring(0, [Math]::Min(8, $giteeToken.Length)))..." -ForegroundColor Cyan
Write-Host ""

# 调用主发布脚本
$scriptPath = Join-Path $PSScriptRoot "release.ps1"

# Build parameter hashtable for splatting
$params = @{
    Version = $Version
    GiteeOwner = $giteeOwner
    GiteeRepo = $giteeRepo
    GiteeToken = $giteeToken
}

if ($NotesFile) {
    $params.NotesFile = $NotesFile
}

if ($SkipPublish) {
    $params.SkipPublish = $true
}

if ($SkipPackage) {
    $params.SkipPackage = $true
}

# Use splatting to pass parameters
& $scriptPath @params

