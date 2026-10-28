"""Read manufacturer STEP geometry without rewriting source or derived meshes."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".tools" / "cad_reader"))
sys.path.insert(0, str(ROOT / "tools"))
from convert_official_cad import items, vec, bbox, sha256
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS

records = []
for name in ("AM3023-1xx0.step", "AM3023-1xx1.step"):
    source = ROOT / "cad" / "source" / "beckhoff" / name
    before = sha256(source)
    reader = STEPControl_Reader()
    reader.ReadFile(str(source))
    reader.TransferRoots()
    shape = reader.OneShape()
    cylinders = []
    for index, item in enumerate(items(shape, TopAbs_FACE), 1):
        face = TopoDS.Face_s(item)
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis()
        bounds = bbox(face)
        direction = vec(axis.Direction())
        location = vec(axis.Location())
        # Axial cylindrical surfaces at front end include shaft, pilot and holes.
        if abs(direction[2]) > 0.999 and bounds["max"][2] > -8:
            cylinders.append({"face": index, "radius_mm": cylinder.Radius(),
                              "axis_location_mm": location,
                              "axis_direction": direction, "bbox_mm": bounds})
    record = {"source": str(source.relative_to(ROOT)), "sha256": before,
              "source_hash_unchanged": sha256(source) == before,
              "native_front_mounting_plane_z_mm": -0.8,
              "native_shaft_direction": [0, 0, 1],
              "front_axial_cylinders": cylinders}
    records.append(record)
out = ROOT / "cad" / "reports" / "am3023_mounting_features.json"
out.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
for record in records:
    print(record["source"])
    for cylinder in record["front_axial_cylinders"]:
        if cylinder["radius_mm"] >= 2:
            print(cylinder["face"], round(cylinder["radius_mm"], 6),
                  [round(v, 6) for v in cylinder["axis_location_mm"]],
                  [round(v, 6) for v in cylinder["bbox_mm"]["min"]],
                  [round(v, 6) for v in cylinder["bbox_mm"]["max"]])
