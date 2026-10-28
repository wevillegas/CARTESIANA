param(
    [string]$WebotsPath = 'C:\Program Files\Webots\msys64\mingw64\bin\webots-bin.exe',
    [string]$PythonPath = 'C:\Python314\python.exe',
    [string]$WorldPath = ''
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskWorld = Join-Path $taskRoot 'worlds\cartesian_robot.wbt'
$taskReport = Join-Path $taskRoot 'docs\validation_report.json'
$taskStdout = Join-Path $taskRoot 'docs\validation_webots_stdout.log'
$taskStderr = Join-Path $taskRoot 'docs\validation_webots_stderr.log'
if (!(Test-Path -LiteralPath $WebotsPath)) { throw "Webots no encontrado: $WebotsPath" }
if (!(Test-Path -LiteralPath $PythonPath)) { throw "Python no encontrado: $PythonPath" }
& $PythonPath (Join-Path $PSScriptRoot 'build_model.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la generación de la geometría' }
if ($WorldPath) { $taskWorld = (Resolve-Path -LiteralPath $WorldPath).Path }
$taskOldValidate = $env:CARTESIAN_VALIDATE
$taskOldPath = $env:PATH
$taskOldHome = $env:WEBOTS_HOME
$taskOldScaling = $env:QT_ENABLE_HIGHDPI_SCALING
$taskOldPluginPath = $env:QT_QPA_PLATFORM_PLUGIN_PATH
$taskOldLaunchTime = $env:WEBOTS_VALIDATION_LAUNCH_UNIX_MS
try {
    $env:CARTESIAN_VALIDATE = '1'
    $taskBinDirectory = Split-Path -Parent $WebotsPath
    $taskWebotsHome = (Resolve-Path -LiteralPath (Join-Path $taskBinDirectory '..\..\..')).Path
    $env:WEBOTS_HOME = $taskWebotsHome
    $env:PATH = "$taskBinDirectory;$taskBinDirectory\cpp;$taskWebotsHome\msys64\usr\bin;$taskOldPath"
    $env:QT_ENABLE_HIGHDPI_SCALING = '1'
    $env:QT_QPA_PLATFORM_PLUGIN_PATH = $null
    # Binario directo: el launcher Windows pierde los handles de stdout/stderr.
    # CreateNoWindow/Hidden mantienen oculta esta instancia de prueba.
    $taskStartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $taskStartInfo.FileName = $WebotsPath
    # Un puerto libre evita interferencia con la instancia ya abierta por el usuario.
    $taskListener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
    $taskListener.Start()
    $taskPort = $taskListener.LocalEndpoint.Port
    $taskListener.Stop()
    $taskStartInfo.Arguments = '--batch --mode=fast --stdout --stderr --port=' + $taskPort + ' "' + $taskWorld + '"'
    $taskStartInfo.WorkingDirectory = $taskRoot
    $taskStartInfo.UseShellExecute = $false
    $taskStartInfo.CreateNoWindow = $true
    $taskStartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $taskStartInfo.RedirectStandardOutput = $true
    $taskStartInfo.RedirectStandardError = $true
    $taskProcess = New-Object System.Diagnostics.Process
    $taskProcess.StartInfo = $taskStartInfo
    $taskStartedAt = Get-Date
    $env:WEBOTS_VALIDATION_LAUNCH_UNIX_MS = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds().ToString()
    if (!$taskProcess.Start()) { throw 'No se pudo iniciar Webots' }
    $taskOutputReader = $taskProcess.StandardOutput.ReadToEndAsync()
    $taskErrorReader = $taskProcess.StandardError.ReadToEndAsync()
    Write-Host "Validación Webots iniciada PID=$($taskProcess.Id)"
    $taskDeadline = (Get-Date).AddMinutes(8)
    while (!$taskProcess.WaitForExit(1000) -and (Get-Date) -lt $taskDeadline) {
    }
    if (!$taskProcess.HasExited) { throw "La instancia de validación no terminó en 8 min; PID=$($taskProcess.Id). Revisar logs antes de intervenir." }
    $taskProcess.WaitForExit()
    [System.IO.File]::WriteAllText($taskStdout, $taskOutputReader.Result)
    [System.IO.File]::WriteAllText($taskStderr, $taskErrorReader.Result)
    if ($taskProcess.ExitCode -ne 0) { throw "Webots terminó con código $($taskProcess.ExitCode). Ver $taskStderr" }
    if (!(Test-Path -LiteralPath $taskReport)) { throw 'No se generó informe de validación' }
    if ((Get-Item -LiteralPath $taskReport).LastWriteTime -lt $taskStartedAt) { throw 'El informe no corresponde a esta ejecución' }
    $taskResult = Get-Content -LiteralPath $taskReport -Raw -Encoding UTF8 | ConvertFrom-Json
    if (!$taskResult.passed) { throw 'El informe contiene pruebas fallidas' }
    if ($taskErrorReader.Result -match '(?m)^ERROR:|Traceback \(most recent call last\)') { throw 'Hay errores críticos en stderr' }
    Write-Host "Informe generado: $taskReport"
    Write-Host "APROBADO; logs: $taskStdout / $taskStderr"
} finally {
    $env:CARTESIAN_VALIDATE = $taskOldValidate
    $env:PATH = $taskOldPath
    $env:WEBOTS_HOME = $taskOldHome
    $env:QT_ENABLE_HIGHDPI_SCALING = $taskOldScaling
    $env:QT_QPA_PLATFORM_PLUGIN_PATH = $taskOldPluginPath
    $env:WEBOTS_VALIDATION_LAUNCH_UNIX_MS = $taskOldLaunchTime
}
