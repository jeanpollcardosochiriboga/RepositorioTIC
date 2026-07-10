<# Reset del adaptador Wi-Fi para recuperar el lease IPv4 (DHCP atascado). #>
$log = 'C:\gateway\docs\fix-wifi.log'
function L($m){ Add-Content -Path $log -Value ('{0}  {1}' -f (Get-Date -Format 'HH:mm:ss'), $m) }
Set-Content -Path $log -Value ("fix-wifi - {0}" -f (Get-Date))

try {
    L 'Disable-NetAdapter Wi-Fi'
    Disable-NetAdapter -Name 'Wi-Fi' -Confirm:$false -ErrorAction Stop
    Start-Sleep -Seconds 4
    L 'Enable-NetAdapter Wi-Fi'
    Enable-NetAdapter -Name 'Wi-Fi' -Confirm:$false -ErrorAction Stop

    # Esperar a que asocie (Status Up)
    $dl = (Get-Date).AddSeconds(35)
    while ((Get-Date) -lt $dl -and (Get-NetAdapter -Name 'Wi-Fi').Status -ne 'Up') { Start-Sleep 2 }
    L ("estado Wi-Fi: {0}" -f (Get-NetAdapter -Name 'Wi-Fi').Status)

    # Pedir lease IPv4
    Start-Sleep -Seconds 3
    & ipconfig /renew "Wi-Fi" | Out-Null
    Start-Sleep -Seconds 4
}
catch { L ("ERROR: " + $_.Exception.Message) }

$ip = (Get-NetIPAddress -InterfaceAlias 'Wi-Fi' -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress -join ','
$gw = (Get-NetIPConfiguration -InterfaceAlias 'Wi-Fi' -ErrorAction SilentlyContinue).IPv4DefaultGateway.NextHop -join ','
L ("IPv4 Wi-Fi: {0}  gateway: {1}" -f $ip, $gw)
if ($ip -and $ip -notlike '169.254*') { L 'RESULTADO: OK, lease IPv4 obtenido' } else { L 'RESULTADO: sigue sin IPv4 (APIPA)' }
L 'FIN'
