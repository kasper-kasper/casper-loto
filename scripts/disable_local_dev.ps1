$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repositoryRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw ".env does not exist."
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([string[]][System.IO.File]::ReadAllLines($envFile))
$pattern = '^\s*MINIAPP_DEV_AUTH_ENABLED\s*='
$updated = $false
for ($index = 0; $index -lt $lines.Count; $index++) {
    if ($lines[$index] -match $pattern) {
        $lines[$index] = "MINIAPP_DEV_AUTH_ENABLED=false"
        $updated = $true
        break
    }
}
if (-not $updated) { $lines.Add("MINIAPP_DEV_AUTH_ENABLED=false") }
[System.IO.File]::WriteAllLines($envFile, $lines)

Write-Output "Local browser development bypass is disabled."
