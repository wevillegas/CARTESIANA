param(
    [string]$WebotsPath = 'C:\Program Files\Webots\msys64\mingw64\bin\webots-bin.exe',
    [string]$PythonPath = 'C:\Python314\python.exe',
    [string]$WorldPath = ''
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
if (!$WorldPath) { $WorldPath = Join-Path $taskRoot 'worlds\cartesian_cad_validation.wbt' }
$taskClock = [System.Diagnostics.Stopwatch]::StartNew()
$taskStartedAt = Get-Date
$taskPassed = $false
$taskResult = $null
$taskConfig = Get-Content -LiteralPath (Join-Path $taskRoot 'config\cad_integration.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskEnabledParts = @($taskConfig.parts | Where-Object { $_.enabled })
$taskExpectedCADChecks = 10 * $taskEnabledParts.Count + 1
try {
    & (Join-Path $PSScriptRoot 'validate_webots.ps1') -WebotsPath $WebotsPath -PythonPath $PythonPath -WorldPath $WorldPath
    if ($LASTEXITCODE -ne 0) { throw "La validación CAD terminó con código $LASTEXITCODE" }
    $taskResult = Get-Content -LiteralPath (Join-Path $taskRoot 'docs\validation_report.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $taskCADChecks = @($taskResult.checks | Where-Object { $_.name -like 'cad_*' })
    if ($taskCADChecks.Count -ne $taskExpectedCADChecks) {
        throw "Se esperaban $taskExpectedCADChecks checks CAD; se encontraron $($taskCADChecks.Count)"
    }
    if (@($taskResult.checks).Count -ne (23 + $taskExpectedCADChecks)) {
        throw 'No se conservaron las 23 comprobaciones originales además de los checks CAD'
    }
    $taskFinalStderr = Get-Content -LiteralPath (Join-Path $taskRoot 'docs\validation_webots_stderr.log') -Raw -Encoding UTF8
    if ($taskFinalStderr -match '(?m)^WARNING:|^ERROR:|Traceback \(most recent call last\)') {
        throw 'Hay warnings/errores en el log CAD; revisar antes de aceptar integración'
    }
    $taskPassed = [bool]$taskResult.passed
} finally {
    $taskClock.Stop()
    # Preservar también una ejecución fallida y nunca copiar un reporte anterior.
    foreach ($taskCopy in @(
        @('validation_report.json', 'cad_visual_validation.json'),
        @('validation_webots_stdout.log', 'cad_visual_webots_stdout.log'),
        @('validation_webots_stderr.log', 'cad_visual_webots_stderr.log'),
        @('validation.jpg', 'cad_views\webots_cad_final.jpg')
    )) {
        $taskSource = Join-Path $taskRoot ('docs\' + $taskCopy[0])
        if ((Test-Path -LiteralPath $taskSource) -and (Get-Item -LiteralPath $taskSource).LastWriteTime -ge $taskStartedAt) {
            $taskDestination = Join-Path $taskRoot ('docs\' + $taskCopy[1])
            [System.IO.Directory]::CreateDirectory((Split-Path -Parent $taskDestination)) | Out-Null
            Copy-Item -LiteralPath $taskSource -Destination $taskDestination
        }
    }
    $taskAssetPaths = @($taskEnabledParts | ForEach-Object { $_.meshes | ForEach-Object { $_.path } } | Sort-Object -Unique)
    $taskAssets = @($taskAssetPaths | ForEach-Object {
        $taskAssetFile = Get-Item -LiteralPath (Join-Path $taskRoot $_)
        [pscustomobject][ordered]@{ path = $_; bytes = $taskAssetFile.Length; sha256 = (Get-FileHash -LiteralPath $taskAssetFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
    $taskSimulatedSeconds = if ($taskResult) { [double]$taskResult.simulation_time_s } else { $null }
    $taskResources = @($taskResult.checks | Where-Object { $_.name -like 'cad_resource_*' })
    $taskApproximateLoad = if ($taskResources.Count) { $taskResources[0].details.approximate_process_launch_to_first_step_wall_s } else { $null }
    $taskPerformance = [ordered]@{
        schema_version = 1
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        passed = $taskPassed
        world = $WorldPath
        enabled_part_count = $taskEnabledParts.Count
        expected_cad_check_count = $taskExpectedCADChecks
        total_validation_wall_s = $taskClock.Elapsed.TotalSeconds
        simulation_time_s = $taskSimulatedSeconds
        simulated_seconds_per_wall_second = if ($null -ne $taskSimulatedSeconds) { $taskSimulatedSeconds / $taskClock.Elapsed.TotalSeconds } else { $null }
        timing_scope = 'Incluye generación, arranque, nueve poses, capturas, 23 pruebas de etapa 1 y cierre. No mide carga aislada ni FPS.'
        fps = $null
        isolated_world_load_time_s = $null
        approximate_process_launch_to_first_step_wall_s = $taskApproximateLoad
        process_launch_to_first_step_scope = 'Aproximación Unix: arranque, carga de world/recursos y configuración hasta primer step. No mide carga aislada ni FPS.'
        cad_mesh_bytes = ($taskAssets | Measure-Object -Property bytes -Sum).Sum
        files = $taskAssets
        cad_resource_checks = $taskResources
    }
    $taskPerformance | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath (Join-Path $taskRoot 'docs\cad_performance.json') -Encoding UTF8
}
Write-Host 'Validación CAD guardada en docs\cad_visual_validation.json y docs\cad_performance.json'
