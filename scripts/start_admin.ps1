$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($null -eq $npmCommand) {
    $portableNpm = Get-ChildItem -Path (Join-Path $repositoryRoot ".tools\node\node-v*-win-x64\npm.cmd") `
        -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $portableNpm) { throw "Node.js 22+ is required." }
    $npm = $portableNpm.FullName
} else {
    $npm = $npmCommand.Source
}
$env:Path = (Split-Path -Parent $npm) + ";" + $env:Path

Write-Output "Starting K-Loto Admin at http://127.0.0.1:5174"
Write-Output "Keep this terminal open. Press Ctrl+C to stop."
Push-Location (Join-Path $repositoryRoot "frontend\admin")
try {
    & $npm run dev
} finally {
    Pop-Location
}
