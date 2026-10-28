"""Append the optional AX5203 family CAD to the existing Blender library.

Run once with Blender --background --factory-startup --python this_script.
No robot mesh is exported. Native STEP/OBJ vertex coordinates stay in metres.
"""
from __future__ import annotations
import array
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_official_cad_blender import counts, bounds, import_obj, sha

BLEND = ROOT / "blender/official_cad_components.blend"
SOURCE = ROOT / "cad/converted/ax5203_native.obj"
OBJECT_NAME = "AX5203_OFFICIAL_LIBRARY_CLASS_C"
PREVIEW = ROOT / "docs/cad_views/ax5203_blender.jpg"
REPORT = ROOT / "cad/reports/ax5203_blender_processing.json"


def mesh_signature(obj):
    digest = hashlib.sha256()
    if obj.type == "MESH":
        vertices = array.array("f", [0.0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get("co", vertices)
        loops = array.array("i", [0]) * len(obj.data.loops)
        obj.data.loops.foreach_get("vertex_index", loops)
        materials = array.array("i", [0]) * len(obj.data.polygons)
        obj.data.polygons.foreach_get("material_index", materials)
        digest.update(vertices.tobytes()); digest.update(loops.tobytes()); digest.update(materials.tobytes())
        digest.update(json.dumps([m.name if m else None for m in obj.data.materials]).encode())
    return {"type": obj.type, "data_signature": digest.hexdigest(),
            "matrix_world": [list(row) for row in obj.matrix_world],
            "collections": sorted(c.name for c in obj.users_collection),
            "hide_render": obj.hide_render, "hide_viewport": obj.hide_viewport}


def main():
    if not bpy.app.background:
        raise RuntimeError("Use background Blender; never modify the user's open GUI scene.")
    integrated_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT / "meshes/cad").glob("*") if p.is_file()}
    scan_path = ROOT / "blender/cartesian_scan_cleanup.blend"
    scan_hash = sha(scan_path)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    original_collections = sorted(c.name for c in bpy.data.collections)
    original_state = {o.name: mesh_signature(o) for o in bpy.data.objects
                      if o.name != OBJECT_NAME and not o.name.startswith("AX5203_LIBRARY_")}
    collection = bpy.data.collections.get("BECKHOFF_AX5203")
    if collection is None:
        raise RuntimeError("Expected the existing BECKHOFF_AX5203 collection.")
    already_appended = OBJECT_NAME in bpy.data.objects
    obj = bpy.data.objects[OBJECT_NAME] if already_appended else import_obj(SOURCE, collection)
    obj.name = OBJECT_NAME
    obj["classification"] = "C - official base model; full suffix/revision and envelope unresolved"
    obj["source"] = "cad/converted/ax5203_native.obj"
    obj["units"] = "metres"
    obj["axis_policy"] = "Native STEP axes retained. Display translation only; no functional axis assumed."
    if already_appended:
        source_report = json.loads((ROOT / "cad/reports/ax5203_conversion.json").read_text())
        tessellation = source_report["tessellation"]
        before = {"vertices": tessellation["vertices"], "faces": tessellation["triangles"], "triangles": tessellation["triangles"]}
        native_before = source_report["mesh_bbox_m"]
        obj.location = (0, 0, 0)
        bpy.context.view_layer.update()
    else:
        before = counts(obj)
        native_before = bounds(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if not already_appended:
        decimate = obj.modifiers.new("Optional library silhouette reduction", "DECIMATE")
        decimate.ratio = min(1.0, 30000 / before["triangles"])
        decimate.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=decimate.name)
    after = counts(obj)
    native_after = bounds(obj)
    # Keep raw vertices untouched and shift only the display object away from AMs.
    obj.location = (0, .5, 0)
    bpy.context.view_layer.update()
    display_bbox = bounds(obj)
    center = Vector([(display_bbox["min"][i] + display_bbox["max"][i]) / 2 for i in range(3)])
    # Blender ortho_scale spans image width; use enough room for this tall object.
    dimension = max(display_bbox["dimensions"]) * 2.2
    scene = bpy.context.scene
    previous_camera = scene.camera
    previous_filepath = scene.render.filepath
    camera = bpy.data.objects.get("AX5203_LIBRARY_PREVIEW_CAMERA")
    if camera is None:
        camera = bpy.data.objects.new("AX5203_LIBRARY_PREVIEW_CAMERA", bpy.data.cameras.new("AX5203_LIBRARY_PREVIEW_CAMERA"))
        scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = dimension
    camera.location = center + Vector((2, -3, 1.8)).normalized() * dimension * 3
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    for name, direction, energy in (("AX5203_LIBRARY_KEY", (1, -2, 3), 250), ("AX5203_LIBRARY_FILL", (-2, 1, 2), 180)):
        light = bpy.data.objects.get(name)
        if light is None:
            data = bpy.data.lights.new(name, "AREA")
            light = bpy.data.objects.new(name, data)
            scene.collection.objects.link(light)
        else:
            data = light.data
        data.energy = energy
        data.size = dimension * 1.4
        light.hide_render = False
        light.location = center + Vector(direction).normalized() * dimension * 2.5
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    for old_name in original_state:
        if bpy.data.objects[old_name].type == "MESH":
            bpy.data.objects[old_name].hide_render = True
    obj.hide_render = False
    scene.camera = camera
    scene.render.filepath = str(PREVIEW)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    for old_name, state in original_state.items():
        bpy.data.objects[old_name].hide_render = state["hide_render"]
    scene.camera = previous_camera
    scene.render.filepath = previous_filepath
    # Preview helpers remain available but inactive for the existing library scene.
    for name in ("AX5203_LIBRARY_KEY", "AX5203_LIBRARY_FILL"):
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_viewport = True
    if {name: mesh_signature(bpy.data.objects[name]) for name in original_state} != original_state:
        raise RuntimeError("An original Blender object changed.")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), check_existing=False)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    retained = {name: mesh_signature(bpy.data.objects[name]) for name in original_state} == original_state
    hashes_after = {path: sha(ROOT / path) for path in integrated_hashes}
    collections_after = sorted(c.name for c in bpy.data.collections)
    report = {
        "blender_version": bpy.app.version_string, "classification": "C", "integrated_into_webots": False,
        "blend": BLEND.relative_to(ROOT).as_posix(), "blend_bytes": BLEND.stat().st_size,
        "source": SOURCE.relative_to(ROOT).as_posix(), "source_sha256": sha(SOURCE),
        "collection": "BECKHOFF_AX5203", "object": OBJECT_NAME, "units": "metres",
        "before": before, "after": counts(bpy.data.objects[OBJECT_NAME]),
        "before_count_scope": "Raw source OBJ counts" if already_appended else "Blender imported OBJ counts",
        "target_triangles": 30000, "reduction_percent": 100 * (1 - after["triangles"] / before["triangles"]),
        "native_bbox_before_m": native_before, "native_bbox_after_m": native_after,
        "display_bbox_m": bounds(bpy.data.objects[OBJECT_NAME]), "display_translation_m": [0, .5, 0],
        "rotation": "identity", "scale": [1, 1, 1],
        "bbox_dimension_difference_m": [native_after["dimensions"][i] - native_before["dimensions"][i] for i in range(3)],
        "orientation_note": "Native STEP axes retained; no shaft or functional axis inferred for this cabinet drive.",
        "collections_before": original_collections, "collections_after": collections_after,
        "existing_collections_preserved": set(original_collections).issubset(collections_after),
        "existing_objects_preserved": retained, "existing_object_count": len(original_state),
        "integrated_mesh_sha256_before": integrated_hashes, "integrated_mesh_sha256_after": hashes_after,
        "integrated_meshes_unchanged": hashes_after == integrated_hashes,
        "scan_cleanup_blend_unchanged": sha(scan_path) == scan_hash,
        "preview": PREVIEW.relative_to(ROOT).as_posix(), "preview_bytes": PREVIEW.stat().st_size,
        "exported_robot_meshes": [],
    }
    if not retained or hashes_after != integrated_hashes or not report["scan_cleanup_blend_unchanged"]:
        raise RuntimeError("Preservation verification failed.")
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": REPORT.relative_to(ROOT).as_posix(), "before": before, "after": after,
                      "preserved": retained, "integrated_meshes_unchanged": report["integrated_meshes_unchanged"]}))


if __name__ == "__main__":
    main()
