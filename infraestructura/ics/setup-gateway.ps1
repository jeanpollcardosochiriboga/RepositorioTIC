<#
  setup-gateway.ps1 — Instalador (UNA sola vez, requiere ADMIN) del gateway del laboratorio.
  Pasos:
    1. Deshabilita adaptadores virtuales que confunden a ICS (VMware/VirtualBox). NO toca vEthernet (WSL).
    2. Pone el perfil WiFi actual en auto-conexion.
    3. Registra la tarea programada 'ReapplyICS' que corre C:\gateway\reapply-ics.ps1 al arranque como SYSTEM.
    4. Ejecuta reapply-ics.ps1 una vez para aplicar ICS ahora.
#>

$ErrorActionPreference = 'Continue'
$ScriptPath = 'C:\gateway\reapply-ics.ps1'
$SetupLog   = 'C:\gateway\setup.log'

function Log([string]$m) {
    $line = ('{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
    Write-Host $line
    Add-Content -Path $SetupLog -Value $line
}

# Confirmar elevacion
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Log 'ERROR: este script requiere privilegios de administrador.'; exit 1 }
Log '=== setup-gateway: inicio (admin OK) ==='

# 1. Deshabilitar adaptadores virtuales innecesarios (NO vEthernet WSL, NO Ethernet/Ethernet 3/Wi-Fi)
$toDisable = @(
    'VMware Network Adapter VMnet8',
    'VMware Network Adapter VMnet1',
    'Ethernet 2'   # VirtualBox Host-Only (MAC 0A:00:27:00:00:11)
)
foreach ($name in $toDisable) {
    $ad = Get-NetAdapter -Name $name -ErrorAction SilentlyContinue
    if ($null -eq $ad) { Log ("adaptador no encontrado (omito): {0}" -f $name); continue }
    if ($ad.Status -eq 'Disabled') { Log ("ya deshabilitado: {0}" -f $name); continue }
    try { Disable-NetAdapter -Name $name -Confirm:$false -ErrorAction Stop; Log ("deshabilitado: {0}" -f $name) }
    catch { Log ("ERROR deshabilitando {0}: {1}" -f $name, $_.Exception.Message) }
}

# 2. Perfil WiFi actual -> auto-conexion
try {
    $ifInfo = netsh wlan show interfaces
    $ssidLine = ($ifInfo | Select-String -Pattern '^\s*SSID\s*:\s*(.+)$' | Select-Object -First 1)
    if ($ssidLine) {
        $ssid = $ssidLine.Matches[0].Groups[1].Value.Trim()
        Log ("SSID WiFi conectado: {0}" -f $ssid)
        $r = netsh wlan set profileparameter name="$ssid" connectionmode=auto
        Log ("set connectionmode=auto -> {0}" -f ($r -join ' '))
    } else {
        Log 'No se pudo detectar SSID conectado; revisar perfil WiFi manualmente.'
    }
} catch { Log ("ERROR configurando WiFi auto: {0}" -f $_.Exception.Message) }

# 3. Registrar tarea programada ReapplyICS (al arranque, SYSTEM, privilegios maximos)
try {
    $taskName = 'ReapplyICS'
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Log 'tarea previa ReapplyICS eliminada (se re-crea)'
    }
    $action    = New-ScheduledTaskAction -Execute 'powershell.exe' `
                    -Argument ('-NonInteractive -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $ScriptPath)
    $trigger   = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
                    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
                    -Principal $principal -Settings $settings -Description 'Re-aplica ICS (WiFi->Ethernet) al arranque' | Out-Null
    Log 'tarea ReapplyICS registrada (AtStartup / SYSTEM)'
} catch { Log ("ERROR registrando tarea: {0}" -f $_.Exception.Message) }

# 4. Aplicar ICS ahora
try {
    Log 'ejecutando reapply-ics.ps1 ahora...'
    & powershell.exe -NonInteractive -NoProfile -ExecutionPolicy Bypass -File $ScriptPath
    Log 'reapply-ics.ps1 ejecutado (ver C:\gateway\ics.log)'
} catch { Log ("ERROR ejecutando reapply-ics.ps1: {0}" -f $_.Exception.Message) }

Log '=== setup-gateway: fin ==='
