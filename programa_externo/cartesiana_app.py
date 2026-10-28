"""CARTESIANA - programa externo: registra puntos de una trayectoria y la ejecuta.

La máquina tiene a bordo una PC industrial que escucha por TCP/IP. Este programa
es el CLIENTE TCP: se conecta a IP:puerto (127.0.0.1:5000 si Webots corre en la
misma PC) y envía comandos de texto del protocolo CARTESIANA.

Flujo de uso, como el panel de la máquina real:
  1. Conectar.  2. Inicializar (HOME: busca los sensores de inicio de carrera).
  3. Mover a mano y "Guardar punto actual".  4. Ejecutar la trayectoria.

Ejecutar:  python cartesiana_app.py      (solo usa la biblioteca estándar de Python)
"""

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from enlace import Enlace

APP = "CARTESIANA - Trayectorias"
HERE = Path(__file__).resolve().parent
TRAJ_DIR = HERE / "trayectorias"
GRIP_TEXT = {"": "—", "OPEN": "Abrir", "CLOSE": "Cerrar"}
GRIP_CODE = {v: k for k, v in GRIP_TEXT.items()}


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.enlace = Enlace(on_line=self._linea_desde_hilo)
        self.ui_queue = queue.Queue()          # mensajes de los hilos hacia la interfaz
        self.jobs = queue.Queue()              # trabajos para el hilo que habla con la máquina
        self.cancel = threading.Event()
        self.busy = False
        self.pos = [0.0, 0.0, 0.0]
        self.grip_closed = False
        self.limits = {"X": (0, 500), "Y": (0, 400), "Z": (-180, 0)}
        self.homed = False
        self.puntos = []
        self.archivo = None
        threading.Thread(target=self._worker, daemon=True).start()
        self._construir()
        self.after(50, self._atender_ui)
        self.protocol("WM_DELETE_WINDOW", self._salir)

    # ================================================================ interfaz
    def _construir(self):
        pad = {"padx": 6, "pady": 4}
        top = ttk.LabelFrame(self, text="Conexión")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Máquina (TCP/IP)  IP").grid(row=0, column=5, padx=(6, 4))
        self.ent_host = ttk.Entry(top, width=14)
        self.ent_host.insert(0, "127.0.0.1")
        self.ent_host.grid(row=0, column=6)
        ttk.Label(top, text=":").grid(row=0, column=7)
        self.ent_port = ttk.Entry(top, width=6)
        self.ent_port.insert(0, "5000")
        self.ent_port.grid(row=0, column=8)
        self.btn_con = ttk.Button(top, text="Conectar", command=self._conectar)
        self.btn_con.grid(row=0, column=9, padx=10)
        self.lbl_estado = ttk.Label(top, text="Desconectado", foreground="#b00")
        self.lbl_estado.grid(row=0, column=10, sticky="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", **pad)

        # ---- posición
        fpos = ttk.LabelFrame(left, text="Posición actual (mm de máquina)")
        fpos.pack(fill="x", pady=4)
        self.lbl_pos = ttk.Label(fpos, text="X —   Y —   Z —", font=("Consolas", 13, "bold"))
        self.lbl_pos.pack(padx=6, pady=4)
        self.lbl_grip = ttk.Label(fpos, text="Pinza: —")
        self.lbl_grip.pack(pady=(0, 4))

        # ---- inicialización (homing)
        fhome = ttk.LabelFrame(left, text="Inicialización")
        fhome.pack(fill="x", pady=4)
        self.lbl_home = tk.Label(fhome, text="SIN INICIALIZAR", fg="white", bg="#c62828", font=("Segoe UI", 10, "bold"))
        self.lbl_home.pack(fill="x", padx=4, pady=(4, 2))
        ttk.Button(fhome, text="Inicializar (buscar sensores X, Y, Z)", command=self._inicializar).pack(fill="x", padx=4, pady=(2, 4))

        # ---- jog
        fjog = ttk.LabelFrame(left, text="Mover manualmente")
        fjog.pack(fill="x", pady=4)
        ttk.Label(fjog, text="Paso (mm)").grid(row=0, column=0, columnspan=2)
        self.paso = ttk.Combobox(fjog, width=6, values=["1", "5", "10", "25", "50"])
        self.paso.set("10")
        self.paso.grid(row=0, column=2, columnspan=2, pady=2)
        for row, axis in enumerate("XYZ", start=1):
            ttk.Button(fjog, text=f"{axis} −", width=6, command=lambda a=axis: self._jog(a, -1)).grid(row=row, column=0, columnspan=2, pady=2)
            ttk.Button(fjog, text=f"{axis} +", width=6, command=lambda a=axis: self._jog(a, +1)).grid(row=row, column=2, columnspan=2, pady=2)
        ttk.Button(fjog, text="Ir al cero (0, 0, 0)", command=lambda: self._encolar_cmd("MOVE 0 0 0")).grid(row=4, column=0, columnspan=4, sticky="ew", pady=4)
        fir = ttk.Frame(fjog)
        fir.grid(row=5, column=0, columnspan=4, pady=2)
        self.ent_xyz = []
        for i, axis in enumerate("XYZ"):
            ttk.Label(fir, text=axis).grid(row=0, column=2 * i)
            e = ttk.Entry(fir, width=6)
            e.insert(0, "0")
            e.grid(row=0, column=2 * i + 1)
            self.ent_xyz.append(e)
        ttk.Button(fjog, text="Ir a X Y Z", command=self._ir_a).grid(row=6, column=0, columnspan=4, sticky="ew")

        fsp = ttk.Frame(fjog)
        fsp.grid(row=7, column=0, columnspan=4, pady=4)
        ttk.Label(fsp, text="Velocidad mm/s").pack(side="left")
        self.ent_vel = ttk.Entry(fsp, width=5)
        self.ent_vel.insert(0, "40")
        self.ent_vel.pack(side="left", padx=3)
        ttk.Button(fsp, text="Aplicar", command=lambda: self._encolar_cmd(f"SPEED {self.ent_vel.get()}")).pack(side="left")

        # ---- pinza
        fg = ttk.LabelFrame(left, text="Pinza (grip)")
        fg.pack(fill="x", pady=4)
        ttk.Button(fg, text="Abrir", command=lambda: self._encolar_cmd("GRIP OPEN")).pack(side="left", expand=True, fill="x", padx=3, pady=4)
        ttk.Button(fg, text="Cerrar", command=lambda: self._encolar_cmd("GRIP CLOSE")).pack(side="left", expand=True, fill="x", padx=3, pady=4)

        self.btn_stop = tk.Button(left, text="STOP", bg="#c62828", fg="white", font=("Segoe UI", 12, "bold"),
                                  command=self._stop)
        self.btn_stop.pack(fill="x", pady=8)

        # ---- trayectoria
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, **pad)
        ftr = ttk.LabelFrame(right, text="Trayectoria")
        ftr.pack(fill="both", expand=True)
        cols = ("n", "x", "y", "z", "pinza", "espera")
        self.tree = ttk.Treeview(ftr, columns=cols, show="headings", height=10, selectmode="browse")
        for col, text, width in zip(cols, ("#", "X mm", "Y mm", "Z mm", "Pinza al llegar", "Espera ms"),
                                    (40, 80, 80, 80, 120, 90)):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        sb = ttk.Scrollbar(ftr, orient="vertical", command=self.tree.yview)
        sb.pack(side="left", fill="y", pady=4)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._editar_punto())

        btns = ttk.Frame(ftr)
        btns.pack(side="left", fill="y", padx=4, pady=4)
        for text, cmd in (("Guardar punto actual", self._guardar_punto),
                          ("Editar punto…", self._editar_punto),
                          ("Ir al punto", self._ir_al_punto),
                          ("Subir", lambda: self._mover_punto(-1)),
                          ("Bajar", lambda: self._mover_punto(+1)),
                          ("Borrar", self._borrar_punto),
                          ("Borrar todo", self._borrar_todo),
                          (None, None),
                          ("Abrir archivo…", self._abrir),
                          ("Guardar archivo…", self._guardar)):
            if text is None:
                ttk.Separator(btns).pack(fill="x", pady=6)
                continue
            ttk.Button(btns, text=text, command=cmd).pack(fill="x", pady=2)

        fex = ttk.Frame(right)
        fex.pack(fill="x", pady=4)
        self.btn_run = ttk.Button(fex, text="Ejecutar trayectoria", command=self._ejecutar)
        self.btn_run.pack(side="left")
        self.repetir = tk.BooleanVar(value=False)
        ttk.Checkbutton(fex, text="Repetir en ciclo", variable=self.repetir).pack(side="left", padx=10)
        self.lbl_prog = ttk.Label(fex, text="")
        self.lbl_prog.pack(side="left", padx=10)

        flog = ttk.LabelFrame(right, text="Mensajes del protocolo  (>> enviado   << recibido)")
        flog.pack(fill="both", expand=True)
        self.txt_log = tk.Text(flog, height=10, font=("Consolas", 9), state="disabled", wrap="none")
        self.txt_log.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        sb2 = ttk.Scrollbar(flog, orient="vertical", command=self.txt_log.yview)
        sb2.pack(side="left", fill="y", pady=4)
        self.txt_log.configure(yscrollcommand=sb2.set)
        self.txt_log.tag_configure("out", foreground="#1565c0")
        self.txt_log.tag_configure("err", foreground="#c62828")

        fcmd = ttk.Frame(right)
        fcmd.pack(fill="x")
        ttk.Label(fcmd, text="Comando manual:").pack(side="left")
        self.ent_cmd = ttk.Entry(fcmd)
        self.ent_cmd.pack(side="left", fill="x", expand=True, padx=4)
        self.ent_cmd.bind("<Return>", lambda e: self._cmd_manual())
        ttk.Button(fcmd, text="Enviar", command=self._cmd_manual).pack(side="left")

    # ================================================================ hilos
    def _linea_desde_hilo(self, direction, text):
        self.ui_queue.put(("log", direction, text))

    def _post(self, *msg):
        self.ui_queue.put(msg)

    def _worker(self):
        """Único hilo que conversa con la máquina: un comando, una respuesta."""
        while True:
            job = self.jobs.get()
            try:
                job()
            except Exception as error:
                self._post("error", str(error))
            finally:
                self._post("idle")

    def _encolar(self, job):
        if not self.enlace.abierto:
            messagebox.showwarning(APP, "Primero conectá con la máquina.")
            return False
        if self.busy:
            self._post("log", "!", "Ocupado: esperá a que termine o presioná STOP.")
            return False
        self.busy = True
        self.cancel.clear()
        self.jobs.put(job)
        return True

    def _cmd(self, line):
        """Ejecutar en el hilo de trabajo: envía, espera y procesa la respuesta."""
        reply = self.enlace.comando(line)
        self._procesar(reply)
        if reply.startswith("ERR"):
            raise RuntimeError(f"{line}  →  {reply}")
        return reply

    def _procesar(self, reply):
        parts = reply.split()
        if parts[0] == "POS" and len(parts) >= 6:
            self.pos = [float(v) for v in parts[1:4]]
            self.grip_closed = parts[4] == "CLOSED"
            if len(parts) >= 7:
                self._homed(parts[6] == "HOMED")
            self._post("pos", parts[5] == "HELD")
        elif parts[:2] == ["DONE", "MOVE"] and len(parts) == 5:
            self.pos = [float(v) for v in parts[2:5]]
            self._post("pos", None)
        elif parts[:2] == ["DONE", "HOME"]:
            self.pos = [0.0, 0.0, 0.0]
            self._homed(True)
            self._post("pos", None)
        elif parts[:2] == ["DONE", "RESET"]:
            self.grip_closed = False
            self._post("pos", False)
        elif parts[:2] == ["ERR", "NOT_HOMED"]:
            self._homed(False)
        elif parts[:2] == ["DONE", "GRIP"]:
            self.grip_closed = parts[2] == "CLOSE"
            self._post("pos", parts[3] == "HELD" if len(parts) > 3 and self.grip_closed else False)
        elif parts[0] == "INFO":
            self._homed(len(parts) > 3 and parts[3] == "HOMED")
            values = dict(zip(parts[4::2], parts[5::2]))
            for axis in "XYZ":
                try:
                    self.limits[axis] = (float(values[axis + "MIN"]), float(values[axis + "MAX"]))
                except (KeyError, ValueError):
                    pass

    def _encolar_cmd(self, line):
        if line.upper().startswith("MOVE") and not self._listo_para_mover():
            return
        self._encolar(lambda: self._cmd(line))

    def _homed(self, value):
        """Lo llama el hilo de trabajo: actualiza el estado de inicialización."""
        self.homed = value
        self._post("home", value)

    def _listo_para_mover(self):
        if self.enlace.abierto and not self.homed:
            messagebox.showinfo(APP, "La máquina no está inicializada: no sabe dónde está.\n"
                                     "Presioná «Inicializar» para que busque los sensores de inicio de carrera.")
            return False
        return True

    def _inicializar(self):
        def homing():
            self._post("prog", "Inicializando: buscando sensor X, luego Y, luego Z…")
            self._cmd("HOME")
            self._cmd("INFO")   # ahora sí informa el recorrido real de cada eje
            self._cmd("POS?")
            self._post("prog", "Máquina inicializada en (0, 0, 0)")
        self._encolar(homing)

    # ================================================================ conexión
    def _conectar(self):
        if self.enlace.abierto:
            self.enlace.cerrar()
            self._estado(False)
            return
        try:
            self.enlace.abrir(self.ent_host.get().strip(), int(self.ent_port.get()))
        except Exception as error:
            messagebox.showerror(APP, f"No se pudo conectar:\n{error}")
            return
        self._estado(True)

        def saludo():
            self._cmd("PING")
            self._cmd("INFO")
            self._cmd(f"SPEED {self.ent_vel.get()}")
            self._cmd("POS?")
        self._encolar(saludo)

    def _estado(self, conectado):
        if conectado:
            self.lbl_estado.config(text=f"Conectado: {self.enlace.descripcion}", foreground="#1b5e20")
            self.btn_con.config(text="Desconectar")
        else:
            self.lbl_estado.config(text="Desconectado", foreground="#b00")
            self.btn_con.config(text="Conectar")

    # ================================================================ acciones
    def _jog(self, axis, sign):
        try:
            step = float(self.paso.get())
        except ValueError:
            return
        target = list(self.pos)
        target["XYZ".index(axis)] += sign * step
        # Los tres ejes dentro del recorrido (la posición medida puede pasarse unas décimas).
        target = [max(self.limits[a][0], min(self.limits[a][1], v)) for a, v in zip("XYZ", target)]
        self._encolar_cmd("MOVE " + " ".join(f"{v:.1f}" for v in target))

    def _ir_a(self):
        try:
            values = [float(e.get().replace(",", ".")) for e in self.ent_xyz]
        except ValueError:
            messagebox.showwarning(APP, "X, Y y Z deben ser números (mm).")
            return
        self._encolar_cmd("MOVE " + " ".join(f"{v:.1f}" for v in values))

    def _stop(self):
        self.cancel.set()
        if self.enlace.abierto:
            try:
                self.enlace.enviar("STOP")
            except Exception as error:
                self._post("error", str(error))

    def _cmd_manual(self):
        line = self.ent_cmd.get().strip()
        if not line:
            return
        if line.upper() == "STOP":
            self._stop()
        else:
            self._encolar_cmd(line)
        self.ent_cmd.delete(0, "end")

    # ================================================================ trayectoria
    def _redibujar(self, select=None):
        self.tree.delete(*self.tree.get_children())
        for n, p in enumerate(self.puntos, start=1):
            self.tree.insert("", "end", iid=str(n - 1), values=(
                n, f"{p['x']:.1f}", f"{p['y']:.1f}", f"{p['z']:.1f}", GRIP_TEXT[p.get("pinza", "")], p.get("espera_ms", 0)))
        if select is not None and 0 <= select < len(self.puntos):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))

    def _seleccion(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _guardar_punto(self):
        if not self.homed:
            messagebox.showinfo(APP, "Primero inicializá la máquina: sin el cero de los sensores, los puntos no tienen sentido.")
            return
        punto = {"x": self.pos[0], "y": self.pos[1], "z": self.pos[2], "pinza": "", "espera_ms": 0}
        index = self._seleccion()
        index = len(self.puntos) if index is None else index + 1
        self.puntos.insert(index, punto)
        self._redibujar(index)
        self._editar_punto(index)

    def _editar_punto(self, index=None):
        index = self._seleccion() if index is None else index
        if index is None:
            return
        p = self.puntos[index]
        win = tk.Toplevel(self)
        win.title(f"Punto {index + 1}")
        win.transient(self)
        win.resizable(False, False)
        entries = {}
        for row, (key, label) in enumerate((("x", "X mm"), ("y", "Y mm"), ("z", "Z mm"), ("espera_ms", "Espera al llegar (ms)"))):
            ttk.Label(win, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=3)
            e = ttk.Entry(win, width=10)
            e.insert(0, f"{p[key]:.1f}" if key != "espera_ms" else str(p[key]))
            e.grid(row=row, column=1, padx=6, pady=3)
            entries[key] = e
        ttk.Label(win, text="Pinza al llegar").grid(row=4, column=0, sticky="e", padx=6, pady=3)
        cmb = ttk.Combobox(win, width=8, state="readonly", values=list(GRIP_TEXT.values()))
        cmb.set(GRIP_TEXT[p.get("pinza", "")])
        cmb.grid(row=4, column=1, padx=6, pady=3)

        def aceptar():
            try:
                for key in ("x", "y", "z"):
                    p[key] = float(entries[key].get().replace(",", "."))
                p["espera_ms"] = int(float(entries["espera_ms"].get()))
            except ValueError:
                messagebox.showwarning(APP, "Valores numéricos inválidos.", parent=win)
                return
            p["pinza"] = GRIP_CODE[cmb.get()]
            self._redibujar(index)
            win.destroy()
        ttk.Button(win, text="Aceptar", command=aceptar).grid(row=5, column=0, columnspan=2, pady=6)
        win.bind("<Return>", lambda e: aceptar())
        win.grab_set()

    def _ir_al_punto(self):
        index = self._seleccion()
        if index is not None:
            p = self.puntos[index]
            self._encolar_cmd(f"MOVE {p['x']:.1f} {p['y']:.1f} {p['z']:.1f}")

    def _mover_punto(self, delta):
        index = self._seleccion()
        if index is None or not 0 <= index + delta < len(self.puntos):
            return
        self.puntos[index], self.puntos[index + delta] = self.puntos[index + delta], self.puntos[index]
        self._redibujar(index + delta)

    def _borrar_punto(self):
        index = self._seleccion()
        if index is not None:
            del self.puntos[index]
            self._redibujar(min(index, len(self.puntos) - 1))

    def _borrar_todo(self):
        if self.puntos and messagebox.askyesno(APP, "¿Borrar todos los puntos?"):
            self.puntos.clear()
            self._redibujar()

    def _abrir(self):
        path = filedialog.askopenfilename(initialdir=TRAJ_DIR, filetypes=[("Trayectoria", "*.json")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.puntos = [{"x": float(p["x"]), "y": float(p["y"]), "z": float(p["z"]),
                            "pinza": p.get("pinza", "").upper(), "espera_ms": int(p.get("espera_ms", 0))}
                           for p in data["puntos"]]
            if "velocidad_mm_s" in data:
                self.ent_vel.delete(0, "end")
                self.ent_vel.insert(0, str(data["velocidad_mm_s"]))
        except Exception as error:
            messagebox.showerror(APP, f"Archivo inválido:\n{error}")
            return
        self.archivo = path
        self.title(f"{APP} - {Path(path).name}")
        self._redibujar(0)

    def _guardar(self):
        path = filedialog.asksaveasfilename(initialdir=TRAJ_DIR, defaultextension=".json",
                                            initialfile=Path(self.archivo).name if self.archivo else "trayectoria.json",
                                            filetypes=[("Trayectoria", "*.json")])
        if not path:
            return
        data = {"formato": "CARTESIANA trayectoria v1", "unidad": "mm desde home",
                "velocidad_mm_s": float(self.ent_vel.get() or 40), "puntos": self.puntos}
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.archivo = path
        self.title(f"{APP} - {Path(path).name}")

    def _ejecutar(self):
        if not self._listo_para_mover():
            return
        if not self.puntos:
            messagebox.showinfo(APP, "La trayectoria está vacía. Guardá puntos primero.")
            return
        puntos = [dict(p) for p in self.puntos]
        vel = self.ent_vel.get()

        def correr():
            self._cmd(f"SPEED {vel}")
            vuelta = 0
            while True:
                vuelta += 1
                for n, p in enumerate(puntos):
                    if self.cancel.is_set():
                        self._post("prog", "Detenida por el usuario")
                        return
                    self._post("prog", f"Vuelta {vuelta} · punto {n + 1}/{len(puntos)}", n)
                    self._cmd(f"MOVE {p['x']:.1f} {p['y']:.1f} {p['z']:.1f}")
                    if p.get("pinza"):
                        self._cmd(f"GRIP {p['pinza']}")
                    if p.get("espera_ms"):
                        self._cmd(f"WAIT {p['espera_ms']}")
                if not self.repetir.get():
                    break
            self._post("prog", f"Trayectoria completa ({len(puntos)} puntos)")
        self._encolar(correr)

    # ================================================================ bucle UI
    def _atender_ui(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                kind = msg[0]
                if kind == "log":
                    self._log(msg[1], msg[2])
                elif kind == "pos":
                    x, y, z = self.pos
                    self.lbl_pos.config(text=f"X {x:7.1f}   Y {y:7.1f}   Z {z:7.1f}")
                    if msg[1] is not None:
                        self.lbl_grip.config(text="Pinza: " + ("cerrada" if self.grip_closed else "abierta") +
                                                  (" · con pieza" if msg[1] else ""))
                    for e, v in zip(self.ent_xyz, self.pos):
                        e.delete(0, "end")
                        e.insert(0, f"{v:.1f}")
                elif kind == "home":
                    if msg[1]:
                        self.lbl_home.config(text="INICIALIZADA (cero en los sensores)", bg="#2e7d32")
                    else:
                        self.lbl_home.config(text="SIN INICIALIZAR", bg="#c62828")
                elif kind == "prog":
                    self.lbl_prog.config(text=msg[1])
                    if len(msg) > 2:
                        self.tree.selection_set(str(msg[2]))
                        self.tree.see(str(msg[2]))
                elif kind == "error":
                    self._log("!", msg[1])
                    if not self.enlace.abierto:
                        self._estado(False)
                elif kind == "idle":
                    self.busy = False
        except queue.Empty:
            pass
        if not self.enlace.abierto and self.btn_con.cget("text") == "Desconectar":
            self._estado(False)
        self.after(50, self._atender_ui)

    def _log(self, direction, text):
        prefix = {">": ">> ", "<": "<< ", "!": "!! "}.get(direction, "")
        tag = "out" if direction == ">" else "err" if (direction == "!" or text.startswith("ERR")) else None
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", prefix + text + "\n", tag)
        lines = int(self.txt_log.index("end-1c").split(".")[0])
        if lines > 1000:
            self.txt_log.delete("1.0", f"{lines - 1000}.0")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _salir(self):
        self.cancel.set()
        self.enlace.cerrar()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
