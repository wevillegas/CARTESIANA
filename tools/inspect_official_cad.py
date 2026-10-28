"""Extract AM3023 dimensional features from unmodified manufacturer STEP."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from convert_official_cad import (ROOT, BRepAdaptor_Surface, BRepGProp, GProp_GProps,
                                  STEPControl_Reader, IFSelect_RetDone, TopAbs_FACE,
                                  GeomAbs_Cylinder, GeomAbs_Plane, TopoDS, bbox, items, sha256, vec)


def inspect(path):
    before = sha256(path)
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError("STEP read failed.")
    reader.SetSystemLengthUnit(1.0)
    reader.TransferRoots()
    shape = reader.OneShape()
    front_planes, rear_planes, shafts, mounting, pilot, pilot_end = [], [], [], [], [], []
    for index, part in enumerate(items(shape, TopAbs_FACE), 1):
        face = TopoDS.Face_s(part)
        surface = BRepAdaptor_Surface(face, True)
        extent = bbox(face)
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, props)
        if surface.GetType() == GeomAbs_Plane:
            normal = vec(surface.Plane().Axis().Direction())
            if abs(normal[2]) > .999999 and props.Mass() > 100:
                entry = {"face": index, "z_mm": props.CentreOfMass().Z(), "area_mm2": props.Mass(),
                         "bbox_mm": extent}
                if normal[2] > .999999 and abs(extent["dimensions"][0] - 58) < .01 and abs(extent["dimensions"][1] - 58) < .01:
                    front_planes.append(entry)
                if props.CentreOfMass().Z() < -100:
                    rear_planes.append(entry)
                if 0 < props.CentreOfMass().Z() < 5 and 35 < extent["dimensions"][0] < 45 and abs(extent["dimensions"][0] - extent["dimensions"][1]) < .01:
                    pilot_end.append(entry)
        elif surface.GetType() == GeomAbs_Cylinder:
            cyl = surface.Cylinder()
            axis = vec(cyl.Axis().Direction())
            origin = vec(cyl.Axis().Location())
            if abs(axis[2]) > .999999:
                entry = {"face": index, "radius_mm": cyl.Radius(), "center_xy_mm": origin[:2], "bbox_mm": extent}
                if abs(origin[0]) + abs(origin[1]) < 1e-6 and extent["max"][2] > 15:
                    shafts.append(entry)
                elif abs(origin[0]) + abs(origin[1]) < 1e-6 and 19 < cyl.Radius() < 21 and extent["max"][2] > 0:
                    pilot.append(entry)
                elif 1.5 < cyl.Radius() < 4.5 and extent["max"][2] >= -.81:
                    mounting.append(entry)
    if len(front_planes) != 1:
        raise RuntimeError("Expected one 58 x 58 mm flange plane.")
    front_z = front_planes[0]["z_mm"]
    full_bbox = bbox(shape)
    centers = sorted({tuple(round(x, 5) for x in m["center_xy_mm"]) for m in mounting})
    report = {
        "source": str(path.relative_to(ROOT)), "source_sha256": before, "source_unchanged": sha256(path) == before,
        "native_axis": "+Z shaft output; body extends -Z; connector envelope toward +Y",
        "all_units": "mm", "full_bbox": full_bbox, "flange_plane_z": front_z,
        "flange_width": front_planes[0]["bbox_mm"]["dimensions"][0],
        "flange_height": front_planes[0]["bbox_mm"]["dimensions"][1],
        "body_length_flange_to_back": front_z - full_bbox["min"][2],
        "shaft_tip_z": full_bbox["max"][2], "shaft_protrusion_from_flange": full_bbox["max"][2] - front_z,
        "shaft_diameter": max(2 * c["radius_mm"] for c in shafts),
        "pilot_cylinder_diameter": max(2 * c["radius_mm"] for c in pilot),
        "pilot_front_chamfer_end_diameter": max(p["bbox_mm"]["dimensions"][0] for p in pilot_end),
        "pilot_note": "Main cylindrical locating pilot is Ø40 mm; its front chamfer terminates at a Ø39 mm planar section. Do not confuse that section with the locating diameter.",
        "mounting_hole_center_candidates_xy": centers, "mounting_hole_cylinder_candidates": mounting,
        "front_flange_evidence": front_planes, "rear_plane_evidence": rear_planes,
        "shaft_evidence": shafts, "pilot_cylinder_evidence": pilot, "pilot_end_plane_evidence": pilot_end,
        "dimension_scope": "Envelope includes connectors and shaft. Body length excludes shaft. Manual lengths may include coupling, mount or approximate measurement; do not scale CAD to force 200/240 mm.",
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    reports = [inspect(path.resolve()) for path in args.sources]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(json.dumps([{key: d[key] for key in ("source", "flange_width", "flange_height", "body_length_flange_to_back", "shaft_protrusion_from_flange", "shaft_diameter", "mounting_hole_center_candidates_xy")} for d in reports], indent=2))


if __name__ == "__main__":
    main()
