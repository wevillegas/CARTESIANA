# Notas técnicas del modelo cartesiano

Estas notas describen la primera etapa en Webots R2025a. La geometría se genera con `tools/build_model.py` desde `config/robot_parameters.json`; el mundo usa metros, segundos, kilogramos, radianes para rotaciones y `coordinateSystem "ENU"`. Los parámetros numéricos que no proceden de las medidas suministradas están identificados como aproximados o provisionales.

## Referencia física y simplificación

Las fotografías `IMG_0274.HEIC` a `IMG_0284.HEIC` muestran un montaje con guía longitudinal Y en un lateral, un módulo transversal X transportado por Y y un módulo vertical Z transportado por X. La herramienta está en el carro vertical. El servo X se representa en el extremo derecho, el servo Y en el extremo +Y y el servo Z encima del módulo vertical. Esta orientación da un modelo coherente con las vistas generales; las posiciones exactas todavía deben medirse.

Se usan `Box`, `Cylinder`, `Transform`, `Shape` y `PBRAppearance`. La estructura tiene tonos gris claro, goma negra, módulos de aluminio y servos/portacables negros. Se añadieron placas y tres pequeñas marcas de color para distinguir X, Y y Z. No se representan tornillos, borneras, cableado individual ni componentes del gabinete.

Los escaneos `.3dm` permanecen fuera del modelo. Los originales de `referencias/` se conservan y su manifiesto SHA-256 está en `docs/reference_manifest.json`. Las vistas de `docs/reference_previews/` son copias derivadas de lectura.

## Datos suministrados frente a decisiones del modelo

| Grupo | Datos usados del equipo físico |
| --- | --- |
| Mesa | 0.90 × 0.60 m; bastidor 0.85 m; goma 0.01 m |
| Estructura | Travesaños inferiores aprox. a 0.205 m; barras principales aprox. 0.045 m; laterales aprox. 0.055 m |
| Gabinete | 0.60 × 0.334 × 0.60 m; profundidad con tapa aprox. 0.35 m; separación del piso aprox. 0.05 m |
| Soportes | 0.035 × 0.152 × 0.155 m |
| X | Módulo 0.815 × 0.110 × 0.055 m; servo 0.200 × 0.060 × 0.060 m |
| Y | Módulo 0.042 × 0.710 × 0.093 m; servo 0.060 × 0.200 × 0.060 m |
| Z | Módulo 0.040 × 0.095 × 0.355 m; servo 0.060 × 0.060 × 0.240 m |

Los tamaños de esta tabla se expresan en X, Y, Z. La mesa alcanza 0.85 m antes de la goma y 0.86 m después. Los travesaños inferiores se sitúan con su centro a 0.205 m: la interpretación exacta de la medición, centro o borde, deberá revisarse cuando se releve el bastidor.

Las siguientes dimensiones **no fueron medidas en el equipo**:

| Pieza aproximada | Tamaño X, Y, Z, en metros |
| --- | --- |
| Carro Y | 0.100, 0.160, 0.043 |
| Carro X | 0.120, 0.140, 0.035 |
| Carro Z | 0.085, 0.035, 0.080 |
| Cuerpo de herramienta | 0.060, 0.055, 0.120 |
| Vástago de herramienta | Radio 0.012; longitud 0.120 |

Las posiciones de montaje, la cantidad y distribución de soportes, las placas, manija del gabinete, guías superficiales y los segmentos de portacables también son decisiones aproximadas de esta etapa. Las etiquetas Beckhoff/Rexroth no se reproducen gráficamente. La herramienta sólo tiene una forma neumática reconocible; no se simulan presión ni válvulas.

## Sólidos y relación padre-hijo

| DEF del sólido | Nombre en Webots | Padre/montaje | Función |
| --- | --- | --- | --- |
| raíz del PROTO | `cartesian_robot` | Mundo | Robot estático, mesa, goma y soportes |
| `CABINET` | `gabinete_electrico` | Raíz | Gabinete fijo delante de la mesa |
| `FIXED_Y` | `modulo_y_fijo` | Raíz | Guía y servo Y fijos |
| `Y_CARRIAGE` | `carro_y_con_eje_x` | Endpoint de SliderJoint Y de la raíz | Transporta módulo X y sus descendientes |
| `X_MODULE` | `modulo_x_y_servo` | `Y_CARRIAGE` | Módulo X con servo, rígido al carro Y |
| `X_CARRIAGE` | `carro_x_con_eje_z` | Endpoint de SliderJoint X de `Y_CARRIAGE` | Transporta módulo Z y sus descendientes |
| `Z_MODULE` | `modulo_z_y_servo` | `X_CARRIAGE` | Módulo y servo Z, rígidos al carro X |
| `Z_CARRIAGE` | `carro_z_y_herramienta` | Endpoint de SliderJoint Z de `X_CARRIAGE` | Único conjunto desplazado por Z |
| `TOOL` | `herramienta_neumatica_aproximada` | `Z_CARRIAGE` | Herramienta fija al carro Z |
| `TOOL_TIP` | `punto_herramienta` | `Z_CARRIAGE` | Referencia sin geometría para medir TCP |

La guía Y y su joint son hijos de la misma base estática: no es necesario colocar el joint dentro del sólido visual `FIXED_Y`. El resultado cinemático es el mismo, porque el padre del joint permanece fijo. Los módulos X y Z tampoco necesitan envolver sus joints: comparten respectivamente el padre móvil que los transporta.

En concreto, Y traslada `Y_CARRIAGE`, `X_MODULE`, `X_CARRIAGE`, `Z_MODULE`, `Z_CARRIAGE` y herramienta. X traslada `X_CARRIAGE`, `Z_MODULE`, `Z_CARRIAGE` y herramienta. Z traslada `Z_CARRIAGE` y herramienta. No hay tres ejes independientes.

## Articulaciones y coordenadas

Cada articulación es un `SliderJoint` con `JointParameters`, un `LinearMotor` y un `PositionSensor`. Los ejes son Y `(0, 1, 0)`, X `(1, 0, 0)` y Z `(0, 0, 1)`. No se aplican rotaciones de montaje a esta cadena, por lo que los desplazamientos se suman directamente en los ejes cartesianos del robot.

La posición inicial de los tres joints es cero y está dentro de sus límites de mando. No es una posición de fin de carrera ni representa un homing real. La configuración actual requiere `min < 0 < max` para cada eje.

La guía Y se ubica aproximadamente en `(-0.32, 0, 1.0615)`. El centro del carro Y parte de `(-0.32, 0, 1.1295)`. Las traslaciones de sus descendientes se expresan respecto a sus padres, no respecto al mundo:

```text
X_MODULE en Y_CARRIAGE  = (0.32,  0.00, 0.0490)
X_CARRIAGE en Y_CARRIAGE = (0.32, -0.02, 0.1060)
Z_MODULE en X_CARRIAGE  = (0.00, -0.068, 0.1770)
Z_CARRIAGE en X_CARRIAGE = (0.00, -0.130, 0.1645)
TOOL_TIP en Z_CARRIAGE  = (0.00,  0.00, -0.2400)
```

Por suma de esas traslaciones, el TCP inicial está en `(0, -0.15, 1.16)` respecto a la raíz. Para desplazamientos `q = (qx, qy, qz)`:

```text
TCP(q) = (0, -0.15, 1.16) + q
```

Con la raíz sin rotación y situada en el origen, ésa es también la posición del mundo. El Jacobiano de traslación es la matriz identidad: cada eje cambia una sola coordenada del TCP. La cadena mecánica Y → X → Z describe qué cuerpos se mueven, aunque los argumentos de la API se escriban siempre en orden X, Y, Z.

## Elección de los límites provisionales

Los valores de mando son X `[-0.25, +0.25]`, Y `[-0.20, +0.20]` y Z `[-0.09, +0.09]` m. Las longitudes exteriores de los módulos no se usan como recorridos. El margen se obtiene de:

```text
margen = largo_guía / 2 - largo_carro / 2
         - máximo |centro_inicial_carro + q - centro_guía|
```

| Eje | Guía | Carro a lo largo del eje | Mayor alejamiento entre centros | Margen mínimo con límites de mando |
| --- | ---: | ---: | ---: | ---: |
| X | 0.815 | 0.120 | 0.2500 | 0.0975 |
| Y | 0.710 | 0.160 | 0.2000 | 0.0750 |
| Z | 0.355 | 0.080 | 0.1025 | 0.0350 |

En Z, el centro inicial de la guía está a 1.4125 m y el del carro a 1.4000 m. El desplazamiento inferior de -0.09 m suma la desalineación inicial de 0.0125 m al alejamiento máximo. De ahí el margen de 0.035 m.

Los `minStop`/`maxStop` físicos se colocan 0.005 m por fuera de los límites del motor. Incluso en esos topes los márgenes son X 0.0925 m, Y 0.0700 m y Z 0.0300 m, mayores que el margen de diseño de 0.020 m exigido por el generador. Los valores se eligieron para no trabajar al final de las guías ni iniciar la simulación contra un tope.

La punta más baja de la herramienta está a `1.16 - 0.09 = 1.07 m`, a 0.21 m de la goma superior situada a 0.86 m. Este cálculo corresponde al modelo aproximado; no prueba interferencias de piezas reales todavía no relevadas.

Al sustituir límites por recorridos medidos habrá que revisar carros, offsets, topes y punto de herramienta. `build_model.py` valida el margen de guía y la altura de la herramienta antes de escribir los archivos generados.

## Física y estabilidad

El `Robot` raíz no tiene `Physics`, por lo que queda anclado al mundo. La mesa y la guía Y no pueden caer. Los endpoints Y, X y Z sí tienen `Physics { density -1 mass ... }`, con masa de 12, 5 y 1.5 kg, respectivamente. Cada masa representa la agrupación rígida del sólido correspondiente, sin añadir otra masa independiente para cada pieza visual descendiente. Estos valores no fueron medidos.

Los módulos y la herramienta sin `Physics` se comportan como partes rígidas de sus padres. Los `boundingObject` de los sólidos móviles agrupan cajas/cilindros simples para su carro y piezas transportadas. La apariencia visual y la geometría de colisión se generan por separado; no hay mallas complejas.

`selfCollision FALSE` evita contactos entre piezas del mismo robot. Los joints conservan la relación de montaje y los límites protegen los recorridos. El modelo no reproduce contactos internos entre carros y guías ni detecta por sí mismo todas las interferencias reales. Los segmentos de portacables son decorativos rígidos unidos a Y y no representan una cadena flexible.

Los motores tienen fuerzas máximas aproximadas de X 250 N, Y 500 N y Z 150 N, con velocidades máximas 0.04, 0.04 y 0.025 m/s, aceleración 0.10 m/s², ganancia proporcional 3 y amortiguamiento en joints. Son ajustes para esta simulación, no especificaciones eléctricas o mecánicas de los servos Beckhoff.

## Control y comprobaciones

El controlador resuelve los dispositivos por los nombres `motor_x`, `motor_y`, `motor_z`, `sensor_x`, `sensor_y` y `sensor_z`; habilita los sensores al paso de simulación de 16 ms. `move_to(x, y, z)` limita los objetivos a los intervalos definidos en el JSON. La demostración espera convergencia por sensores y usa una tolerancia de 0.8 mm con 0.20 s de asentamiento.

El robot dispone de `supervisor TRUE` para observar los sólidos internos del PROTO durante las pruebas. Se compara la posición de los carros, módulos y TCP antes y después de movimientos de un eje por vez. Estas mediciones comprueban la jerarquía, además de verificar que un sensor se haya movido.

| Prueba | Cuerpos que deben trasladarse | Cuerpos que deben permanecer fijos |
| --- | --- | --- |
| Sólo Y | Carro Y, módulo/carros X, módulo/carro Z y herramienta | Base y módulo Y |
| Sólo X | Carro X, módulo/carro Z y herramienta | Base, módulo Y, carro Y y módulo X |
| Sólo Z | Carro Z y herramienta | Base, módulo Y, carro Y, módulo X, carro X y módulo Z |

El resultado ejecutado se documenta en `docs/validation_report.json`, y las salidas completas en `docs/validation_webots_stdout.log` y `docs/validation_webots_stderr.log`. El informe debe renovarse si se modifica el modelo. Abrir un world o revisar el texto de un PROTO sin ejecutar el controlador no demuestra esta cinemática.

En modo `CARTESIAN_VALIDATE=1` también se recorren las ocho esquinas del volumen provisional, se prueban comandos fuera de límites y entradas NaN/infinito, y se mantiene el cero final durante 3 s para medir estabilidad. Las métricas continuas se calculan en cada timestep de 16 ms; el JSON guarda muestras cada 0.5 s, transiciones y extremos para que siga siendo legible. La captura de Webots queda en `docs/validation.jpg`.

La primera ejecución detectó una excursión transitoria de unos 5.3 mm fuera del intervalo de mando. Se redujo la ganancia proporcional de 15 a 3 para ajustar el frenado a las velocidades y aceleración elegidas, sin aumentar la tolerancia de validación. También se corrigió la orientación FLU de la cámara inicial y la ubicación lateral del módulo Z para apoyarlo coherentemente sobre su carro; no cambió el TCP de referencia. `docs/validation_initial_failure.json` conserva el informe inicial y el informe principal registra la ejecución más reciente.

La ejecución física posterior aprobó **23 comprobaciones**, con `passed: true`, `exit_status: 0` y `failed_checks: []`, tras 193.424 s de tiempo simulado. Cada prueba de jerarquía observó directamente ocho nodos, incluidos los módulos X y Z con sus servos. Se evaluaron 12 083 muestras de timestep y se exportaron 413 muestras representativas.

| Métrica continua observada | Resultado |
| --- | ---: |
| Mayor excursión de sensor respecto al intervalo de mando | 0.00004905 m |
| Mayor deriva de la guía Y fija | 0 m |
| Mayor diferencia entre componentes de matrices de orientación | 0.00001926, adimensional |
| Mayor error cinemático de la punta respecto a posición esperada | 0.00020250 m |
| Separación mínima de la punta respecto a la goma | 0.20974872 m |

La medida de orientación compara componentes de matrices, no un ángulo en radianes. El exceso de 0.049 mm corresponde a un transitorio físico dentro de la tolerancia de sensor de 0.8 mm; los comandos sí se recortan exactamente a los límites. La prueba de estabilidad final de 3 s también aprobó. Estos números caracterizan este modelo y ejecución; no son mediciones del robot real.

El script de validación ejecuta `webots-bin.exe` directamente para preservar los handles de salida en Windows, mientras que el script de apertura usa `webots.exe`. Se asigna un puerto libre para convivir con la instancia del usuario y los cambios temporales de entorno se restauran al terminar. No se requiere modificar la configuración global de Python ni abrir Blender.

La última ejecución terminó con código 0 y stderr vacío; stdout no contiene errores ni advertencias de parser, PROTO, dispositivos o Physics. El PROTO contiene exactamente tres SliderJoint, tres LinearMotor y tres PositionSensor, sin HingeJoint. Los nombres y SHA-256 de los 13 archivos de referencias coinciden con la inspección inicial (`reference_integrity.json`).

## Segunda etapa y medidas pendientes

Los escaneos 3D se integrarán en una segunda etapa después de validar completamente la cinemática.

Antes de sustituir primitivas por geometría detallada conviene medir recorridos útiles, posiciones de referencia/homing, tamaños y apoyos de carros, posiciones de cada módulo y servo, TCP y dimensiones de la herramienta, masas/centros de gravedad, velocidades y aceleraciones admisibles, y las zonas de posible interferencia. La geometría visual importada debe conservar los tres joints y sus padres; las colisiones podrán seguir siendo simples para mantener estabilidad.
