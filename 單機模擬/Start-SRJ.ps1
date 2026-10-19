param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('SAM', 'REN', 'JEFF')]
    [string]$Role,
    [switch]$PreflightOnly
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$script = Join-Path $repo 'scripts\srj_local_simulation.py'
$requirements = Join-Path $repo 'MuscleCore分析資料\website\requirements.txt'
if (-not (Test-Path -LiteralPath $script) -or -not (Test-Path -LiteralPath $requirements)) {
    throw '請從完整的 LLM_PJ 專案目錄啟動；程式或依賴清單不存在。'
}

$pythonExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $candidate = (& py -3 -c 'import sys; print(sys.executable)' 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path -LiteralPath $candidate)) {
        $pythonExe = $candidate
    }
}
if (-not $pythonExe) {
    $candidate = Get-Command python -ErrorAction SilentlyContinue
    if ($candidate) { $pythonExe = $candidate.Source }
}
if (-not $pythonExe) { throw '請先安裝 Python 3.11～3.14 x64；不會改動正式環境。' }
$version = & $pythonExe -c 'import sys; print(sys.version_info.major, sys.version_info.minor, 64 if sys.maxsize > 2**32 else 32)'
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^3 (11|12|13|14) 64$') {
    throw "需要 Python 3.11～3.14 x64，目前為 $version"
}

$private = Join-Path $env:LOCALAPPDATA 'VibeCart\SRJLocalSimulation'
$venv = Join-Path $private 'venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
$reports = Join-Path $private 'reports'
New-Item -ItemType Directory -Path $private, $reports -Force | Out-Null
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $pythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw '無法建立私有 Python 虛擬環境。' }
}
$requirementsHash = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
$marker = Join-Path $venv 'srj-dependencies.sha256'
if (-not (Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne $requirementsHash) {
    & $venvPython -m pip install --disable-pip-version-check -r $requirements 'mongomock==4.3.0'
    if ($LASTEXITCODE -ne 0) { throw '依賴安裝失敗；請確認可連 PyPI 後再雙擊。' }
    Set-Content -LiteralPath $marker -Value $requirementsHash -Encoding ascii
}

$raw = & $venvPython $script --role $Role --self-check
if ($LASTEXITCODE -ne 0) { throw '本機 12 項登入／權限／頁面預檢失敗，未啟動網站。' }
$result = $raw | ConvertFrom-Json
if ($result.status -ne 'passed' -or $result.atlas_contacted -ne $false) {
    throw '預檢範圍或資料隔離狀態不符合預期。'
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$report = Join-Path $reports "$Role-$stamp.json"
$result | Add-Member -NotePropertyName role -NotePropertyValue $Role
$result | Add-Member -NotePropertyName checked_at_taipei -NotePropertyValue (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
$result | Add-Member -NotePropertyName host -NotePropertyValue $env:COMPUTERNAME
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $report -Encoding utf8
Write-Host "本機預檢 12/12 通過；去敏報告：$report"
if ($PreflightOnly) { return }
Write-Host '接著只在 127.0.0.1 啟動。畫面上的密碼是每次隨機產生的本機示範密碼。'
& $venvPython $script --role $Role
if ($LASTEXITCODE -ne 0) { throw '本機模擬網站啟動或執行失敗。' }
