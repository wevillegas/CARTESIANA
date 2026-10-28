# Integración visual CAD en Webots: etapa 2B

Se reemplaza únicamente el visual primitivo del servo Z por la carcasa oficial de familia **AM3023 con freno**, clase B. El visual se aloja en `Z_MODULE`; acompaña X e Y y permanece en el módulo fijo cuando se mueve su carro Z. El controlador principal, sus parámetros, joints, sensores, motores, física y boundingObjects se conservan. El piloto escaneado X sigue integrado.

El STEP corresponde a `AM3023-1xx1`, mientras la fotografía vertical identifica `AM3023-0C41-0000`. Coinciden familia, flange y variante con freno; el CAD tiene chavetero y el código fotografiado indica eje liso. Es una sustitución visual de carcasa de fabricante a escala real, con diferencias declaradas. La medida axial manual de 240 mm sigue sin reconciliarse con los 187.5 mm completos del CAD; no se añadió un soporte inventado ni una escala para explicarla.

## Originales, respaldos y escenas separadas

Se revalidó que el proyecto no tiene repositorio Git. Se conserva `backups/stage1_validated` y se crea el checkpoint `backups/stage2_validated`, de 90 archivos, previo al CAD. La comparación final verifica todos los archivos registrados de ambos checkpoints sin alteraciones. Los originales de referencia, `meshes/axis_x_surface_visual.obj` y `blender/cartesian_scan_cleanup.blend` se incluyen en el manifiesto de 15 assets protegidos `cad/reports/stage2b_protected_assets.json`.

Los ZIP, STEP y PDF Beckhoff permanecen en `cad/source/beckhoff/`; los PDF Rexroth, en `cad/source/rexroth/`, con distinción entre host oficial y copia de manual en distribuidor. Los hashes de fuente se comprueban al convertir y en el cierre. La escena nueva es **`blender/official_cad_components.blend`**, separada de la escena del scan. Se organiza en `BECKHOFF_AM3023`, `REXROTH_CKK`, `BECKHOFF_AX5203`, `OPTIONAL_PANEL_COMPONENTS` y `WEBOTS_EXPORTS`. Las Collections sin modelos son reservas explícitas.

## Pipeline STEP → mesh → Blender → Webots

1. Lectura STEP con OpenCascade y verificación de unidades, sólido, bbox y features de montaje.
2. Teselación controlada a OBJ en coordenadas nativas, conversión uniforme milímetros → metros mediante factor 0.001 y conservación de los colores STEP.
3. Importación OBJ en Blender con Y forward / Z up, conversión a origen de flange, orientación canónica y reducción Decimate hasta aproximadamente 15 000 triángulos.
4. Copia destinada a Z, aplicación de orientación y traslación en sus vértices y exportación triangulada por material.
5. Carga con `Shape`, `PBRAppearance` y `Mesh` en una transformación visual local de identidad. Las rutas son relativas `../meshes/cad/...`. La colisión sigue usando las primitivas del modelo validado.

La medición dimensional fiable se realiza sobre el BRep original. Decimate cambia levemente el bbox de la mesh visual: el conjunto de Z mide aproximadamente **58 × 97.024 × 187.551 mm**, frente a **58 × 97 × 187.5 mm** en el CAD. No se modificó el STEP para obtener la mesh.

## Origen y orientación del servo Z

El origen canónico está en el plano frontal de flange: cuerpo +X, eje -X y conectores +Z. El visual de Z aplica la matriz de `config/cad_integration.json`, que lleva cuerpo a **+Z**, eje a **-Z** y conectores a **+Y**, con flange local **(0, 0, 0.1775) m** respecto a `Z_MODULE`. Es una orientación rígida, determinante +1 y escala uniforme 1.

Las coordenadas se guardan ya en el marco local del Solid. El `CAD_SERVO_Z_VISUAL` cargado por Webots tiene pose local de identidad y escala implícita unitaria. El conjunto ocupa Z local aproximadamente **0.157500 a 0.345051 m**. La cara frontal se apoya en el extremo superior del módulo Z de 355 mm, en el montaje elegido para el modelo; su posición exacta en la máquina requiere relevamiento adicional.

Se elimina sólo el visual primitivo del servo Z (`remove_visual_indices: [2]`). El módulo, motor simulado y cuerpo de colisión no cambian. El flange, eje y conectores se verifican en la captura cercana y en las comprobaciones complementarias.

## Conteos y archivos

| Derivado | Triángulos | Tamaño |
| --- | ---: | ---: |
| `cad/converted/am3023_no_brake_native.obj` | 50 452 | 5 023 247 bytes |
| `cad/converted/am3023_brake_native.obj` | 49 534 | 4 961 793 bytes |
| Biblioteca Blender sin freno | 15 000 | Incluida en el `.blend` |
| Biblioteca Blender con freno | 14 999 | Incluida en el `.blend` |
| Biblioteca AX5203, clase C | 30 000 | Incluida en el `.blend`, sin integración Webots |
| `meshes/cad/servo_z_am3023_brake_material_0.obj` | 1 306 | 91 299 bytes |
| `meshes/cad/servo_z_am3023_brake_material_1.obj` | 6 664 | 547 156 bytes |
| `meshes/cad/servo_z_am3023_brake_material_2.obj` | 7 029 | 502 670 bytes |
| Total visual Z | **14 999** | **1 141 125 bytes** |

La reducción es 70.27 % sin freno y 69.72 % con freno. Se exportan normales, triángulos y tres colores originales; no se requiere atlas de textura para estos OBJ. Los colores se convierten en apariencias Webots compatibles. Los originales son un solo sólido CAD por variante; separar por material no añade cuerpos físicos ni grados de libertad.

## Reproducción local

Las rutas siguientes corresponden al entorno inspeccionado. La dependencia CAD se carga únicamente desde `.tools/cad_reader`; la simulación Webots no la necesita.

```powershell
Set-Location 'E:\ROBOTICA\CARTESIANO'
$cadPython = 'C:\Users\Baltasar\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $cadPython .\tools\inspect_cad_environment.py
& $cadPython .\tools\convert_official_cad.py .\cad\source\beckhoff\AM3023-1xx0.step --output .\cad\converted\am3023_no_brake_native.obj --report .\cad\reports\am3023_no_brake_conversion.json --linear-mm 0.2 --angular-degrees 12
& $cadPython .\tools\convert_official_cad.py .\cad\source\beckhoff\AM3023-1xx1.step --output .\cad\converted\am3023_brake_native.obj --report .\cad\reports\am3023_brake_conversion.json --linear-mm 0.2 --angular-degrees 12
& $cadPython .\tools\convert_official_cad.py .\cad\source\beckhoff\AX5203.stp --output .\cad\converted\ax5203_native.obj --report .\cad\reports\ax5203_conversion.json --linear-mm 0.3 --angular-degrees 15
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --background --factory-startup --python .\tools\prepare_official_cad_blender.py
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' --background --factory-startup --python .\tools\append_ax5203_library.py
& 'C:\Python314\python.exe' .\tools\build_model.py
& 'C:\Python314\python.exe' .\tools\check_kinematic_invariants.py --baseline .\backups\stage2_validated --report .\cad\reports\kinematic_invariants.json
& .\tools\validate_cad_visuals.ps1
& .\tools\validate_scan_visuals.ps1
& .\tools\validate_webots.ps1
```

El script Blender sólo permite modo background y usa una escena factory startup propia. No modifica una escena abierta por el usuario. `config/cad_processing.json` define los candidatos y su presupuesto de triángulos; `config/cad_integration.json` define la única integración activa. Una regeneración reproduce las geometrías derivadas y mundos; primero conservar cualquier edición manual intencional de esos derivados.

El comando opcional `append_ax5203_library.py` se ejecuta después del preparador AM3023, requiere el OBJ AX5203 previamente convertido y conserva los objetos/Collections previos. Añade el candidato C a la Collection de biblioteca con escala 1, orientación nativa y desplazamiento Y +0.5 m para separación visual. No cambia `config/cad_integration.json` ni exporta nuevas meshes integradas.

## Validación y evidencia

La comprobación estática contra el checkpoint etapa 2 aprueba **14/14** checks. Compara campos protegidos y jerarquía, conserva exactamente tres SliderJoint, tres LinearMotor y tres PositionSensor y exige que las colisiones no contengan Mesh. El controlador principal, runtime.ini y parámetros mantienen sus bytes. El cierre [regression_comparison.json](E:/ROBOTICA/CARTESIANO/cad/reports/regression_comparison.json) comprueba 15/15 assets protegidos intactos, fuentes AM3023 y meshes integradas sin cambios y cinco deltas cinemáticos exactamente cero.

La ejecución CAD real de Webots aprueba **34/34** checks: las 23 comprobaciones originales más 11 complementarias. Prueba negativo, centro y positivo de cada eje, recursos/URLs/hashes, escala y pose local de identidad y herencia de movimiento respecto a `Z_MODULE`. Produce `docs/cad_visual_validation.json`, logs y capturas en `docs/cad_views/`. La prueba complementaria del scan con el servo CAD aprueba también **34/34**. La ejecución final del controlador original aprueba **23/23**, tras **193.424 s simulados**, con sus cinco métricas continuas idénticas a las del checkpoint etapa 2. Los logs finales no presentan errores ni warnings relevantes.

El helper CAD inicialmente terminó las 34 pruebas pero falló después al sumar `bytes` de un `OrderedDictionary` en PowerShell 5.1. Se corrigió sólo ese helper usando registros `PSCustomObject`; la nueva ejecución completó el informe de rendimiento. También se amplió el encuadre del controlador complementario porque el primer close-up recortaba la vista vertical. Estos fallos de evidencia no exigieron cambios de cinemática. Registro: `cad/reports/validation_helper_notes.md`.

La ejecución corregida tarda aproximadamente **63.40 s de pared** y recorre **258.32 s simulados**, incluyendo arranque, nueve poses, capturas y pruebas originales. Es una duración completa de validación, no una medida aislada de carga ni FPS. El primer paso observado se produjo aproximadamente 2.94 s después del lanzamiento del proceso en esa ejecución. El rendimiento puede cambiar según el equipo y el viewport.

| Evidencia | Archivo |
| --- | --- |
| AM3023 sin freno en Blender | `docs/cad_views/am3023_no_brake_blender.jpg` |
| AM3023 con freno en Blender | `docs/cad_views/am3023_brake_blender.jpg` |
| AX5203 de biblioteca, clase C | `docs/cad_views/ax5203_blender.jpg` |
| Servo Z, cercano | `docs/cad_views/webots_servo_z_closeup.jpg` |
| Robot completo con CAD | `docs/cad_views/webots_cad_final.jpg` |
| Poses de ejes | `docs/cad_views/webots_{x,y,z}_{negative,center,positive}.jpg` |

## Componentes conservados y condiciones para extender

X conserva el scan parcial y su núcleo visual; los servos X/Y conservan primitivas porque su asignación y variantes no están totalmente resueltas. Y/Z lineales, mesa, gabinete, carros y herramienta conservan su representación anterior. Rexroth se integrará sólo si se comprueba sección, carro, fijaciones y configuración frente a la foto y las medidas. Una longitud configurable no autoriza estirar todo el conjunto.

La investigación Rexroth cerró sin STEP local A/B. El candidato configurado CKK090 L750 OF01 generó MNR R030537116, diferente de R036037003, y queda clase C sin descarga: el eConfigurator requiere email de entrega y PARTcommunity SSO. El catálogo/manuales permiten comparar dimensiones de familia, no una mesh CAD verificada. Por eso no se genera un mundo de comparación con un falso CAD Rexroth ni se sustituye el scan X. El MNR fotografiado se asigna a X por contexto; Z probable tiene otro MNR. [Investigación Rexroth](E:/ROBOTICA/CARTESIANO/cad/reports/rexroth_research.json).

AX5203 se descargó y convirtió de manera opcional, y queda clase C en `cad/converted/ax5203_native.obj` y en la biblioteca Blender: **30 000 triángulos**, sin integración ni exportación Webots. La ficha actual excluye conectores y no se homologaron sus extremos con el envelope STEP histórico. C6925/EK1100/EL1008/EL2008 quedan para una etapa de gabinete.

Para replicar AM3023 en X/Y, registrar qué etiqueta corresponde a cada eje, freno y dirección de salida. Para mejorar Z, medir flange a tapa trasera, eje libre, separador/acoplamiento real si existe y offset de montaje. Los límites y el TCP seguirán siendo los de la simulación validada hasta contar con medidas explícitas.
