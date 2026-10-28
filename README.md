# CARTESIANA — Gemelo digital en Webots con conexión TCP/IP

Trabajo final de **Seminario de Informática I (2026)**: gemelo digital de CARTESIANA, una máquina cartesiana de tres ejes (X, Y, Z) con un grip en la punta, simulada en **Webots**.

Un **programa externo** se conecta por **TCP/IP** a la máquina simulada, que hace de la PC industrial que la máquina real tiene a bordo. Le envía comandos de texto para inicializarla, moverla a mano, grabar puntos de una trayectoria y reproducirla.

```text
programa externo (cliente TCP) ── 127.0.0.1:5000 ──► Webots: controlador cartesiana_tcp (servidor TCP)
```

## Inicio rápido

**Requisitos:** Webots R2025a (también funcionó en R2023b) y Python 3.10 o más nuevo, sin librerías extra.

1. En Webots: **File → Open World** → `worlds/cartesiana_tcp.wbt` → **Run**.
2. Ejecutar el programa externo: `python programa_externo/cartesiana_app.py` (en Windows, `programa_externo/iniciar_programa.bat`).
3. **Conectar** a `127.0.0.1:5000` → **Inicializar**. La máquina busca sus sensores de inicio de carrera en X, Y y Z.
4. Mover a mano y **Guardar punto actual**, o **Abrir archivo…** → `trayectorias/ciclo_A_B_A.json` → **Ejecutar trayectoria**.

> Si Webots no encuentra Python, editar la línea `COMMAND` de `controllers/cartesiana_tcp/runtime.ini` y de `controllers/cartesian_controller/runtime.ini` con la ruta del `python.exe` de tu PC.

Al cerrar Webots, elegir **no guardar** el mundo: el estado de la simulación no necesita guardarse.

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `worlds/` | `cartesiana_tcp.wbt` (gemelo digital con TCP) y `cartesian_robot.wbt` (modelo cinemático original) |
| `controllers/cartesiana_tcp/` | PC industrial simulada: servidor TCP, protocolo, homing, grip |
| `controllers/cartesian_controller/` | Control cinemático validado (base del anterior) |
| `programa_externo/` | Programa de trayectorias (Python + Tkinter) y trayectorias de ejemplo |
| `protos/`, `meshes/`, `textures/` | Modelo del robot generado por `tools/build_model.py` |
| `config/` | Medidas, límites, homing, zona de trabajo y puerto TCP |
| `docs/` | Documento de virtualización, protocolo, guía de estudio e informes de validación |

## Documentación

- [Protocolo de comunicación v2](docs/protocolo_cartesiana.md)
- [Documento de virtualización (PDF)](docs/CARTESIANA_virtualizacion.pdf)
- [Informe para el profesor (PDF)](docs/Informe_CARTESIANA_profesor.pdf)
- [Guía de estudio para la defensa (PDF)](docs/Guia_estudio_defensa_CARTESIANA.pdf)

Los STEP y manuales del fabricante (Beckhoff, Rexroth) y las fotos originales no se incluyen en el repositorio.

## Historia del modelo: robot cartesiano industrial XYZ en Webots

Réplica mecánica de un robot cartesiano industrial con módulos Bosch Rexroth y servos Beckhoff. La primera etapa comprobó proporciones, los tres movimientos prismáticos y su relación padre-hijo con geometría nativa de Webots. La segunda etapa incorpora una superficie escaneada de prueba en el módulo X. La etapa 2B añade CAD oficial de familia Beckhoff para el visual del servo Z, conservando el modelo mecánico validado y la representación híbrida de las piezas restantes.

Raíz del proyecto: la carpeta `CARTESIANO` que contiene este README (originalmente `E:\ROBOTICA\CARTESIANO`). Todas las rutas internas del proyecto son relativas, así que puede moverse a cualquier ubicación. En los comandos de abajo, reemplazar `<CARPETA_CARTESIANO>` por la ruta real de la carpeta.

### Abrir y ejecutar

Entorno comprobado: **Webots R2025a** y **Python 3.14.4**, con el intérprete `C:\Python314\python.exe`. El archivo `controllers/cartesian_controller/runtime.ini` selecciona Python para este controlador sin cambiar la instalación global. La configuración por controlador está descrita en la [guía oficial de programación de Webots R2025a](https://github.com/cyberbotics/webots/blob/R2025a/docs/guide/controller-programming.md).

El mundo que hay que abrir es:

```text
<CARPETA_CARTESIANO>\worlds\cartesian_robot.wbt
```

Desde PowerShell:

```powershell
Set-Location '<CARPETA_CARTESIANO>'
& .\tools\open_webots.ps1
```

También se puede abrir desde **File > Open World** en Webots o ejecutar directamente:

```powershell
& 'C:\Program Files\Webots\msys64\mingw64\bin\webots.exe' --mode=realtime --stdout --stderr '<CARPETA_CARTESIANO>\worlds\cartesian_robot.wbt'
```

El nodo `CartesianRobot` ya tiene `controller "cartesian_controller"`. Al ejecutar la simulación, Webots inicia el controlador Python automáticamente; no hay que lanzarlo como un programa independiente. Si el mundo está pausado, presionar **Run**. **Reset** reinicia la secuencia desde la posición central de montaje.

El script de apertura inicia la instancia con la ventana oculta; se puede mostrar desde el ícono de Webots en la barra de tareas. La apertura directa o **File > Open World** permite verla desde el inicio.

La demostración hace primero movimientos de un eje por vez para mostrar la jerarquía y luego recorre posiciones XYZ lentamente. El avance se decide con las lecturas de los sensores y una permanencia dentro de tolerancia. La consola informa posición y objetivo periódicamente, sin imprimir en cada paso.

Para repetir las pruebas automatizadas con Webots real:

```powershell
Set-Location '<CARPETA_CARTESIANO>'
& .\tools\validate_webots.ps1
```

Consultar `docs/validation_report.json` junto con `docs/validation_webots_stdout.log` y `docs/validation_webots_stderr.log`. `passed: true`, `exit_status: 0` y `failed_checks: []` indican una ejecución aprobada. También se exporta `docs/validation.jpg`. El informe corresponde a la ejecución que lo generó; después de cambiar dimensiones, límites o controlador hay que volver a validarlo.

La apertura usa `C:\Program Files\Webots\msys64\mingw64\bin\webots.exe`; la validación usa directamente `C:\Program Files\Webots\msys64\mingw64\bin\webots-bin.exe` para capturar correctamente stdout/stderr en Windows. Ambos scripts seleccionan un puerto libre y crean una instancia propia sin cerrar la instancia que el usuario ya tenga abierta.

### Referencias utilizadas

Se inspeccionaron las once fotografías `IMG_0274.HEIC` a `IMG_0284.HEIC` de `referencias/`. Las vistas generales orientaron el montaje Y → X → Z; los detalles permitieron ubicar servos, placas, portacables y herramienta. `IMG_0282.HEIC` muestra el gabinete delante de la mesa; `IMG_0283.HEIC` identifica el aspecto del servo Beckhoff.

Los originales permanecen en `referencias/`. `docs/reference_manifest.json` registra nombres, tamaños y hashes SHA-256. Las imágenes JPG y `docs/reference_previews/contact_sheet.jpg` son derivados para inspección; no reemplazan los originales. La lectura HEIC usa un entorno local en `.tools/image_reader`, únicamente para preparar estas vistas. La simulación no necesita esa dependencia.

La verificación final de los 13 archivos originales aprobó: `docs/reference_integrity.json` registra que sus nombres y hashes SHA-256 no cambiaron.

También existen `untitled.3dm` y `untitled 2.3dm`. Durante la etapa 1 no se incorporaron ni convirtieron y Blender no intervino. En la etapa 2 se leyeron sin modificar los originales y se prepararon derivados en Blender, descritos al final de este README.

Compromiso conservado como antecedente de la etapa 1: **Los escaneos 3D se integrarán en una segunda etapa después de validar completamente la cinemática.**

### Coordenadas y arquitectura

El mundo utiliza `WorldInfo.coordinateSystem "ENU"`. Todas las dimensiones y posiciones están en metros.

- **+X:** derecha, en dirección transversal de la mesa.
- **+Y:** fondo, en dirección longitudinal de la guía fija.
- **+Z:** arriba, vertical.

El origen de la base está en el piso, bajo el centro de la mesa. En la cámara inicial, X aparece hacia la derecha y Y hacia el fondo. La guía Y está situada en el lado izquierdo de la mesa, aproximadamente en `x = -0.32 m`.

```text
CartesianRobot / Robot: mesa, gabinete y soportes estáticos
├── FIXED_Y: guía Y y servo Y fijos
└── SliderJoint Y: axis 0 1 0
    └── Y_CARRIAGE: carro Y
        ├── X_MODULE: módulo X y servo X
        └── SliderJoint X: axis 1 0 0
            └── X_CARRIAGE: carro X
                ├── Z_MODULE: módulo Z y servo Z
                └── SliderJoint Z: axis 0 0 1
                    └── Z_CARRIAGE: carro Z
                        ├── TOOL: herramienta simplificada
                        └── TOOL_TIP: punto de referencia de la herramienta
```

Por esta anidación, **Y mueve todo X, Z y herramienta**; **X mueve Z y herramienta**; **Z mueve su carro y herramienta**. Las guías que no pertenecen al conjunto móvil conservan su posición.

| Eje | Articulación | Motor | Sensor |
| --- | --- | --- | --- |
| X | `SliderJoint`, `axis 1 0 0` | `motor_x` | `sensor_x` |
| Y | `SliderJoint`, `axis 0 1 0` | `motor_y` | `sensor_y` |
| Z | `SliderJoint`, `axis 0 0 1` | `motor_z` | `sensor_z` |

Hay exactamente tres `SliderJoint`, tres `LinearMotor` y tres `PositionSensor`. No se usan articulaciones rotacionales para los ejes XYZ. `SliderJoint` proporciona un grado de libertad de traslación y admite motor/sensor lineales, según la [referencia oficial de Webots R2025a](https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/sliderjoint.md).

### Medidas del robot físico

Estas son las medidas suministradas del equipo; las marcadas «aprox.» ya venían aproximadas. No representan recorridos útiles. El arreglo de tamaños que usa Webots siempre sigue el orden **X, Y, Z**.

| Elemento | Medidas usadas, en metros |
| --- | --- |
| Mesa | X 0.90 × Y 0.60; altura del bastidor 0.85 |
| Goma superior | Espesor 0.01; superficie final a Z 0.86 |
| Travesaños inferiores | Altura aprox. 0.205 desde el piso |
| Barras principales | Sección aprox. 0.045 |
| Barras laterales | Ancho aprox. 0.055 |
| Gabinete | Largo 0.60 × ancho aprox. 0.334 × alto 0.60; ancho con tapa aprox. 0.35; separación del piso aprox. 0.05 |
| Soportes | X 0.035 × Y 0.152 × Z 0.155 |
| Módulo X | X 0.815 × Y 0.110 × Z 0.055 |
| Servo X | X 0.200 × Y 0.060 × Z 0.060; extremo derecho |
| Módulo Y | X 0.042 × Y 0.710 × Z 0.093 |
| Servo Y | X 0.060 × Y 0.200 × Z 0.060; extremo longitudinal +Y |
| Módulo Z | X 0.040 × Y 0.095 × Z 0.355 |
| Servo Z | X 0.060 × Y 0.060 × Z 0.240; vertical sobre el módulo |

La orientación del gabinete convierte el largo dado en X y el ancho en Y. Las posiciones exactas de montaje no fueron relevadas: se eligieron a partir de las fotos, con coherencia geométrica. Las medidas de carros, herramienta, placas y portacables son aproximaciones del modelo; están separadas de las medidas suministradas en la configuración.

### Límites y dinámica provisionales

**Los recorridos útiles reales siguen siendo desconocidos.** Los límites siguientes son provisionales y conservadores; se refieren a desplazamientos desde la posición de montaje `q = 0`.

| Eje | Mínimo | Máximo | Recorrido simulado | Velocidad máxima | Margen geométrico mínimo del carro a la guía |
| --- | ---: | ---: | ---: | ---: | ---: |
| X | -0.25 m | +0.25 m | 0.50 m | 0.040 m/s | 0.0975 m |
| Y | -0.20 m | +0.20 m | 0.40 m | 0.040 m/s | 0.0750 m |
| Z | -0.09 m | +0.09 m | 0.18 m | 0.025 m/s | 0.0350 m |

Los márgenes se calculan con las dimensiones aproximadas de los carros y sus posiciones de montaje. Los topes mecánicos simulados quedan 0.005 m más allá de cada límite de mando. El generador exige un margen geométrico de 0.02 m incluso con esa extensión. En Z se incluye la diferencia de 0.0125 m entre el centro de la guía y el centro inicial del carro.

Las masas asignadas a los sólidos móviles son aproximadas: Y 12 kg, X 5 kg y Z 1.5 kg. Las fuerzas máximas configuradas son Y 500 N, X 250 N y Z 150 N. Son parámetros de simulación para estabilidad, **no especificaciones ni mediciones de los servos reales**. La aceleración de mando es 0.10 m/s².

La base es estática. Los tres carros tienen `Physics` y colisiones simples `Box`/`Cylinder`. Las colisiones internas del robot están desactivadas (`selfCollision FALSE`) para que las superficies visuales de guía y carro no interfieran con las restricciones de los joints. Esto limita la simulación de contactos internos; los límites y su comprobación geométrica evitan sacar los carros de las guías.

### Cambiar límites y regenerar

La fuente central es `config/robot_parameters.json`. Los nombres conceptuales `X_MIN`, `X_MAX`, `Y_MIN`, `Y_MAX`, `Z_MIN`, `Z_MAX` corresponden a:

```json
"limits": {
  "x": {"min": -0.25, "max": 0.25},
  "y": {"min": -0.20, "max": 0.20},
  "z": {"min": -0.09, "max": 0.09}
}
```

Editar `limits.x.min/max` para X, `limits.y.min/max` para Y y `limits.z.min/max` para Z. La posición inicial cero debe quedar dentro de los límites y los carros deben conservar margen respecto a las guías. Después:

```powershell
Set-Location '<CARPETA_CARTESIANO>'
& 'C:\Python314\python.exe' .\tools\build_model.py
& .\tools\validate_webots.ps1
```

El generador actualiza `protos/CartesianRobot.proto` y `worlds/cartesian_robot.wbt`, comprueba la geometría y rechaza límites incompatibles. El controlador lee la misma configuración. Recargar el mundo en Webots después de regenerar. No editar únicamente los límites del PROTO: se perderían en la siguiente generación.

### Control XYZ y punto de herramienta

`move_to(x, y, z)` recibe posiciones de los tres ejes en metros, como desplazamientos cartesianos desde el cero de montaje. Limita cada coordenada al intervalo correspondiente y aplica el objetivo al motor. Los valores negativos indican el sentido opuesto de desplazamiento; no son coordenadas negativas de altura sobre el piso.

La clase `CartesianController` hereda de `Supervisor`. `configure()` obtiene los dispositivos y comprueba que los límites del PROTO coincidan con el JSON. `move_to()` devuelve el objetivo efectivamente aplicado como diccionario `{"x": ..., "y": ..., "z": ...}`; si recibe NaN o infinito, rechaza toda la orden sin cambiar ningún objetivo.

`set_speed(x=None, y=None, z=None)` configura velocidades positivas en m/s y las acota a las máximas de los motores. `wait_until_reached(timeout=None)` avanza la simulación hasta que los tres sensores permanezcan dentro de tolerancia durante el tiempo de asentamiento; si no convergen, produce un `TimeoutError` visible. `move_to()` ordena el movimiento y `wait_until_reached()` espera su finalización.

El cero es una referencia elegida para esta primera simulación, **no un homing físico**. No se simulan sensores de fin de carrera ni una rutina de búsqueda de origen.

Con la base en su posición y orientación originales, la punta de la herramienta cumple:

```text
TCP = [0.00, -0.15, 1.16] + [x, y, z]  (metros)
```

Así, `move_to(0.10, -0.05, -0.04)` lleva la punta aproximadamente a `[0.10, -0.20, 1.12]` en coordenadas del mundo. Para un objetivo absoluto `(Xw, Yw, Zw)`, los desplazamientos son `(Xw, Yw + 0.15, Zw - 1.16)`, sujetos a los límites. Si se cambia la traslación o rotación del robot, hay que aplicar también esa transformación.

Los sensores se habilitan al `basicTimeStep` de 16 ms. La tolerancia configurada es 0.0008 m, con 0.20 s de asentamiento. La telemetría sale cada 1 s y existe un tiempo máximo para detectar un movimiento que no alcance el objetivo.

### Archivos

```text
CARTESIANO
├── README.md
├── config
│   └── robot_parameters.json
├── worlds
│   └── cartesian_robot.wbt
├── protos
│   └── CartesianRobot.proto
├── controllers
│   └── cartesian_controller
│       ├── cartesian_controller.py
│       └── runtime.ini
├── tools
│   ├── build_model.py
│   ├── open_webots.ps1
│   ├── validate_webots.ps1
│   └── preview_references.py
├── docs
│   ├── model_notes.md
│   ├── reference_manifest.json
│   ├── reference_integrity.json
│   ├── reference_previews
│   ├── validation_initial_failure.json
│   ├── validation_report.json
│   ├── validation.jpg
│   ├── validation_webots_stdout.log
│   └── validation_webots_stderr.log
├── meshes                       (mesh piloto de la segunda etapa)
└── referencias                  (originales)
```

### Validación y alcance de la etapa 1

La prueba de Y comprueba que se desplacen carro Y, módulo X, módulo Z y herramienta; la prueba de X comprueba que se desplacen carro X, módulo Z y herramienta manteniendo la guía Y; la prueba de Z comprueba que sólo se desplacen su carro y la herramienta. El controlador usa `Supervisor` para observar posiciones de los sólidos, además de los sensores de las articulaciones. Las consultas de nodos internos del PROTO y la exportación de imágenes están descritas en la [referencia oficial de Supervisor](https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/supervisor.md).

Los resultados numéricos y el estado de aprobación se guardan en `docs/validation_report.json`. Los logs permiten revisar errores de carga, PROTO, dispositivos, controlador y física. Las pruebas deben ejecutarse después de cualquier modificación relevante; la revisión de sintaxis por sí sola no valida el funcionamiento.

El modo de prueba se activa con `CARTESIAN_VALIDATE=1`, configurado temporalmente por `validate_webots.ps1`. Además de los tres ejes aislados y la demo, prueba las ocho esquinas del espacio provisional, el recorte de órdenes fuera de rango, el rechazo de entradas no finitas y la estabilidad durante 3 s. Mide límites, deriva, orientaciones, error del TCP y separación de la herramienta respecto a la goma en cada paso. El informe exporta muestras cada 0.5 s junto con transiciones y extremos. Webots termina con código 0 si aprueba y 1 si falla.

La ejecución física de la etapa 1 **aprobó las 23 comprobaciones**, con código de salida 0, tras 193.424 s de tiempo simulado. Se observaron directamente ocho nodos, incluidos `X_MODULE` y `Z_MODULE`. Se evaluaron 12 083 muestras a 16 ms y se exportaron 413 muestras de evidencia. El error máximo del TCP fue 0.203 mm; la excursión transitoria máxima respecto al límite de mando fue 0.049 mm, dentro de la tolerancia de 0.8 mm y sin alcanzar los topes. La guía Y tuvo deriva cero y la separación mínima de la herramienta a la goma fue 0.20975 m. El informe de esta etapa se conserva en `backups/stage1_validated/docs/validation_report.json`.

La ejecución final de la etapa 1 terminó sin errores ni advertencias en stdout/stderr; stderr estaba vacío. Se verificó visualmente la captura generada por Webots, con mesa, gabinete y robot completos en el encuadre.

El modelo no reproduce TwinCAT, EtherCAT, drives AX5203, encoders BiSS, PLC, potencia eléctrica ni neumática. Los portacables son segmentos decorativos rígidos. La herramienta es un volumen simplificado unido al carro Z y admite una futura sustitución por gripper, cilindro o cuarto actuador.

Para continuar conviene medir recorridos útiles y puntos de homing, dimensiones reales de los carros, posiciones de montaje y del TCP, masa y centro de gravedad de cada conjunto móvil, holguras, interferencias, velocidades/aceleraciones seguras y características de la herramienta. Con esos datos se reemplazarán parámetros provisionales y se ampliará la geometría escaneada manteniendo esta jerarquía cinemática y colisiones simples.

### Etapa 2 - Integración de escaneos 3D

Se implementa un **piloto visual controlado**, conforme a la alternativa del punto 36 del pedido. Los dos archivos 3DM contienen la misma geometría y UV: una Mesh de 16 217 vértices y 25 000 triángulos, más una nube de 2 775 puntos. No son capturas complementarias. Sus unidades declaradas son metros; se conserva escala uniforme 1. La reconstrucción fusiona guías, carros, servos y cables y presenta superficies deformadas, de modo que no permite separar todos los links con fiabilidad.

La pieza elegida es `meshes/axis_x_surface_visual.obj`: una **superficie parcial** del módulo X. De 359 triángulos seleccionados se retiran 13 de seis islas pequeñas; Decimate reduce los 346 restantes a **300 triángulos y 274 vértices**. La reducción es 13.29 % por Decimate y 16.43 % total incluyendo limpieza. El OBJ ocupa **32 157 bytes**, conserva UV y exporta normales calculadas por Blender. Usa `textures/scan_atlas.jpg`, de 2048 × 2048 píxeles y **854 785 bytes**. El PNG extraído permanece en `blender/derived/scan_atlas.png`. Conteos y bbox están en `docs/mesh_processing.json`.

| Mesh | Solid | Movimiento heredado | Origen local y escala |
| --- | --- | --- | --- |
| `axis_x_surface_visual.obj` | `X_MODULE`, hijo de `Y_CARRIAGE` | Viaja con Y; permanece en el módulo cuando se mueve el carro X o Z | Origen de `X_MODULE`; rotación local cero y escala 1 |

La región se registra con una rotación de +2.58° sobre Z y traslación `(0.16, -0.34982, 0.0365)` m. Después se expresa respecto al origen mundial inicial del módulo X `(0, 0, 1.1785)` m. Es una alineación de esa superficie, **no un registro global de la máquina ni un homing del scan**. No se aplicó deformación independiente por eje.

Se retiran únicamente los visuales originales del cuerpo y de la guía superficial de X. Un pequeño núcleo visual nativo de `0.805 × 0.025 × 0.040 m` completa huecos de la superficie parcial. Servo X, tapa lateral y marcador siguen siendo primitivas. Mesa, gabinete, Y, Z, carros y herramienta conservan sus visuales paramétricos; los `boundingObject`, `Physics`, joints, dispositivos, controlador y parámetros mantienen su estructura validada.

La mesa detectada en el scan tiene aproximadamente 0.61 m en su X y 0.90 m en su Y, mientras que el modelo validado usa 0.90 m en X y 0.60 m en Y. Girar toda la captura para forzar la mesa alteraría la correspondencia de los módulos. El gabinete está abierto y deformado. Por estas razones se conservan sus primitivas y no se presenta la superficie piloto como un módulo X completo.

Blender instalado: **5.2.2 LTS**, en `E:\SteamLibrary\steamapps\common\Blender\blender.exe`. La lectura 3DM usa **rhino3dm 8.35.0**, instalado sólo en `.tools/scan_reader` con Python 3.12 del runtime bundled. El controlador de Webots continúa usando Python 3.14.4. No se cambian instalaciones globales.

No había repositorio Git inicializado; se guardó un checkpoint de 33 archivos de la etapa 1 en `backups/stage1_validated`, con `checkpoint_manifest.json`. Los originales de `referencias/` mantienen su manifiesto de integridad.

Archivos principales de esta etapa:

```text
blender/cartesian_scan_cleanup.blend     escena reproducible de limpieza y exportación
blender/scan_inspection.blend            inspección del scan crudo
blender/derived/                         OBJ/MTL/PNG/NPZ derivados
config/scan_integration.json             selección, registro y relación con X_MODULE
meshes/axis_x_surface_visual.obj         superficie piloto para Webots
textures/scan_atlas.jpg                  textura derivada para Webots
tools/inspect_scans.py                   lectura y extracción no destructiva
tools/prepare_blender_scene.py           modos inspect/final de Blender
tools/check_kinematic_invariants.py      comparación con el checkpoint
docs/scan_analysis.md                    análisis físico y de calidad
docs/mesh_integration.md                 procedimiento y límites del piloto
docs/mesh_processing.json                conteos, bbox y transformaciones
docs/scan_views/                         vistas crudas, procesadas y de Webots
```

La comparación estática aprobó **14 comprobaciones**; la ejecución principal aprobó nuevamente las **23 pruebas existentes** y la prueba auxiliar de Webots aprobó **34**, incluyendo esas pruebas y nueve posiciones de extremos/centro. La Mesh acompaña a su padre con error máximo de 0.000000968 m. Las nueve capturas y el detalle cercano muestran la superficie parcial rugosa con núcleo interior, sin el fragmento flotante eliminado.

La comparación final contra el checkpoint aprobó: los nombres de las 23 pruebas y todas sus métricas continuas son idénticos, con diferencia **cero**. La ejecución principal duró 193.424 s simulados; error máximo del TCP **0.203 mm**, excursión máxima de sensor respecto al límite de mando **0.049 mm**, deriva de guía Y **0** y separación mínima de herramienta a la goma **0.20975 m**. Controlador, parámetros y runtime conservan identidad byte por byte. Los **13 originales** de referencias mantienen sus hashes. Ambas ejecuciones finales terminaron con stderr vacío, sin errores, warnings ni errores OpenGL.

La evidencia está en `docs/kinematic_invariants.json`, `docs/validation_report.json`, `docs/scan_visual_validation.json`, `docs/stage2_regression_comparison.json`, `docs/stage2_change_manifest.json` y `docs/scan_views/webots_*.jpg`; el detalle y comandos están en `docs/mesh_integration.md`. Se midieron aproximadamente **2.67 s** desde el arranque hasta el primer paso y **52.92 s** para la prueba auxiliar completa, con 258.32 s simulados. No se instrumentaron FPS ni carga aislada.

### Etapa 2B - CAD de fabricante

Se descargaron los STEP oficiales Beckhoff `AM3023-1xx0` y `AM3023-1xx1`, sus ZIP originales y el manual AM3000/AM3500. Se verificaron flange, centrador, eje, agujeros, conectores y longitudes sin/con freno sobre el CAD original. Se clasifican como **B: misma familia, geometría verificada**; no son el part number exacto fotografiado `AM3023-0C40-0000` / `AM3023-0C41-0000`. Los STEP tienen chavetero y los códigos fotografiados indican eje liso. [Repositorio oficial Beckhoff](https://download.beckhoff.com/download/technical_drawings/Drive_Technology/step/AM30xx).

Se integra solamente la carcasa visual del servo Z con freno, identificada en la foto `IMG_0275`, bajo `Z_MODULE`. Su flange está en `(0,0,0.1775)` m locales, eje hacia -Z, cuerpo hacia +Z y conectores hacia +Y. El visual viaja con X/Y y permanece en el módulo mientras se mueve el carro Z. La transformación cargada tiene identidad local y escala 1; joints, controlador, límites, física y boundingObjects se conservan. El piloto LiDAR de X y `cartesian_scan_cleanup.blend` permanecen intactos. Los servos X/Y no se replican hasta resolver su asignación y variante física.

La sección de carcasa es 58×58 mm, cercana a los 60×60 mm aproximados. El total axial CAD con eje es 153.4 mm sin freno y 187.5 mm con freno, respectivamente 23.30 % y 21.875 % menor que los 200/240 mm manuales. Son diferencias importantes pendientes de medir con extremos equivalentes; no se inventó un soporte ni se estiró el CAD para resolverlas. Los conectores elevan el envelope transversal completo a 58×97 mm.

STEP → OpenCascade 7.9.3.1 en entorno local → OBJ en metros → Blender 5.2.2 LTS → Mesh visual Webots R2025a. La escena separada es `blender/official_cad_components.blend`. La teselación 50 452/49 534 triángulos se reduce a 15 000/14 999. El servo Z usa tres OBJ por color, **14 999 triángulos y 1 141 125 bytes**. AX5203 oficial queda como candidato **C** en la biblioteca Blender, con 30 000 triángulos, sin integración en el robot/gabinete: revisión y envelope completo frente a ficha sin conectores pendientes de reconciliar. La conversión no instala una aplicación CAD grande ni abre STEP directamente en Blender.

Las comprobaciones estáticas contra `backups/stage2_validated` aprueban **14/14** y la prueba CAD real **34/34** (23 originales + 11 complementarias). La prueba del scan con el servo CAD también aprueba **34/34**, y el controlador original final **23/23**. Las cinco métricas cinemáticas tienen delta exactamente cero; 15 assets de referencia/scan permanecen intactos y no se detectaron regresiones. La duración de la prueba CAD fue 63.40 s de pared / 258.32 s simulados, incluyendo capturas y pruebas; no mide FPS. [Comparación final de regresión](cad/reports/regression_comparison.json).

```powershell
Set-Location '<CARPETA_CARTESIANO>'
& .\tools\validate_cad_visuals.ps1
& .\tools\validate_scan_visuals.ps1
& .\tools\validate_webots.ps1
```

El proyecto sigue sin Git; se conserva el backup etapa 1 y se añade `backups/stage2_validated`, de 90 archivos. Procedencia y SHA256 están en `cad/reports/cad_sources.json`; los CAD sólo se usan localmente en este proyecto académico. Rexroth se investigó mediante documentos oficiales y configuradores: R036037003 se asigna a X por contexto fotográfico, pero no se decodificó su configuración legacy. El candidato moderno CKK090 L750 produce otro MNR, clase C sin STEP local; exportación por email/SSO. No se reemplazó X. La sección de cuerpo 90 × 40 mm y H1 = 56 mm del conjunto dibujado requieren datums físicos claros frente a los 110 × 55 mm manuales; carro/placa reales sin confirmar. El máximo 750 mm actual no se presume límite legacy. [Reporte Rexroth](cad/reports/rexroth_research.json). El gabinete y sus componentes opcionales quedan subordinados al trabajo mecánico.

Documentación: [investigación CAD](docs/cad_research.md), [integración reproducible](docs/cad_integration.md), [comparación dimensional](cad/reports/cad_comparison.json) y [reporte de los 21 puntos](docs/cad_stage2b_final_report.md). Capturas: [servo Z](docs/cad_views/webots_servo_z_closeup.jpg) y [robot completo con CAD](docs/cad_views/webots_cad_final.jpg).

### Etapa 3 - Gemelo digital con conexión TCP/IP (trabajo final)

CARTESIANA tiene a bordo una **PC industrial que escucha por TCP/IP**. En la simulación, ese papel lo cumple el controlador `cartesiana_tcp`, que es un servidor TCP en `0.0.0.0:5000`. El **programa externo** (`programa_externo/cartesiana_app.py`) es el cliente: se conecta directamente por TCP, sin puertos serie, y envía comandos de texto (`HOME`, `MOVE`, `GRIP`, `POS?`, `STOP`...).

```text
programa externo (cliente) --TCP/IP 127.0.0.1:5000--> Webots: cartesiana_tcp (servidor)
```

**Inicialización (homing):** como la máquina real, que tiene encoders relativos, la simulación arranca en una posición desconocida y rechaza los movimientos (`ERR NOT_HOMED`). El comando `HOME` (botón "Inicializar" del programa) mueve X, luego Y y luego Z hasta sus sensores de inicio de carrera, que son los bloques amarillos. Cada sensor define el cero de su eje, y recién entonces la máquina queda en (0, 0, 0).

Para usarlo:

1. En Webots, abrir `worlds/cartesiana_tcp.wbt` y presionar **Run**.
2. Ejecutar `programa_externo/iniciar_programa.bat`. IP `127.0.0.1`, puerto `5000`, **Conectar**.
3. Presionar **Inicializar** y esperar a que el indicador diga "INICIALIZADA".
4. Mover a mano y usar **Guardar punto actual**, o abrir `trayectorias/ciclo_A_B_A.json`. Después, **Ejecutar trayectoria**.

Documentación: `docs/protocolo_cartesiana.md` (protocolo v2) y `docs/CARTESIANA_virtualizacion.pdf` (documento de la entrega). El mundo `cartesian_robot.wbt` y su controlador siguen funcionando igual: la validación original sigue aprobando 23 de 23 comprobaciones.

La versión anterior, que usaba puerto serie COM5 y bridge HW VSP, se descartó porque la máquina no tiene Arduino. Quedó guardada en `backups/obsoleto_arduino_com/`.
#   C A R T E S I A N A  
 