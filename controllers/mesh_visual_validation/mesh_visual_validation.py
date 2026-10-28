"""Auditoría visual complementaria; importa el controlador validado sin editarlo."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "controllers/cartesian_controller"))
from cartesian_controller import AXES, CartesianController, max_difference

VIEWS = ROOT / "docs/scan_views"
IDENTITY_POSE = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def visual_scale(node):
    """Pose tiene escala implícita 1; Transform debe exponer su escala real."""
    kind, base = node.getTypeName(), node.getBaseTypeName()
    if base not in ("Pose", "Transform"):
        raise RuntimeError(f"SCAN_X_VISUAL no es Pose/Transform: {kind}, base {base}")
    field = node.getField("scale")
    if field is None and base == "Transform":
        field = node.getBaseNodeField("scale")
    if field is None:
        if base != "Pose":
            raise RuntimeError("Transform sin campo scale accesible: no se puede verificar identidad")
        return [1.0, 1.0, 1.0], kind, base, "Pose: escala implícita unitaria"
    return field.getSFVec3f(), kind, base, "campo runtime scale"


def world_bounds(pose, vertices):
    points = [[sum(pose[4 * row + column] * point[column] for column in range(3)) + pose[4 * row + 3]
               for row in range(3)] for point in vertices]
    return {"min": [min(point[i] for point in points) for i in range(3)],
            "max": [max(point[i] for point in points) for i in range(3)]}


class MeshVisualValidation(CartesianController):
    def configure(self):
        started = time.perf_counter()
        super().configure()
        self.configuration_wall_s = time.perf_counter() - started
        launch_ms = os.environ.get("WEBOTS_VALIDATION_LAUNCH_UNIX_MS")
        self.launch_to_first_step_wall_s = time.time() - float(launch_ms) / 1000 if launch_ms else None

    def capture_view(self, name):
        """Refrescar rendering por pasos simulados; sin sleeps de reloj real."""
        VIEWS.mkdir(parents=True, exist_ok=True)
        target = VIEWS / name
        self.simulationSetMode(self.SIMULATION_MODE_REAL_TIME)
        try:
            for _ in range(max(4, math.ceil(64 / self.timestep))):
                self._step()
            target.unlink(missing_ok=True)
            self.exportImage(str(target), 95)
            self._step()
            if not target.is_file() or not target.stat().st_size:
                raise RuntimeError(f"No se generó la captura {target}")
        finally:
            self.simulationSetMode(self.SIMULATION_MODE_FAST)
        return str(target.relative_to(ROOT)).replace("\\", "/")

    def closeup(self, module):
        children = self.getRoot().getField("children")
        viewpoint = next((children.getMFNode(i) for i in range(children.getCount())
                          if children.getMFNode(i).getTypeName() == "Viewpoint"), None)
        if viewpoint is None:
            raise RuntimeError("Falta Viewpoint para captura cercana")
        position, orientation, fov = (viewpoint.getField(field) for field in ("position", "orientation", "fieldOfView"))
        saved = (position.getSFVec3f(), orientation.getSFRotation(), fov.getSFFloat())
        center = module.getPosition()
        try:
            # Viewpoint R2025a: +X local mira hacia delante; giro +90° mira +Y.
            position.setSFVec3f([center[0], center[1] - 1.05, center[2]])
            orientation.setSFRotation([0.0, 0.0, 1.0, math.pi / 2])
            fov.setSFFloat(0.8)
            return self.capture_view("webots_mesh_closeup.jpg")
        finally:
            position.setSFVec3f(saved[0])
            orientation.setSFRotation(saved[1])
            fov.setSFFloat(saved[2])

    def run_validation(self):
        config = json.loads((ROOT / "config/scan_integration.json").read_text(encoding="utf-8"))
        part = next(part for part in config["parts"] if part["name"] == "axis_x_surface_visual" and part["enabled"])
        asset = ROOT / "meshes" / (part["name"] + ".obj")
        lines = asset.read_text(encoding="utf-8").splitlines()
        vertices = [list(map(float, line.split()[1:4])) for line in lines if line.startswith("v ")]
        faces = [line for line in lines if line.startswith("f ")]
        finite = bool(vertices and faces) and all(math.isfinite(value) for point in vertices for value in point)
        visual = self.getSelf().getFromProtoDef("SCAN_X_VISUAL")
        module = self.nodes[part["solid_def"]]
        if visual is None:
            raise RuntimeError("Falta DEF SCAN_X_VISUAL en el PROTO integrado")
        shape = visual.getField("children").getMFNode(0)
        geometry = shape.getField("geometry").getSFNode()
        urls = geometry.getField("url")
        expected_url = "../meshes/" + asset.name
        loaded_url = urls.getMFString(0)
        scale, runtime_type, runtime_base_type, scale_source = visual_scale(visual)
        identity = all(math.isfinite(value) for value in scale) and max_difference(scale, [1, 1, 1]) < 1e-12
        local_identity_error = max_difference(visual.getPose(module), IDENTITY_POSE)
        local = world_bounds(IDENTITY_POSE, vertices)
        origin = part["origin_world"]
        inside_region = all(any(all(region["min"][i] - 1e-6 <= point[i] + origin[i] <= region["max"][i] + 1e-6
                                         for i in range(3)) for region in part["regions"]) for point in vertices)
        self._record_check("visual_mesh_resource_and_local_bounds", finite and identity and inside_region and local_identity_error <= 1e-6
                           and geometry.getTypeName() == "Mesh" and loaded_url == expected_url, {
            "asset": str(asset.relative_to(ROOT)), "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            "vertices": len(vertices), "faces": len(faces), "bytes": asset.stat().st_size,
            "local_bounds_m": local, "vertices_inside_config_regions": inside_region, "url": loaded_url,
            "unit_scale": identity, "controller_configuration_to_first_step_wall_s": self.configuration_wall_s,
            "runtime_node_type": runtime_type, "runtime_base_type": runtime_base_type,
            "runtime_scale": scale, "scale_source": scale_source,
            "local_pose_difference_from_identity": local_identity_error,
            "timing_scope": "Configuración del controlador hasta primer step; excluye carga previa de Webots.",
            "approximate_process_launch_to_first_step_wall_s": self.launch_to_first_step_wall_s,
            "launch_timing_scope": "Aproximación por reloj Unix: arranque del proceso, carga del world/recursos y configuración hasta primer step. No es carga aislada ni FPS.",
        })
        self._go("centro antes de auditoría visual", (0, 0, 0))
        home_pose, home_sensor = visual.getPose(), self.positions()
        for axis in ("y", "x", "z"):
            for label, value in (("negative", self.limits[axis][0]), ("center", 0), ("positive", self.limits[axis][1])):
                target = [0.0, 0.0, 0.0]
                target[AXES.index(axis)] = value
                self._go(f"mesh {axis} {label}", target)
                visual_pose, parent_pose = visual.getPose(), module.getPose()
                current = self.positions()
                observed_delta = [visual_pose[i] - home_pose[i] for i in (3, 7, 11)]
                expected_delta = [0, current["y"] - home_sensor["y"], 0]
                pose_error = max_difference(visual_pose, parent_pose)
                local_pose_error = max_difference(visual.getPose(module), IDENTITY_POSE)
                follow_error = max_difference(observed_delta, expected_delta)
                screenshot = self.capture_view(f"webots_{axis}_{label}.jpg")
                self._record_check(f"visual_mesh_pose_{axis}_{label}", pose_error <= 1e-6 and local_pose_error <= 1e-6 and follow_error <= self.kinematic_tolerance, {
                    "target_m": target, "sensor_m": current, "parent_solid": part["solid_def"],
                    "pose_difference_from_parent": pose_error, "expected_delta_m": expected_delta,
                    "local_pose_difference_from_identity": local_pose_error,
                    "observed_delta_m": observed_delta, "maximum_follow_error_m": follow_error,
                    "world_vertex_bounds_m": world_bounds(visual_pose, vertices), "screenshot": screenshot,
                })
        self._go("centro para captura cercana", (0, 0, 0))
        screenshot = self.closeup(module)
        self._record_check("visual_closeup_exported", True, {"screenshot": screenshot, "viewpoint_restored": True})
        super().run_validation()


if __name__ == "__main__":
    MeshVisualValidation().run()
