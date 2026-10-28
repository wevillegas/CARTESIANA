"""Read-only STEP inspection and controlled OCCT tessellation to metre-scale OBJ.

Run with the bundled CPython 3.12. CAD bindings are isolated in .tools/cad_reader.
Source STEP files are hashed before and after, and are never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".tools" / "cad_reader"))

import numpy as np
import OCP
from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TColStd import TColStd_SequenceOfAsciiString
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDocStd import TDocStd_Document
from OCP.Quantity import Quantity_Color, Quantity_TOC_sRGB
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorSurf, XCAFDoc_ColorGen
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vec(p):
    return [float(p.X()), float(p.Y()), float(p.Z())]


def bbox(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    a = list(box.Get())
    return {"min": a[:3], "max": a[3:], "dimensions": [a[i + 3] - a[i] for i in range(3)]}


def items(shape, kind):
    explorer = TopExp_Explorer(shape, kind)
    while explorer.More():
        yield explorer.Current()
        explorer.Next()


def geometry_features(shape):
    planes, cylinders = [], []
    kinds = Counter()
    for index, part in enumerate(items(shape, TopAbs_FACE), 1):
        face = TopoDS.Face_s(part)
        surface = BRepAdaptor_Surface(face, True)
        kind = surface.GetType()
        kinds[str(kind)] += 1
        prop = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, prop)
        if kind == GeomAbs_Plane:
            plane = surface.Plane()
            planes.append({"face": index, "area_mm2": prop.Mass(), "centroid_mm": vec(prop.CentreOfMass()),
                           "normal": vec(plane.Axis().Direction()), "bbox_mm": bbox(face)})
        elif kind == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            cylinders.append({"face": index, "area_mm2": prop.Mass(), "radius_mm": cylinder.Radius(),
                              "axis_location_mm": vec(cylinder.Axis().Location()),
                              "axis_direction": vec(cylinder.Axis().Direction()), "bbox_mm": bbox(face)})
    return {"surface_types": dict(kinds), "largest_planes": sorted(planes, key=lambda x: x["area_mm2"], reverse=True)[:30],
            "cylinders": sorted(cylinders, key=lambda x: x["area_mm2"], reverse=True)[:60]}


def native_color(colors, shape, fallback=(0.7, 0.7, 0.7)):
    color = Quantity_Color()
    if colors.GetColor(shape, XCAFDoc_ColorSurf, color) or colors.GetColor(shape, XCAFDoc_ColorGen, color):
        return tuple(round(float(x), 9) for x in color.Values(Quantity_TOC_sRGB))
    return fallback


def triangulate_faces(shape, colors):
    """Preserve CAD face seams and smooth vertex normals within each CAD face."""
    parts = []
    missing_faces = 0
    degenerate_triangles = 0
    default_color = native_color(colors, shape)
    for sub in items(shape, TopAbs_FACE):
        face = TopoDS.Face_s(sub)
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, location)
        if triangulation is None:
            missing_faces += 1
            continue
        transform = location.Transformation()
        vertices = np.asarray([vec(triangulation.Node(i).Transformed(transform))
                               for i in range(1, triangulation.NbNodes() + 1)], dtype=float)
        faces = np.asarray([triangulation.Triangle(i).Get()
                            for i in range(1, triangulation.NbTriangles() + 1)], dtype=np.int64) - 1
        if face.Orientation() == TopAbs_REVERSED:
            faces[:, [1, 2]] = faces[:, [2, 1]]
        weighted = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]],
                            vertices[faces[:, 2]] - vertices[faces[:, 0]])
        valid = np.linalg.norm(weighted, axis=1) > 1e-12
        degenerate_triangles += int((~valid).sum())
        faces, weighted = faces[valid], weighted[valid]
        normals = np.zeros_like(vertices)
        for col in range(3):
            np.add.at(normals, faces[:, col], weighted)
        lengths = np.linalg.norm(normals, axis=1)
        normals = np.divide(normals, lengths[:, None], out=np.zeros_like(normals), where=lengths[:, None] > 0)
        parts.append((vertices * 0.001, normals, faces, native_color(colors, face, default_color)))
    return parts, missing_faces, degenerate_triangles


def convert(source, output, report_path, linear_mm, angular_degrees):
    started = time.perf_counter()
    source = Path(source).resolve()
    output = Path(output).resolve()
    report_path = Path(report_path).resolve()
    if source == output or source.suffix.lower() not in (".step", ".stp"):
        raise ValueError("Expected a source STEP and a separate derived OBJ.")
    if not output.is_relative_to(ROOT / "cad" / "converted"):
        raise ValueError("Derived output must stay in cad/converted.")
    original_hash = sha256(source)
    text = source.read_text(encoding="latin1")
    caf_reader = STEPCAFControl_Reader()
    caf_reader.SetColorMode(True)
    caf_reader.SetNameMode(True)
    if caf_reader.ReadFile(str(source)) != IFSelect_RetDone:
        raise RuntimeError(f"OpenCascade failed to read {source}")
    reader = caf_reader.Reader()
    units = [TColStd_SequenceOfAsciiString() for _ in range(3)]
    reader.FileUnits(*units)
    source_units = [[seq.Value(i).ToCString() for i in range(1, seq.Length() + 1)] for seq in units]
    # OCCT length unit is millimetres; use a uniform 0.001 factor only at export.
    reader.SetSystemLengthUnit(1.0)
    document = TDocStd_Document(TCollection_ExtendedString("BinXCAF"))
    if not caf_reader.Transfer(document):
        raise RuntimeError("STEP XCAF transfer failed.")
    colors = XCAFDoc_DocumentTool.ColorTool_s(document.Main())
    # Binding returns a reader value: obtain it again after XCAF transfer.
    reader = caf_reader.Reader()
    transferred = reader.NbRootsForTransfer()
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError("STEP transfer produced no shape.")
    solids = list(items(shape, TopAbs_SOLID))
    if not solids:
        solids = [shape]
    solid_reports = []
    for i, solid in enumerate(solids, 1):
        prop = GProp_GProps()
        BRepGProp.VolumeProperties_s(solid, prop)
        solid_reports.append({"index": i, "name": f"solid_{i:03d}", "bbox_mm": bbox(solid),
                              "volume_mm3": prop.Mass(), "centroid_mm": vec(prop.CentreOfMass()),
                              "faces": sum(1 for _ in items(solid, TopAbs_FACE)),
                              "valid_brep": BRepCheck_Analyzer(solid).IsValid()})
    mesh = BRepMesh_IncrementalMesh(shape, linear_mm, False, math.radians(angular_degrees), True)
    if not mesh.IsDone():
        raise RuntimeError("CAD tessellation did not complete.")
    output.parent.mkdir(parents=True, exist_ok=True)
    vertex_count = triangle_count = missing_count = degenerate_count = 0
    mesh_bbox_min, mesh_bbox_max = np.full(3, np.inf), np.full(3, -np.inf)
    materials = {}
    material_triangles = Counter()
    with output.open("w", encoding="ascii", newline="\n") as stream:
        stream.write(f"# Derived from {source.name}; original SHA256 {original_hash}\n")
        stream.write("# OCCT-controlled tessellation; coordinates metres; native STEP orientation retained.\n")
        stream.write(f"# Linear deflection {linear_mm} mm; angular deflection {angular_degrees} degrees.\n")
        stream.write(f"mtllib {output.with_suffix('.mtl').name}\n")
        for solid_report, solid in zip(solid_reports, solids):
            groups, missing, degenerate = triangulate_faces(solid, colors)
            missing_count += missing
            degenerate_count += degenerate
            solid_report["mesh_vertices"] = sum(len(group[0]) for group in groups)
            solid_report["mesh_triangles"] = sum(len(group[2]) for group in groups)
            stream.write(f"o {solid_report['name']}\ng {solid_report['name']}\n")
            for vertices, normals, faces, color in groups:
                if color not in materials:
                    materials[color] = f"cad_color_{len(materials) + 1:02d}"
                name = materials[color]
                stream.write(f"usemtl {name}\n")
                material_triangles[name] += len(faces)
                mesh_bbox_min = np.minimum(mesh_bbox_min, vertices.min(axis=0))
                mesh_bbox_max = np.maximum(mesh_bbox_max, vertices.max(axis=0))
                for point in vertices:
                    stream.write("v %.9g %.9g %.9g\n" % tuple(point))
                for normal in normals:
                    stream.write("vn %.8g %.8g %.8g\n" % tuple(normal))
                for triangle in faces + vertex_count + 1:
                    stream.write("f " + " ".join(f"{i}//{i}" for i in triangle) + "\n")
                vertex_count += len(vertices)
                triangle_count += len(faces)
    material_path = output.with_suffix(".mtl")
    with material_path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("# Native STEP colors, resolved with XCAF, RGB in the STEP sRGB color space.\n")
        for color, name in materials.items():
            stream.write(f"newmtl {name}\nKd " + " ".join(str(x) for x in color) + "\nKs 0.08 0.08 0.08\nNs 32\nd 1\n\n")
    report = {
        "source": str(source.relative_to(ROOT)), "source_sha256": original_hash,
        "source_size_bytes": source.stat().st_size, "source_hash_unchanged": sha256(source) == original_hash,
        "consulted_utc": datetime.now(timezone.utc).isoformat(), "tool": "cadquery-ocp-novtk",
        "tool_package_version": "7.9.3.1.1", "ocp_version": OCP.__version__, "units_from_step": source_units,
        "cad_system_units": "mm", "export_units": "m", "uniform_export_scale": 0.001,
        "axis_transform": "identity: retain native STEP XYZ; positioning belongs to downstream visual transform",
        "transferred_roots": transferred, "cad_solids": len(solids), "cad_faces": sum(1 for _ in items(shape, TopAbs_FACE)),
        "cad_bbox_mm": bbox(shape), "solids": solid_reports,
        "step_product_records": re.findall(r"PRODUCT\s*\([^;]+", text),
        "step_rgb_colors": sorted(set(re.findall(r"COLOUR_RGB\s*\([^;]+", text))),
        "color_handling": "Native STEP face colors recovered with XCAF; missing face colors inherit the solid color. OBJ+MTL retain CAD color regions and normals.",
        "materials": [{"name": name, "step_srgb": list(color), "triangles": material_triangles[name]}
                      for color, name in materials.items()],
        "material_file": str(material_path.relative_to(ROOT)),
        "material_sha256": sha256(material_path),
        "tessellation": {"linear_deflection_mm": linear_mm, "angular_deflection_degrees": angular_degrees,
                         "relative_deflection": False, "vertices": vertex_count, "triangles": triangle_count,
                         "missing_faces": missing_count, "discarded_degenerate_triangles": degenerate_count,
                         "simplification": "None. CAD tessellation only; no nonuniform scaling or feature deformation."},
        "mesh_bbox_m": {"min": mesh_bbox_min.tolist(), "max": mesh_bbox_max.tolist(),
                        "dimensions": (mesh_bbox_max - mesh_bbox_min).tolist()},
        "features": geometry_features(shape), "output": str(output.relative_to(ROOT)),
        "output_size_bytes": output.stat().st_size, "output_sha256": sha256(output),
        "elapsed_seconds": time.perf_counter() - started,
    }
    if missing_count:
        raise RuntimeError(f"{missing_count} faces were not tessellated.")
    if not report["source_hash_unchanged"]:
        raise RuntimeError("Source CAD hash changed.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("source", "cad_solids", "cad_faces", "cad_bbox_mm", "tessellation", "output", "output_size_bytes", "elapsed_seconds")}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--linear-mm", type=float, default=0.2)
    parser.add_argument("--angular-degrees", type=float, default=12.0)
    args = parser.parse_args()
    if args.linear_mm <= 0 or not 1 <= args.angular_degrees <= 45:
        parser.error("Use positive linear deflection and an angular deflection from 1 to 45 degrees.")
    convert(args.source, args.output, args.report, args.linear_mm, args.angular_degrees)


if __name__ == "__main__":
    main()
