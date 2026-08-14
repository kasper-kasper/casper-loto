$ErrorActionPreference = "Stop"

ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

mypy backend/src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($null -eq $npmCommand) {
    $portableNpm = Get-ChildItem -Path ".tools\node\node-v*-win-x64\npm.cmd" `
        -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $portableNpm) {
        Write-Error "Node.js/npm is required for Mini App checks."
        exit 1
    }
    $npmPath = $portableNpm.FullName
} else {
    $npmPath = $npmCommand.Source
}
$nodeDirectory = Split-Path -Parent $npmPath
$env:Path = $nodeDirectory + ";" + $env:Path

Push-Location "frontend\miniapp"
try {
    & $npmPath run typecheck
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $npmPath run lint
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $npmPath test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $npmPath run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
