param(
  [string]$Port = "COM8",
  [ValidateSet("START", "STOP", "STATUS", "TWAI")]
  [string]$Command = "STATUS",
  [int]$Baud = 115200,
  [switch]$ConfirmSafety
)

$ErrorActionPreference = "Stop"

if ($Command -eq "START" -and -not $ConfirmSafety) {
  throw "START ist gesperrt. Firmware-Flag kAllowCanStart=false; erst Hardwarefreigabe, neuer Build und dann -ConfirmSafety."
}

$serial = New-Object System.IO.Ports.SerialPort $Port, $Baud, "None", 8, "One"
$serial.DtrEnable = $false
$serial.RtsEnable = $false
$serial.ReadTimeout = 300
$serial.WriteTimeout = 300
$serial.Open()
Start-Sleep -Milliseconds 500
$serial.DiscardInBuffer()
$serial.WriteLine($Command)
$deadline = (Get-Date).AddSeconds(3)
$output = New-Object System.Text.StringBuilder
while ((Get-Date) -lt $deadline) {
  $chunk = $serial.ReadExisting()
  if ($chunk) { [void]$output.Append($chunk) }
  Start-Sleep -Milliseconds 100
}
$serial.Close()
Write-Output $output.ToString()
