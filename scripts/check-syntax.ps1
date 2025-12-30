# 简单的语法检查
$scriptPath = ".\scripts\test-gitlab-release.ps1"
$content = Get-Content $scriptPath -Raw

# 检查基本语法
try {
    $null = [System.Management.Automation.PSParser]::Tokenize($content, [ref]$null)
    Write-Host "语法检查通过！" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "语法错误: $_" -ForegroundColor Red
    exit 1
}

