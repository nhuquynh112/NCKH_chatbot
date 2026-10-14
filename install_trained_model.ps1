param(
    [string]$ModelPath,
    [string]$WorkDir = 'D:\NCKH\Codex'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$profilePath = Join-Path $projectRoot 'backend\rag_data\model_profile.json'
$profile = Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($ModelPath)) {
    $ModelPath = Join-Path $projectRoot $profile.gguf_path
}
$modelFile = Get-Item -LiteralPath $ModelPath -ErrorAction Stop
if ($modelFile.PSIsContainer -or $modelFile.Extension -ne '.gguf') {
    throw 'ModelPath phải là file GGUF của bản 3B đã train.'
}
if ($modelFile.Length -ne $profile.gguf_bytes) {
    throw 'Trọng số chưa được tải đủ. Nếu vừa clone project, chạy git lfs pull rồi cài lại.'
}
if ((Get-FileHash -LiteralPath $modelFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $profile.gguf_sha256) {
    throw 'File GGUF không khớp bản đã kiểm tra. Chưa import model.'
}
if ($profile.model -notmatch '^[a-zA-Z0-9][a-zA-Z0-9._/-]*:[a-zA-Z0-9._-]+$' -or $profile.model -match 'cloud') {
    throw 'Tên model phải là một tag Ollama chạy local.'
}
$ollama = Get-Command ollama -ErrorAction Stop
$workRoot = [IO.Path]::GetFullPath($WorkDir).TrimEnd('\')
New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
$temporaryFile = Join-Path $workRoot ('Modelfile-import-' + [guid]::NewGuid().ToString('N'))
$template = Get-Content -LiteralPath (Join-Path $projectRoot 'backend\rag_data\Modelfile.techcare3b') -Raw
$localPath = $modelFile.FullName.Replace('\', '/')
try {
    $template.Replace('FROM __LOCAL_GGUF__', ('FROM "' + $localPath + '"')) |
        Set-Content -LiteralPath $temporaryFile -Encoding utf8
    & $ollama.Source create $profile.model -f $temporaryFile
    if ($LASTEXITCODE -ne 0) { throw 'Ollama chưa import được model.' }
    Write-Host ('Đã cài ' + $profile.model + '. Khởi động lại backend để sử dụng.')
}
finally {
    if ([IO.Path]::GetFullPath($temporaryFile).StartsWith($workRoot + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $temporaryFile)) {
        Remove-Item -LiteralPath $temporaryFile -Force
    }
}
