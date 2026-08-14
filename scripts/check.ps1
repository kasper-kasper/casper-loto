$ErrorActionPreference = "Stop"

ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

mypy backend/src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
