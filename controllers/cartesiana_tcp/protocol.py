"""Protocolo de texto CARTESIANA v2 (independiente de Webots, se puede probar solo).

Cada mensaje es UNA línea de texto ASCII terminada en '\\n' ('\\r\\n' también se acepta).
Las distancias van en milímetros y las velocidades en mm/s, en coordenadas de
máquina: el cero de cada eje es su sensor de inicio de carrera, fijado por el
ciclo de inicialización (HOME). Antes de HOME la máquina no sabe dónde está.

El cliente envía un comando y espera su respuesta antes de enviar el siguiente,
como haría con un Arduino por puerto serie. Las respuestas empiezan siempre con
una de estas palabras: READY, PONG, INFO, POS, STATUS, SWITCH, OK, DONE o ERR.

Ver docs/protocolo_cartesiana.md para la tabla completa.
"""

import math

VERSION = "2.0"
DEVICE = "CARTESIANA"
MAX_LINE = 128

# Comandos que se responden enseguida, aunque el robot se esté moviendo.
IMMEDIATE = {"PING", "INFO", "POS?", "STATUS?", "SWITCH?", "STOP"}
# Comandos que entran a la cola y se ejecutan de a uno, en orden.
QUEUED = {"MOVE", "HOME", "SPEED", "GRIP", "WAIT", "RESET"}

ALIASES = {"POS": "POS?", "STATUS": "STATUS?", "?": "STATUS?", "SWITCH": "SWITCH?"}


class ProtocolError(ValueError):
    """Error de formato: se responde con la línea ``reply``."""

    def __init__(self, reply):
        super().__init__(reply)
        self.reply = reply


class Command:
    __slots__ = ("name", "args", "raw")

    def __init__(self, name, args, raw):
        self.name, self.args, self.raw = name, args, raw

    @property
    def immediate(self):
        return self.name in IMMEDIATE

    def __repr__(self):
        return f"Command({self.name!r}, {self.args!r})"


def _number(token, what):
    try:
        value = float(token)
    except ValueError:
        raise ProtocolError(f"ERR SYNTAX {what} debe ser un numero") from None
    if not math.isfinite(value):
        raise ProtocolError(f"ERR SYNTAX {what} debe ser finito")
    return value


def parse(line):
    """Convierte una línea recibida en un Command, o lanza ProtocolError."""
    raw = line.strip()
    if len(raw) > MAX_LINE:
        raise ProtocolError("ERR TOOLONG")
    if not raw:
        return None
    tokens = raw.replace(",", " ").replace(";", " ").split()
    name = tokens[0].upper()
    name = ALIASES.get(name, name)
    args = tokens[1:]
    if name not in IMMEDIATE and name not in QUEUED:
        raise ProtocolError(f"ERR UNKNOWN {tokens[0][:20]}")

    if name in ("PING", "INFO", "POS?", "STATUS?", "SWITCH?", "STOP", "HOME", "RESET"):
        if args:
            raise ProtocolError(f"ERR SYNTAX {name} no lleva argumentos")
        return Command(name, (), raw)
    if name == "MOVE":
        if len(args) != 3:
            raise ProtocolError("ERR SYNTAX MOVE x y z")
        return Command(name, tuple(_number(a, axis) for a, axis in zip(args, "XYZ")), raw)
    if name == "SPEED":
        if len(args) != 1:
            raise ProtocolError("ERR SYNTAX SPEED v")
        value = _number(args[0], "v")
        if value <= 0:
            raise ProtocolError("ERR SYNTAX v debe ser positiva")
        return Command(name, (value,), raw)
    if name == "WAIT":
        if len(args) != 1:
            raise ProtocolError("ERR SYNTAX WAIT ms")
        value = _number(args[0], "ms")
        if not 0 <= value <= 60000:
            raise ProtocolError("ERR SYNTAX ms entre 0 y 60000")
        return Command(name, (value,), raw)
    if name == "GRIP":
        if len(args) != 1 or args[0].upper() not in ("OPEN", "CLOSE"):
            raise ProtocolError("ERR SYNTAX GRIP OPEN|CLOSE")
        return Command(name, (args[0].upper(),), raw)
    raise ProtocolError(f"ERR UNKNOWN {tokens[0][:20]}")  # pragma: no cover


def mm(value_m):
    """Metros a texto en mm con un decimal."""
    value = round(value_m * 1000.0, 1)
    return f"{value + 0.0:.1f}"  # + 0.0 evita "-0.0"


def fmt_pos(xyz_m, gripper_closed, holding, homed):
    return ("POS " + " ".join(mm(v) for v in xyz_m) + " " +
            ("CLOSED" if gripper_closed else "OPEN") + " " + ("HELD" if holding else "EMPTY") + " " +
            ("HOMED" if homed else "NOT_HOMED"))


def strip_telnet(data):
    """Quita secuencias Telnet/RFC 2217 (IAC = 0xFF) y bytes no imprimibles.

    Si alguien se conecta con un cliente Telnet, este intercala esas secuencias
    con los datos; el protocolo es texto plano y no las necesita.
    """
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        b = data[i]
        if b == 0xFF and i + 1 < n:
            cmd = data[i + 1]
            if cmd == 0xFF:            # 0xFF literal escapado
                i += 2
                continue
            if cmd == 0xFA:            # subnegociación: IAC SB ... IAC SE
                end = data.find(b"\xff\xf0", i + 2)
                i = n if end < 0 else end + 2
                continue
            i += 3 if 0xFB <= cmd <= 0xFE else 2   # WILL/WONT/DO/DONT llevan opción
            continue
        if b in (9, 10, 13) or 32 <= b < 127:
            out.append(b)
        i += 1
    return bytes(out)


class LineBuffer:
    """Junta los bytes que llegan por TCP y devuelve líneas completas."""

    def __init__(self):
        self._data = b""

    def feed(self, chunk):
        self._data += strip_telnet(chunk)
        lines = []
        while b"\n" in self._data:
            line, self._data = self._data.split(b"\n", 1)
            lines.append(line.decode("ascii", errors="replace").rstrip("\r"))
        if len(self._data) > 4 * MAX_LINE:  # basura sin salto de línea
            self._data = b""
            lines.append("\x00TOOLONG")
        return lines
