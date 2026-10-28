"""Reproducible visual-only scan preparation; run with Blender --background.

Examples (arguments after Blender's ``--``):
  blender --background --factory-startup --python tools/prepare_blender_scene.py -- --mode inspect
  blender --background --factory-startup --python tools/prepare_blender_scene.py -- --mode final

The input OBJ is a derived file; this script never writes reference scans.  All
coordinates exported to Webots are metres with +X/+Y/+Z unchanged (ENU).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("inspect", "final"), default="inspect")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--source-obj", default="blender/derived/scan_raw.obj")
    parser.add_argument("--config", default="config/scan_integration.json")
    parser.add_argument("--resolution", type=int, default=1100)
    parser.add_argument("--no-render", action="store_true")
    return parser.parse_args(argv)


def resolved(root: Path, path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def reset_background_scene():
    # Refuse interactive execution so an existing unsaved user scene is safe.
    if not bpy.app.background:
        raise RuntimeError("Run this script with Blender --background; it must not replace an interactive scene.")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    engines = {entry.identifier for entry in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    if not scene.world.node_tree:
        scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.105, 0.115, 0.13, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.75
    scene.view_settings.view_transform = "AgX"
    return scene


def collection(name):
    item = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(item)
    return item


def move_to_collection(obj, destination):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    destination.objects.link(obj)


def import_source(path, destination):
    if not path.is_file():
        raise FileNotFoundError(f"Derived OBJ not found: {path}")
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z", validate_meshes=True)
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        raise ValueError("The derived OBJ contains no mesh.")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    if len(imported) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.name = "SCAN_RAW_DERIVED_METRES"
    move_to_collection(obj, destination)
    return obj


def bounding_box(points):
    if not points:
        return None
    minimum = [min(point[i] for point in points) for i in range(3)]
    maximum = [max(point[i] for point in points) for i in range(3)]
    return {
        "min": minimum,
        "max": maximum,
        "dimensions": [maximum[i] - minimum[i] for i in range(3)],
    }


def object_points(obj, world=True):
    if world:
        return [obj.matrix_world @ vert.co for vert in obj.data.vertices]
    return [vert.co.copy() for vert in obj.data.vertices]


def mesh_counts(obj):
    obj.data.calc_loop_triangles()
    return {"vertices": len(obj.data.vertices), "faces": len(obj.data.polygons), "triangles": len(obj.data.loop_triangles)}


def image_paths(root):
    return [relative(root, Path(bpy.path.abspath(image.filepath))) for image in bpy.data.images if image.source == "FILE" and image.filepath]


def rendering_stage(bounds, resolution):
    stage = collection("RENDER_STAGE")
    center = Vector([(bounds["min"][i] + bounds["max"][i]) * 0.5 for i in range(3)])
    diagonal = max(Vector(bounds["dimensions"]).length, 0.1)
    for name, offset, power, size in (
        ("Key", (1.0, -1.5, 2.0), 1300, 1.4),
        ("Fill", (-1.5, -0.3, 0.7), 800, 1.6),
        ("Rim", (0.2, 1.5, 1.0), 1050, 1.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power * diagonal * diagonal
        data.shape = "DISK"
        data.size = size * diagonal
        obj = bpy.data.objects.new(name, data)
        stage.objects.link(obj)
        obj.location = center + Vector(offset) * diagonal
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("Scan inspection orthographic camera")
    camera = bpy.data.objects.new("Scan inspection orthographic camera", camera_data)
    stage.objects.link(camera)
    camera_data.type = "ORTHO"
    camera_data.clip_start = max(diagonal * 0.001, 0.0001)
    camera_data.clip_end = diagonal * 20
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    return camera, center, diagonal


def render_views(root, objects, prefix, resolution):
    points = [point for obj in objects for point in object_points(obj)]
    bounds = bounding_box(points)
    if bounds is None:
        return []
    camera, center, diagonal = rendering_stage(bounds, resolution)
    output = root / "docs" / "scan_views"
    output.mkdir(parents=True, exist_ok=True)
    views = {
        "isometric": (1.3, -1.8, 1.25),
        "front": (0, -1, 0),
        "top": (0, 0, 1),
        "side": (1, 0, 0),
    }
    outputs = []
    for name, direction in views.items():
        camera.location = center + Vector(direction).normalized() * diagonal * 3
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        inverse = camera.matrix_world.inverted()
        projected = [inverse @ point for point in points]
        width = max(p.x for p in projected) - min(p.x for p in projected)
        height = max(p.y for p in projected) - min(p.y for p in projected)
        camera.data.ortho_scale = max(width, height, 0.01) * 1.16
        path = output / f"{prefix}_{name}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        outputs.append(relative(root, path))
    return outputs


def alignment_matrix(alignment):
    scale = float(alignment.get("scale", 1.0))
    rotation = float(alignment.get("rotation_z", 0.0))
    translation = [float(value) for value in alignment.get("translation", [0, 0, 0])]
    if scale <= 0 or len(translation) != 3 or not all(math.isfinite(x) for x in [scale, rotation, *translation]):
        raise ValueError("Alignment requires finite values, positive uniform scale and three translation coordinates.")
    return Matrix.Translation(Vector(translation)) @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Scale(scale, 4)


def selected_faces(source, coordinates, spec):
    regions = spec.get("regions", [])
    if not regions:
        raise ValueError(f"Part {spec['name']} needs an explicit selection region.")
    mode = spec.get("selection", "all_vertices")
    exclusions = spec.get("exclude_regions", [])
    epsilon = float(spec.get("selection_epsilon", 1e-8))

    def inside(point, region):
        return all(float(region["min"][i]) - epsilon <= point[i] <= float(region["max"][i]) + epsilon for i in range(3))

    result = []
    for face in source.data.polygons:
        vertices = [coordinates[index] for index in face.vertices]
        centroid = sum(vertices, Vector()) / len(vertices)
        keep = False
        for region in regions:
            method = region.get("selection", mode)
            if method == "all_vertices":
                keep = all(inside(point, region) for point in vertices)
            elif method == "centroid":
                keep = inside(centroid, region)
            else:
                raise ValueError(f"Unknown region selection mode: {method}")
            if keep:
                break
        if keep and not any(inside(centroid, region) for region in exclusions):
            result.append(face.index)
    return result


def filter_components(mesh, face_indices, minimum):
    """Discard small islands through virtual 1 micrometre edge connectivity.

    OBJ/scan UV seams can duplicate vertices along a continuous surface.  Only
    the connectivity keys are quantized; mesh vertices and UVs stay intact.
    """
    if minimum <= 1 or not face_indices:
        return face_indices, 0, []
    parent = list(range(len(face_indices)))
    sizes = [1] * len(face_indices)

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            if sizes[a] < sizes[b]:
                a, b = b, a
            parent[b] = a
            sizes[a] += sizes[b]

    position_ids = {}
    canonical_vertices = []
    for vertex in mesh.vertices:
        key = tuple(round(float(value) / 1e-6) for value in vertex.co)
        canonical_vertices.append(position_ids.setdefault(key, len(position_ids)))
    edge_owner = {}
    for local_index, face_index in enumerate(face_indices):
        verts = tuple(canonical_vertices[index] for index in mesh.polygons[face_index].vertices)
        for index, first in enumerate(verts):
            edge = tuple(sorted((first, verts[(index + 1) % len(verts)])))
            if edge in edge_owner:
                union(local_index, edge_owner[edge])
            else:
                edge_owner[edge] = local_index
    component_sizes = {}
    for index in range(len(face_indices)):
        component_sizes[find(index)] = component_sizes.get(find(index), 0) + 1
    retained = [face for index, face in enumerate(face_indices) if component_sizes[find(index)] >= minimum]
    return retained, len(face_indices) - len(retained), sorted(component_sizes.values(), reverse=True)


def make_part(source, coordinates, face_indices, spec, destination):
    origin = Vector(spec["origin_world"])
    used = sorted({index for face in face_indices for index in source.data.polygons[face].vertices})
    mapping = {old: new for new, old in enumerate(used)}
    vertices = [coordinates[index] - origin for index in used]
    faces = [[mapping[index] for index in source.data.polygons[face].vertices] for face in face_indices]
    mesh = bpy.data.meshes.new(spec["name"] + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for material in source.data.materials:
        mesh.materials.append(material)
    for output_face, source_index in zip(mesh.polygons, face_indices):
        source_face = source.data.polygons[source_index]
        output_face.material_index = source_face.material_index
        output_face.use_smooth = source_face.use_smooth
    for source_layer in source.data.uv_layers:
        layer = mesh.uv_layers.new(name=source_layer.name)
        for output_face, source_index in zip(mesh.polygons, face_indices):
            source_face = source.data.polygons[source_index]
            for out_loop, source_loop in zip(output_face.loop_indices, source_face.loop_indices):
                layer.data[out_loop].uv = source_layer.data[source_loop].uv
    obj = bpy.data.objects.new(spec["name"], mesh)
    destination.objects.link(obj)
    obj.location = origin
    obj["webots_solid_def"] = spec.get("solid_def", "")
    obj["origin_world_m"] = list(origin)
    obj["selection_mode"] = spec.get("selection", "all_vertices")
    obj["source_face_count"] = len(face_indices)
    bpy.context.view_layer.update()
    return obj


def reduce_part(obj, target):
    before = mesh_counts(obj)
    if target and before["triangles"] > int(target):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new("Visual silhouette reduction", "DECIMATE")
        modifier.decimate_type = "COLLAPSE"
        modifier.ratio = int(target) / before["triangles"]
        modifier.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return before, mesh_counts(obj)


def export_local_obj(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    origin = obj.location.copy()
    # The .blend displays parts globally; the OBJ must be local to its Solid.
    obj.location = (0, 0, 0)
    bpy.context.view_layer.update()
    try:
        bpy.ops.wm.obj_export(
            filepath=str(path), check_existing=False,
            forward_axis="Y", up_axis="Z", global_scale=1.0,
            apply_modifiers=True, apply_transform=True,
            export_selected_objects=True, export_triangulated_mesh=True,
            export_uv=True, export_normals=True, export_materials=False,
        )
    finally:
        obj.location = origin
        bpy.context.view_layer.update()


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Store texture paths relative to this .blend, never in reference originals.
    for image in bpy.data.images:
        if image.source == "FILE" and image.filepath:
            absolute = bpy.path.abspath(image.filepath)
            image.filepath = "//" + str(Path(absolute).relative_to(path.parent)).replace("\\", "/") if Path(absolute).is_relative_to(path.parent) else str(Path(absolute))
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)


def main():
    args = arguments()
    root = args.project_root.resolve()
    config = {}
    if args.mode == "final":
        config = json.loads(resolved(root, args.config).read_text(encoding="utf-8-sig"))
    source_path = resolved(root, config.get("source_obj", args.source_obj))
    scene = reset_background_scene()
    raw_collection = collection("RAW_SCAN_REFERENCE")
    raw = import_source(source_path, raw_collection)
    report = {
        "mode": args.mode,
        "blender_version": bpy.app.version_string,
        "source_obj": relative(root, source_path),
        "source_counts": mesh_counts(raw),
        "source_bbox_m": bounding_box(object_points(raw)),
        "coordinate_system": "+X right, +Y back, +Z up; metres; OBJ export Y-forward/Z-up identity",
        "textures": image_paths(root),
    }
    if args.mode == "inspect":
        report["renders"] = [] if args.no_render else render_views(root, [raw], "raw", args.resolution)
        blend_path = root / "blender" / "scan_inspection.blend"
        save_blend(blend_path)
        report["blend_file"] = relative(root, blend_path)
        write_json(root / "docs" / "scan_raw_preview.json", report)
    else:
        alignment = config.get("alignment", {})
        transform = alignment_matrix(alignment)
        coordinates = [transform @ vert.co for vert in raw.data.vertices]
        aligned_collection = collection("ALIGNED_SCAN_REFERENCE")
        aligned = raw.copy()
        aligned.data = raw.data.copy()
        aligned.name = "SCAN_ALIGNED_WORLD_REFERENCE"
        aligned_collection.objects.link(aligned)
        for vertex, point in zip(aligned.data.vertices, coordinates):
            vertex.co = point
        aligned.data.update()
        raw_collection.hide_render = raw_collection.hide_viewport = True
        aligned_collection.hide_render = aligned_collection.hide_viewport = True
        visual_collection = collection("WEBOTS_VISUAL_LINKS")
        parts = []
        report["alignment"] = alignment
        report["aligned_bbox_m"] = bounding_box(coordinates)
        report["parts"] = []
        for spec in config.get("parts", []):
            if not spec.get("enabled", True):
                continue
            name = spec["name"]
            if not name or Path(name).name != name or any(character in name for character in ':\\/'):
                raise ValueError(f"Invalid part name: {name}")
            faces = selected_faces(raw, coordinates, spec)
            selected_count = len(faces)
            faces, discarded, components = filter_components(raw.data, faces, int(spec.get("min_component_faces", 0)))
            if not faces:
                raise ValueError(f"Part {name} selected no usable faces; revise its regions.")
            obj = make_part(raw, coordinates, faces, spec, visual_collection)
            before, after = reduce_part(obj, spec.get("target_triangles", 0))
            output_path = resolved(root, spec.get("output_obj", f"meshes/{name}.obj"))
            export_local_obj(obj, output_path)
            parts.append(obj)
            report["parts"].append({
                "name": name, "solid_def": spec.get("solid_def", ""),
                "origin_world_m": list(spec["origin_world"]),
                "regions_world_m": spec["regions"],
                "selection_mode": spec.get("selection", "all_vertices"),
                "source_faces_selected": selected_count,
                "faces_discarded_small_components": discarded,
                "component_sizes_faces": components,
                "before_decimate": before, "after_decimate": after,
                "triangle_reduction_percent": (1 - after["triangles"] / before["triangles"]) * 100 if before["triangles"] else 0,
                "bbox_local_m": bounding_box(object_points(obj, world=False)),
                "bbox_world_m": bounding_box(object_points(obj)),
                "object_rotation_rad": list(obj.rotation_euler), "object_scale": list(obj.scale),
                "obj_file": relative(root, output_path), "obj_bytes": output_path.stat().st_size,
                "uv_layers": [layer.name for layer in obj.data.uv_layers],
            })
        if not parts:
            raise ValueError("The integration configuration contains no enabled parts.")
        report["renders"] = [] if args.no_render else render_views(root, parts, "processed", args.resolution)
        blend_path = resolved(root, config.get("blend_file", "blender/cartesian_scan_cleanup.blend"))
        save_blend(blend_path)
        report["blend_file"] = relative(root, blend_path)
        report["total_obj_bytes"] = sum(part["obj_bytes"] for part in report["parts"])
        write_json(resolved(root, config.get("report_file", "docs/mesh_processing.json")), report)
    print("SCAN_BLENDER_RESULT " + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
