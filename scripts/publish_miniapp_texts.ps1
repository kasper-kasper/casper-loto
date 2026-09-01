$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repositoryRoot
try {
    $changes = @(git status --porcelain)
    if ($changes.Count -eq 0) {
        Write-Host "No text changes found."
        exit 0
    }
    $unexpected = @($changes | Where-Object {
        $_.Substring(3).Replace("\", "/") -ne "frontend/miniapp/src/content.ts"
    })
    if ($unexpected.Count -gt 0) {
        throw "Other project files are changed. Ask the developer before publishing."
    }

    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -eq $npmCommand) {
        $npmCommand = Get-ChildItem -Path ".tools\node\node-v*-win-x64\npm.cmd" `
            -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if ($null -eq $npmCommand) {
        throw "Node.js was not found. Ask the developer for help."
    }
    $npmPath = $npmCommand.Source
    if (-not $npmPath) { $npmPath = $npmCommand.FullName }
    $env:Path = (Split-Path -Parent $npmPath) + ";" + $env:Path

    Push-Location "frontend\miniapp"
    try {
        & $npmPath run typecheck
        if ($LASTEXITCODE -ne 0) { throw "Typecheck failed." }
        & $npmPath run lint
        if ($LASTEXITCODE -ne 0) { throw "Lint failed." }
        & $npmPath test
        if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
        & $npmPath run build
        if ($LASTEXITCODE -ne 0) { throw "Build failed." }
    } finally {
        Pop-Location
    }

    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "Git formatting check failed." }
    git add frontend/miniapp/src/content.ts
    git commit -m "copy: update Mini App texts"
    if ($LASTEXITCODE -ne 0) { throw "Git commit failed." }
    & ".\.venv\Scripts\python.exe" scripts/release_vps.py --services gateway
    if ($LASTEXITCODE -ne 0) { throw "Mini App deployment failed." }
    Write-Host "Done: Mini App texts are published."
} finally {
    Pop-Location
}
