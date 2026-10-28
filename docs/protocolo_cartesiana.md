# Protocolo CARTESIANA v2.0

Protocolo de texto plano entre el **programa externo** (cliente TCP) y la **PC industrial de la máquina** (servidor TCP). En la simulación, la PC industrial es el controlador de Webots `cartesiana_tcp`, que escucha en el puerto `5000`.

## Transporte

```
Programa externo  ── TCP/IP ──►  PC industrial (Webots: cartesiana_tcp)
 cliente                           servidor, 0.0.0.0:5000
```

- **Socket TCP directo.** No es HTTP ni API REST: es una conexión que se abre una vez y queda abierta, por la que pasan líneas de texto en los dos sentidos.
- Dirección: `127.0.0.1:5000` si todo corre en la misma PC. Si Webots está en otra, su IP (por ejemplo `192.168.0.2:5000`) y el puerto 5000 abierto en el firewall.
- Una línea de texto ASCII por mensaje, terminada en `\n` (`\r\n` también se acepta). Máximo 128 caracteres.
- Mayúsculas o minúsculas indistintas. Los argumentos se separan con espacios o comas. El decimal es el punto.
- **Un comando, una respuesta:** el cliente envía un comando y espera su respuesta antes de mandar el siguiente.
- Un solo cliente a la vez. Si se conecta otro, recibe `ERR BUSY` y se cierra su conexión.
- Al conectarse, el servidor saluda con `READY CARTESIANA 2.0 HOMED|NOT_HOMED`.

## Coordenadas e inicialización (homing)

La máquina real tiene **encoders relativos**: al encenderse no sabe dónde está. Por eso:

1. Al arrancar, la máquina está en una posición **desconocida**. La simulación la ubica al azar. Las posiciones que informa son relativas al punto de encendido y no sirven para trabajar.
2. Mientras no esté inicializada, rechaza los movimientos con `ERR NOT_HOMED`.
3. El comando **`HOME`** ejecuta el **ciclo de inicialización**. Para cada eje, en orden **X → Y → Z**:
   - se mueve rápido hacia su **sensor de inicio de carrera** hasta que se activa;
   - se aleja 6 mm;
   - vuelve lento (10 mm/s) y, **en el instante en que el sensor se activa**, esa posición pasa a ser el **cero** del eje.
4. Al terminar los tres ejes responde `DONE HOME`: la máquina está en `(0, 0, 0)` y acepta movimientos.

| Eje | Sensor de inicio de carrera | Recorrido después del homing |
| --- | --- | --- |
| X | extremo izquierdo | 0 a 497 mm |
| Y | extremo delantero | 0 a 397 mm |
| Z | arriba | −177 a 0 mm (negativo = hacia abajo) |

Unidades: **milímetros** y **mm/s**, en coordenadas de máquina. El cero es el sensor, y no se puede ir más allá de él. Los sensores están 3 mm antes del tope mecánico, por eso el recorrido es 3 mm menor que el del eje.

## Comandos inmediatos

Se responden al instante, aunque la máquina se esté moviendo.

| Comando | Respuesta | Descripción |
| --- | --- | --- |
| `PING` | `PONG` | Comprobar el enlace |
| `INFO` | `INFO CARTESIANA 2.0 HOMED XMIN 0.0 XMAX 497.1 … VMAX 25.0` | Estado y recorrido de cada eje. Sin inicializar, los límites son `?` |
| `POS?` | `POS x y z OPEN\|CLOSED HELD\|EMPTY HOMED\|NOT_HOMED` | Posición, estado del grip, si sostiene la pieza y si está inicializada |
| `STATUS?` | `STATUS IDLE\|BUSY n HOMED\|NOT_HOMED` | Si está ejecutando algo, cuántos comandos esperan y estado |
| `SWITCH?` | `SWITCH X1 Y0 Z0` | Estado de los sensores de inicio de carrera (1 = activado) |
| `STOP` | `ERR ABORTED <cmd>` (uno por comando cortado) y luego `OK STOP` | Frena donde está y descarta lo pendiente. Si cortó un `HOME`, la máquina queda sin inicializar |

## Comandos en cola

Se ejecutan de a uno, en orden, y responden al terminar.

| Comando | Respuesta | Descripción |
| --- | --- | --- |
| `HOME` | `DONE HOME` | Ciclo de inicialización X → Y → Z |
| `MOVE x y z` | `DONE MOVE x y z` (posición alcanzada) | Mueve los tres ejes a la vez. Requiere inicialización |
| `SPEED v` | `OK SPEED X40.0 Y40.0 Z25.0` | Velocidad para los tres ejes; cada eje la limita a su máximo |
| `GRIP CLOSE` | `DONE GRIP CLOSE HELD` o `DONE GRIP CLOSE EMPTY` | Cierra el grip. `HELD` si había una pieza entre los dedos |
| `GRIP OPEN` | `DONE GRIP OPEN [ZOCALO_A\|ZOCALO_B\|MESA]` | Abre el grip. Si soltó la pieza, indica dónde quedó |
| `WAIT ms` | `DONE WAIT` | Pausa (0 a 60000 ms) |
| `RESET` | `DONE RESET` | Devuelve la pieza al zócalo A y abre el grip (para repetir la demo) |

Un movimiento termina cuando los tres ejes quedan a menos de 0.8 mm del objetivo durante 0.2 s. El grip funciona aunque la máquina no esté inicializada.

## Errores

| Respuesta | Causa |
| --- | --- |
| `ERR NOT_HOMED` | Se pidió un `MOVE` sin haber hecho `HOME` |
| `ERR RANGE <eje> <valor> (<min>..<max>)` | Destino fuera del recorrido. **No se mueve**: la orden se rechaza, no se recorta |
| `ERR UNKNOWN <palabra>` | Comando inexistente |
| `ERR SYNTAX <detalle>` | Faltan argumentos o no son números válidos |
| `ERR TIMEOUT <cmd>` | No terminó a tiempo (por ejemplo, por un choque); además frena |
| `ERR ABORTED <cmd>` | Cortado por `STOP` |
| `ERR TOOLONG` | Línea de más de 128 caracteres |
| `ERR BUSY` | Ya hay otro cliente conectado |

Si el cliente se desconecta en medio de un movimiento, la máquina frena y descarta los comandos pendientes.

## Ejemplo: encender, inicializar y llevar la pieza de A a B

```text
<< READY CARTESIANA 2.0 NOT_HOMED
>> MOVE 100 100 -40         << ERR NOT_HOMED (enviar HOME primero)
>> HOME                     << DONE HOME
>> POS?                     << POS 0.0 0.0 0.1 OPEN EMPTY HOMED
>> SWITCH?                  << SWITCH X1 Y1 Z1
>> SPEED 40                 << OK SPEED X40.0 Y40.0 Z25.0
>> MOVE 100 100 -40         << DONE MOVE 99.6 99.6 -40.0
>> MOVE 100 100 -160        << DONE MOVE 100.0 100.0 -159.6
>> GRIP CLOSE               << DONE GRIP CLOSE HELD
>> MOVE 100 100 -40         << DONE MOVE 100.0 100.0 -40.4
>> MOVE 400 200 -40         << DONE MOVE 399.6 200.0 -40.1
>> MOVE 400 200 -160        << DONE MOVE 400.0 200.0 -159.6
>> GRIP OPEN                << DONE GRIP OPEN ZOCALO_B
>> MOVE -1 0 0              << ERR RANGE X -1.0 (0..497)
```

## Zona de trabajo del gemelo digital

| Elemento | Coordenadas de máquina (mm) |
| --- | --- |
| Zócalo A (verde), donde empieza la pieza | X 100, Y 100 |
| Zócalo B (azul) | X 400, Y 200 |
| Altura de agarre | Z −160 (más abajo, los dedos tocan el zócalo) |
| Altura segura de traslado | Z −40 |

Los zócalos son un ejemplo para la demostración: no están en la máquina real. Están sobre columnas porque el recorrido Z provisional no llega a la mesa. Se reubican en `config/robot_parameters.json` (`workcell`) y se regenera con `tools/build_model.py`.

## Trayectorias del programa externo

El programa guarda las trayectorias como JSON en `programa_externo/trayectorias/`, en coordenadas de máquina:

```json
{
  "formato": "CARTESIANA trayectoria v2",
  "unidad": "mm de máquina (cero en los sensores de inicio de carrera)",
  "velocidad_mm_s": 40,
  "puntos": [
    {"x": 100.0, "y": 100.0, "z": -160.0, "pinza": "CLOSE", "espera_ms": 300}
  ]
}
```

Al ejecutar, cada punto se convierte en `MOVE x y z`. Después va `GRIP OPEN|CLOSE`, si el punto tiene acción de grip, y `WAIT ms`, si tiene espera. El programa espera cada `DONE` antes de enviar el siguiente comando.
