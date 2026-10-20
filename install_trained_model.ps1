param(
    [string]$ModelPath,
    [string]$WorkDir = $(if ($env:CHATBOT_WORK_DIR) { $env:CHATBOT_WORK_DIR } else { Join-Path ([IO.Path]::GetTempPath()) 'TechCare' }),
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelProfilePath = Join-Path $projectRoot 'backend\rag_data\model_profile.json'
$modelProfile = Get-Content -LiteralPath $modelProfilePath -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($ModelPath)) {
    $ModelPath = Join-Path $projectRoot $modelProfile.gguf_path
}
if (-not (Test-Path -LiteralPath $ModelPath -PathType Leaf)) {
    throw "Không tìm thấy GGUF: $ModelPath. Từ thư mục project chạy git lfs pull trước."
}
$modelFile = Get-Item -LiteralPath $ModelPath -ErrorAction Stop
if ($modelFile.PSIsContainer -or $modelFile.Extension -ne '.gguf') {
    throw 'ModelPath phải là file GGUF của bản 3B đã train.'
}
if ($modelFile.Length -ne $modelProfile.gguf_bytes) {
    throw 'Trọng số chưa được tải đủ. Nếu vừa clone project, chạy git lfs pull rồi cài lại.'
}
if ((Get-FileHash -LiteralPath $modelFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $modelProfile.gguf_sha256) {
    throw 'File GGUF không khớp bản đã kiểm tra. Chưa import model.'
}
if ($modelProfile.model -notmatch '^[a-zA-Z0-9][a-zA-Z0-9._/-]*:[a-zA-Z0-9._-]+$' -or $modelProfile.model -match 'cloud') {
    throw 'Tên model phải là một tag Ollama chạy local.'
}
if ($VerifyOnly) {
    Write-Host ('SHA256 và kích thước GGUF khớp profile: ' + $modelProfile.model)
    return
}
$ollama = Get-Command ollama -ErrorAction Stop
$workRoot = [IO.Path]::GetFullPath($WorkDir).TrimEnd('\')
if ($workRoot.Equals($projectRoot, [StringComparison]::OrdinalIgnoreCase) -or $workRoot.StartsWith($projectRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'WorkDir phải nằm ngoài repository để không lưu file tạm vào project.'
}
New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
$temporaryFile = Join-Path $workRoot ('Modelfile-import-' + [guid]::NewGuid().ToString('N'))
$template = Get-Content -LiteralPath (Join-Path $projectRoot 'backend\rag_data\Modelfile.techcare3b') -Raw
$localPath = $modelFile.FullName.Replace('\', '/')
try {
    [IO.File]::WriteAllText($temporaryFile,
        $template.Replace('FROM __LOCAL_GGUF__', ('FROM "' + $localPath + '"')),
        [Text.UTF8Encoding]::new($false))
    & $ollama.Source create $modelProfile.model -f $temporaryFile
    if ($LASTEXITCODE -ne 0) { throw 'Ollama chưa import được model.' }
    Write-Host ('Đã cài ' + $modelProfile.model + '. Khởi động lại backend để sử dụng.')
}
finally {
    if ([IO.Path]::GetFullPath($temporaryFile).StartsWith($workRoot + '\', [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $temporaryFile)) {
        Remove-Item -LiteralPath $temporaryFile -Force
    }
}
