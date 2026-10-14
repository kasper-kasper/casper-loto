$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repositoryRoot ".env"
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$alembic = Join-Path $repositoryRoot ".venv\Scripts\alembic.exe"
$toolLogs = Join-Path $repositoryRoot ".tools\local-dev-logs"

if (-not (Test-Path -LiteralPath $envFile)) { throw ".env does not exist." }
if (-not (Test-Path -LiteralPath $python)) { throw "Python virtual environment .venv is missing." }

$envLines = [System.IO.File]::ReadAllLines($envFile)
$enabled = $envLines | Where-Object { $_ -match '^\s*MINIAPP_DEV_AUTH_ENABLED\s*=\s*(true|1|yes)\s*$' }
if ($null -eq $enabled) { throw "Run scripts\enable_local_dev.ps1 first." }
$databaseLine = $envLines | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1
if ($null -eq $databaseLine -or $databaseLine -notmatch '@(?<host>\[[^\]]+\]|[^:/]+)(:\d+)?/') {
    throw "DATABASE_URL is missing or malformed."
}
$databaseHost = $Matches['host'].Trim('[', ']')
if ($databaseHost -notin @('localhost', '127.0.0.1', '::1')) {
    throw "Local development refuses a non-loopback DATABASE_URL."
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($null -eq $npmCommand) {
    $portableNpm = Get-ChildItem -Path (Join-Path $repositoryRoot ".tools\node\node-v*-win-x64\npm.cmd") -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $portableNpm) { throw "Node.js 22+ is required." }
    $npm = $portableNpm.FullName
} else {
    $npm = $npmCommand.Source
}
$env:Path = (Split-Path -Parent $npm) + ";" + $env:Path

New-Item -ItemType Directory -Path $toolLogs -Force | Out-Null
Push-Location $repositoryRoot
try {
    & $python -m scripts.migrate_database
    if ($LASTEXITCODE -ne 0) { throw "Alembic migration failed." }

    $api = Start-Process -FilePath $python `
        -ArgumentList @('-m', 'uvicorn', 'k_loto.main:app', '--host', '127.0.0.1', '--port', '8000') `
        -WorkingDirectory $repositoryRoot `
        -RedirectStandardOutput (Join-Path $toolLogs "api.out.log") `
        -RedirectStandardError (Join-Path $toolLogs "api.err.log") `
        -WindowStyle Hidden -PassThru
    $miniApp = Start-Process -FilePath $npm `
        -ArgumentList @('run', 'dev:browser') `
        -WorkingDirectory (Join-Path $repositoryRoot "frontend\miniapp") `
        -RedirectStandardOutput (Join-Path $toolLogs "miniapp.out.log") `
        -RedirectStandardError (Join-Path $toolLogs "miniapp.err.log") `
        -WindowStyle Hidden -PassThru

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null
            Invoke-WebRequest -Uri "http://127.0.0.1:5173" -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) { throw "Local services did not become ready. Check .tools\local-dev-logs." }

    Write-Output "K-Loto local test mode is ready at http://127.0.0.1:5173"
    Write-Output "API process: $($api.Id); Mini App process: $($miniApp.Id)"
    Write-Output "Keep this terminal open. Press Ctrl+C to stop both services."
    Start-Process "http://127.0.0.1:5173"
    while (-not $api.HasExited -and -not $miniApp.HasExited) {
        Start-Sleep -Seconds 2
        $api.Refresh()
        $miniApp.Refresh()
    }
} finally {
    if ($null -ne $api -and -not $api.HasExited) { Stop-Process -Id $api.Id }
    if ($null -ne $miniApp -and -not $miniApp.HasExited) { Stop-Process -Id $miniApp.Id }
    Pop-Location
}
