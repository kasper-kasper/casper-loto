$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repositoryRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Create .env from .env.example first."
}

function Set-EnvValue([string]$Name, [string]$Value) {
    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.AddRange([string[]][System.IO.File]::ReadAllLines($envFile))
    $pattern = "^\s*" + [regex]::Escape($Name) + "\s*="
    $updated = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match $pattern) {
            $lines[$index] = "$Name=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) { $lines.Add("$Name=$Value") }
    [System.IO.File]::WriteAllLines($envFile, $lines)
}

$secretBytes = [byte[]]::new(48)
$random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $random.GetBytes($secretBytes)
} finally {
    $random.Dispose()
}
$secret = [Convert]::ToBase64String($secretBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')

Set-EnvValue "APP_ENV" "development"
Set-EnvValue "MINIAPP_DEV_AUTH_ENABLED" "true"
Set-EnvValue "MINIAPP_DEV_SESSION_SECRET" $secret
Set-EnvValue "MINIAPP_DEV_USER_TELEGRAM_ID" "900000001"
Set-EnvValue "MINIAPP_DEV_INITIAL_BALANCE" "100000"
Set-EnvValue "MINIAPP_DEV_WEEKLY_TICKET_PRICE" "100"
Set-EnvValue "MINIAPP_DEV_WEEKLY_BASE_JACKPOT" "10000"
Set-EnvValue "MINIAPP_DEV_WEEKLY_RESERVE" "100000"

Write-Output "Local browser development mode is enabled in .env."
Write-Output "The generated session secret was saved without printing it."
