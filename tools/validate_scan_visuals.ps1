param(
    [string]$WebotsPath = 'C:\Program Files\Webots\msys64\mingw64\bin\webots-bin.exe',
    [string]$PythonPath = 'C:\Python314\python.exe',
    [string]$WorldPath = ''
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
if (!$WorldPath) { $WorldPath = Join-Path $taskRoot 'worlds\cartesian_mesh_validation.wbt' }
$taskClock = [System.Diagnostics.Stopwatch]::StartNew()
$taskStartedAt = Get-Date
$taskPassed = $false
$taskResult = $null
try {
    & (Join-Path $PSScriptRoot 'validate_webots.ps1') -WebotsPath $WebotsPath -PythonPath $PythonPath -WorldPath $WorldPath
    if ($LASTEXITCODE -ne 0) { throw "La validación visual terminó con código $LASTEXITCODE" }
        $taskResult = Get-Content -LiteralPath (Join-Path $taskRoot 'docs\validation_report.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $taskVisualChecks = @($taskResult.checks | Where-Object { $_.name -like 'visual_*' })
    if ($taskVisualChecks.Count -ne 11) { throw "Se esperaban 11 checks visuales; se encontraron $($taskVisualChecks.Count)" }
    $taskPassed = [bool]$taskResult.passed
} finally {
    $taskClock.Stop()
    # Conservar también evidencia de una ejecución fallida; nunca copiar informe viejo.
    foreach ($taskCopy in @(
        @('validation_report.json', 'scan_visual_validation.json'),
        @('validation_webots_stdout.log', 'scan_visual_webots_stdout.log'),
        @('validation_webots_stderr.log', 'scan_visual_webots_stderr.log')
    )) {
        $taskSource = Join-Path $taskRoot ('docs\' + $taskCopy[0])
        if ((Test-Path -LiteralPath $taskSource) -and (Get-Item -LiteralPath $taskSource).LastWriteTime -ge $taskStartedAt) {
            Copy-Item -LiteralPath $taskSource -Destination (Join-Path $taskRoot ('docs\' + $taskCopy[1]))
        }
    }
    $taskAssets = @(Get-ChildItem -LiteralPath (Join-Path $taskRoot 'meshes') -File | Where-Object { $_.Extension -in '.obj', '.mtl' })
    $taskTextures = @(Get-ChildItem -LiteralPath (Join-Path $taskRoot 'textures') -File -ErrorAction SilentlyContinue)
    $taskSimulatedSeconds = if ($taskResult) { [double]$taskResult.simulation_time_s } else { $null }
    $taskResource = if ($taskResult) { $taskResult.checks | Where-Object { $_.name -eq 'visual_mesh_resource_and_local_bounds' } } else { $null }
    $taskPerformance = [ordered]@{
        schema_version = 1
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        passed = $taskPassed
        world = $WorldPath
        total_validation_wall_s = $taskClock.Elapsed.TotalSeconds
        simulation_time_s = $taskSimulatedSeconds
        simulated_seconds_per_wall_second = if ($null -ne $taskSimulatedSeconds) { $taskSimulatedSeconds / $taskClock.Elapsed.TotalSeconds } else { $null }
        timing_scope = 'Incluye generación, arranque, nueve poses, capturas, 23 pruebas de etapa 1 y cierre. No mide tiempo aislado de carga ni FPS.'
        fps = $null
        isolated_world_load_time_s = $null
        approximate_process_launch_to_first_step_wall_s = if ($taskResource) { $taskResource.details.approximate_process_launch_to_first_step_wall_s } else { $null }
        process_launch_to_first_step_scope = 'Aproximación por reloj Unix: arranque de proceso, carga de world/recursos y configuración del controlador hasta primer step. No mide carga aislada ni FPS.'
        mesh_and_material_bytes = ($taskAssets | Measure-Object -Property Length -Sum).Sum
        texture_bytes = ($taskTextures | Measure-Object -Property Length -Sum).Sum
        files = @(@($taskAssets) + @($taskTextures) | ForEach-Object { @{ path = $_.FullName; bytes = $_.Length } })
        mesh_resource_and_local_bounds = if ($taskResource) { $taskResource.details } else { $null }
    }
    $taskPerformance | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $taskRoot 'docs\scan_performance.json') -Encoding UTF8
}
Write-Host 'Validación complementaria guardada en docs\scan_visual_validation.json y docs\scan_performance.json'
