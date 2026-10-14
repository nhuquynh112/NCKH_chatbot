param(
    [string]$WorkDir = 'D:\NCKH\Codex',
    [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$EvaluationLabel = 'after'
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$env:PYTHONIOENCODING = "utf-8"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Không tìm thấy Python. Hãy cài Python hoặc tạo backend\.venv trước."
    }
    $python = $pythonCommand.Source
}

$testEnvironment = @{}
foreach ($key in @('DATABASE_URL', 'ENVIRONMENT', 'WARM_AI_ON_STARTUP', 'TEMP', 'TMP', 'CHATBOT_WORK_DIR', 'PYTHONPYCACHEPREFIX')) {
    $testEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
$testWorkRoot = [IO.Path]::GetFullPath($WorkDir).TrimEnd('\')
$testTempRoot = Join-Path $testWorkRoot 'test_tmp'
New-Item -ItemType Directory -Path $testTempRoot -Force | Out-Null
$env:CHATBOT_WORK_DIR = $testWorkRoot
$env:TEMP = $testTempRoot
$env:TMP = $testTempRoot
$env:PYTHONPYCACHEPREFIX = Join-Path $testWorkRoot 'python_cache'
$testDbPath = Join-Path $testTempRoot ("techcare-unit-" + [Guid]::NewGuid().ToString('N') + '.db')
$env:DATABASE_URL = 'sqlite:///' + $testDbPath.Replace('\', '/')
$env:ENVIRONMENT = 'test'
$env:WARM_AI_ON_STARTUP = 'false'

Write-Host "[1/6] Backend unit tests (database thử riêng)" -ForegroundColor Cyan
Push-Location $backendRoot
try {
    & $python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Backend unit tests failed.' }
    Write-Host "[2/6] Bộ hồi quy catalog/API" -ForegroundColor Cyan
    & $python evaluate_chatbot.py
    if ($LASTEXITCODE -ne 0) { throw 'Catalog/API regression failed.' }
    Write-Host "[3/6] FAQ/RAG trên câu hỏi cố định" -ForegroundColor Cyan
    & $python evaluate_quality.py --label $EvaluationLabel --legacy-faqs
    if ($LASTEXITCODE -ne 0) { throw 'FAQ/RAG evaluation failed.' }
    Write-Host "[4/6] Ollama gián đoạn" -ForegroundColor Cyan
    $offlineLabel = if ($EvaluationLabel -eq 'after') { 'offline' } else { $EvaluationLabel + '-offline' }
    & $python evaluate_quality.py --label $offlineLabel --offline --legacy-faqs
    if ($LASTEXITCODE -ne 0) { throw 'Offline evaluation failed.' }
}
finally {
    foreach ($key in $testEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $testEnvironment[$key], 'Process')
    }
    Pop-Location
    if (([IO.Path]::GetFullPath($testDbPath)).StartsWith($testTempRoot + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $testDbPath)) {
        Remove-Item -LiteralPath $testDbPath -Force
    }
}

Write-Host "[5/6] Frontend lint" -ForegroundColor Cyan
Push-Location $frontendRoot
try {
    npm run lint
    if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed.' }
    Write-Host "[6/6] Frontend production build" -ForegroundColor Cyan
    $testBuildRoot = Join-Path $testWorkRoot ('frontend-test-build-' + [Guid]::NewGuid().ToString('N'))
    npm run build -- --outDir $testBuildRoot
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
}
finally {
    if ($testBuildRoot -and ([IO.Path]::GetFullPath($testBuildRoot)).StartsWith($testWorkRoot + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $testBuildRoot)) {
        Remove-Item -LiteralPath $testBuildRoot -Recurse -Force
    }
    Pop-Location
}

Write-Host "Hoàn tất. Báo cáo nằm ở CHATBOT_EVALUATION_REPORT.md; output thử nghiệm ở $testWorkRoot\evaluation_artifacts." -ForegroundColor Green
