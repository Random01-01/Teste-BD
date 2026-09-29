$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:AURA_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Aura'
$python = Join-Path $env:AURA_DATA_DIR 'venv\Scripts\python.exe'
try {
    if (-not (Test-Path $python)) { throw 'Abra Configurar Aura antes de iniciar.' }
    & $python (Join-Path $PSScriptRoot 'run.py')
    if ($LASTEXITCODE -ne 0) { throw 'O Aura não iniciou. Confira a mensagem acima.' }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Pressione Enter para fechar'
    exit 1
}
