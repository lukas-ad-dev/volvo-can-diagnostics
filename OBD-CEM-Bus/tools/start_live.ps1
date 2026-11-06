$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8765"
$deadline = (Get-Date).AddSeconds(20)
$status = $null

while ((Get-Date) -lt $deadline) {
  try {
    $health = Invoke-RestMethod -Uri "$base/api/health" -TimeoutSec 1
    if ($health.ok) {
      $status = Invoke-RestMethod -Uri "$base/api/status" -TimeoutSec 2
      if ($status.connected -and $status.firmware_can) { break }
    }
  } catch {}
  Start-Sleep -Milliseconds 500
}

if (-not $status -or -not $status.connected) {
  Write-Host "ESP/COM nicht verbunden. Der Browser wird trotzdem geoeffnet."
  Start-Process $base
  exit 1
}

$fw = $status.firmware_can
if ($null -eq $fw -or -not $fw.twai_installed) {
  try {
    Invoke-RestMethod -Uri "$base/api/can/start" -Method Post -ContentType "application/json" -Body "{}" -TimeoutSec 5 | Out-Null
  } catch {
    Write-Host "CAN START fehlgeschlagen: $($_.Exception.Message)"
  }
}

Start-Sleep -Seconds 2
$status = Invoke-RestMethod -Uri "$base/api/status" -TimeoutSec 3
if ($status.firmware_can) {
  Write-Host ("CAN={0} TWAI={1} Bitrate={2} Frames={3} Busfehler={4}" -f $status.firmware_can.can_state, $status.firmware_can.twai_state_name, $status.firmware_can.bitrate_kbps, $status.counters.frames_received, $status.firmware_can.bus_errors)
} else {
  Write-Host "Firmwarestatus noch nicht verfuegbar; Browser wird geoeffnet."
}
Start-Process $base
