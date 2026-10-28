# Integración visual del piloto escaneado

Esta etapa integra una superficie parcial del módulo X en el proyecto funcional de Webots R2025a. Aplica la alternativa controlada del punto 36 del pedido: comprobar el recorrido 3DM → Blender → OBJ/textura → Webots sin forzar la separación de cuerpos que la captura fusiona. `docs/scan_analysis.md` explica por qué la mayor parte del robot conserva primitivas.

## Checkpoint y originales

No había repositorio Git inicializado; no se creó un commit ni se descartó trabajo existente. Antes de modificar el modelo se guardaron 33 archivos de la etapa 1 en `backups/stage1_validated`, con hashes en `checkpoint_manifest.json`. Incluye PROTO, world, parámetros, controlador, documentación y evidencia de las 23 pruebas anteriores.

`referencias/untitled 2.3dm` y `referencias/untitled.3dm` se abren sólo en lectura. Sus Mesh tienen geometría y UV idénticas; se deriva una única fuente desde `untitled 2.3dm`. Las once fotografías y ambos 3DM se verifican contra el manifiesto original; todos los archivos de trabajo se guardan fuera de `referencias/`.

## Herramientas y dependencias

| Herramienta | Versión y ubicación | Uso |
| --- | --- | --- |
| Webots | R2025a, `C:\Program Files\Webots` | Simulación y validación |
| Blender | 5.2.2 LTS, `E:\SteamLibrary\steamapps\common\Blender\blender.exe` | Python API en background |
| rhino3dm | 8.35.0, `.tools/scan_reader` | Lectura 3DM y extracción no destructiva |
| Python bundled | 3.12, `C:\Users\Baltasar\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` | Lector con NumPy/Pillow |
| Python del controlador | 3.14.4, `C:\Python314\python.exe` | Controlador y herramientas Webots |

rhino3dm se instaló con `pip --target` sólo en la carpeta local `.tools/scan_reader`; `inspect_scans.py` incorpora esa ruta a sus módulos. No se instaló Rhino ni un importador global de Blender y no se cambiaron instalaciones globales. Webots no necesita Blender/rhino3dm para ejecutar el world ya exportado.

## Pipeline reproducible

1. `tools/inspect_scans.py` inspecciona ambos 3DM, comprueba unidades/topología y extrae `blender/derived/scan_raw.obj`, `scan_raw.mtl`, `scan_raw.npz` y `scan_atlas.png`. También genera `textures/scan_atlas.jpg` mediante RGB/JPEG calidad 92 optimizado.
2. `tools/prepare_blender_scene.py --mode inspect` importa el OBJ derivado, genera vistas crudas y guarda `blender/scan_inspection.blend`.
3. El mismo script con `--mode final` lee `config/scan_integration.json`, registra la región, conserva UV, selecciona, limpia islas, reduce triángulos y exporta la pieza local. Guarda el `.blend` final, vistas e informe `docs/mesh_processing.json`.
4. `tools/build_model.py` incorpora la Mesh visual a su Solid.
5. `tools/check_kinematic_invariants.py` compara campos protegidos, jerarquía y archivos centrales con el checkpoint.
6. `tools/validate_scan_visuals.ps1` comprueba extremos/centro de cada eje y genera capturas adicionales; después `tools/validate_webots.ps1` deja el informe principal con sus 23 pruebas. `tools/finalize_stage2_report.py` compara ese informe con el checkpoint y actualiza integridad/manifiesto.

Comandos para repetir el procedimiento con las instalaciones detectadas:

```powershell
Set-Location 'E:\ROBOTICA\CARTESIANO'
$taskBundledPython = 'C:\Users\Baltasar\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskBlender = 'E:\SteamLibrary\steamapps\common\Blender\blender.exe'
& $taskBundledPython .\tools\inspect_scans.py
& $taskBlender --background --factory-startup --python .\tools\prepare_blender_scene.py -- --mode inspect
& $taskBlender --background --factory-startup --python .\tools\prepare_blender_scene.py -- --mode final
& 'C:\Python314\python.exe' .\tools\build_model.py
& 'C:\Python314\python.exe' .\tools\check_kinematic_invariants.py
& .\tools\validate_scan_visuals.ps1
& .\tools\validate_webots.ps1
& 'C:\Python314\python.exe' .\tools\finalize_stage2_report.py
```

Blender se ejecuta con `--factory-startup` en una instancia de background; no modifica la escena abierta del usuario. La lectura regenera el informe base `docs/scan_analysis_base.md` y el JSON, conservando el análisis completado `docs/scan_analysis.md`. Selección y transformaciones se cambian en `config/scan_integration.json`, no arrastrando la Mesh en Webots.

## Selección y limpieza

El scan incluye mesa, gabinete, soportes, módulos, servos, herramienta y cables unidos en una reconstrucción. No se integra completo. Se seleccionan sólo triángulos cuyos **tres vértices** estén dentro de esta región, después del registro del piloto:

```text
Mínimo mundial inicial: [-0.4075, -0.0575, 1.1510] m
Máximo mundial inicial: [+0.4075, +0.0575, 1.2115] m
```

La envolvente es cercana al módulo X paramétrico de 0.815 × 0.110 × 0.055 m y su guía superficial. Todo lo exterior queda fuera de la exportación, incluidos gabinete, mesa, módulos Y/Z, carros y cables externos. Es un recorte de superficie controlado, no una segmentación de un link completo por color.

En la primera vista procesada se detectó un pequeño triángulo flotante. Se activó un umbral de cuatro caras por componente. La conectividad se calcula con posiciones coincidentes a **1 micrómetro**, pero es virtual: se conservan los índices y UV originales. Se retiran **13 caras de seis islas de hasta tres caras** y permanecen cuatro componentes de 135, 115, 88 y 8 caras.

No se aplica welding destructivo a costuras UV ni se cierran huecos con superficies inventadas. La superficie sigue siendo parcial y tiene bordes irregulares. Un pequeño núcleo visual paramétrico interior completa la apariencia en Webots; no es una segunda envolvente completa del módulo.

## Origen, escala y orientación

Los 3DM declaran metros. Blender conserva Z arriba y exporta OBJ con `forward_axis="Y"`, `up_axis="Z"`, escala global 1. Se mantiene +X derecha, +Y fondo y +Z arriba del mundo ENU. No se añade una conversión oculta de 90° durante la exportación.

| Parámetro | Valor |
| --- | --- |
| Escala uniforme de registro | 1.0 |
| Rotación sobre Z | +2.58°, `0.0450294947 rad` |
| Traslación de registro | `[0.16, -0.34982, 0.0365]` m |
| Origen mundial inicial del Solid | `[0, 0, 1.1785]` m |
| Rotación del objeto exportado | `[0, 0, 0]` rad |
| Escala del objeto exportado | `[1, 1, 1]` |
| Offset local de Mesh en Webots | `[0, 0, 0]` m |

Para cada vértice original:

```text
p_región = Rz(0.0450294947) · p_scan + [0.16, -0.34982, 0.0365]
p_OBJ    = p_región - [0, 0, 1.1785]
```

En el `.blend`, la pieza se muestra en el montaje mundial. En el OBJ, los vértices son locales al `X_MODULE`: el script pone temporalmente la ubicación del objeto en cero para exportar y luego la restaura. La rotación y escala de registro quedan aplicadas en los vértices; Webots no necesita escala 0.001 ni offsets grandes.

La transformación vale únicamente para la región piloto. No es un registro global de la mesa/máquina ni describe la posición de los joints en la captura. El cero del controlador y el TCP siguen siendo los de la etapa 1.

## Optimización y formato

El OBJ crudo contiene 25 000 triángulos, pero no se carga completo en Webots. La pieza se reduce con **Decimate / Collapse**, aplicado antes de exportar:

| Estado de la pieza | Vértices | Caras/triángulos |
| --- | ---: | ---: |
| Región seleccionada antes de limpieza | 322 | 359 |
| Tras retirar islas pequeñas | 298 | 346 |
| Tras Decimate | 274 | 300 |

Decimate reduce **13.2948 %** de los triángulos de la pieza limpia. La reducción total respecto a la selección inicial es **16.4345 %**, incluyendo las 13 caras retiradas. El objetivo de 300 es moderado para esta superficie pequeña. Se conservan las UV; Blender calcula y exporta las normales de la superficie procesada. Las normales originales del 3DM no se trasladan a la nueva topología.

El OBJ final se exporta triangulado y sin MTL; Webots define explícitamente `PBRAppearance` y el atlas. El OBJ/MTL/PNG crudos siguen disponibles para inspección en Blender.

```text
Bbox local mínimo: [-0.404343, -0.056780, -0.027299] m
Bbox local máximo: [+0.406437, +0.055634, +0.032359] m
Dimensiones:       [0.810780, 0.112414, 0.059659] m
Z mundial inicial: 1.1512008 .. 1.2108593 m
```

Esas dimensiones reflejan el **recorte elegido**, no una medición independiente de la sección completa del módulo real. Tamaños finales: OBJ **32 157 bytes**, atlas JPEG RGB 2048 × 2048 **854 785 bytes**, `.blend` de limpieza **1 860 494 bytes**. Los dos recursos de runtime suman **886 942 bytes**. PNG crudo, OBJ/MTL de referencia y escenas de trabajo no se cargan en el world.

## Relación Mesh → Solid y física

| Mesh | Solid receptor | Movimiento |
| --- | --- | --- |
| `axis_x_surface_visual.obj` | `X_MODULE`, hijo de `Y_CARRIAGE` | Viaja con Y; no acompaña el desplazamiento relativo de carros X/Z |

El módulo X y su servo pertenecen al conjunto transportado por Y. El carro X se desliza respecto a ese módulo y transporta Z. Por eso la superficie se agrega a `X_MODULE`, no al carro X.

La Mesh está únicamente bajo `Shape`/`PBRAppearance`, con rutas relativas `../meshes/axis_x_surface_visual.obj` y `../textures/scan_atlas.jpg`. Se retiran sólo los visuales del cuerpo y la guía superior de X, manteniendo servo, tapa lateral y marcador. Se añade un núcleo interior nativo de **0.805 × 0.025 × 0.040 m**.

Los `boundingObject` siguen usando los `Box`/`Cylinder` de la etapa 1. Joints, ejes, límites, fuerzas, PID, masas, padres de Solid y dispositivos no se ajustan para hacer encajar el scan. `config/robot_parameters.json`, el controlador principal y `runtime.ini` conservan identidad byte por byte con el checkpoint. El PROTO cambia sus visuales, pero el guard compara los campos cinemáticos y físicos protegidos.

## Regiones descartadas

La mesa no se integra porque su dimensión larga aparece en Y del scan, distinta de X del modelo validado. El gabinete abierto está deformado y no coincide con su envolvente cerrada. Carros Y/X/Z y herramienta se mezclan con guías, montajes y cables. Módulos Y/Z y servos requieren mejores medidas y separación. La nube de puntos tiene otro registro XY y no se mezcla con la Mesh.

Todo el robot, salvo la superficie piloto, conserva primitivas. La topología cerrada del scan no demuestra separación física de guías y carros; la cinemática no se modifica para encajar esa geometría ambigua.

## Validación y evidencia

La comparación estática aprobó **14 comprobaciones**: campos protegidos, jerarquía, identidad de archivos centrales, colisiones primitivas, dispositivos, rutas de Mesh y casos adversarios. `docs/kinematic_invariants.json` contiene el resultado. El checker por sí solo no demuestra dónde están los vértices ni que la superficie esté bien segmentada.

La ejecución principal con la Mesh final limpia aprobó nuevamente las **23 pruebas existentes**, con código de salida 0 y 193.424 s simulados. La prueba auxiliar aprobó **34 comprobaciones**, también con código 0. Hereda la clase original sin modificar el controlador principal y ejecuta las pruebas existentes más la carga/transformación de Mesh, nueve posiciones negativa/cero/positiva de Y, X y Z y captura cercana.

El error máximo de seguimiento de la Mesh respecto al movimiento esperado fue **0.000000968 m**. La diferencia inicial de la pose local respecto a identidad fue aproximadamente `5.29e-23`; Webots expone el Transform sin escala explícita como un nodo `Pose` con escala implícita unitaria. La primera versión del test auxiliar intentó leer un campo `scale` inexistente; se corrigió el comprobador para admitir esa representación de runtime, sin cambiar cinemática ni assets. El fallo inicial está conservado en `docs/scan_visual_initial_failure.json`.

Se inspeccionaron las nueve capturas y el detalle cercano: la superficie es rugosa/parcial, el núcleo cubre sus huecos y ya no aparece el pequeño fragmento flotante. Ambas ejecuciones finales tienen stderr vacío, sin errores, warnings ni errores de OpenGL.

`docs/stage2_regression_comparison.json` aprobó la comparación: mismos nombres de las 23 pruebas, mismos valores de métricas continuas y diferencias **cero** contra el informe de la etapa 1. Controlador principal, parámetros y runtime son byte por byte idénticos; los 13 archivos originales de referencias mantienen sus nombres y hashes.

| Métrica de la ejecución principal final | Resultado | Diferencia con etapa 1 |
| --- | ---: | ---: |
| Excursión máxima de sensor respecto al límite de mando | 0.0000490499947 m | 0 |
| Deriva máxima de guía Y fija | 0 m | 0 |
| Diferencia máxima de componentes de matrices de orientación | 0.0000192614448 | 0 |
| Error cinemático máximo del TCP | 0.0002024971382 m | 0 |
| Separación mínima de la herramienta a la goma | 0.2097487208355 m | 0 |

La métrica de orientación es adimensional y compara componentes de matrices; no representa un ángulo. La excursión de sensor de 0.049 mm es el transitorio físico ya presente en la etapa 1, dentro de su tolerancia de 0.8 mm. Los objetivos enviados por `move_to` siguen recortándose a los mismos límites. No se detectó regresión cinemática o física en estas pruebas.

Evidencia de esta etapa:

- `docs/validation_report.json` y logs habituales: 23 pruebas físicas.
- `docs/scan_visual_validation.json`, logs de la prueba auxiliar y capturas `docs/scan_views/webots_*.jpg`: carga, textura, origen, arrastre y revisión de las nueve posiciones.
- `docs/scan_performance.json`: tiempo hasta el primer paso y duración total de la prueba; son medidas aproximadas de arranque/carga/configuración, no FPS.
- `docs/stage2_regression_comparison.json`: comparación contra el checkpoint.
- `docs/stage2_change_manifest.json`: registro de archivos/recursos de esta etapa.

La prueba auxiliar midió aproximadamente **2.6668 s** desde el lanzamiento del proceso hasta el primer paso de controlador y **52.9173 s** de duración total para **258.32 s** simulados, alrededor de **4.88 s simulados por segundo real**. Incluye generación, arranque, cargas, pruebas y capturas; no es un benchmark de FPS ni una medición aislada del tiempo de carga. Los logs auxiliares no contienen errores ni warnings y stderr está vacío.

Para abrir el resultado: `tools/open_webots.ps1` o `E:\ROBOTICA\CARTESIANO\worlds\cartesian_robot.wbt`. La escena `E:\ROBOTICA\CARTESIANO\blender\cartesian_scan_cleanup.blend` conserva colecciones `RAW_SCAN_REFERENCE` y `ALIGNED_SCAN_REFERENCE` ocultas, y la pieza en `WEBOTS_VISUAL_LINKS`.

## Alcance y continuidad

La superficie aporta textura de la máquina, pero conserva irregularidades y huecos; no es un módulo X CAD completo. La discrepancia de sección de la viga y la correspondencia X/Y de la mesa siguen pendientes. No se afirma que el registro sea válido para otros links ni que haya una mejora física.

Los recorridos continúan provisionales: X ±0.25 m, Y ±0.20 m, Z ±0.09 m. Para continuar conviene medir sección/guía real de X, puntos comunes de registro, dimensiones y offsets de carros/módulos/TCP, y capturar cada link en una posición conocida. Cada nueva incorporación deberá conservar colisiones simples y aprobar el guard, las pruebas existentes y la revisión visual en extremos/centro.
