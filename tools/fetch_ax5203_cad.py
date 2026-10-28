"""Preserve the AX5203 STEP archive from Beckhoff's official download index."""
from __future__ import annotations
import hashlib
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = "https://download.beckhoff.com/download/technical_drawings/Drive_Technology/step/AX5000/"
PRODUCT = "https://www.beckhoff.com/en-en/products/motion/servo-drives/ax5000-digital-compact-servo-drives/ax5203.html"
DEST = ROOT / "cad/source/beckhoff"


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 academic CAD provenance inspection"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read(), response.geturl()


def preserve(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"Refusing to overwrite differing original: {path}")
    else:
        path.write_bytes(data)
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    listing_bytes, listing_url = get(DIRECTORY)
    listing = listing_bytes.decode("utf-8", errors="replace")
    links = re.findall(r'href=["\']([^"\']+)', listing, flags=re.I)
    matching = [link for link in links if link.rsplit("/", 1)[-1].lower() == "ax5203_stp.zip"]
    if len(matching) != 1:
        raise RuntimeError("No unique AX5203 archive in the official directory listing.")
    url = urllib.request.urljoin(listing_url, matching[0])
    payload, actual_url = get(url)
    DEST.mkdir(parents=True, exist_ok=True)
    assets = [preserve(DEST / "AX5203_stp.zip", payload)]
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        members = archive.namelist()
        for member in archive.infolist():
            if member.is_dir() or Path(member.filename).suffix.lower() not in (".step", ".stp"):
                continue
            if member.file_size > 50_000_000:
                raise RuntimeError("Unexpected STEP size in archive.")
            name = Path(member.filename.replace("\\", "/")).name
            assets.append(preserve(DEST / name, archive.read(member)))
    page_note = ""
    try:
        page, _ = get(PRODUCT)
        clean = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", "", page.decode("utf-8", errors="replace"), flags=re.S | re.I)
        clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", clean))
        page_note = clean
    except Exception as exc:
        page_note = "Product page retrieval failed: " + str(exc)
    dimensions = {}
    for key, expression in (("height_without_connectors", r"Height without connectors\s+(\d+(?:\.\d+)?)\s*mm"),
                            ("depth_without_connectors", r"Depth without connectors\s+(\d+(?:\.\d+)?)\s*mm"),
                            ("width", r"Width\s+(\d+(?:\.\d+)?)\s*mm")):
        match = re.search(expression, page_note, flags=re.I)
        if match:
            dimensions[key] = float(match.group(1))
    conversion_path = ROOT / "cad/reports/ax5203_conversion.json"
    conversion = json.loads(conversion_path.read_text()) if conversion_path.exists() else None
    step_asset = next(Path(ROOT / a["path"]) for a in assets if Path(a["path"]).suffix.lower() in (".stp", ".step"))
    step_header = step_asset.read_text(encoding="latin1").split("ENDSEC;", 1)[0]
    header_date = re.search(r"'(\d{4}-\d{2}-\d{2}T[^']+)'", step_header)
    report = {"component": "AX5203", "manufacturer": "Beckhoff", "observed_model": "AX5203",
              "full_electrical_suffix_on_machine": None, "status": "DOWNLOADED_OFFICIAL_STEP",
              "official": True, "classification": "C - official AX5203 CAD; visual compatibility awaits envelope and hardware-revision reconciliation",
              "exact_part_number": False, "source_url": actual_url, "directory_url": listing_url,
              "product_url": PRODUCT, "format": "ZIP containing STEP", "consulted_utc": datetime.now(timezone.utc).isoformat(),
              "assets": assets, "archive_members": members, "usage": "Local academic project only; not redistributed externally",
              "license": "Manufacturer CAD, all proprietary rights retained; no open redistribution license identified in archive",
              "manual_real_dimensions_mm": None, "official_product_dimensions_mm": dimensions,
              "published_order_code_family": "AX5203-0000-0x0x",
              "step_header_created": header_date.group(1) if header_date else None,
              "step_internal_product_name": "AX-2Kanal-ohne-Modul",
              "step_export_software": "Autodesk Inventor 2008",
              "integration": "Prepared asset only; not integrated into the robot or cabinet",
              "envelope_warning": "Current product dimensions exclude connectors. STEP includes a different full envelope; hardware revision and CAD state have not been reconciled. Do not claim an exact suffix match or automatically integrate.",
              "converted_asset": {"obj": conversion["output"], "obj_sha256": conversion["output_sha256"],
                                  "obj_bytes": conversion["output_size_bytes"], "cad_bbox_mm": conversion["cad_bbox_mm"],
                                  "cad_solids": conversion["cad_solids"], "cad_faces": conversion["cad_faces"],
                                  "triangles": conversion["tessellation"]["triangles"], "report": str(conversion_path.relative_to(ROOT))}
                                 if conversion else None,
              "lookup_budget": "Two searches; only official directory and product page; no priority3 research."}
    path = ROOT / "cad/reports/ax5203_research.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "source_url": actual_url, "assets": assets}, indent=2))


if __name__ == "__main__":
    main()
