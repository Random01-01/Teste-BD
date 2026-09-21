param([ValidateSet('Essential','Complete')][string]$Mode = 'Essential')
$ErrorActionPreference = 'Stop'
$AppDir = Split-Path $PSScriptRoot -Parent
$DataDir = Join-Path $env:LOCALAPPDATA 'Aura'
$env:AURA_DATA_DIR = $DataDir
$env:PYTHONUTF8 = '1'

function Find-AuraPython {
    $candidates = @()
    foreach ($version in @('3.13','3.12')) {
        foreach ($base in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore')) {
            $key = Join-Path $base "$version\InstallPath"
            if (Test-Path $key) {
                $install = (Get-Item $key).GetValue('')
                if ($install) { $candidates += (Join-Path $install 'python.exe') }
            }
        }
        $candidates += (Join-Path $env:LOCALAPPDATA ("Programs\Python\Python" + $version.Replace('.','') + '\python.exe'))
    }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notmatch 'WindowsApps') { $candidates += $command.Source }
    foreach ($file in $candidates | Select-Object -Unique) {
        if (Test-Path $file) {
            & $file -c "import sys,struct;sys.exit(0 if sys.version_info[:2] in [(3,12),(3,13)] and struct.calcsize('P')==8 else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $file }
        }
    }
    return $null
}

function Find-AuraMySQL {
    $folders = @(Join-Path $env:ProgramFiles 'MySQL\MySQL Server 8.4\bin')
    $command = Get-Command mysqld.exe -ErrorAction SilentlyContinue
    if ($command) { $folders += (Split-Path $command.Source -Parent) }
    foreach ($folder in $folders | Select-Object -Unique) {
        $file = Join-Path $folder 'mysqld.exe'
        if (Test-Path $file) {
            $version = & $file --version
            if ($LASTEXITCODE -eq 0 -and $version -match '\b8\.4\.') { return $folder }
        }
    }
    return $null
}

function Install-Dependency([string]$Id, [string]$Version = '', [string]$Scope = '') {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'Instale/atualize o Instalador de Aplicativo (App Installer) pela Microsoft Store, para obter winget, e tente novamente. Nenhum pacote foi baixado de fonte alternativa.'
    }
    Write-Host "Baixando/instalando $Id pela fonte oficial winget..."
    $arguments = @('install','--id',$Id,'--exact','--source','winget','--silent','--accept-package-agreements','--accept-source-agreements')
    if ($Version) { $arguments += @('--version', $Version) }
    if ($Scope) { $arguments += @('--scope', $Scope) }
    & $winget.Source @arguments
    if ($LASTEXITCODE -eq 3010) { throw 'O pré-requisito solicitou reinicialização. Reinicie o Windows e abra Configurar Aura novamente.' }
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível instalar $Id (código $LASTEXITCODE). Verifique internet, permissão/UAC e winget; depois tente novamente." }
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'O Aura requer Windows x64.' }
    Write-Host 'AURA - CONFIGURACAO LOCAL' -ForegroundColor Cyan
    Write-Host 'Feche o Aura antes de atualizar. As senhas não aparecem ao digitar.'
    Write-Host 'Não feche esta janela antes da mensagem de conclusão.'
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $DataDir /inheritance:r /grant:r "*$($sid):(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível restringir as permissões da pasta de dados.' }
    $python = Find-AuraPython
    if (-not $python -and $Mode -eq 'Complete') {
        Install-Dependency 'Python.Python.3.13' '' 'user'
        $python = Find-AuraPython
    }
    if (-not $python) { throw 'Python 3.12 ou 3.13 x64 não encontrado. Instale-o ou use o Setup Completo.' }
    $mysqlBin = ''
    if ($Mode -eq 'Complete') {
        $vc = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue
        if (-not $vc -or $vc.Installed -ne 1) { Install-Dependency 'Microsoft.VCRedist.2015+.x64' }
        $mysqlBin = Find-AuraMySQL
        if (-not $mysqlBin) {
            Install-Dependency 'Oracle.MySQL' '8.4.9'
            $mysqlBin = Find-AuraMySQL
        }
        if (-not $mysqlBin) { throw 'MySQL 8.4 não encontrado após a instalação. Consulte o LEIAME.' }
    }
    $venv = Join-Path $DataDir 'venv'
    if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
        & $python -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente Python.' }
    }
    $runtime = Join-Path $venv 'Scripts\python.exe'
    & $runtime -m pip install --only-binary=:all: -r (Join-Path $AppDir 'backend\requirements-windows.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Falha no download das dependências Python. Confira a internet e use Python x64 compatível.' }
    $configureArgs = @((Join-Path $PSScriptRoot 'configure.py'), '--mode', $Mode)
    if ($mysqlBin) { $configureArgs += @('--mysql-bin', $mysqlBin) }
    & $runtime @configureArgs
    if ($LASTEXITCODE -ne 0) { throw 'A configuração do Aura não terminou. Leia a mensagem acima e tente novamente.' }
    Read-Host 'Pressione Enter para fechar'
    exit 0
} catch {
    Write-Host "`nERRO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Não foi apagado o banco existente. Corrija o problema e abra Configurar Aura novamente.'
    Read-Host 'Pressione Enter para fechar'
    exit 1
}
