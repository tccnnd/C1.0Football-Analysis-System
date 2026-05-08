param(
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    throw "Please run this script in an Administrator PowerShell window."
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$pythonwExe = Join-Path $projectRoot "venv\Scripts\pythonw.exe"

$ruleNames = @(
    "Allow_API_Football_Python_443",
    "Allow_API_Football_PythonW_443"
)

if ($Rollback) {
    foreach ($name in $ruleNames) {
        $rule = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
        if ($rule) {
            Remove-NetFirewallRule -DisplayName $name
            Write-Host "Removed rule: $name"
        }
    }
    return
}

function Upsert-AllowRule {
    param(
        [Parameter(Mandatory = $true)][string]$DisplayName,
        [Parameter(Mandatory = $true)][string]$ProgramPath
    )

    if (-not (Test-Path -LiteralPath $ProgramPath)) {
        Write-Host "Skip (program not found): $ProgramPath"
        return
    }

    $existing = Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue
    if ($existing) {
        Set-NetFirewallRule -DisplayName $DisplayName -Direction Outbound -Action Allow -Enabled True -Profile Any | Out-Null
        Set-NetFirewallApplicationFilter -AssociatedNetFirewallRule $existing -Program $ProgramPath | Out-Null
        Set-NetFirewallPortFilter -AssociatedNetFirewallRule $existing -Protocol TCP -RemotePort 443 | Out-Null
        Write-Host "Updated rule: $DisplayName"
    } else {
        New-NetFirewallRule `
            -DisplayName $DisplayName `
            -Direction Outbound `
            -Action Allow `
            -Enabled True `
            -Profile Any `
            -Program $ProgramPath `
            -Protocol TCP `
            -RemotePort 443 `
            -Description "Allow API-Football HTTPS outbound from V24 app Python runtime." | Out-Null
        Write-Host "Created rule: $DisplayName"
    }
}

Upsert-AllowRule -DisplayName "Allow_API_Football_Python_443" -ProgramPath $pythonExe
Upsert-AllowRule -DisplayName "Allow_API_Football_PythonW_443" -ProgramPath $pythonwExe

Write-Host ""
Write-Host "Connectivity test: v3.football.api-sports.io:443"
Test-NetConnection v3.football.api-sports.io -Port 443 | Select-Object ComputerName, RemoteAddress, RemotePort, TcpTestSucceeded | Format-Table -AutoSize

