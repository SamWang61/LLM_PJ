$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$profilePath = Join-Path $PSScriptRoot '.env.v4-test'
if (-not (Test-Path -LiteralPath $profilePath)) {
    throw 'Missing private .env.v4-test. See docs/AI_DASHBOARD.md; never paste credentials into Git.'
}
$env:APP_ENV_FILE = $profilePath
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') run.py
exit $LASTEXITCODE
