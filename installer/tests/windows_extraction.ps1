param([Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference = 'Stop'
function Install-Test([string]$Label, [string]$Selection, [string]$Target) {
    $exe = (Resolve-Path "dist/windows/Aura-Setup-$Label-$Version.exe").Path
    $arguments = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=`"$Target`""
    if ($Selection) { $arguments += " /TYPE=custom /COMPONENTS=`"$Selection`"" }
    else { $arguments += ' /TYPE=recommended' }
    $result = Start-Process $exe -ArgumentList $arguments -Wait -PassThru
    if ($result.ExitCode -ne 0) { throw "Installer failed: $Label ($Selection)" }
    foreach ($file in @('LEIAME.txt','backend/manage.py','desktop/Components.ps1')) {
        if (-not (Test-Path "$Target/$file")) { throw "Missing application file: $file" }
    }
    if (Test-Path "$Target/backend/.env") { throw 'Secret file included in installer' }
    if ($Label -eq 'Completo') {
        $options = Get-Content "$Target/desktop/install-options.json" -Raw | ConvertFrom-Json
        . "$Target/desktop/Components.ps1"
        Assert-AuraOptions $options
        $expected = if ($Selection) { $Selection.Split(',') } else { @('app','python','vcredist','mysql') }
        foreach ($name in @('python','vcredist','mysql','dbeaver','heidisql')) {
            if ($options.$name -ne ($name -in $expected)) { throw "Checkbox not persisted: $Selection / $name" }
        }
    }
}
Install-Test 'Essencial' '' (Join-Path $env:RUNNER_TEMP 'Aura Installed Essencial')
$target = Join-Path $env:RUNNER_TEMP 'Aura Installed Completo'
Install-Test 'Completo' '' $target
# Reinstall in the same directory, including deselection, with no interactive configuration.
foreach ($selection in @('app,dbeaver','app,heidisql','app,python,vcredist,mysql,dbeaver,heidisql','app')) {
    Install-Test 'Completo' $selection $target
}
Write-Host 'PASS: both EXEs extracted; recommended and custom component selections preserved.'
