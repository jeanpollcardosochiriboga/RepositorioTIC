<#
  reapply-ics.ps1 — Re-aplica Internet Connection Sharing (ICS) en el gateway del laboratorio.

  Upstream (publico)  : Wi-Fi
  Compartido (privado): Ethernet  -> queda en 192.168.137.1 -> WAN del router OpenWrt (192.168.1.1)

  Pensado para ejecutarse al arranque como SYSTEM (tarea programada ReapplyICS).
  Es idempotente: limpia cualquier "compartir" previo y vuelve a enlazar Wi-Fi -> Ethernet.
#>

$ErrorActionPreference = 'Stop'

$PublicAlias  = 'Wi-Fi'      # conexion con internet (upstream)
$PrivateAlias = 'Ethernet'   # adaptador hacia la WAN del router
$PrivateIP    = '192.168.137.1'
$PrivatePfx   = 24
$LogPath      = 'C:\gateway\ics.log'

function Write-Log {
    param([string]$Msg)
    $line = ('{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Msg)
    Add-Content -Path $LogPath -Value $line
}

function Test-AdapterUp {
    param([string]$Alias)
    # 'Up' es suficiente: ICS comparte el adaptador publico aunque la clasificacion de
    # conectividad aun no diga 'Internet'. (No usar IPv4Connectivity: es poco fiable al arranque.)
    try { return ((Get-NetAdapter -Name $Alias -ErrorAction Stop).Status -eq 'Up') }
    catch { return $false }
}

Write-Log '=== reapply-ics: inicio ==='

# 1. Esperar (hasta ~90 s) a que la WiFi y el Ethernet esten 'Up'
$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    $wifi = Test-AdapterUp $PublicAlias
    $eth  = Test-AdapterUp $PrivateAlias
    if ($wifi -and $eth) { break }
    Write-Log ("esperando adaptadores... wifi={0} eth={1}" -f $wifi, $eth)
    Start-Sleep -Seconds 3
}
Write-Log ("estado tras espera: wifi={0} eth={1}" -f (Test-AdapterUp $PublicAlias), (Test-AdapterUp $PrivateAlias))

# 2. Re-aplicar ICS via COM HNetCfg.HNetShare
#    NOTA: los miembros son ParameterizedProperty; el metodo correcto es
#    INetSharingConfigurationForINetConnection (NO ...ForINetSharingConfiguration).
$comOk = $false
try {
    $share = New-Object -ComObject HNetCfg.HNetShare

    # Mapa nombre -> configuracion de sharing
    $cfgByName = @{}
    foreach ($conn in $share.EnumEveryConnection) {
        $props = $share.NetConnectionProps.Invoke($conn)
        $cfgByName[$props.Name] = $share.INetSharingConfigurationForINetConnection.Invoke($conn)
    }
    Write-Log ('conexiones detectadas: ' + (($cfgByName.Keys) -join ', '))

    if (-not $cfgByName.ContainsKey($PublicAlias))  { throw "No existe la conexion publica '$PublicAlias'" }
    if (-not $cfgByName.ContainsKey($PrivateAlias)) { throw "No existe la conexion privada '$PrivateAlias'" }

    # Desactivar cualquier sharing previo (limpia binding viejo o adaptador equivocado)
    foreach ($name in $cfgByName.Keys) {
        if ($cfgByName[$name].SharingEnabled) {
            $cfgByName[$name].DisableSharing()
            Write-Log ("DisableSharing -> {0}" -f $name)
        }
    }

    # Habilitar: 0 = ICSSHARINGTYPE_PUBLIC (upstream), 1 = ICSSHARINGTYPE_PRIVATE (LAN compartida)
    $cfgByName[$PublicAlias].EnableSharing(0)
    $cfgByName[$PrivateAlias].EnableSharing(1)
    Write-Log ("EnableSharing publico={0} privado={1}" -f $PublicAlias, $PrivateAlias)

    # Verificar
    $pubOn  = $cfgByName[$PublicAlias].SharingEnabled
    $privOn = $cfgByName[$PrivateAlias].SharingEnabled
    Write-Log ("verificacion SharingEnabled publico={0} privado={1}" -f $pubOn, $privOn)
    $comOk = ($pubOn -and $privOn)
}
catch {
    Write-Log ("ERROR aplicando ICS via COM: " + $_.Exception.Message)
}

# Fallback: si el COM no dejo el sharing activo, reiniciar el servicio para que
# re-lea la config persistida (EnableRebootPersistConnection=1) y reconstruya el NAT.
if (-not $comOk) {
    try {
        Write-Log 'fallback: Restart-Service SharedAccess'
        Restart-Service SharedAccess -Force -ErrorAction Stop
    } catch { Write-Log ("ERROR en fallback Restart-Service: " + $_.Exception.Message) }
}

# 3. Verificar / forzar IP del adaptador privado (ICS normalmente la fija en 192.168.137.1)
Start-Sleep -Seconds 2
try {
    $has = Get-NetIPAddress -InterfaceAlias $PrivateAlias -AddressFamily IPv4 -ErrorAction SilentlyContinue |
           Where-Object { $_.IPAddress -eq $PrivateIP }
    if (-not $has) {
        Write-Log ("Ethernet sin {0}; forzando IP estatica" -f $PrivateIP)
        New-NetIPAddress -InterfaceAlias $PrivateAlias -IPAddress $PrivateIP -PrefixLength $PrivatePfx -ErrorAction Stop | Out-Null
    }
    $ip = (Get-NetIPAddress -InterfaceAlias $PrivateAlias -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress -join ','
    Write-Log ("IP final en {0}: {1}" -f $PrivateAlias, $ip)
}
catch {
    Write-Log ("ERROR verificando IP de {0}: {1}" -f $PrivateAlias, $_.Exception.Message)
}

Write-Log '=== reapply-ics: fin ==='
