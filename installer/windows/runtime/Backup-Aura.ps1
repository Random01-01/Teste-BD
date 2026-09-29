$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:AURA_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Aura'
$python = Join-Path $env:AURA_DATA_DIR 'venv\Scripts\python.exe'
try {
    if (-not (Test-Path $python)) { throw 'Configure o Aura primeiro.' }
    & $python (Join-Path $PSScriptRoot 'backup.py')
    if ($LASTEXITCODE -ne 0) { throw 'Backup não concluído. Confira a mensagem acima.' }
    Read-Host 'Pressione Enter para fechar'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Pressione Enter para fechar'
    exit 1
}
