"""Compare the final core validation with its checkpoint and inventory stage 2."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "backups/stage1_validated"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (ROOT / "docs" / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    core = read(ROOT / "docs/validation_report.json")
    baseline = read(BASE / "docs/validation_report.json")
    visual = read(ROOT / "docs/scan_visual_validation.json")
    guard = read(ROOT / "docs/kinematic_invariants.json")
    metrics = {name: {"stage1": value, "stage2": core["continuous_metrics"][name],
                      "delta": core["continuous_metrics"][name] - value}
               for name, value in baseline["continuous_metrics"].items()}
    identical_checks = [c["name"] for c in core["checks"]] == [c["name"] for c in baseline["checks"]]
    protected = ["config/robot_parameters.json", "controllers/cartesian_controller/cartesian_controller.py",
                 "controllers/cartesian_controller/runtime.ini"]
    protected_results = {path: sha(ROOT / path) == sha(BASE / path) for path in protected}
    resource = next(check['details'] for check in visual['checks']
                    if check['name'] == 'visual_mesh_resource_and_local_bounds')
    validated_asset_unchanged = sha(ROOT / resource['asset']) == resource['sha256']
    originals = read(ROOT / "docs/reference_manifest.json")
    differences = [entry["Name"] for entry in originals
                   if not (ROOT / "referencias" / entry["Name"]).is_file()
                   or sha(ROOT / "referencias" / entry["Name"]).upper() != entry["SHA256"].upper()]
    integrity = {"all_originals_unchanged": not differences, "verified_file_count": len(originals),
                 "differences": differences, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    write("reference_integrity.json", integrity)
    logs = {}
    for name in ("validation_webots_stdout.log", "validation_webots_stderr.log",
                 "scan_visual_webots_stdout.log", "scan_visual_webots_stderr.log"):
        content = (ROOT / "docs" / name).read_text(encoding="utf-8-sig")
        logs[name] = {"bytes": (ROOT / "docs" / name).stat().st_size,
                      "warning_error_lines": [line for line in content.splitlines()
                          if re.search(r"\b(?:WARNING|ERROR|OpenGL error)\b|Traceback", line, re.I)]}
    passed = (core["passed"] and visual["passed"] and identical_checks and len(core["checks"]) == 23
              and sum(c["name"].startswith("visual_") for c in visual["checks"]) == 11
              and all(protected_results.values()) and not differences
              and all(value["delta"] == 0 for value in metrics.values())
              and guard["passed"] and validated_asset_unchanged
              and not any(log["warning_error_lines"] for log in logs.values()))
    comparison = {"passed": passed, "core_checks": len(core["checks"]), "core_check_names_unchanged": identical_checks,
                  "visual_total_checks": len(visual["checks"]), "protected_files_byte_identical": protected_results,
                  "validated_asset_unchanged": validated_asset_unchanged,
                  "original_reference_integrity": integrity, "continuous_metrics_comparison": metrics,
                  "core_simulation_time_s": core["simulation_time_s"],
                  "core_simulation_time_unchanged": core["simulation_time_s"] == baseline["simulation_time_s"],
                  "logs": logs, "regressions_detected": not passed}
    write("stage2_regression_comparison.json", comparison)
    checkpoint = read(BASE / "checkpoint_manifest.json")
    files = []
    for folder in ("blender", "config", "controllers", "docs", "meshes", "protos", "textures", "tools", "worlds"):
        files.extend(path for path in (ROOT / folder).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    files.append(ROOT / "README.md")
    changes = []
    for path in sorted(files):
        relative = path.relative_to(ROOT).as_posix()
        digest = sha(path)
        old = checkpoint["files"].get(relative)
        if old != digest and relative != "docs/stage2_change_manifest.json":
            changes.append({"path": relative, "status": "created" if old is None else "modified",
                            "bytes": path.stat().st_size, "sha256": digest})
    write("stage2_change_manifest.json", {"git_state": checkpoint["git_state"],
          "scope": "Project artifacts; excludes references, backups, local dependencies, Python caches and this manifest itself.",
          "files": changes})
    print(json.dumps({"passed": passed, "core_checks": len(core["checks"]),
                      "visual_checks": len(visual["checks"]), "originals_unchanged": not differences,
                      "changed_or_created_files": len(changes), "metric_deltas": {k: v["delta"] for k, v in metrics.items()}}))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
