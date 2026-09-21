param([Parameter(Mandatory=$true)][string]$RuntimeDir)
$ErrorActionPreference = 'Stop'
. (Join-Path $RuntimeDir 'Components.ps1')
function Assert($Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Assert-Throws([scriptblock]$Action) {
    $threw = $false
    try { & $Action | Out-Null } catch { $threw = $true }
    Assert $threw 'Expected a clear failure'
}
$temp = Join-Path $env:TEMP ('aura-components-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $temp | Out-Null
try {
    $path = Join-Path $temp 'options.json'
    $script:requests = @()
    $originalInstall = ${function:Install-Dependency}
    function Install-Dependency($Id, $Version, $Scope) {
        Assert ($Scope -eq 'user') 'Optional clients should prefer current user'
        $script:requests += $Id
    }
    foreach ($mask in 0..31) {
        $o = [pscustomobject]@{schema=1;python=[bool]($mask -band 1);vcredist=[bool]($mask -band 2);mysql=[bool]($mask -band 4);dbeaver=[bool]($mask -band 8);heidisql=[bool]($mask -band 16)}
        $o | ConvertTo-Json | Set-Content $path -Encoding UTF8
        $loaded = Get-AuraOptions 'Complete' $path
        Assert-AuraOptions $loaded
        Assert ($loaded.dbeaver -eq $o.dbeaver -and $loaded.mysql -eq $o.mysql) 'Saved selections were lost'
        $script:requests = @()
        Install-AuraOptionalTools $loaded
        Assert (($script:requests -contains 'DBeaver.DBeaver.Community') -eq $o.dbeaver) 'DBeaver selection not respected'
        Assert (($script:requests -contains 'HeidiSQL.HeidiSQL') -eq $o.heidisql) 'HeidiSQL selection not respected'
        foreach ($hasConfig in @($false,$true)) {
            foreach ($hasManaged in @($false,$true)) {
                $mode = Get-AuraDatabaseMode $loaded $hasConfig $hasManaged
                $private = $hasManaged -or (-not $hasConfig -and $o.mysql)
                Assert (($mode -eq 'Complete') -eq $private) 'Existing database selection was changed'
            }
        }
        $essential = Get-AuraOptions 'Essential' $path
        Assert (-not ($essential.python -or $essential.vcredist -or $essential.mysql -or $essential.dbeaver -or $essential.heidisql)) 'Essential inherited Complete choices'
    }
    Require-AuraPermission $true 'test'
    Assert-Throws { Require-AuraPermission $false 'test' }
    $loaded.python = 'true'
    Assert-Throws { Assert-AuraOptions $loaded }
    '{"schema":2}' | Set-Content $path
    Assert-Throws { Get-AuraOptions 'Complete' $path }
    Remove-Item $path
    $script:answers = [Collections.Generic.Queue[string]]::new()
    foreach ($answer in @('n','n','n','s','n')) { $script:answers.Enqueue($answer) }
    function Read-Host($Prompt) { return $script:answers.Dequeue() }
    $custom = Get-AuraOptions 'Complete' $path
    Assert (-not $custom.python -and -not $custom.mysql -and $custom.dbeaver -and -not $custom.heidisql) 'ZIP choices not saved'
    $resumed = Get-AuraOptions 'Complete' $path
    Assert ($resumed.dbeaver) 'Resume should not prompt or reset choices'
    # Optional failure must be reported, while still attempting the other selected tool.
    function Install-Dependency($Id, $Version, $Scope) {
        $script:requests += $Id
        if ($Id -eq 'DBeaver.DBeaver.Community') { throw 'simulated network failure' }
    }
    $custom.heidisql = $true
    $script:requests = @()
    Assert-Throws { Install-AuraOptionalTools $custom }
    Assert ($script:requests.Count -eq 2) 'A failed optional package hid another selected package'
    # Exercise real argument construction, with a fake winget executable only.
    Set-Item Function:Install-Dependency $originalInstall
    function Get-Command($Name) { return [pscustomobject]@{Source='Invoke-FakeWinget'} }
    function Invoke-FakeWinget {
        $script:wingetArgs = $args
        $global:LASTEXITCODE = $script:exitCode
    }
    $script:exitCode = 0
    Install-Dependency 'DBeaver.DBeaver.Community' '' 'user'
    Assert ($script:wingetArgs -contains '--no-upgrade') 'Existing third-party software must not be upgraded implicitly'
    Assert (($script:wingetArgs -join ' ') -match '--id DBeaver.DBeaver.Community --exact --source winget') 'Unexpected download source or ID'
    foreach ($hex in @('8A15002B','8A150061','8A15010D')) {
        $script:exitCode = [BitConverter]::ToInt32([BitConverter]::GetBytes([Convert]::ToUInt32($hex,16)),0)
        Install-Dependency 'test-package'
    }
    $script:exitCode = 3010
    Assert-Throws { Install-Dependency 'test-package' }
    $script:exitCode = 1
    Assert-Throws { Install-Dependency 'test-package' }
    Write-Host 'PASS: 32 selections, database preservation, optional failures, winget arguments and exit codes.'
} finally {
    Remove-Item -Recurse -Force $temp
}

$global:LASTEXITCODE = 0
