"""CARTESIANA - controlador Webots que simula la PC industrial de la máquina.

Es un SERVIDOR TCP (por defecto 0.0.0.0:5000). El programa externo se conecta
directamente por TCP/IP y le envía comandos de texto (ver protocol.py).

Como la máquina real:
  * los encoders son RELATIVOS: al encender, la máquina no sabe dónde está.
    La simulación arranca con los ejes en una posición al azar;
  * cada eje tiene un SENSOR DE INICIO DE CARRERA (X y Y en su extremo mínimo,
    Z arriba);
  * hasta hacer el ciclo de inicialización (comando HOME) rechaza los movimientos
    con ERR NOT_HOMED. HOME mueve X hasta su sensor, después Y, después Z: cada
    sensor define el cero de su eje. Recién entonces queda en (0, 0, 0).

Hereda la cinemática validada de controllers/cartesian_controller y agrega el
servidor TCP no bloqueante, la cola de comandos, el homing, el grip de dos dedos
y una pieza que se puede llevar de un zócalo a otro.

La pieza no tiene física: cuando el grip la toma, el controlador (Supervisor)
la traslada con la punta en cada paso; al soltarla la apoya en el zócalo que
tenga debajo, o sobre la mesa.
"""

from collections import deque
import errno
import json
import math
import os
from pathlib import Path
import random
import socket
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent / "cartesian_controller"))

from cartesian_controller import AXES, CartesianController, SimulationEnded  # noqa: E402
from controller import Motor  # noqa: E402
import protocol  # noqa: E402

PROJECT_ROOT = HERE.parents[1]
COMM_PATH = PROJECT_ROOT / "config" / "comunicacion.json"


class Task:
    """Un comando de la cola en ejecución."""

    def __init__(self, command):
        self.command = command
        self.started = None
        self.deadline = None
        self.settled_since = None
        self.data = {}


class CartesianaTCP(CartesianController):

    def __init__(self):
        super().__init__()
        comm = json.loads(COMM_PATH.read_text(encoding="utf-8")) if COMM_PATH.exists() else {}
        self.host = os.environ.get("CARTESIANA_HOST", comm.get("host", "0.0.0.0"))
        self.port = int(os.environ.get("CARTESIANA_PORT", comm.get("port", 5000)))
        self.echo = bool(comm.get("log_messages", True))
        self.server = None
        self.client = None
        self.client_name = ""
        self.buffer = protocol.LineBuffer()
        self.queue = deque()
        self.task = None
        self.grip_motors = {}
        self.grip_sensors = {}
        self.grip_closed = False
        self.holding = False
        self.homed = False
        # Cero de cada eje en coordenadas de articulación (m). Antes del homing es la
        # posición de encendido: el "contador" del encoder relativo arranca en 0 ahí.
        self.zero = {axis: 0.0 for axis in AXES}
        self.speed = {}
        self._next_listen_try = 0.0

    # ------------------------------------------------------------------ setup
    def configure(self):
        super().configure()
        self.telemetry_period = 1e9  # la telemetría propia (en coordenadas de máquina) va en _labels
        self.gripper = self.parameters["gripper"]
        self.workcell = self.parameters["workcell"]
        self.homing = self.parameters["homing"]
        for side in ("left", "right"):
            motor = self.getDevice(f"grip_{side}")
            sensor = self.getDevice(f"grip_{side}_sensor")
            if not isinstance(motor, Motor):
                raise RuntimeError(f"Falta grip_{side}: regenerar el PROTO con tools/build_model.py")
            sensor.enable(self.timestep)
            motor.setPosition(0.0)
            self.grip_motors[side], self.grip_sensors[side] = motor, sensor
        self.piece = self.getFromDef("PIEZA")
        if self.piece is None:
            raise RuntimeError("Falta DEF PIEZA: abrir worlds/cartesiana_tcp.wbt")
        self.piece_translation = self.piece.getField("translation")
        self.piece_rotation = self.piece.getField("rotation")
        # Posición inicial de la pieza calculada desde la configuración (no desde el .wbt):
        # si alguien guarda el mundo con la pieza en otro lado, al arrancar vuelve al zócalo.
        self.piece_start = self._piece_home()
        self.piece_translation.setSFVec3f(self.piece_start)
        self.piece_rotation.setSFRotation([0, 0, 1, 0])
        self.sockets = {}
        for name in self.workcell["sockets_mm"]:
            node = self.getFromDef(f"ZOCALO_{name}")
            if node is not None:
                self.sockets[name] = node
        self.speed = {a: self.motors[a].getMaxVelocity() for a in AXES}
        self._power_on()
        self._listen()

    def _power_on(self):
        """Encendido: la máquina quedó donde la dejaron y no sabe dónde está."""
        h = self.homing
        start = {a: 0.0 for a in AXES}
        if h.get("random_start", True):
            rng = random.Random()
            margin = h.get("random_margin", 0.03)
            for a in AXES:
                low, high = self.limits[a]
                if a == "z":  # mitad superior: el grip no arranca metido en un zócalo
                    low = max(low, h.get("random_z_min", 0.0))
                start[a] = rng.uniform(low + margin, high - margin)
            robot = self.getSelf()
            for a in AXES:
                joint = robot.getFromProtoDef(f"JOINT_{a.upper()}")
                if joint is None:
                    raise RuntimeError(f"Falta DEF JOINT_{a.upper()}: regenerar el PROTO")
                joint.setJointPosition(start[a])
            self.move_to(*(start[a] for a in AXES))
            self._step()
        q = self.positions()
        self.zero = dict(q)          # encoder relativo: cuenta 0 donde se encendió
        self.homed = False
        print("[CARTESIANA] Encendida en posición DESCONOCIDA. Enviar HOME para el ciclo de inicialización.",
              flush=True)

    def _piece_home(self):
        """Centro de la pieza apoyada en su zócalo inicial (mismo cálculo que tools/build_model.py)."""
        h, w = self.homing, self.workcell

        def joint(axis, value_mm):
            low, high = self.limits[axis]
            switch = low + h["switch_tolerance"] if h["switch_at"][axis] == "min" else high - h["switch_tolerance"]
            return switch + value_mm / 1000.0
        x_mm, y_mm = w["sockets_mm"][w["piece_start"]]
        q = (joint("x", x_mm), joint("y", y_mm), joint("z", w["pick_z_mm"]))
        tip = [zero + d for zero, d in zip(self.tool_tip_zero, q)]
        return [tip[0], tip[1], tip[2] - self.gripper["grip_center_below_tip"]]

    def _listen(self):
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name != "nt":  # en Windows SO_REUSEADDR permitiría dos servidores en el mismo puerto
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            server.setblocking(False)
            self.server = server
            print(f"[TCP] Servidor escuchando en {self.host}:{self.port}. "
                  f"El programa externo se conecta a 127.0.0.1:{self.port} (o a la IP de esta PC).", flush=True)
        except OSError as error:
            self.server = None
            print(f"[TCP] No se pudo abrir el puerto {self.port}: {error}. "
                  "¿Hay otra simulación abierta? Se reintenta en 3 s.", flush=True)
            self._next_listen_try = self.getTime() + 3.0

    # ------------------------------------------------------- coordenadas de máquina
    def machine(self, q=None):
        """Posición en coordenadas de máquina (m): articulación menos el cero."""
        q = self.positions() if q is None else q
        return {a: q[a] - self.zero[a] for a in AXES}

    def machine_limits(self):
        """Recorrido permitido en coordenadas de máquina. El sensor es el borde: el cero
        queda en un extremo y no se puede ir más allá de él."""
        lim = {}
        for a in AXES:
            low, high = self.limits[a][0] - self.zero[a], self.limits[a][1] - self.zero[a]
            if self.homing["switch_at"][a] == "min":
                low = 0.0
            else:
                high = 0.0
            lim[a] = (low, high)
        return lim

    def switch_active(self, axis, q=None):
        """Sensor de inicio de carrera simulado: se activa al llegar al extremo del eje."""
        q = self.positions()[axis] if q is None else q
        tol = self.homing["switch_tolerance"]
        low, high = self.limits[axis]
        if self.homing["switch_at"][axis] == "min":
            return q <= low + tol
        return q >= high - tol

    # ---------------------------------------------------------------- red
    def _send(self, line):
        if self.echo:
            print(f"[TCP] -> {line}", flush=True)
        if self.client is None:
            return
        try:
            self.client.sendall((line + "\n").encode("ascii", errors="replace"))
        except OSError:
            self._drop_client("error al enviar")

    def _drop_client(self, reason):
        if self.client is not None:
            try:
                self.client.close()
            except OSError:
                pass
            print(f"[TCP] Cliente {self.client_name} desconectado ({reason}).", flush=True)
        self.client = None
        self.buffer = protocol.LineBuffer()
        # Igual que una máquina que pierde el enlace: frena y descarta lo pendiente.
        if self.task is not None or self.queue:
            self._abort_all(reply=False)

    def _poll_network(self):
        if self.server is None:
            if self.getTime() >= self._next_listen_try:
                self._listen()
            return
        try:
            conn, addr = self.server.accept()
            if self.client is None:
                conn.setblocking(False)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.client, self.client_name = conn, f"{addr[0]}:{addr[1]}"
                print(f"[TCP] Cliente conectado desde {self.client_name}", flush=True)
                self._send(f"READY {protocol.DEVICE} {protocol.VERSION} " + ("HOMED" if self.homed else "NOT_HOMED"))
            else:
                conn.sendall(b"ERR BUSY\n")
                conn.close()
        except BlockingIOError:
            pass
        except OSError as error:
            if error.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                print(f"[TCP] Error aceptando conexión: {error}", flush=True)
        if self.client is None:
            return
        while True:
            try:
                chunk = self.client.recv(4096)
            except (BlockingIOError, InterruptedError):
                break
            except OSError as error:
                self._drop_client(str(error))
                return
            if not chunk:
                self._drop_client("cerró la conexión")
                return
            for line in self.buffer.feed(chunk):
                self._handle_line(line)
            if self.client is None:
                return

    def _handle_line(self, line):
        if line == "\x00TOOLONG":
            self._send("ERR TOOLONG")
            return
        try:
            command = protocol.parse(line)
        except protocol.ProtocolError as error:
            if self.echo:
                print(f"[TCP] <- {line.strip()}", flush=True)
            self._send(error.reply)
            return
        if command is None:
            return
        if self.echo:
            print(f"[TCP] <- {command.raw}", flush=True)
        if command.immediate:
            self._run_immediate(command)
        else:
            self.queue.append(Task(command))

    # ------------------------------------------------------- comandos inmediatos
    def _run_immediate(self, command):
        name = command.name
        if name == "PING":
            self._send("PONG")
        elif name == "INFO":
            state = "HOMED" if self.homed else "NOT_HOMED"
            if self.homed:
                lim = self.machine_limits()
                ranges = " ".join(f"{a.upper()}MIN {protocol.mm(lim[a][0])} {a.upper()}MAX {protocol.mm(lim[a][1])}"
                                  for a in AXES)
            else:
                ranges = " ".join(f"{a.upper()}MIN ? {a.upper()}MAX ?" for a in AXES)
            vmax = min(self.motors[a].getMaxVelocity() for a in AXES) * 1000
            self._send(f"INFO {protocol.DEVICE} {protocol.VERSION} {state} {ranges} VMAX {vmax:.1f}")
        elif name == "POS?":
            m = self.machine()
            self._send(protocol.fmt_pos([m[a] for a in AXES], self.grip_closed, self.holding, self.homed))
        elif name == "STATUS?":
            state = "BUSY" if self.task is not None else "IDLE"
            self._send(f"STATUS {state} {len(self.queue)} " + ("HOMED" if self.homed else "NOT_HOMED"))
        elif name == "SWITCH?":
            self._send("SWITCH " + " ".join(f"{a.upper()}{int(self.switch_active(a))}" for a in AXES))
        elif name == "STOP":
            self._abort_all(reply=True)
            self._send("OK STOP")

    def _abort_all(self, reply):
        current = self.positions()
        self.move_to(*(current[a] for a in AXES))
        self._restore_speeds()
        for side in ("left", "right"):
            self.grip_motors[side].setPosition(self.grip_sensors[side].getValue())
        pending = ([self.task] if self.task else []) + list(self.queue)
        if self.task is not None and self.task.command.name == "HOME":
            self.homed = False  # un homing interrumpido deja el cero sin definir
        self.task = None
        self.queue.clear()
        if reply:
            for task in pending:
                self._send(f"ERR ABORTED {task.command.name}")

    def _restore_speeds(self):
        for a in AXES:
            self.motors[a].setVelocity(self.speed[a])

    # ------------------------------------------------------- comandos en cola
    def _start(self, task):
        name, args = task.command.name, task.command.args
        now = self.getTime()
        task.started = now
        task.deadline = now + self.timeout_seconds
        if name == "MOVE":
            if not self.homed:
                self._send("ERR NOT_HOMED (enviar HOME primero)")
                return False
            lim = self.machine_limits()
            margin = 0.002  # hasta 2 mm afuera = error de redondeo/medición: se ajusta al límite
            target = {}
            for axis, value_mm in zip(AXES, args):
                value = value_mm / 1000.0
                low, high = lim[axis]
                if not low - margin <= value <= high + margin:
                    self._send(f"ERR RANGE {axis.upper()} {value_mm:.1f} ({low * 1000:.0f}..{high * 1000:.0f})")
                    return False
                value = min(high, max(low, value))
                target[axis] = value + self.zero[axis]
            self.move_to(*(target[a] for a in AXES))
        elif name == "HOME":
            task.deadline = now + self.homing["timeout_s"]
            task.data.update(order=list(self.homing["order"]), index=0, phase="start")
            self.homed = False
            print("[CARTESIANA] Ciclo de inicialización: X, luego Y, luego Z.", flush=True)
        elif name == "SPEED":
            v = args[0] / 1000.0
            applied = self.set_speed(x=v, y=v, z=v)
            self.speed.update(applied)
            self._send("OK SPEED " + " ".join(f"{a.upper()}{applied[a] * 1000:.1f}" for a in AXES))
            return False
        elif name == "WAIT":
            task.deadline = now + args[0] / 1000.0
        elif name == "GRIP":
            self._start_grip(task, args[0])
        elif name == "RESET":
            self._release_piece(to_start=True)
            for side in ("left", "right"):
                self.grip_motors[side].setPosition(0.0)
            self.grip_closed = False
            self._send("DONE RESET")
            return False
        return True

    def _update(self, task):
        """Devuelve True cuando el comando terminó (y ya respondió)."""
        name = task.command.name
        now = self.getTime()
        if name == "WAIT":
            if now >= task.deadline:
                self._send("DONE WAIT")
                return True
            return False
        if name == "GRIP":
            return self._update_grip(task)
        if name == "HOME":
            return self._update_home(task)
        actual = self.positions()
        reached = all(abs(actual[a] - self.target[a]) <= self.tolerance for a in AXES)
        if reached:
            task.settled_since = now if task.settled_since is None else task.settled_since
            if now - task.settled_since >= self.settle_seconds:
                m = self.machine(actual)
                self._send("DONE MOVE " + " ".join(protocol.mm(m[a]) for a in AXES))
                return True
        else:
            task.settled_since = None
        if now > task.deadline:
            self._send(f"ERR TIMEOUT {name}")
            self._abort_all(reply=True)
            return True
        return False

    # ------------------------------------------------------------ homing
    def _update_home(self, task):
        """Máquina de estados del ciclo de inicialización, un eje por vez.

        Por eje: búsqueda rápida hacia el sensor -> al activarse frena -> se aleja
        unos mm -> vuelve lento -> en el instante en que el sensor se activa, esa
        posición pasa a ser el cero del eje.
        """
        h, d = self.homing, task.data
        if self.getTime() > task.deadline:
            self._send("ERR TIMEOUT HOME")
            self._abort_all(reply=True)
            return True
        axis = d["order"][d["index"]]
        motor = self.motors[axis]
        q = self.positions()
        low, high = self.limits[axis]
        toward = low if h["switch_at"][axis] == "min" else high
        away = 1.0 if h["switch_at"][axis] == "min" else -1.0
        phase = d["phase"]
        if phase == "start":
            print(f"[CARTESIANA] HOME {axis.upper()}: búsqueda rápida del sensor", flush=True)
            if self.switch_active(axis, q[axis]):
                d["phase"] = "backoff_start"   # ya estaba sobre el sensor: primero alejarse
            else:
                motor.setVelocity(min(h["fast_speed"], motor.getMaxVelocity()))
                motor.setPosition(toward)
                self.target[axis] = toward
                d["phase"] = "fast"
        elif phase == "fast":
            if self.switch_active(axis, q[axis]):
                d["phase"] = "backoff_start"
        if d["phase"] == "backoff_start":
            back = q[axis] + away * h["backoff"]
            motor.setVelocity(min(h["fast_speed"], motor.getMaxVelocity()))
            motor.setPosition(back)
            self.target[axis] = back
            d["phase"] = "backoff"
        elif phase == "backoff":
            if abs(q[axis] - self.target[axis]) <= self.tolerance and not self.switch_active(axis, q[axis]):
                motor.setVelocity(h["slow_speed"])
                motor.setPosition(toward)
                self.target[axis] = toward
                d["phase"] = "slow"
        elif phase == "slow":
            if self.switch_active(axis, q[axis]):
                # Flanco del sensor: este es el cero del eje. Frenar ahí.
                self.zero[axis] = q[axis]
                motor.setPosition(q[axis])
                self.target[axis] = q[axis]
                motor.setVelocity(self.speed[axis])
                print(f"[CARTESIANA] HOME {axis.upper()}: sensor activado, cero definido", flush=True)
                d["index"] += 1
                d["phase"] = "start"
                if d["index"] == len(d["order"]):
                    self.homed = True
                    self._restore_speeds()
                    print("[CARTESIANA] Inicializada en (0, 0, 0). Lista para recibir movimientos.", flush=True)
                    self._send("DONE HOME")
                    return True
        return False

    # ------------------------------------------------------------ grip
    def _grip_point(self):
        tip = self.nodes["TOOL_TIP"].getPosition()
        return [tip[0], tip[1], tip[2] - self.gripper["grip_center_below_tip"]]

    def _piece_in_reach(self):
        g, p = self._grip_point(), self.piece_translation.getSFVec3f()
        return (math.hypot(g[0] - p[0], g[1] - p[1]) <= self.gripper["piece_tolerance_xy"]
                and abs(g[2] - p[2]) <= self.gripper["piece_tolerance_z"])

    def _start_grip(self, task, action):
        g = self.gripper
        if action == "CLOSE":
            catch = (not self.holding) and self._piece_in_reach()
            # Dedo de ancho w a open_x del centro: toca la pieza al recorrer open_x - s/2 - w/2.
            contact = g["finger_open_x"] - g["piece_size"] / 2 - g["finger_size"][0] / 2
            target = contact if (catch or self.holding) else g["travel"]
            task.data.update(target=target, catch=catch)
        else:
            target = 0.0
            task.data.update(target=target)
        task.deadline = self.getTime() + 4.0
        for side in ("left", "right"):
            self.grip_motors[side].setPosition(target)

    def _update_grip(self, task):
        target = task.data["target"]
        done = all(abs(self.grip_sensors[s].getValue() - target) <= 0.0008 for s in ("left", "right"))
        if task.command.args[0] == "CLOSE":
            if done:
                if task.data["catch"]:
                    self.holding = True
                self.grip_closed = True
                self._send("DONE GRIP CLOSE " + ("HELD" if self.holding else "EMPTY"))
                return True
        else:
            if self.holding and self.grip_sensors["left"].getValue() < target + 0.004:
                task.data["place"] = self._release_piece()
            if done:
                self.grip_closed = False
                place = task.data.get("place")
                self._send("DONE GRIP OPEN" + (f" {place}" if place else ""))
                return True
        if self.getTime() > task.deadline:
            self._send("ERR TIMEOUT GRIP")
            return True
        return False

    def _follow_piece(self):
        if self.holding:
            self.piece_translation.setSFVec3f(self._grip_point())
            self.piece_rotation.setSFRotation([0, 0, 1, 0])

    def _release_piece(self, to_start=False):
        """Soltar la pieza y apoyarla. Devuelve dónde quedó."""
        self.holding = False
        size = self.gripper["piece_size"]
        if to_start:
            self.piece_translation.setSFVec3f(self.piece_start)
            self.piece_rotation.setSFRotation([0, 0, 1, 0])
            return "ZOCALO_" + self.workcell["piece_start"]
        p = list(self.piece_translation.getSFVec3f())
        plate = self.workcell["socket_plate"]
        for name, node in self.sockets.items():
            base = node.getPosition()
            top = self.piece_start[2] - size / 2  # todos los zócalos tienen la misma altura
            if (abs(p[0] - base[0]) <= plate[0] / 2 and abs(p[1] - base[1]) <= plate[1] / 2
                    and -0.002 <= p[2] - size / 2 - top <= 0.03):
                self.piece_translation.setSFVec3f([base[0], base[1], top + size / 2])
                return f"ZOCALO_{name}"
        self.piece_translation.setSFVec3f([p[0], p[1], self.table_surface_z + size / 2])
        return "MESA"

    # ------------------------------------------------------------ bucle
    def _labels(self):
        m = self.machine()
        state = f"cliente {self.client_name}" if self.client else f"esperando conexión en :{self.port}"
        busy = self.task.command.raw if self.task else "libre"
        home = "INICIALIZADA" if self.homed else "SIN INICIALIZAR (enviar HOME)"
        pos = " | ".join(f"{a.upper()} {m[a] * 1000:+7.1f} mm" for a in AXES)
        sw = " ".join(f"{a.upper()}{'*' if self.switch_active(a) else '-'}" for a in AXES)
        self.setLabel(0, f"CARTESIANA: {home}", 0.02, 0.02, 0.06, 0x7CFC7C if self.homed else 0xFF8A80)
        self.setLabel(1, f"{pos}   sensores {sw}", 0.02, 0.075, 0.055, 0xC7EDFF)
        self.setLabel(2, f"TCP: {state} | {busy}", 0.02, 0.13, 0.055, 0xFFE08A)

    def serve(self):
        print("[CARTESIANA] Gemelo digital listo. Esperando comandos del programa externo.", flush=True)
        label_time = -1.0
        while True:
            self._step()
            self._poll_network()
            if self.task is None and self.queue:
                self.task = self.queue.popleft()
                if not self._start(self.task):
                    self.task = None
            if self.task is not None and self._update(self.task):
                self.task = None
            self._follow_piece()
            if self.getTime() - label_time >= 0.25:
                label_time = self.getTime()
                self._labels()

    def run(self):
        try:
            self.configure()
            self.serve()
        except SimulationEnded:
            print("[CARTESIANA] Simulación finalizada.", flush=True)
        except Exception:
            traceback.print_exc()
            raise
        finally:
            for sock in (self.client, self.server):
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass


if __name__ == "__main__":
    CartesianaTCP().run()
