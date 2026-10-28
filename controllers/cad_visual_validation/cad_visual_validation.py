"""Auditoría CAD visual: reutiliza el controlador validado sin modificarlo."""
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

VIEWS = ROOT / "docs/cad_views"
IDENTITY_POSE = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
MOVING_AXES = {
    "FIXED_Y": (), "Y_CARRIAGE": ("y",), "X_MODULE": ("y",),
    "X_CARRIAGE": ("x", "y"), "Z_MODULE": ("x", "y"),
    "Z_CARRIAGE": AXES, "TOOL": AXES, "TOOL_TIP": AXES,
}


def visual_scale(node):
    """Pose implica escala 1; Transform debe permitir leer su campo scale."""
    kind, base = node.getTypeName(), node.getBaseTypeName()
    if base not in ("Pose", "Transform"):
        raise RuntimeError(f"DEF visual no es Pose/Transform: {kind}, base {base}")
    field = node.getField("scale")
    if field is None and base == "Transform":
        field = node.getBaseNodeField("scale")
    if field is None:
        if base != "Pose":
            raise RuntimeError("Transform sin campo scale verificable")
        return [1.0, 1.0, 1.0], kind, base, "Pose: escala implícita unitaria"
    return field.getSFVec3f(), kind, base, "campo runtime scale"


def world_bounds(pose, vertices):
    points = [[sum(pose[4 * row + column] * point[column] for column in range(3))
               + pose[4 * row + 3] for row in range(3)] for point in vertices]
    return {"min": [min(point[i] for point in points) for i in range(3)],
            "max": [max(point[i] for point in points) for i in range(3)]}


def inspect_obj(mesh):
    """Leer recursos locales y verificar triángulos, índices y valores finitos."""
    relative = Path(mesh["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Ruta CAD debe ser relativa y local: {relative}")
    asset = (ROOT / relative).resolve()
    asset.relative_to(ROOT.resolve())
    if asset.suffix.lower() != ".obj":
        raise ValueError(f"El validador de esta etapa requiere OBJ: {relative}")
    vertices, faces, vector_values = [], [], []
    for raw_line in asset.read_text(encoding="utf-8").splitlines():
        fields = raw_line.split()
        if not fields:
            continue
        if fields[0] == "v":
            point = [float(value) for value in fields[1:4]]
            if len(point) != 3:
                raise ValueError(f"Vértice incompleto en {relative}")
            vertices.append(point)
            vector_values.extend(point)
        elif fields[0] in ("vn", "vt"):
            vector_values.extend(float(value) for value in fields[1:])
        elif fields[0] == "f":
            indices = [int(value.split("/")[0]) for value in fields[1:]]
            # OBJ negativo es relativo al conjunto de vértices ya definido.
            indices = [index - 1 if index > 0 else len(vertices) + index for index in indices]
            faces.append(indices)
    finite = bool(vertices and faces) and all(math.isfinite(value) for value in vector_values)
    triangles = all(len(face) == 3 and len(set(face)) == 3
                    and all(0 <= index < len(vertices) for index in face) for face in faces)
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    expected_digest = mesh.get("sha256")
    details = {
        "path": relative.as_posix(), "sha256": digest, "expected_sha256": expected_digest,
        "sha256_matches_config": expected_digest is None or digest == expected_digest.lower(),
        "vertices": len(vertices), "triangles": len(faces), "bytes": asset.stat().st_size,
        "finite_values": finite, "triangular_valid_indices": triangles,
        "local_bounds_m": world_bounds(IDENTITY_POSE, vertices) if vertices else None,
    }
    return vertices, details, finite and triangles and details["sha256_matches_config"]


class CADVisualValidation(CartesianController):
    def configure(self):
        started = time.perf_counter()
        super().configure()
        self.configuration_wall_s = time.perf_counter() - started
        launch_ms = os.environ.get("WEBOTS_VALIDATION_LAUNCH_UNIX_MS")
        self.launch_to_first_step_wall_s = time.time() - float(launch_ms) / 1000 if launch_ms else None

    def capture_view(self, name):
        """Refrescar la vista mediante pasos simulados, sin esperas de reloj real."""
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
        return target.relative_to(ROOT).as_posix()

    def closeup(self, entry):
        children = self.getRoot().getField("children")
        viewpoint = next((children.getMFNode(i) for i in range(children.getCount())
                          if children.getMFNode(i).getTypeName() == "Viewpoint"), None)
        if viewpoint is None:
            raise RuntimeError("Falta Viewpoint para captura CAD cercana")
        position, orientation, fov = (viewpoint.getField(field)
                                      for field in ("position", "orientation", "fieldOfView"))
        saved = (position.getSFVec3f(), orientation.getSFRotation(), fov.getSFFloat())
        bounds = world_bounds(entry["visual"].getPose(), entry["vertices"])
        center = [(bounds["min"][i] + bounds["max"][i]) / 2 for i in range(3)]
        # ENU/FLU: +X local es la dirección de mirada. Giro +90° mira +Y.
        # Encadre según silueta X/Z real del CAD, sin asumir longitud nominal.
        view_fov = 0.65
        extent = max(bounds["max"][i] - bounds["min"][i] for i in (0, 2))
        depth = bounds["max"][1] - bounds["min"][1]
        # fieldOfView es horizontal; la vista Webots de estas capturas es
        # aproximadamente 2:1. Reservar margen vertical para ambos extremos.
        distance = max(0.7, extent / (2 * math.tan(view_fov / 2)) * 2.6 + depth / 2)
        try:
            position.setSFVec3f([center[0], center[1] - distance, center[2]])
            orientation.setSFRotation([0.0, 0.0, 1.0, math.pi / 2])
            fov.setSFFloat(view_fov)
            screenshot = self.capture_view("webots_servo_z_closeup.jpg")
            return screenshot, {"cad_world_bounds_m": bounds, "camera_position_m": position.getSFVec3f(),
                                "camera_orientation_axis_angle": orientation.getSFRotation(),
                                "field_of_view_rad": view_fov}
        finally:
            position.setSFVec3f(saved[0])
            orientation.setSFRotation(saved[1])
            fov.setSFFloat(saved[2])

    def inspect_part(self, part):
        visual = self.getSelf().getFromProtoDef(part["visual_def"])
        module = self.nodes[part["solid_def"]]
        if visual is None:
            raise RuntimeError(f"Falta DEF {part['visual_def']} en el PROTO")
        if part["solid_def"] not in MOVING_AXES:
            raise RuntimeError(f"Link sin regla de jerarquía: {part['solid_def']}")
        configured_meshes = part["meshes"]
        if not configured_meshes:
            raise RuntimeError(f"Parte CAD sin meshes: {part['name']}")
        children = visual.getField("children")
        loaded = []
        all_vertices = []
        resources = []
        resources_ok = True
        for mesh in configured_meshes:
            vertices, details, passed = inspect_obj(mesh)
            all_vertices.extend(vertices)
            resources.append(details)
            resources_ok = resources_ok and passed
        shapes_ok = children is not None and children.getCount() == len(configured_meshes)
        if children is not None:
            for index in range(children.getCount()):
                shape = children.getMFNode(index)
                geometry_field = shape.getField("geometry") if shape.getTypeName() == "Shape" else None
                geometry = geometry_field.getSFNode() if geometry_field else None
                urls = geometry.getField("url") if geometry and geometry.getTypeName() == "Mesh" else None
                actual_urls = [urls.getMFString(i) for i in range(urls.getCount())] if urls else []
                loaded.append(actual_urls)
                expected_url = "../" + Path(configured_meshes[index]["path"]).as_posix() if index < len(configured_meshes) else None
                shapes_ok = shapes_ok and actual_urls == [expected_url]
        scale, runtime_type, runtime_base_type, scale_source = visual_scale(visual)
        unit_scale = all(math.isfinite(value) for value in scale) and max_difference(scale, [1, 1, 1]) <= 1e-12
        local_pose_error = max_difference(visual.getPose(module), IDENTITY_POSE)
        self._record_check(f"cad_resource_{part['name']}", resources_ok and shapes_ok and unit_scale
                           and local_pose_error <= 1e-6, {
            "part_name": part["name"], "solid_def": part["solid_def"], "visual_def": part["visual_def"],
            "resources": resources, "runtime_urls": loaded, "shape_mesh_urls_match_config": shapes_ok,
            "local_bounds_m": world_bounds(IDENTITY_POSE, all_vertices), "unit_scale": unit_scale,
            "runtime_node_type": runtime_type, "runtime_base_type": runtime_base_type,
            "runtime_scale": scale, "scale_source": scale_source,
            "local_pose_difference_from_identity": local_pose_error,
            "controller_configuration_to_first_step_wall_s": self.configuration_wall_s,
            "approximate_process_launch_to_first_step_wall_s": self.launch_to_first_step_wall_s,
            "launch_timing_scope": "Aproximación Unix desde arranque de proceso hasta primer step. Incluye carga/configuración; no mide carga aislada ni FPS.",
        })
        return {"part": part, "visual": visual, "module": module, "vertices": all_vertices}

    def run_validation(self):
        config = json.loads((ROOT / "config/cad_integration.json").read_text(encoding="utf-8"))
        enabled = [part for part in config["parts"] if part.get("enabled", False)]
        if not enabled:
            raise RuntimeError("No hay partes CAD enabled para auditar")
        entries = [self.inspect_part(part) for part in enabled]
        self._go("centro antes de auditoría CAD", (0, 0, 0))
        home_sensor = self.positions()
        for entry in entries:
            entry["home_pose"] = entry["visual"].getPose()
        for axis in ("y", "x", "z"):
            for label, value in (("negative", self.limits[axis][0]), ("center", 0),
                                 ("positive", self.limits[axis][1])):
                target = [0.0, 0.0, 0.0]
                target[AXES.index(axis)] = value
                self._go(f"CAD {axis} {label}", target)
                current = self.positions()
                screenshot = self.capture_view(f"webots_{axis}_{label}.jpg")
                for entry in entries:
                    part, visual, module = entry["part"], entry["visual"], entry["module"]
                    visual_pose, parent_pose = visual.getPose(), module.getPose()
                    observed_delta = [visual_pose[i] - entry["home_pose"][i] for i in (3, 7, 11)]
                    expected_delta = [current[coordinate] - home_sensor[coordinate]
                                      if coordinate in MOVING_AXES[part["solid_def"]] else 0.0
                                      for coordinate in AXES]
                    pose_error = max_difference(visual_pose, parent_pose)
                    local_pose_error = max_difference(visual.getPose(module), IDENTITY_POSE)
                    follow_error = max_difference(observed_delta, expected_delta)
                    orientation_error = max(abs(visual_pose[i] - entry["home_pose"][i])
                                            for i in (0, 1, 2, 4, 5, 6, 8, 9, 10))
                    self._record_check(f"cad_pose_{part['name']}_{axis}_{label}", pose_error <= 1e-6
                                       and local_pose_error <= 1e-6 and follow_error <= self.kinematic_tolerance
                                       and orientation_error <= self.orientation_tolerance, {
                        "target_m": target, "sensor_m": current, "parent_solid": part["solid_def"],
                        "expected_follow_axes": MOVING_AXES[part["solid_def"]],
                        "pose_difference_from_parent": pose_error,
                        "local_pose_difference_from_identity": local_pose_error,
                        "expected_delta_m": expected_delta, "observed_delta_m": observed_delta,
                        "maximum_follow_error_m": follow_error, "orientation_difference": orientation_error,
                        "world_vertex_bounds_m": world_bounds(visual_pose, entry["vertices"]), "screenshot": screenshot,
                    })
        self._go("centro para captura CAD cercana", (0, 0, 0))
        primary = next((entry for entry in entries if entry["part"]["solid_def"] == "Z_MODULE"), entries[0])
        screenshot, camera = self.closeup(primary)
        self._record_check("cad_closeup_exported", True, {
            "part_name": primary["part"]["name"], "screenshot": screenshot,
            "viewpoint_restored": True, **camera,
        })
        # Conserva y ejecuta todas las pruebas de la implementación principal.
        super().run_validation()


if __name__ == "__main__":
    CADVisualValidation().run()
