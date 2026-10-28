"""Enlace TCP/IP con la CARTESIANA.

La máquina tiene a bordo una PC industrial que escucha por TCP/IP. En la
simulación, ese papel lo cumple el controlador de Webots (servidor en el puerto
5000). Este módulo es el CLIENTE: abre un socket TCP, envía comandos de texto
(una línea por comando) y espera la respuesta de cada uno.
"""

import queue
import socket
import threading
import time

# Palabras con las que empieza una respuesta del controlador (ver protocolo).
REPLY_WORDS = ("PONG", "INFO", "POS", "STATUS", "SWITCH", "OK", "DONE", "ERR")


class Enlace:
    """Abre la conexión, lee líneas en un hilo y permite enviar comando-respuesta."""

    def __init__(self, on_line=None):
        self.on_line = on_line or (lambda direction, text: None)
        self._sock = None
        self._replies = queue.Queue()
        self._reader = None
        self._alive = False
        self._send_lock = threading.Lock()
        self._cmd_lock = threading.Lock()
        self.descripcion = ""

    # ------------------------------------------------------------ apertura
    def abrir(self, host, puerto):
        """Conecta como cliente TCP al servidor de la máquina (host:puerto)."""
        sock = socket.create_connection((host, int(puerto)), timeout=5)
        sock.settimeout(0.1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock = sock
        self.descripcion = f"{host}:{puerto}"
        self._replies = queue.Queue()
        self._alive = True
        self._reader = threading.Thread(target=self._leer, daemon=True)
        self._reader.start()

    @property
    def abierto(self):
        return self._alive

    def cerrar(self):
        self._alive = False
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    # ------------------------------------------------------------ lectura
    def _leer(self):
        """Hilo lector: arma líneas con los bytes que llegan por el socket."""
        buffer = b""
        while self._alive:
            try:
                data = self._sock.recv(4096)
            except socket.timeout:
                continue
            except OSError as error:
                if self._alive:
                    self.on_line("!", f"Conexión perdida: {error}")
                    self._alive = False
                    self._replies.put(None)
                break
            if not data:
                if self._alive:
                    self.on_line("!", "La máquina cerró la conexión")
                    self._alive = False
                    self._replies.put(None)
                break
            buffer += data
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                line = raw.decode("ascii", errors="replace").strip()
                if not line:
                    continue
                self.on_line("<", line)
                # "OK STOP" y el saludo READY no son la respuesta del comando en curso.
                if line.startswith(REPLY_WORDS) and not line.startswith("OK STOP"):
                    self._replies.put(line)

    # ------------------------------------------------------------ escritura
    def enviar(self, line):
        """Envía una línea sin esperar respuesta (lo usa STOP)."""
        if not self._alive:
            raise ConnectionError("no hay conexión")
        with self._send_lock:
            self._sock.sendall((line + "\n").encode("ascii"))
        self.on_line(">", line)

    def comando(self, line, timeout=150.0):
        """Envía un comando y espera SU respuesta (una línea). Lanza TimeoutError."""
        with self._cmd_lock:
            while not self._replies.empty():  # descartar respuestas viejas
                self._replies.get_nowait()
            self.enviar(line)
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"sin respuesta a '{line}'")
                try:
                    reply = self._replies.get(timeout=remaining)
                except queue.Empty:
                    raise TimeoutError(f"sin respuesta a '{line}'") from None
                if reply is None:
                    raise ConnectionError("conexión perdida")
                return reply
