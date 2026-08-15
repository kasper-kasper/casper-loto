$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($null -eq $npmCommand) {
    $portableNpm = Get-ChildItem -Path (Join-Path $repositoryRoot ".tools\node\node-v*-win-x64\npm.cmd") `
        -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $portableNpm) { throw "Node.js/npm is required." }
    $npmPath = $portableNpm.FullName
} else {
    $npmPath = $npmCommand.Source
}
$env:Path = (Split-Path -Parent $npmPath) + ";" + $env:Path
Push-Location (Join-Path $repositoryRoot "frontend\web")
try {
    & $npmPath run dev
} finally {
    Pop-Location
}
