"""Inventory CAD conversion tools and project-local OCP bindings."""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".tools" / "cad_reader"
sys.path.insert(0, str(LOCAL))


def main():
    executables = {name: shutil.which(name) for name in ("FreeCAD", "FreeCADCmd", "FreeCADCmd.exe", "FreeCAD.exe", "CADAssistant", "cadassistant.exe", "assimp", "gmsh")}
    roots = [Path("C:/Program Files"), Path("C:/Program Files (x86)"),
             Path.home() / "AppData/Local/Programs", Path("E:/SteamLibrary/steamapps/common")]
    candidates = []
    for root in roots:
        if root.exists():
            for folder in root.iterdir():
                if folder.is_dir() and any(s in folder.name.lower() for s in ("freecad", "cad assistant", "cascade", "gmsh", "assimp", "blender")):
                    candidates.append(str(folder))
    distributions = []
    for dist in importlib.metadata.distributions(path=[str(LOCAL)]):
        distributions.append({"name": dist.metadata["Name"], "version": dist.version,
                              "license": dist.metadata.get("License"), "requires": dist.requires})
    local_files = [p for p in LOCAL.rglob("*") if p.is_file()]
    binaries = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                 "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in local_files if p.suffix in (".pyd", ".dll")]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "python": sys.executable,
        "python_version": platform.python_version(), "platform": platform.platform(),
        "executables_on_path": executables, "standard_install_roots_checked": list(map(str, roots)),
        "matching_directories": candidates, "scope": "PATH and standard install directories; no exhaustive drive search.",
        "chosen_converter": "cadquery-ocp-novtk 7.9.3.1.1, OCCT 7.9.3, project-local Python bindings",
        "local_dependency_directory": str(LOCAL.relative_to(ROOT)), "local_distributions": distributions,
        "local_dependency_size_bytes": sum(p.stat().st_size for p in local_files), "local_binaries": binaries,
        "download": {"pypi": "https://pypi.org/project/cadquery-ocp-novtk/7.9.3.1.1/",
                     "wheel": "cadquery_ocp_novtk-7.9.3.1.1-cp312-cp312-win_amd64.whl",
                     "wheel_size_bytes": 46364919,
                     "wheel_sha256_from_pypi": "5d22339cdaac64c396f0658de8728915acfac9b868406f0078e52f50a3c25c65",
                     "additional_dependency": "cadquery-ocp-proxy 7.9.3.1.1 (approximately 3.3 kB wheel)"},
        "license": {"python_wrapper": "Apache-2.0", "occt": "LGPL-2.1 with Open CASCADE exception",
                    "wrapper_source": "https://github.com/CadQuery/OCP", "occt_source": "https://dev.opencascade.org/resources/licensing"},
        "reproduce_install": [sys.executable, "-m", "pip", "install", "--target", ".tools/cad_reader", "cadquery-ocp-novtk==7.9.3.1.1"],
        "conversion_method": "STEP via OCCT XCAF, native face colors and solid inheritance; BRepMesh absolute deflection; metre-scale OBJ+MTL.",
        "reliability": "Native OpenCascade STEP reader and CAD tessellator. Each source hash verified unchanged; BRep validity and missing faces checked. Blender optimization is a separate derivative stage.",
        "other_software_installed": False, "global_python_changes": False,
        "blender_step_support": "No native STEP import used. Only converted OBJ goes into background Blender.",
    }
    path = ROOT / "cad/reports/conversion_environment.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "dependency_bytes": report["local_dependency_size_bytes"], "packages": distributions}, indent=2))


if __name__ == "__main__":
    main()
