param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$NotesFile = "",
    [switch]$SkipPublish
)

Write-Warning "publish-release.ps1 is deprecated. Forwarding to release.ps1."
$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "release.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "release.ps1 not found at $scriptPath"
}

$arguments = @("-Version", $Version)
if ($NotesFile) {
    $arguments += @("-NotesFile", $NotesFile)
}
if ($SkipPublish) {
    $arguments += "-SkipPublish"
}

& $scriptPath @arguments