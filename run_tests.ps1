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

Write-Host "[1/4] Backend unit tests" -ForegroundColor Cyan
Push-Location $backendRoot
try {
    & $python -m unittest discover -s tests -v
    Write-Host "[2/4] Bộ đánh giá chatbot tổng hợp" -ForegroundColor Cyan
    & $python evaluate_chatbot.py
}
finally {
    Pop-Location
}

Write-Host "[3/4] Frontend lint" -ForegroundColor Cyan
Push-Location $frontendRoot
try {
    npm run lint
    Write-Host "[4/4] Frontend production build" -ForegroundColor Cyan
    npm run build
}
finally {
    Pop-Location
}

Write-Host "Hoàn tất. Xem backend\EVALUATION_REPORT.md để đọc kết quả." -ForegroundColor Green
