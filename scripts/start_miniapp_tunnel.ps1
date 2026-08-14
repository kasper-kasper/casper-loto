$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repositoryRoot ".env"
$miniAppUrl = "http://127.0.0.1:5173"
$toolDirectory = Join-Path $repositoryRoot ".tools\cloudflared"
$cloudflared = Join-Path $toolDirectory "cloudflared.exe"

if (Test-Path -LiteralPath $envFile) {
    $bypassEnabled = Select-String -LiteralPath $envFile `
        -Pattern '^\s*MINIAPP_DEV_AUTH_ENABLED\s*=\s*(true|1|yes)\s*$' `
        -CaseSensitive:$false
    if ($null -ne $bypassEnabled) {
        throw "Disable MINIAPP_DEV_AUTH_ENABLED before opening a public tunnel."
    }
}

try {
    Invoke-WebRequest -Uri $miniAppUrl -Method Head -TimeoutSec 3 | Out-Null
} catch {
    throw "Mini App is not running at $miniAppUrl. Start npm run dev:telegram first."
}

if (-not (Test-Path -LiteralPath $cloudflared)) {
    New-Item -ItemType Directory -Path $toolDirectory -Force | Out-Null
    Write-Output "Downloading cloudflared from the official Cloudflare release..."
    Invoke-WebRequest `
        -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
        -OutFile $cloudflared
}

Write-Output "Starting a temporary HTTPS tunnel."
Write-Output "Copy the https://...trycloudflare.com URL into MINIAPP_URL, then restart the bot."
Write-Output "Keep this terminal open. Press Ctrl+C to stop the tunnel."
& $cloudflared tunnel --url $miniAppUrl --no-autoupdate
