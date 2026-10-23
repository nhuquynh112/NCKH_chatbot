param(
    [string]$WorkDir = $(if ($env:CHATBOT_WORK_DIR) { $env:CHATBOT_WORK_DIR } else { Join-Path ([IO.Path]::GetTempPath()) 'TechCare' }),
    [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$EvaluationLabel = 'after'
)

$ErrorActionPreference = 'Stop'
# Check native exit codes explicitly, including on Windows PowerShell 5.1.
$PSNativeCommandUseErrorActionPreference = $false
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$workRoot = [IO.Path]::GetFullPath($WorkDir).TrimEnd('\')
if ($workRoot.Equals($projectRoot, [StringComparison]::OrdinalIgnoreCase) -or $workRoot.StartsWith($projectRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'WorkDir phải nằm ngoài repository.'
}
$runRoot = Join-Path $workRoot ('tests-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
$testTempRoot = Join-Path $runRoot 'tmp'
New-Item -ItemType Directory -Path $testTempRoot -Force | Out-Null
$historicalInputs = @{
    PRODUCTS_PATH = 'techcare_products.json'
    RAG_DOCUMENTS_PATH = 'techcare_rag_documents.json'
    PRODUCT_CATALOG_PATH = 'product_catalog_extended.md'
    KNOWLEDGE_BASE_PATH = 'knowledge_base.md'
    CURATED_FAQ_PATH = 'faq_curated.json'
    LEGACY_VECTOR_INDEX_PATH = 'vector_index.json'
}
$environmentKeys = @('DATABASE_URL', 'ENVIRONMENT', 'AUTO_SEED', 'WARM_AI_ON_STARTUP', 'CHAT_PROVIDER', 'TEMP', 'TMP', 'CHATBOT_WORK_DIR', 'PYTHONPYCACHEPREFIX', 'PYTHONIOENCODING') + @($historicalInputs.Keys)
$savedEnvironment = @{}
foreach ($key in $environmentKeys) { $savedEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }

function Invoke-TestStep {
    param([string]$Label, [string]$Executable, [string[]]$CommandArguments)
    Write-Host $Label -ForegroundColor Cyan
    $stepPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 wraps native stderr as ErrorRecord, including
        # harmless library warnings. The native exit code decides success.
        $ErrorActionPreference = 'Continue'
        & $Executable @CommandArguments 2>&1 | Tee-Object -FilePath (Join-Path $runRoot ($Label.Substring(0, 2) + '.log'))
        $stepExitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $stepPreference }
    if ($stepExitCode -ne 0) { throw "$Label failed (exit $stepExitCode). Logs: $runRoot" }
}

$testDbPath = Join-Path $testTempRoot 'unit.db'
$buildRoot = Join-Path $runRoot 'frontend-build'
try {
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONPYCACHEPREFIX = Join-Path $runRoot 'python_cache'
    $env:CHATBOT_WORK_DIR = $runRoot
    $env:TEMP = $testTempRoot
    $env:TMP = $testTempRoot
    $env:DATABASE_URL = 'sqlite:///' + $testDbPath.Replace('\', '/')
    $env:ENVIRONMENT = 'test'
    $env:AUTO_SEED = 'true'
    $env:WARM_AI_ON_STARTUP = 'false'
    $env:CHAT_PROVIDER = 'ollama'
    Push-Location $backendRoot
    try {
        Invoke-TestStep '01 Backend unit/integration' $python @('-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v')
        # The fixed evaluation questions/answers describe the preserved catalog.
        # Keep them on that corpus; the unit suite above also checks rag_data_150.
        foreach ($key in $historicalInputs.Keys) {
            [Environment]::SetEnvironmentVariable($key, (Join-Path $backendRoot ('rag_data\' + $historicalInputs[$key])), 'Process')
        }
        Invoke-TestStep '02 Catalog/API regression' $python @('-B', 'evaluate_chatbot.py')
        Invoke-TestStep '03 FAQ/RAG fixed cases' $python @('-B', 'evaluate_quality.py', '--label', $EvaluationLabel, '--legacy-faqs')
        $offlineLabel = $EvaluationLabel + '-offline'
        Invoke-TestStep '04 Offline Ollama' $python @('-B', 'evaluate_quality.py', '--label', $offlineLabel, '--offline', '--legacy-faqs')
    }
    finally { Pop-Location }
    Push-Location $frontendRoot
    try {
        Invoke-TestStep '05 Frontend lint' $npm @('run', 'lint')
        Invoke-TestStep '06 Production build' $npm @('run', 'build', '--', '--outDir', $buildRoot)
    }
    finally { Pop-Location }
    Write-Host "Hoàn tất 6 nhóm kiểm thử. Log và phản hồi mới: $runRoot" -ForegroundColor Green
    # Remove only this run's generated build; keep test evidence outside Git.
    if ([IO.Path]::GetFullPath($buildRoot).StartsWith($runRoot + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $buildRoot)) {
        Remove-Item -LiteralPath $buildRoot -Recurse -Force
    }
}
finally {
    foreach ($key in $environmentKeys) { [Environment]::SetEnvironmentVariable($key, $savedEnvironment[$key], 'Process') }
    if ([IO.Path]::GetFullPath($testDbPath).StartsWith($testTempRoot + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $testDbPath)) {
        Remove-Item -LiteralPath $testDbPath -Force
    }
}
