param([string]$WebotsPath = 'C:\Program Files\Webots\msys64\mingw64\bin\webots.exe')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskWorld = Join-Path $taskRoot 'worlds\cartesian_robot.wbt'
if (!(Test-Path -LiteralPath $WebotsPath)) { throw "Webots no encontrado: $WebotsPath" }
# Launcher independiente. La interfaz se puede mostrar desde la barra de tareas.
$taskListener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
$taskListener.Start()
$taskPort = $taskListener.LocalEndpoint.Port
$taskListener.Stop()
Start-Process -FilePath $WebotsPath -ArgumentList @('--mode=realtime', "--port=$taskPort", ('"' + $taskWorld + '"')) -WorkingDirectory $taskRoot -WindowStyle Hidden
