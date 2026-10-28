"""Control XYZ en metros y validación ejecutable del cartesiano de Webots.

Las posiciones son desplazamientos de las articulaciones desde el montaje cero.
La posición global de la punta es ``tool_tip_zero + (x, y, z)`` en ENU.
Los recorridos de config/robot_parameters.json son PROVISIONALES, no medidos.
"""

from datetime import datetime, timezone
from itertools import product
import json
import math
import os
from pathlib import Path
import traceback

from controller import Motor, PositionSensor, Supervisor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARAMETERS_PATH = PROJECT_ROOT / "config" / "robot_parameters.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "validation_report.json"
SCREENSHOT_PATH = PROJECT_ROOT / "docs" / "validation.jpg"
AXES = ("x", "y", "z")
NODE_NAMES = ("FIXED_Y", "Y_CARRIAGE", "X_MODULE", "X_CARRIAGE", "Z_MODULE", "Z_CARRIAGE", "TOOL", "TOOL_TIP")


class SimulationEnded(RuntimeError):
    """El usuario detuvo o cerró la simulación durante un movimiento."""


def finite_number(value, name):
    """Rechazar NaN/infinito antes de transmitir cualquier comando al motor."""
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} debe ser un número finito") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} debe ser un número finito")
    return result


def max_difference(first, second):
    return max(abs(a - b) for a, b in zip(first, second))


class CartesianController(Supervisor):
    """Tres motores de posición con límites, velocidades y espera por sensores."""

    def __init__(self):
        super().__init__()
        self.validation_mode = os.environ.get("CARTESIAN_VALIDATE", "0") == "1"
        self.timestep = int(round(self.getBasicTimeStep()))
        self.target = {axis: 0.0 for axis in AXES}
        self.motors = {}
        self.sensors = {}
        self.nodes = {}
        self._last_telemetry = -math.inf
        self._reference = None
        self._snapshots = []
        self._checks = []
        self._phase = "startup"
        self._metrics = {
            "maximum_sensor_limit_excess_m": 0.0,
            "maximum_fixed_drift_m": 0.0,
            "maximum_orientation_difference": 0.0,
            "maximum_tip_kinematic_error_m": 0.0,
            "minimum_tool_clearance_m": math.inf,
        }
        self.parameters = {}

    def configure(self):
        """Cargar parámetros y comprobar su coincidencia con el PROTO generado."""
        self.parameters = json.loads(PARAMETERS_PATH.read_text(encoding="utf-8"))
        self.limits = {}
        for axis in AXES:
            limits = self.parameters["limits"][axis]
            minimum = finite_number(limits["min"], f"{axis}_min")
            maximum = finite_number(limits["max"], f"{axis}_max")
            if not minimum < 0.0 < maximum:
                raise ValueError(f"Límites inválidos para {axis}: deben contener home=0")
            self.limits[axis] = (minimum, maximum)
            motor = self.getDevice(f"motor_{axis}")
            sensor = self.getDevice(f"sensor_{axis}")
            if not isinstance(motor, Motor) or motor.getType() != Motor.LINEAR:
                raise RuntimeError(f"Falta el LinearMotor motor_{axis}")
            if not isinstance(sensor, PositionSensor) or sensor.getType() != PositionSensor.LINEAR:
                raise RuntimeError(f"Falta el PositionSensor lineal sensor_{axis}")
            actual = (motor.getMinPosition(), motor.getMaxPosition())
            if max_difference(actual, self.limits[axis]) > 1e-9:
                raise RuntimeError(
                    f"Límites de motor_{axis} {actual} distintos de JSON {self.limits[axis]}. "
                    "Regenerar el PROTO desde config/robot_parameters.json."
                )
            attached_sensor = motor.getPositionSensor()
            if attached_sensor is None or attached_sensor.getName() != f"sensor_{axis}":
                raise RuntimeError(f"motor_{axis} no tiene sensor_{axis} en el mismo joint")
            sensor.enable(self.timestep)
            self.motors[axis] = motor
            self.sensors[axis] = sensor

        for name in ("tolerance", "settle_seconds", "telemetry_period", "timeout_seconds", "acceleration"):
            value = finite_number(self.parameters[name], name)
            if value <= 0.0:
                raise ValueError(f"{name} debe ser positivo")
            setattr(self, name, value)
        if self.timestep <= 0:
            raise RuntimeError("basicTimeStep debe ser positivo")
        self.tool_tip_zero = [finite_number(v, "tool_tip_zero") for v in self.parameters["tool_tip_zero"]]
        if len(self.tool_tip_zero) != 3:
            raise ValueError("tool_tip_zero debe contener tres coordenadas ENU")
        validation = self.parameters.get("validation", {})
        self.kinematic_tolerance = finite_number(validation.get("kinematic_tolerance", 0.003), "kinematic_tolerance")
        self.orientation_tolerance = finite_number(validation.get("orientation_tolerance", 0.003), "orientation_tolerance")
        self.stability_tolerance = finite_number(validation.get("stability_tolerance", 0.0015), "stability_tolerance")
        self.table_surface_z = finite_number(validation.get("table_surface_z", self.parameters.get("table_surface_z", 0.86)), "table_surface_z")
        self.tool_margin = finite_number(validation.get("tool_margin", 0.01), "tool_margin")
        self.table_size = validation.get("table_size", [0.90, 0.60])
        self.table_center = validation.get("table_center", [0.0, 0.0])
        self.set_speed(**self.parameters["speeds"])
        for motor in self.motors.values():
            motor.setAcceleration(self.acceleration)

        robot_node = self.getSelf()
        for name in NODE_NAMES:
            node = robot_node.getFromProtoDef(name)
            if node is None:
                raise RuntimeError(f"Falta DEF {name} dentro de CartesianRobot.proto")
            self.nodes[name] = node
        self._record_check("devices_and_config", True, {
            "motor_names": [motor.getName() for motor in self.motors.values()],
            "sensor_names": [sensor.getName() for sensor in self.sensors.values()],
            "limits_m": self.limits,
            "motor_limits_match_json": True,
            "sensor_sampling_period_ms": self.timestep,
        })
        print("[CARTESIANO] Control XYZ listo; límites PROVISIONALES en metros.", flush=True)
        self.move_to(0.0, 0.0, 0.0)
        self._step()

    def move_to(self, x, y, z):
        """Ordenar posiciones en metros; recortar límites y devolver target aplicado.

        La validación completa ocurre antes de enviar comandos: si alguna entrada
        no es finita se rechaza toda la orden sin modificar los tres targets.
        """
        requested = {axis: finite_number(value, axis) for axis, value in zip(AXES, (x, y, z))}
        applied = {
            axis: min(self.limits[axis][1], max(self.limits[axis][0], requested[axis]))
            for axis in AXES
        }
        for axis in AXES:
            self.motors[axis].setPosition(applied[axis])
        self.target = applied
        if requested != applied:
            print(f"[CARTESIANO] Target recortado: pedido={requested}, aplicado={applied}", flush=True)
        return dict(applied)

    def set_speed(self, x=None, y=None, z=None):
        """Velocidades positivas en m/s, acotadas por maxVelocity de cada motor."""
        requested = {axis: finite_number(value, f"velocidad {axis}")
                     for axis, value in zip(AXES, (x, y, z)) if value is not None}
        if any(value <= 0.0 for value in requested.values()):
            raise ValueError("Las velocidades deben ser positivas")
        applied = {axis: min(value, self.motors[axis].getMaxVelocity())
                   for axis, value in requested.items()}
        if any(value <= 0.0 for value in applied.values()):
            raise RuntimeError("Un motor tiene maxVelocity inválida")
        for axis, value in applied.items():
            self.motors[axis].setVelocity(value)
        return applied

    def positions(self):
        values = {axis: self.sensors[axis].getValue() for axis in AXES}
        if not all(math.isfinite(value) for value in values.values()):
            raise RuntimeError(f"Lectura no finita de sensores: {values}")
        return values

    def wait_until_reached(self, timeout=None):
        """Esperar proximidad al target sostenida durante settle_seconds."""
        timeout = self.timeout_seconds if timeout is None else finite_number(timeout, "timeout")
        if timeout <= 0.0:
            raise ValueError("timeout debe ser positivo")
        deadline = self.getTime() + timeout
        settled_since = None
        while self.getTime() <= deadline:
            self._step()
            now = self.getTime()
            actual = self.positions()
            reached = all(abs(actual[axis] - self.target[axis]) <= self.tolerance for axis in AXES)
            if reached:
                settled_since = now if settled_since is None else settled_since
                if now - settled_since >= self.settle_seconds:
                    return actual
            else:
                settled_since = None
        raise TimeoutError(
            f"No se alcanzó {self.target} en {timeout:.1f} s; sensores={self.positions()}"
        )

    def hold(self, seconds):
        """Mantener el control activo durante un intervalo de tiempo simulado."""
        end = self.getTime() + finite_number(seconds, "seconds")
        while self.getTime() < end:
            self._step()

    def _step(self):
        if self.step(self.timestep) == -1:
            raise SimulationEnded("Webots terminó la simulación")
        actual = self.positions()
        if self.getTime() - self._last_telemetry >= self.telemetry_period:
            self._last_telemetry = self.getTime()
            text = " | ".join(f"{axis.upper()} = {actual[axis]:+.4f} m" for axis in AXES)
            target_text = ", ".join(f"{axis.upper()}={self.target[axis]:+.3f}" for axis in AXES)
            print(f"[t={self.getTime():7.2f} s] {text} | Target {target_text}", flush=True)
            self.setLabel(0, "ENU: +X derecha | +Y fondo | +Z arriba", 0.02, 0.02, 0.055, 0xFFFFFF)
            self.setLabel(1, text, 0.02, 0.075, 0.055, 0xC7EDFF)
        if self.validation_mode and self.nodes:
            self._capture_snapshot(actual)

    def _capture_snapshot(self, actual=None):
        actual = self.positions() if actual is None else actual
        positions = {name: node.getPosition() for name, node in self.nodes.items()}
        orientations = {name: node.getOrientation() for name, node in self.nodes.items()}
        numbers = [v for vector in (*positions.values(), *orientations.values()) for v in vector]
        if not all(math.isfinite(v) for v in numbers):
            raise RuntimeError("Posición/orientación global no finita en la física")
        expected_tip = [zero + actual[axis] for zero, axis in zip(self.tool_tip_zero, AXES)]
        tip = positions["TOOL_TIP"]
        tip_error = max_difference(tip, expected_tip)
        clearance = tip[2] - self.table_surface_z
        limit_excess = max(
            max(self.limits[axis][0] - actual[axis], actual[axis] - self.limits[axis][1], 0.0)
            for axis in AXES
        )
        fixed_drift = orientation_difference = 0.0
        if self._reference is not None:
            fixed_drift = max_difference(positions["FIXED_Y"], self._reference["positions"]["FIXED_Y"])
            orientation_difference = max(
                max_difference(orientations[name], self._reference["orientations"][name]) for name in NODE_NAMES
            )
        self._metrics["maximum_sensor_limit_excess_m"] = max(self._metrics["maximum_sensor_limit_excess_m"], limit_excess)
        self._metrics["maximum_fixed_drift_m"] = max(self._metrics["maximum_fixed_drift_m"], fixed_drift)
        self._metrics["maximum_orientation_difference"] = max(self._metrics["maximum_orientation_difference"], orientation_difference)
        self._metrics["maximum_tip_kinematic_error_m"] = max(self._metrics["maximum_tip_kinematic_error_m"], tip_error)
        self._metrics["minimum_tool_clearance_m"] = min(self._metrics["minimum_tool_clearance_m"], clearance)
        snapshot = {
            "time_s": self.getTime(), "phase": self._phase,
            "sensor_m": actual, "target_m": dict(self.target),
            "positions": positions, "orientations": orientations,
            "tip_kinematic_error_m": tip_error,
            "fixed_drift_m": fixed_drift,
            "orientation_difference": orientation_difference,
            "tool_clearance_above_rubber_m": clearance,
            # Puede ser negativo: el espacio libre lateral no limita el recorrido.
            "tip_table_horizontal_margins_m": [
                self.table_size[i] / 2 - abs(tip[i] - self.table_center[i]) for i in range(2)
            ],
        }
        self._snapshots.append(snapshot)
        return snapshot

    def _record_check(self, name, passed, details):
        self._checks.append({"name": name, "passed": bool(passed), "details": details})
        if self.validation_mode:
            print(f"[VALIDACION] {'PASS' if passed else 'FAIL'} {name}", flush=True)

    def _go(self, label, target):
        self._phase = label
        print(f"[CARTESIANO] {label}: {target}", flush=True)
        self.move_to(*target)
        result = self.wait_until_reached()
        self.hold(0.35)
        return result

    def demo_once(self):
        """Ejes aislados para apreciar la jerarquía; luego posiciones combinadas."""
        sequence = (
            ("home", (0.0, 0.0, 0.0)),
            ("Y aislado", (0.0, 0.12, 0.0)), ("home", (0.0, 0.0, 0.0)),
            ("X aislado", (0.15, 0.0, 0.0)), ("home", (0.0, 0.0, 0.0)),
            ("Z aislado", (0.0, 0.0, 0.06)), ("home", (0.0, 0.0, 0.0)),
            ("A", (-0.15, -0.12, -0.05)),
            ("B", (0.15, 0.12, 0.07)),
            ("C", (0.0, -0.10, 0.0)),
            ("home", (0.0, 0.0, 0.0)),
        )
        for label, target in sequence:
            self._go(label, target)

    def _test_isolated_axis(self, axis, displacement, moving_nodes):
        self._go(f"home antes de {axis.upper()}", (0.0, 0.0, 0.0))
        before = self._capture_snapshot()
        target = [0.0, 0.0, 0.0]
        target[AXES.index(axis)] = displacement
        self._go(f"TEST {axis.upper()}", target)
        after = self._capture_snapshot()
        delta = after["sensor_m"][axis] - before["sensor_m"][axis]
        details = {"commanded_displacement_m": displacement, "measured_displacement_m": delta, "nodes": {}}
        passed = abs(delta - displacement) <= self.tolerance
        for name in NODE_NAMES:
            observed = [a - b for a, b in zip(after["positions"][name], before["positions"][name])]
            expected = [0.0, 0.0, 0.0]
            if name in moving_nodes:
                expected[AXES.index(axis)] = delta
            error = max_difference(observed, expected)
            orientation_error = max_difference(after["orientations"][name], before["orientations"][name])
            node_passed = error <= self.kinematic_tolerance and orientation_error <= self.orientation_tolerance
            details["nodes"][name] = {
                "expected_delta_m": expected, "observed_delta_m": observed,
                "maximum_delta_error_m": error, "orientation_difference": orientation_error,
                "passed": node_passed,
            }
            passed = passed and node_passed
        for other in AXES:
            if other != axis:
                passed = passed and abs(after["sensor_m"][other] - before["sensor_m"][other]) <= self.tolerance
        self._record_check(f"hierarchy_{axis}", passed, details)

    def run_validation(self):
        """Pruebas físicas reales; un fallo hace terminar Webots con código 1."""
        self._go("home de validación", (0.0, 0.0, 0.0))
        self.hold(0.5)
        self._reference = self._capture_snapshot()
        self._record_check("tool_tip_home", self._reference["tip_kinematic_error_m"] <= self.kinematic_tolerance, {
            "expected_enu_m": self.tool_tip_zero,
            "measured_enu_m": self._reference["positions"]["TOOL_TIP"],
            "maximum_error_m": self._reference["tip_kinematic_error_m"],
        })
        self._test_isolated_axis("y", 0.12, {"Y_CARRIAGE", "X_MODULE", "X_CARRIAGE", "Z_MODULE", "Z_CARRIAGE", "TOOL", "TOOL_TIP"})
        self._test_isolated_axis("x", 0.15, {"X_CARRIAGE", "Z_MODULE", "Z_CARRIAGE", "TOOL", "TOOL_TIP"})
        self._test_isolated_axis("z", 0.06, {"Z_CARRIAGE", "TOOL", "TOOL_TIP"})

        # Se prueba la demo solicitada además de las verificaciones aisladas.
        self.demo_once()
        self._record_check("automatic_demo", True, {"last_position_m": self.positions()})

        for extremes in product((0, 1), repeat=3):
            corner = tuple(self.limits[axis][index] for axis, index in zip(AXES, extremes))
            actual = self._go("esquina conservadora", corner)
            errors = {axis: abs(actual[axis] - target) for axis, target in zip(AXES, corner)}
            self._record_check("workspace_corner_" + "".join(map(str, extremes)),
                               max(errors.values()) <= self.tolerance,
                               {"target_m": corner, "sensor_m": actual, "errors_m": errors})

        for bound in (0, 1):
            requested = tuple(self.limits[axis][bound] + (-1.0 if bound == 0 else 1.0) for axis in AXES)
            expected = {axis: self.limits[axis][bound] for axis in AXES}
            applied = self.move_to(*requested)
            self._phase = f"clamp_{bound}"
            actual = self.wait_until_reached()
            passed = applied == expected and all(abs(actual[axis] - expected[axis]) <= self.tolerance for axis in AXES)
            self._record_check(f"clamp_{'minimum' if bound == 0 else 'maximum'}", passed,
                               {"requested_m": requested, "applied_m": applied, "sensor_m": actual})

        nonfinite_details = []
        for values in ((math.nan, 0.0, 0.0), (0.0, math.inf, 0.0), (0.0, 0.0, -math.inf)):
            previous = dict(self.target)
            rejected = False
            try:
                self.move_to(*values)
            except ValueError:
                rejected = True
            commands = {axis: self.motors[axis].getTargetPosition() for axis in AXES}
            unchanged = self.target == previous and commands == previous
            nonfinite_details.append({"input": [str(v) for v in values], "rejected": rejected, "targets_unchanged": unchanged})
        self._record_check("nonfinite_rejected_atomically", all(d["rejected"] and d["targets_unchanged"] for d in nonfinite_details), nonfinite_details)

        self._go("home final", (0.0, 0.0, 0.0))
        self._phase = "stable_hold_3_seconds"
        baseline = self._capture_snapshot()
        start_index = len(self._snapshots)
        self.hold(3.0)
        stable = self._snapshots[start_index:]
        drift = max(max_difference(sample["positions"][name], baseline["positions"][name])
                    for sample in stable for name in NODE_NAMES)
        sensor_error = max(abs(sample["sensor_m"][axis] - self.target[axis]) for sample in stable for axis in AXES)
        self._record_check("stable_hold_3_seconds", drift <= self.stability_tolerance and sensor_error <= self.tolerance, {
            "duration_s": self.getTime() - baseline["time_s"], "sample_count": len(stable),
            "maximum_body_drift_m": drift, "maximum_sensor_error_m": sensor_error,
            "drift_tolerance_m": self.stability_tolerance,
        })
        metric_limits = {
            "maximum_sensor_limit_excess_m": self.tolerance,
            "maximum_fixed_drift_m": self.stability_tolerance,
            "maximum_orientation_difference": self.orientation_tolerance,
            "maximum_tip_kinematic_error_m": self.kinematic_tolerance,
        }
        for name, limit in metric_limits.items():
            self._record_check(name, self._metrics[name] <= limit, {"observed": self._metrics[name], "limit": limit})
        self._record_check("tool_above_rubber_every_timestep", self._metrics["minimum_tool_clearance_m"] >= self.tool_margin, {
            "minimum_clearance_m": self._metrics["minimum_tool_clearance_m"],
            "minimum_required_m": self.tool_margin, "rubber_surface_z_m": self.table_surface_z,
        })
        self.finish_validation()

    def finish_validation(self, error=None):
        if error is not None:
            self._record_check("execution_completed", False, {"error": str(error), "type": type(error).__name__})
        failures = [check["name"] for check in self._checks if not check["passed"]]
        passed = error is None and bool(self._checks) and not failures
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        screenshot_error = None
        try:
            # FAST no siempre refresca la vista; activar rendering antes de exportar.
            self.simulationSetMode(Supervisor.SIMULATION_MODE_REAL_TIME)
            refresh_end = self.getTime() + 0.2
            while self.getTime() < refresh_end:
                if self.step(self.timestep) == -1:
                    raise SimulationEnded("Simulación cerrada antes de exportar imagen")
            SCREENSHOT_PATH.unlink(missing_ok=True)
            self.exportImage(str(SCREENSHOT_PATH), 95)
            # Supervisor procesa exportImage al finalizar el siguiente step.
            if self.step(self.timestep) == -1:
                raise SimulationEnded("Simulación cerrada antes de exportar imagen")
            if not SCREENSHOT_PATH.is_file() or SCREENSHOT_PATH.stat().st_size == 0:
                raise RuntimeError("Webots no generó validation.jpg")
        except Exception as export_error:
            screenshot_error = str(export_error)
            passed = False
            failures.append("screenshot_export")
        metrics = {name: value if math.isfinite(value) else None for name, value in self._metrics.items()}
        # Todas las métricas y la estabilidad se calcularon en CADA timestep.
        # Exportar muestras cada 0.5 s, transiciones y extremos mantiene legible
        # el informe sin perder los eventos que justifican un fallo.
        selected_indices = set()
        next_sample_time = -math.inf
        previous_phase = None
        for index, sample in enumerate(self._snapshots):
            if sample["time_s"] >= next_sample_time or sample["phase"] != previous_phase:
                selected_indices.add(index)
                if index > 0 and sample["phase"] != previous_phase:
                    selected_indices.add(index - 1)
                next_sample_time = sample["time_s"] + 0.5
            previous_phase = sample["phase"]
        if self._snapshots:
            selected_indices.add(len(self._snapshots) - 1)
            for name in ("tip_kinematic_error_m", "fixed_drift_m", "orientation_difference"):
                selected_indices.add(max(range(len(self._snapshots)), key=lambda i: self._snapshots[i][name]))
            selected_indices.add(min(range(len(self._snapshots)), key=lambda i: self._snapshots[i]["tool_clearance_above_rubber_m"]))
            selected_indices.add(max(range(len(self._snapshots)), key=lambda i: max(
                max(self.limits[axis][0] - self._snapshots[i]["sensor_m"][axis],
                    self._snapshots[i]["sensor_m"][axis] - self.limits[axis][1], 0.0) for axis in AXES)))
        report_snapshots = [self._snapshots[index] for index in sorted(selected_indices)]
        report = {
            "schema_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "passed": passed, "exit_status": 0 if passed else 1,
            "simulation_time_s": self.getTime(), "basic_timestep_ms": self.timestep,
            "parameters_file": str(PARAMETERS_PATH), "parameters": self.parameters,
            "coordinate_system": "ENU (+X derecha, +Y fondo, +Z arriba)",
            "provisional_limits": True,
            "checks": self._checks, "failed_checks": failures,
            "continuous_metrics": metrics,
            "snapshot_count": len(self._snapshots),
            "exported_snapshot_count": len(report_snapshots),
            "exported_snapshot_period_s": 0.5,
            "snapshot_sampling_note": "Métricas en cada timestep; muestras exportadas cada 0.5 s más transiciones y extremos.",
            "timestep_snapshots": report_snapshots,
            "screenshot": str(SCREENSHOT_PATH), "screenshot_error": screenshot_error,
        }
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        print(f"[VALIDACION] {'APROBADA' if passed else 'FALLIDA'}: {REPORT_PATH}", flush=True)
        if failures:
            print(f"[VALIDACION] Fallos: {', '.join(failures)}", flush=True)
        self.simulationQuit(0 if passed else 1)
        self.step(self.timestep)

    def run(self):
        try:
            self.configure()
            if self.validation_mode:
                self.run_validation()
            else:
                while True:
                    self.demo_once()
                    self.hold(1.0)
        except SimulationEnded:
            print("[CARTESIANO] Simulación finalizada.", flush=True)
        except Exception as error:
            traceback.print_exc()
            if self.validation_mode:
                self.finish_validation(error)
            else:
                # Un error de configuración/movimiento queda visible en consola.
                raise


if __name__ == "__main__":
    CartesianController().run()
