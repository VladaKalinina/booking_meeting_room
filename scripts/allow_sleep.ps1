$pidFile = Join-Path (Split-Path -Parent $PSScriptRoot) "prevent_sleep.pid"

if (-not (Test-Path $pidFile)) {
    Write-Output "PREVENT_SLEEP_NOT_RUNNING"
    exit 0
}

$processId = [int](Get-Content $pidFile -Raw)
$process = Get-Process -Id $processId -ErrorAction SilentlyContinue

if ($process) {
    Stop-Process -Id $processId -Force
    Write-Output "PREVENT_SLEEP_STOPPED pid=$processId"
}
else {
    Write-Output "PREVENT_SLEEP_PROCESS_NOT_FOUND pid=$processId"
}

Remove-Item $pidFile -Force
