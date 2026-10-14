$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$toolDirectory = Join-Path $repositoryRoot ".venv\Scripts"
$ruff = Join-Path $toolDirectory "ruff.exe"
$mypy = Join-Path $toolDirectory "mypy.exe"
$pytest = Join-Path $toolDirectory "pytest.exe"
foreach ($tool in @($ruff, $mypy, $pytest)) {
    if (-not (Test-Path -LiteralPath $tool)) {
        throw "Python development environment is missing. Run uv sync --extra dev."
    }
}

Push-Location $repositoryRoot
try {
& $ruff check backend bot scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $ruff format --check backend bot scripts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $mypy backend/src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $pytest --ignore=backend/tests/test_web_api.py --ignore=backend/tests/test_web_identity.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$python = Join-Path $toolDirectory "python.exe"
& $python -m scripts.build_frontends --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

} finally {
    Pop-Location
}
