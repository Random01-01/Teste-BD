# Selection policy shared by the GUI installer, ZIP configurator and native tests.
function Assert-AuraOptions($Options) {
    $names = @('schema','python','vcredist','mysql','dbeaver','heidisql')
    if ($null -eq $Options -or ($Options.schema -isnot [int] -and $Options.schema -isnot [long]) -or $Options.schema -ne 1) { throw 'Formato de componentes invalido. Execute o setup novamente.' }
    foreach ($name in @('python','vcredist','mysql','dbeaver','heidisql')) {
        if ($Options.$name -isnot [bool]) { throw "Componente invalido: $name. Execute o setup novamente." }
    }
    foreach ($property in $Options.PSObject.Properties.Name) {
        if ($property -notin $names) { throw "Opcao desconhecida: $property" }
    }
}

function Read-AuraChoice([string]$Question, [bool]$Default) {
    $hint = if ($Default) { 'S/n' } else { 's/N' }
    while ($true) {
        $answer = (Read-Host "$Question [$hint]").Trim().ToLowerInvariant()
        if (-not $answer) { return $Default }
        if ($answer -in @('s','sim')) { return $true }
        if ($answer -in @('n','nao','não')) { return $false }
        Write-Host 'Responda S ou N.'
    }
}

function Get-AuraOptions([string]$Mode, [string]$Path, [bool]$Choose = $false) {
    if ($Mode -eq 'Essential') {
        return [pscustomobject]@{schema=1; python=$false; vcredist=$false; mysql=$false; dbeaver=$false; heidisql=$false}
    }
    $options = [pscustomobject]@{schema=1; python=$true; vcredist=$true; mysql=$true; dbeaver=$false; heidisql=$false}
    if (Test-Path -LiteralPath $Path) {
        $options = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        Assert-AuraOptions $options
        if (-not $Choose) { return $options }
    }
    Write-Host 'SELECAO DE COMPONENTES: desmarcar nao desinstala programas nem dispensa requisitos.'
    Write-Host 'MySQL desmarcado: uma NOVA instalacao usara banco local existente. Bancos Aura ja configurados sao preservados.'
    Write-Host 'DBeaver/HeidiSQL sao clientes de administracao, nao substitutos do servidor MySQL.'
    Write-Host 'Pacotes marcados usam os termos de seus fornecedores via winget. Consulte o LEIAME.'
    $options.python = Read-AuraChoice 'Instalar Python compativel se faltar?' $options.python
    $options.vcredist = Read-AuraChoice 'Instalar Visual C++ Runtime x64 se faltar?' $options.vcredist
    $options.mysql = Read-AuraChoice 'Preparar MySQL 8.4 privado (instalar servidor se faltar)?' $options.mysql
    $options.dbeaver = Read-AuraChoice 'Instalar DBeaver Community (opcional)?' $options.dbeaver
    $options.heidisql = Read-AuraChoice 'Instalar HeidiSQL (opcional)?' $options.heidisql
    $options | ConvertTo-Json | Set-Content -LiteralPath $Path -Encoding UTF8
    return $options
}

function Require-AuraPermission([bool]$Allowed, [string]$Component) {
    if (-not $Allowed) {
        throw "$Component necessario, mas nao encontrado e sua instalacao nao foi selecionada. Prepare-o manualmente ou marque esse componente no setup. Nenhum pacote desmarcado sera instalado."
    }
}

function Get-AuraDatabaseMode($Options, [bool]$HasConfig, [bool]$HasManagedState) {
    # A previous configuration always wins. Never migrate/repoint a database by checkbox.
    if ($HasManagedState -or (-not $HasConfig -and $Options.mysql)) { return 'Complete' }
    return 'Essential'
}

function Get-AuraWingetResult([int]$Code) {
    $hex = [BitConverter]::ToUInt32([BitConverter]::GetBytes($Code), 0).ToString('X8')
    if ($hex -in @('00000000','8A15002B','8A150061','8A15010D')) { return 'ok' }
    if ($hex -in @('00000BC2','00000669','8A150109','8A15010A')) { return 'reboot' }
    return 'error'
}

function Install-Dependency([string]$Id, [string]$Version = '', [string]$Scope = '') {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'Instale/atualize o Instalador de Aplicativo (App Installer) pela Microsoft Store para obter winget. Nenhum pacote foi baixado de fonte alternativa.'
    }
    Write-Host "Preparando $Id pela fonte winget (sem atualizar instalacoes existentes)..."
    $arguments = @('install','--id',$Id,'--exact','--source','winget','--silent','--no-upgrade','--accept-package-agreements','--accept-source-agreements')
    if ($Version) { $arguments += @('--version', $Version) }
    if ($Scope) { $arguments += @('--scope', $Scope) }
    & $winget.Source @arguments
    $result = Get-AuraWingetResult $LASTEXITCODE
    if ($result -eq 'reboot') { throw 'O componente solicitou reinicializacao. Reinicie o Windows e abra Configurar Aura novamente.' }
    if ($result -ne 'ok') { throw "Nao foi possivel instalar $Id (codigo $LASTEXITCODE). Confira internet, UAC e winget; depois tente novamente." }
}

function Install-AuraOptionalTools($Options) {
    $failures = @()
    foreach ($tool in @(@('dbeaver','DBeaver.DBeaver.Community'), @('heidisql','HeidiSQL.HeidiSQL'))) {
        if ($Options.($tool[0])) {
            try { Install-Dependency $tool[1] '' 'user' }
            catch { $failures += $_.Exception.Message }
        }
    }
    if ($failures.Count) {
        throw ('Aura configurado, mas houve falha em gerenciador opcional. Reabra Configurar Aura para tentar novamente. ' + ($failures -join ' / '))
    }
}

function Test-AuraVCRuntime {
    # Microsoft's x64 redistributable may register in either registry view.
    foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)) {
        $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, $view)
        $key = $null
        try {
            $key = $base.OpenSubKey('SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64')
            if ($key -and $key.GetValue('Installed') -eq 1) { return $true }
        } finally {
            if ($key) { $key.Dispose() }
            $base.Dispose()
        }
    }
    return $false
}
