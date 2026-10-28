# CARTESIANA — Gemelo digital en Webots con conexión TCP/IP

Trabajo final de **Seminario de Informática I (UNSTA, 2026)**.

CARTESIANA es una máquina cartesiana de tres ejes (X, Y, Z) con un pequeño grip en la punta, que mueve una pieza de un zócalo a otro. Este proyecto es su **gemelo digital**: la máquina simulada en **Webots** y un **programa externo** que la controla por **TCP/IP**, como lo haría con la máquina real.

```text
┌──────────────────────┐      TCP/IP 127.0.0.1:5000       ┌──────────────────────────────┐
│  Programa externo    │  ── comandos: HOME, MOVE, GRIP ─► │  Webots: cartesiana_tcp      │
│  (cliente TCP)       │  ◄─ respuestas: DONE, POS, ERR ── │  "PC industrial" simulada    │
│  graba y ejecuta     │                                   │  (servidor TCP)              │
│  trayectorias        │                                   │  ejes, sensores y grip       │
└──────────────────────┘                                   └──────────────────────────────┘
```

Con el programa se puede:

1. **Conectar** con la máquina.
2. **Inicializarla**: busca sus sensores de inicio de carrera en X, Y y Z para saber dónde está.
3. **Moverla a mano** y abrir o cerrar el grip.
4. **Grabar puntos** de una trayectoria.
5. **Reproducir la trayectoria** automáticamente, una vez o en ciclo.

---

## Índice

1. [Requisitos](#1-requisitos)
2. [Instalación](#2-instalación)
3. [Tutorial: de abrir el mundo a reproducir una trayectoria](#3-tutorial-de-abrir-el-mundo-a-reproducir-una-trayectoria)
4. [Referencia del programa externo](#4-referencia-del-programa-externo)
5. [Coordenadas y zona de trabajo](#5-coordenadas-y-zona-de-trabajo)
6. [El protocolo en pocas palabras](#6-el-protocolo-en-pocas-palabras)
7. [Usar Webots en otra computadora](#7-usar-webots-en-otra-computadora)
8. [Configuración](#8-configuración)
9. [Solución de problemas](#9-solución-de-problemas)
10. [Estructura del repositorio](#10-estructura-del-repositorio)
11. [Documentación](#11-documentación)

---

## 1. Requisitos

| Programa | Versión | Notas |
| --- | --- | --- |
| [Webots](https://cyberbotics.com/) | **R2025a** (recomendada) | También funcionó en R2023b, con avisos de compatibilidad |
| [Python](https://www.python.org/downloads/) | 3.10 o más nuevo | Solo biblioteca estándar: no hay que instalar nada con `pip`. Tkinter viene incluido en el instalador de python.org |
| Git (opcional) | cualquiera | Solo para clonar el repositorio |

Funciona en Windows, Linux y macOS. Las instrucciones usan Windows como ejemplo.

---

## 2. Instalación

### 2.1 Descargar el proyecto

Con Git:

```bash
git clone https://github.com/wevillegas/CARTESIANA.git
```

Sin Git: en la página del repositorio, **Code → Download ZIP**, y descomprimir.

### 2.2 Indicarle a Webots dónde está Python

Webots ejecuta el controlador con Python. Hay que decirle **qué `python.exe` usar** en estos dos archivos:

- `controllers/cartesiana_tcp/runtime.ini`
- `controllers/cartesian_controller/runtime.ini`

Los dos tienen una línea así:

```ini
[python]
COMMAND = C:/Users/wence/AppData/Local/Python/pythoncore-3.14-64/python.exe
OPTIONS = -u
```

Cambiá la ruta de `COMMAND` por la de tu Python. Para averiguarla, en PowerShell:

```powershell
py -0p          # lista los Python instalados y sus rutas
# o bien
where.exe python
```

Usá barras `/` o dobles barras `\\` en la ruta. Si Python está en el PATH, también sirve poner simplemente `COMMAND = python`.

### 2.3 Lanzador del programa externo (solo Windows)

`programa_externo/iniciar_programa.bat` también tiene una ruta de Python en la línea `set PY=...`. Si esa ruta no existe en tu PC, usa `python` del PATH. Si no lo encuentra, corregí esa línea.

---

## 3. Tutorial: de abrir el mundo a reproducir una trayectoria

Cada paso indica qué deberías ver (✅) y qué hacer si algo sale mal (❌).

### Paso 1 — Abrir el mundo en Webots

1. Abrí Webots → **File → Open World**.
2. Elegí **`worlds/cartesiana_tcp.wbt`**. No es `cartesian_robot.wbt`, que es el modelo sin conexión TCP.

✅ Ves la mesa con el robot, el gabinete al costado, **dos pilares** (techo verde = zócalo A, techo azul = zócalo B), un **cubo rojo** sobre el verde y **tres bloques amarillos** en las puntas de los ejes, que son los sensores de inicio de carrera.

### Paso 2 — Iniciar la simulación

1. Presioná **Run** (▶).
2. Si Windows pregunta si permitir que Python use la red, elegí **Permitir**.

✅ El robot **se ubica en una posición cualquiera**, distinta cada vez. Simula que la máquina no sabe dónde quedó la última vez.

✅ En la vista 3D, arriba a la izquierda: `CARTESIANA: SIN INICIALIZAR (enviar HOME)` en rojo, y `TCP: esperando conexión en :5000`.

✅ En la consola de Webots:

```text
[CARTESIANA] Encendida en posición DESCONOCIDA. Enviar HOME para el ciclo de inicialización.
[TCP] Servidor escuchando en 0.0.0.0:5000 ...
```

❌ Si la consola dice `python.exe was not found`, revisá el paso [2.2](#22-indicarle-a-webots-dónde-está-python).

### Paso 3 — Abrir el programa externo

- **Windows:** doble click en `programa_externo/iniciar_programa.bat`.
- **Cualquier sistema:** desde la carpeta `programa_externo`, ejecutar `python cartesiana_app.py`.

✅ Se abre la ventana **"CARTESIANA - Trayectorias"**.

### Paso 4 — Conectar

1. Arriba, dejá **IP** `127.0.0.1` y **puerto** `5000`.
2. Tocá **Conectar**.

✅ Arriba, en verde: `Conectado: 127.0.0.1:5000`.

✅ En *Mensajes del protocolo*: `<< READY CARTESIANA 2.0 NOT_HOMED` y `<< PONG`.

✅ El cartel de *Inicialización* dice **SIN INICIALIZAR** en rojo.

❌ "No se pudo conectar": Webots no está en **Run**, o se abrió otro mundo.

### Paso 5 — Inicializar (homing)

La máquina real tiene **encoders relativos**: al encenderse no sabe dónde está. Por eso, mientras no se inicialice, **rechaza cualquier movimiento** (`ERR NOT_HOMED`).

1. Tocá **Inicializar (buscar sensores X, Y, Z)**.
2. Mirá Webots. Para cada eje, primero X, después Y y después Z:
   - va **rápido** hacia su sensor hasta tocarlo;
   - retrocede unos milímetros;
   - vuelve **lento** hasta tocarlo de nuevo. Ese punto pasa a ser su **cero**.

✅ El cartel pasa a **INICIALIZADA** en verde, la posición marca `X 0.0  Y 0.0  Z 0.0` y el registro muestra `<< DONE HOME`.

✅ En Webots: `CARTESIANA: INICIALIZADA` y `sensores X* Y* Z*` (el asterisco indica que el sensor está activado).

### Paso 6 — Mover a mano

Tenés dos formas:

- **Botones X −/X +, Y −/Y +, Z −/Z +:** se mueve la cantidad de **Paso (mm)** elegida.
- **Casilleros X, Y, Z + botón "Ir a X Y Z":** va directo a esa posición.

Recordá que **Z es negativo hacia abajo**: 0 es arriba de todo y −160 es la altura para agarrar en los zócalos.

Probá: X `100`, Y `100`, Z `-40` → **Ir a X Y Z**. El robot queda justo arriba del pilar verde.

### Paso 7 — Usar el grip

En *Pinza (grip)*: **Abrir** / **Cerrar**.

- Si al cerrar hay una pieza entre los dedos, el registro dice `DONE GRIP CLOSE HELD`.
- Si no hay nada, dice `DONE GRIP CLOSE EMPTY`.

Para agarrar el cubo a mano: **Abrir** → ir a `100, 100, -160` → **Cerrar** (`HELD`) → subir a `100, 100, -40`.

### Paso 8 — Grabar una trayectoria

Una trayectoria es una **lista de puntos**. Cada punto dice **a dónde ir**, **qué hacer con el grip al llegar** (Abrir, Cerrar o nada) y **cuánto esperar**.

1. En *Comando manual* (abajo) escribí `RESET` + Enter. El cubo vuelve al pilar verde.
2. Tocá **Borrar todo** para empezar con la lista vacía.
3. Por cada fila de esta tabla:
   1. escribí X, Y, Z en los casilleros y tocá **Ir a X Y Z**;
   2. esperá `DONE MOVE` en el registro;
   3. tocá **Guardar punto actual**;
   4. en la ventanita, elegí **Pinza al llegar** y **Espera**, y tocá **Aceptar**.

| # | X, Y, Z | Pinza al llegar | Espera (ms) | Para qué |
| --- | --- | --- | --- | --- |
| 1 | 100, 100, -40 | Abrir | 0 | Llegar arriba del verde con el grip abierto |
| 2 | 100, 100, -160 | Cerrar | 300 | Agarrar el cubo |
| 3 | 100, 100, -40 | — | 0 | Levantarlo |
| 4 | 400, 200, -40 | — | 0 | Llevarlo arriba del azul |
| 5 | 400, 200, -160 | Abrir | 300 | Soltarlo en el azul |
| 6 | 400, 200, -40 | — | 0 | Retirarse |

4. **Guardar archivo…** → por ejemplo `trayectorias/mi_trayectoria.json`.

> **Ojo:** cada punto nuevo se agrega **debajo de la fila seleccionada** (la azul). Para corregir un punto, doble click en la fila. Para reordenar: **Subir** / **Bajar**.

### Paso 9 — Reproducir la trayectoria

1. `RESET` en *Comando manual*, para que el cubo vuelva al pilar verde.
2. **Ir al cero (0, 0, 0)**.
3. **Ejecutar trayectoria**.

✅ El robot repite solo los puntos grabados. La fila en ejecución se marca en la tabla, y abajo aparece `Vuelta 1 · punto 2/6`. Al final: **"Trayectoria completa (6 puntos)"** y el cubo queda en el pilar azul (`DONE GRIP OPEN ZOCALO_B`).

**Para que lo repita en ciclo**, la trayectoria tiene que **devolver el cubo** al verde al final. Si no, la segunda vuelta va a buscarlo donde ya no está. Usá `trayectorias/ciclo_A_B_A.json` (lo lleva y lo devuelve), marcá **Repetir en ciclo** y tocá **Ejecutar trayectoria**.

### Paso 10 — Detener

**STOP** (botón rojo) frena la máquina en el acto y cancela lo pendiente. En el registro aparece `ERR ABORTED MOVE` y `OK STOP`.

### Paso 11 — Reiniciar o cerrar

- **Reset** en Webots (⏮) reinicia la simulación: el robot vuelve a quedar en una posición desconocida. En el programa hay que **Conectar** e **Inicializar** de nuevo, igual que con la máquina real al encenderla.
- Al cerrar Webots, si pregunta si guardar el mundo, elegí **no guardar**. Si se guarda con la simulación andando, queda grabado el estado de ese momento, por ejemplo el cubo en el aire. Igual, al iniciar, el controlador siempre vuelve a poner el cubo en el pilar verde.

---

## 4. Referencia del programa externo

| Sección | Control | Qué hace | Comando que envía |
| --- | --- | --- | --- |
| Conexión | **Conectar / Desconectar** | Abre o cierra la conexión TCP | `PING`, `INFO`, `SPEED`, `POS?` |
| Inicialización | **Inicializar** | Ciclo de homing X → Y → Z | `HOME` |
| Mover manualmente | **X−/X+, Y−/Y+, Z−/Z+** | Mueve un paso en ese eje | `MOVE x y z` |
| | **Ir al cero (0, 0, 0)** | Va al origen (los sensores) | `MOVE 0 0 0` |
| | **Ir a X Y Z** | Va a la posición escrita | `MOVE x y z` |
| | **Velocidad mm/s → Aplicar** | Cambia la velocidad (Z llega a 25 mm/s como máximo) | `SPEED v` |
| Pinza (grip) | **Abrir / Cerrar** | Mueve los dedos | `GRIP OPEN` / `GRIP CLOSE` |
| | **STOP** | Frena todo | `STOP` |
| Trayectoria | **Guardar punto actual** | Agrega la posición actual a la lista | — |
| | **Editar / Ir al punto / Subir / Bajar / Borrar / Borrar todo** | Edita la lista | — |
| | **Abrir archivo… / Guardar archivo…** | Carga o guarda la lista en JSON | — |
| | **Ejecutar trayectoria** (+ *Repetir en ciclo*) | Recorre la lista | `MOVE`, `GRIP`, `WAIT` |
| Abajo | **Comando manual** | Envía cualquier comando del protocolo, por ejemplo `RESET`, `SWITCH?` o `POS?` | el que escribas |
| | **Mensajes del protocolo** | Registro de todo lo enviado (`>>`) y recibido (`<<`) | — |

Las trayectorias se guardan en `programa_externo/trayectorias/`:

| Archivo | Qué hace |
| --- | --- |
| `pick_and_place_A_a_B.json` | Lleva el cubo del zócalo A (verde) al B (azul), una vez |
| `ciclo_A_B_A.json` | Lo lleva al B y lo devuelve al A; sirve para **Repetir en ciclo** |

---

## 5. Coordenadas y zona de trabajo

Después de inicializar, las coordenadas se miden en **milímetros desde los sensores**:

| Eje | Sensor | Recorrido | Sentido |
| --- | --- | --- | --- |
| X | Extremo izquierdo | 0 a 497 mm | + hacia la derecha |
| Y | Extremo delantero | 0 a 397 mm | + hacia el fondo |
| Z | Arriba | −177 a 0 mm | − hacia abajo |

| Lugar | X | Y | Z |
| --- | --- | --- | --- |
| Zócalo A (verde) — arriba | 100 | 100 | −40 |
| Zócalo A — altura de agarre | 100 | 100 | −160 |
| Zócalo B (azul) — arriba | 400 | 200 | −40 |
| Zócalo B — altura de agarre | 400 | 200 | −160 |

No bajes más de −160 sobre un zócalo: los dedos chocan con la placa. Un destino fuera del recorrido se rechaza con `ERR RANGE` y la máquina no se mueve.

---

## 6. El protocolo en pocas palabras

- **Socket TCP** (no es HTTP ni una API REST): una conexión que queda abierta y por la que viajan **líneas de texto**.
- **Un comando, una respuesta:** el cliente envía una línea y espera su respuesta antes de enviar la siguiente.
- Distancias en **mm** y velocidades en **mm/s**.

| Comando | Respuesta | Qué hace |
| --- | --- | --- |
| `PING` | `PONG` | Prueba la conexión |
| `HOME` | `DONE HOME` | Ciclo de inicialización |
| `MOVE x y z` | `DONE MOVE x y z` | Mueve los tres ejes (requiere `HOME`) |
| `GRIP OPEN` / `GRIP CLOSE` | `DONE GRIP …` (`HELD`/`EMPTY`, dónde quedó la pieza) | Abre o cierra el grip |
| `SPEED v` | `OK SPEED …` | Velocidad |
| `WAIT ms` | `DONE WAIT` | Pausa |
| `POS?` | `POS x y z OPEN\|CLOSED HELD\|EMPTY HOMED\|NOT_HOMED` | Estado actual |
| `SWITCH?` | `SWITCH X1 Y0 Z0` | Sensores de inicio de carrera |
| `STATUS?` / `INFO` | `STATUS …` / `INFO …` | Ocupada o libre / recorrido de cada eje |
| `STOP` | `OK STOP` | Frena y cancela |
| `RESET` | `DONE RESET` | Devuelve el cubo al zócalo A (para repetir la demo) |

Errores: `ERR NOT_HOMED`, `ERR RANGE`, `ERR SYNTAX`, `ERR UNKNOWN`, `ERR TIMEOUT`, `ERR ABORTED`, `ERR BUSY` (ya hay otro cliente conectado).

La referencia completa, con ejemplos, está en [`docs/protocolo_cartesiana.md`](docs/protocolo_cartesiana.md).

Para probar el protocolo sin el programa externo, alcanza con un cliente TCP cualquiera. Por ejemplo, en Python:

```python
import socket
s = socket.create_connection(("127.0.0.1", 5000)); f = s.makefile("r")
print(f.readline().strip())                        # READY CARTESIANA 2.0 NOT_HOMED
for cmd in ["PING", "HOME", "POS?"]:
    s.sendall((cmd + "\n").encode()); print(cmd, "->", f.readline().strip())
```

---

## 7. Usar Webots en otra computadora

El controlador escucha en `0.0.0.0:5000`, así que acepta conexiones de la red local.

1. En la PC con Webots, averiguá su IP (`ipconfig` → *Dirección IPv4*, por ejemplo `192.168.0.2`).
2. Abrí el puerto 5000 en el firewall de esa PC. En PowerShell como administrador:

   ```powershell
   New-NetFirewallRule -DisplayName "CARTESIANA Webots 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
   ```

3. En el programa externo de la otra PC, poné esa IP en lugar de `127.0.0.1` y tocá **Conectar**.

---

## 8. Configuración

| Archivo | Qué se configura |
| --- | --- |
| `config/comunicacion.json` | IP de escucha y **puerto** del servidor TCP (5000) |
| `config/robot_parameters.json` | Medidas del robot, límites y velocidades de los ejes, `gripper` (grip), `homing` (orden, ubicación de los sensores, velocidades de búsqueda) y `workcell` (posición de los zócalos en mm de máquina) |

Si cambiás medidas, límites, sensores o zócalos en `robot_parameters.json`, regenerá el modelo y recargá el mundo en Webots:

```powershell
python tools/build_model.py
```

Esto actualiza `protos/CartesianRobot.proto` y los mundos de `worlds/`. No conviene editar esos archivos a mano, porque se sobrescriben al regenerar.

---

## 9. Solución de problemas

| Problema | Causa probable | Solución |
| --- | --- | --- |
| Consola de Webots: `python.exe was not found` | Ruta de Python incorrecta | Corregir `COMMAND` en los `runtime.ini` ([2.2](#22-indicarle-a-webots-dónde-está-python)) |
| El programa no conecta | Webots no está en **Run**, o se abrió otro mundo | Abrir `worlds/cartesiana_tcp.wbt` y presionar **Run** |
| `No se pudo abrir el puerto 5000` en la consola | Hay otra simulación u otro programa usando el puerto | Cerrar las otras ventanas de Webots; el controlador reintenta solo |
| `ERR BUSY` | Ya hay otro cliente conectado | Cerrar el otro programa y volver a conectar |
| `ERR NOT_HOMED` | No se inicializó (o se reinició Webots) | Presionar **Inicializar** |
| `ERR RANGE …` | Destino fuera del recorrido | Usar valores dentro de la [zona de trabajo](#5-coordenadas-y-zona-de-trabajo) |
| `DONE GRIP CLOSE EMPTY` cuando se esperaba agarrar | El grip no estaba exactamente sobre el cubo | Ir a `100, 100, -160` (zócalo A) y volver a cerrar; `RESET` si el cubo quedó en otro lado |
| El cubo aparece en un lugar raro | El mundo se guardó con la simulación andando | Dar **Run**: el controlador lo vuelve a poner en el zócalo A. Si no, `RESET` |
| El programa dice "Conexión perdida" | Se presionó **Reset** o se cerró Webots | **Conectar** de nuevo e **Inicializar** |

---

## 10. Estructura del repositorio

```text
CARTESIANA/
├── worlds/
│   ├── cartesiana_tcp.wbt          ← gemelo digital con TCP (el que se usa)
│   └── cartesian_robot.wbt         ← modelo cinemático original, sin TCP
├── controllers/
│   ├── cartesiana_tcp/             ← "PC industrial": servidor TCP, protocolo, homing, grip
│   │   ├── cartesiana_tcp.py
│   │   ├── protocol.py
│   │   └── runtime.ini             ← ruta de Python
│   └── cartesian_controller/       ← control cinemático validado (base del anterior)
├── programa_externo/
│   ├── cartesiana_app.py           ← interfaz gráfica (Tkinter)
│   ├── enlace.py                   ← cliente TCP
│   ├── iniciar_programa.bat        ← lanzador para Windows
│   └── trayectorias/               ← trayectorias en JSON
├── protos/CartesianRobot.proto     ← modelo del robot (generado)
├── config/                         ← parámetros del robot y de la comunicación
├── tools/build_model.py            ← genera el modelo y los mundos desde config/
├── meshes/, textures/              ← mallas 3D (escaneo y CAD del servo Z)
├── blender/, cad/reports/          ← trabajo de modelado (etapas anteriores)
└── docs/                           ← documentación (ver abajo)
```

---

## 11. Documentación

| Documento | Contenido |
| --- | --- |
| [Protocolo de comunicación](docs/protocolo_cartesiana.md) | Todos los comandos, respuestas, errores y ejemplos |
| [Documento de virtualización (PDF)](docs/CARTESIANA_virtualizacion.pdf) | Documento de la entrega: arquitectura, homing, protocolo, ensayos |
| [Informe para el profesor (PDF)](docs/Informe_CARTESIANA_profesor.pdf) | Resumen breve del trabajo |
| [Guía de estudio para la defensa (PDF)](docs/Guia_estudio_defensa_CARTESIANA.pdf) | Conceptos de red, protocolo y homing, con preguntas y respuestas |
| [Historia del modelo](docs/historia_del_modelo.md) | Detalle técnico de las etapas previas: medidas, cinemática, escaneo 3D, CAD del fabricante, validaciones |

### Limitaciones y supuestos

- Los recorridos, las masas, la ubicación de los sensores (X a la izquierda, Y adelante, Z arriba) y las medidas del grip son **estimados**: no se midieron en la máquina real.
- Los **zócalos y el cubo son un ejemplo** para la demostración. Están sobre columnas porque el recorrido Z provisional no llega a la mesa.
- El agarre se resuelve por software (el controlador mueve la pieza con la punta), no por fricción.
- Los STEP y manuales del fabricante (Beckhoff, Rexroth) y las fotos originales **no se incluyen** en el repositorio.
