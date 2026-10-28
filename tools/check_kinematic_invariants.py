"""Compara la etapa visual con el checkpoint sin ejecutar ni regenerar Webots.

El tokenizador respeta strings/comentarios y verifica ámbitos VRML balanceados.
Sólo omite Shape (incluyendo material/geometría), contenedores puramente visuales
y cámara/luces/fondo/título del world. Physics y boundingObject se comparan completos.
No demuestra alineación de vértices: requiere revisión visual y validación Webots.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r'"(?:\\.|[^"\\])*"|\#[^\r\n]*|[{}\[\],]|[^\s{}\[\],"#]+')
COSMETIC_NODES = {
    "Shape", "Appearance", "PBRAppearance", "Material", "ImageTexture",
    "TextureTransform", "Viewpoint", "Background", "DirectionalLight",
    "PointLight", "SpotLight",
}
CONTAINERS = {"Transform", "Pose", "Group"}
COLLISION_NODES = CONTAINERS | {"Box", "Cylinder", "Sphere", "Capsule"}
IMMUTABLE_FILES = (
    "config/robot_parameters.json",
    "controllers/cartesian_controller/cartesian_controller.py",
    "controllers/cartesian_controller/runtime.ini",
)
MODEL_FILES = ("protos/CartesianRobot.proto", "worlds/cartesian_robot.wbt")


@dataclass
class Sequence:
    opening: str
    parts: list


@dataclass
class Node:
    kind: str
    parts: list
    def_name: str | None = None


def tokenize(source):
    """No regex balanceada: regex sólo lexea; Parser verifica cada ámbito."""
    tokens = []
    cursor = 0
    for match in TOKEN_RE.finditer(source):
        if source[cursor:match.start()].strip():
            raise ValueError(f"VRML no reconocido cerca de offset {cursor}")
        token = match.group()
        if not token.startswith("#") and token != ",":
            tokens.append(token)
        cursor = match.end()
    if source[cursor:].strip():
        raise ValueError(f"VRML no reconocido cerca de offset {cursor}")
    return tokens


class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source)
        self.index = 0

    def parse(self, closing=None):
        parts = []
        while self.index < len(self.tokens):
            token = self.tokens[self.index]
            if token in ("}", "]"):
                if token != closing:
                    raise ValueError(f"Cierre inesperado {token}, token {self.index}")
                self.index += 1
                return parts
            if token == "DEF":
                if self.index + 3 >= len(self.tokens) or self.tokens[self.index + 3] != "{":
                    raise ValueError(f"DEF incompleto en token {self.index}")
                _, def_name, kind, _ = self.tokens[self.index:self.index + 4]
                self.index += 4
                parts.append(Node(kind, self.parse("}"), def_name))
            elif token == "USE":
                if self.index + 1 >= len(self.tokens):
                    raise ValueError("USE incompleto")
                parts.append(Node("USE", [], self.tokens[self.index + 1]))
                self.index += 2
            elif self.index + 1 < len(self.tokens) and self.tokens[self.index + 1] == "{" and token not in ("[", "{"):
                self.index += 2
                parts.append(Node(token, self.parse("}")))
            elif token in ("{", "["):
                self.index += 1
                parts.append(Sequence(token, self.parse("}" if token == "{" else "]")))
            else:
                parts.append(token)
                self.index += 1
        if closing:
            raise ValueError(f"Falta cierre {closing}")
        return parts


def full_tokens(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, Node):
        if value.kind == "USE":
            return ["USE", value.def_name]
        head = ["DEF", value.def_name] if value.def_name else []
        return head + [value.kind, "{"] + full_tokens(value.parts) + ["}"]
    if isinstance(value, Sequence):
        return [value.opening] + full_tokens(value.parts) + ["}" if value.opening == "{" else "]"]
    return [token for part in value for token in full_tokens(part)]


def protected_tokens(value):
    """Conserva sintaxis física completa; elimina sólo ramas visuales conocidas."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [value.opening] + protected_tokens(value.parts) + ["}" if value.opening == "{" else "]"]
    if isinstance(value, Node):
        if value.kind in COSMETIC_NODES:
            return []
        if value.kind == "USE":
            # No se adivina si un USE es visual; comparación conservadora.
            return full_tokens(value)
        body = protected_tokens(value.parts)
        if value.kind in CONTAINERS and not any(isinstance(part, (Node, Sequence)) and contains_protected_node(part) for part in value.parts):
            return []
        if value.kind == "WorldInfo":
            index = 0
            titleless = []
            while index < len(body):
                if body[index] == "title":
                    if index + 1 >= len(body) or not body[index + 1].startswith('"'):
                        raise ValueError("WorldInfo.title no es SFString literal")
                    index += 2
                else:
                    titleless.append(body[index])
                    index += 1
            body = titleless
        head = ["DEF", value.def_name] if value.def_name else []
        return head + [value.kind, "{"] + body + ["}"]
    output = []
    index = 0
    while index < len(value):
        part = value[index]
        if isinstance(part, str) and part in ("boundingObject", "physics"):
            if index + 1 >= len(value):
                raise ValueError(f"Falta valor de {part}")
            output.append(part)
            output.extend(full_tokens(value[index + 1]))
            index += 2
        else:
            output.extend(protected_tokens(part))
            index += 1
    return output


def contains_protected_node(value):
    if isinstance(value, Node):
        if value.kind in COSMETIC_NODES:
            return False
        if value.kind not in CONTAINERS:
            return True
    if isinstance(value, (Node, Sequence)):
        return any(contains_protected_node(part) for part in value.parts)
    if isinstance(value, list):
        return any(contains_protected_node(part) for part in value)
    return False


def walk(value):
    if isinstance(value, Node):
        yield value
    if isinstance(value, (Node, Sequence)):
        yield from walk(value.parts)
    elif isinstance(value, list):
        for part in value:
            yield from walk(part)


def node_field(node, field):
    for index, part in enumerate(node.parts):
        if part == field and index + 1 < len(node.parts):
            return node.parts[index + 1]
    return None


def scalar_field(node, field, count=1):
    for index, part in enumerate(node.parts):
        if part == field:
            if index + 1 < len(node.parts) and node.parts[index + 1] == "IS":
                return full_tokens(node.parts[index + 1:index + 3])
            return full_tokens(node.parts[index + 1:index + 1 + count])
    return None


def solid_hierarchy(parsed):
    records = []

    def visit(value, parent=None, joints=()):
        if isinstance(value, Node):
            if value.kind in ("Robot", "Solid"):
                label = value.def_name or f"{value.kind}:{len(records)}"
                records.append({
                    "id": label, "type": value.kind, "parent_solid": parent,
                    "name": scalar_field(value, "name"),
                    "translation": scalar_field(value, "translation", 3),
                    "rotation": scalar_field(value, "rotation", 4),
                    "joints_from_root": list(joints),
                    "physics_tokens": full_tokens(node_field(value, "physics")) if node_field(value, "physics") is not None else None,
                    "bounding_object_tokens": full_tokens(node_field(value, "boundingObject")) if node_field(value, "boundingObject") is not None else None,
                })
                parent = label
            if value.kind.endswith("Joint"):
                device = node_field(value, "device")
                names = [scalar_field(node, "name") for node in walk(device) if node.kind.endswith("Motor")]
                joints = joints + (names[0][0] if names and names[0] else value.kind,)
        if isinstance(value, (Node, Sequence)):
            visit(value.parts, parent, joints)
        elif isinstance(value, list):
            for part in value:
                visit(part, parent, joints)

    visit(parsed)
    return records


def simple_collisions(parsed):
    definitions = {node.def_name: node for node in walk(parsed) if node.def_name and node.kind != "USE"}
    records = []
    errors = []

    def check(value, owner, seen=()):
        if value == "NULL":
            return
        if isinstance(value, Node):
            if value.kind == "USE":
                if value.def_name in seen or value.def_name not in definitions:
                    errors.append(f"{owner}: USE no resuelto/cíclico {value.def_name}")
                    return
                check(definitions[value.def_name], owner, seen + (value.def_name,))
                return
            if value.kind not in COLLISION_NODES:
                errors.append(f"{owner}: nodo no primitivo en boundingObject: {value.kind}")
            check(value.parts, owner, seen)
        elif isinstance(value, Sequence):
            check(value.parts, owner, seen)
        elif isinstance(value, list):
            for part in value:
                check(part, owner, seen)

    for node in walk(parsed):
        if node.kind not in ("Solid", "Robot"):
            continue
        bounds = node_field(node, "boundingObject")
        if bounds is None:
            continue
        owner = node.def_name or node.kind
        records.append({"solid": owner, "node_types": dict(Counter(child.kind for child in walk(bounds)))})
        check(bounds, owner)
    return records, errors


def visual_meshes(parsed, model_path, project_root):
    records = []
    errors = []

    def visit(value, parent=None, transforms=()):
        if isinstance(value, Node):
            if value.kind in ("Robot", "Solid"):
                parent = value.def_name or value.kind
                transforms = ()
            if value.kind in ("Transform", "Pose"):
                transforms += ({field: scalar_field(value, field, count) for field, count in (("translation", 3), ("rotation", 4), ("scale", 3))},)
            if value.kind == "Mesh":
                url_value = node_field(value, "url")
                urls = [json.loads(token) for token in full_tokens(url_value) if token.startswith('"')] if url_value is not None else []
                for url in urls:
                    target = (model_path.parent / url).resolve()
                    if Path(url).is_absolute() or re.match(r"^[A-Za-z]:", url) or "://" in url:
                        errors.append(f"{parent}: URL no relativa {url}")
                    elif not target.is_relative_to(project_root.resolve()):
                        errors.append(f"{parent}: URL escapa del proyecto {url}")
                    elif not target.is_file():
                        errors.append(f"{parent}: Mesh no existe {url}")
                records.append({"parent_solid": parent, "urls": urls, "visual_transforms": list(transforms)})
        if isinstance(value, (Node, Sequence)):
            visit(value.parts, parent, transforms)
        elif isinstance(value, list):
            for part in value:
                visit(part, parent, transforms)

    visit(parsed)
    return records, errors


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compare_tokens(baseline, current):
    if baseline == current:
        return None
    for index in range(max(len(baseline), len(current))):
        if index >= len(baseline) or index >= len(current) or baseline[index] != current[index]:
            return {"token_index": index, "baseline_context": baseline[max(0, index - 8):index + 9], "current_context": current[max(0, index - 8):index + 9]}


def self_test():
    """Casos de adversario: el filtro no puede ocultar cambios físicos."""
    baseline = '''PROTO Example [] { Robot { children [
Transform { translation 1 2 3 children [ Shape { geometry Box { size 1 1 1 } } ] }
SliderJoint { jointParameters JointParameters { axis 0 1 0 }
device [ LinearMotor { name "motor_y" controlPID 3 0 0 } PositionSensor { name "sensor_y" } ]
endPoint DEF Y Solid { translation 0 0 1 children [ DEF Z Solid { translation 0 0 2 children [] } ]
boundingObject Box { size 1 1 1 } physics Physics { density -1 mass 12 } } }
] boundingObject Box { size 3 3 3 } } }'''
    protected = protected_tokens(Parser(baseline).parse())
    cases = [
        ("visual_replacement_accepted", baseline.replace('geometry Box { size 1 1 1 }', 'geometry Mesh { url [ "../meshes/test.obj" ] }'), True),
        ("visual_transform_accepted", baseline.replace('translation 1 2 3', 'translation 9 8 7'), True),
        ("comments_and_strings_accepted", '# test { ]\n' + baseline.replace('size 1 1 1 } }', 'size 1 1 1 } # ] } ignored\n }'), True),
        ("pid_change_rejected", baseline.replace('controlPID 3 0 0', 'controlPID 15 0 0'), False),
        ("axis_change_rejected", baseline.replace('axis 0 1 0', 'axis 1 0 0'), False),
        ("link_offset_rejected", baseline.replace('translation 0 0 2', 'translation 0 0 9'), False),
        ("bounding_object_change_rejected", baseline.replace('boundingObject Box { size 1 1 1 }', 'boundingObject Box { size 2 1 1 }'), False),
        ("mass_change_rejected", baseline.replace('mass 12', 'mass 10'), False),
        ("parent_change_rejected", baseline.replace('children [ DEF Z Solid', 'children [ Transform { translation 0 0 1 children [ DEF Z Solid').replace('children [] } ]', 'children [] } ] } ]'), False),
    ]
    results = [{"name": name, "passed": (protected_tokens(Parser(source).parse()) == protected) == expected} for name, source, expected in cases]
    _, bad_collisions = simple_collisions(Parser(baseline.replace('boundingObject Box { size 1 1 1 }', 'boundingObject Mesh { url ["bad.obj"] }')).parse())
    results.append({"name": "mesh_collision_rejected", "passed": bool(bad_collisions)})
    try:
        Parser(baseline[:-1]).parse()
        rejected = False
    except ValueError:
        rejected = True
    results.append({"name": "unbalanced_vrml_rejected", "passed": rejected})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ROOT / "backups/stage1_validated")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path, default=ROOT / "docs/kinematic_invariants.json")
    parser.add_argument("--self-test", action="store_true", help="Ejecutar casos adversarios en memoria y terminar sin informe")
    args = parser.parse_args()
    if args.self_test:
        tests = self_test()
        print(json.dumps(tests, indent=2, ensure_ascii=False))
        return 0 if all(test["passed"] for test in tests) else 1
    report = {
        "schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_directory": str(args.baseline.resolve()), "project_root": str(args.root.resolve()),
        "passed": False, "checks": [], "models": {},
        "scope": "Comparación estática. No ejecuta Webots ni build_model.py ni modifica el modelo.",
        "limitations": [
            "Las posiciones de Solid no prueban posición, escala o segmentación de los vértices Mesh.",
            "Requiere validar Webots y revisar meshes en extremos/centro de cada eje.",
            "Los USE se preservan de forma conservadora; cambiar un USE visual requiere revisión explícita.",
            "Cámara, luces, fondo y WorldInfo.title se omiten; física, timestep y coordinateSystem se conservan.",
            "El generador puede cambiar para producir visuales; no se exige identidad byte a byte de build_model.py.",
        ],
    }

    def record(name, passed, details=None):
        report["checks"].append({"name": name, "passed": bool(passed), "details": details})

    try:
        for relative in IMMUTABLE_FILES:
            baseline = (args.baseline / relative).read_bytes()
            current = (args.root / relative).read_bytes()
            record(f"bytewise:{relative}", baseline == current, {"baseline_sha256": digest(baseline), "current_sha256": digest(current)})
        for relative in MODEL_FILES:
            baseline_path = args.baseline / relative
            current_path = args.root / relative
            baseline_bytes, current_bytes = baseline_path.read_bytes(), current_path.read_bytes()
            baseline = Parser(baseline_bytes.decode("utf-8-sig")).parse()
            current = Parser(current_bytes.decode("utf-8-sig")).parse()
            baseline_tokens, current_tokens = protected_tokens(baseline), protected_tokens(current)
            difference = compare_tokens(baseline_tokens, current_tokens)
            record(f"protected_vrml:{relative}", difference is None, difference)
            base_hierarchy, current_hierarchy = solid_hierarchy(baseline), solid_hierarchy(current)
            record(f"solid_hierarchy:{relative}", base_hierarchy == current_hierarchy)
            collisions, collision_errors = simple_collisions(current)
            record(f"primitive_collisions_only:{relative}", not collision_errors, collision_errors)
            meshes, mesh_errors = visual_meshes(current, current_path, args.root)
            record(f"relative_existing_mesh_urls:{relative}", not mesh_errors, mesh_errors)
            inventory = Counter(node.kind for node in walk(current))
            if relative.endswith(".proto"):
                expected = {"SliderJoint": 3, "LinearMotor": 3, "PositionSensor": 3}
                record("three_linear_joints_and_devices", all(inventory[kind] == count for kind, count in expected.items()), {kind: inventory[kind] for kind in expected})
                record("no_rotary_joints", not any(inventory[kind] for kind in ("HingeJoint", "Hinge2Joint", "BallJoint")))
            report["models"][relative] = {
                "baseline_sha256": digest(baseline_bytes), "current_sha256": digest(current_bytes),
                "protected_baseline_sha256": digest(" ".join(baseline_tokens).encode()),
                "protected_current_sha256": digest(" ".join(current_tokens).encode()),
                "node_inventory": dict(inventory), "solid_hierarchy": current_hierarchy,
                "bounding_objects": collisions, "visual_meshes": meshes,
            }
        tests = self_test()
        record("checker_adversarial_cases", all(test["passed"] for test in tests), tests)
    except Exception as error:
        record("inspection_completed", False, {"type": type(error).__name__, "error": str(error)})
    report["passed"] = bool(report["checks"]) and all(check["passed"] for check in report["checks"])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    failures = [check["name"] for check in report["checks"] if not check["passed"]]
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {len(report['checks'])} comprobaciones; {args.report}")
    if failures:
        print("Fallos: " + ", ".join(failures))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
