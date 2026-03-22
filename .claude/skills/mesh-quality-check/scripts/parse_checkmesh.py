#!/usr/bin/env python3
"""Parse OpenFOAM checkMesh output into structured JSON."""

import re
import json
import sys


def parse_checkmesh(text: str) -> dict:
    """Parse checkMesh output text into a structured dictionary."""
    result = {
        "solver": "OpenFOAM",
        "mesh_stats": {},
        "cell_types": {},
        "topology": {},
        "geometry": {},
        "patches": [],
        "overall_status": "UNKNOWN",
    }

    # --- Mesh Statistics ---
    stat_patterns = {
        "points": r"^\s+points:\s+(\d+)",
        "internal_points": r"^\s+internal points:\s+(\d+)",
        "faces": r"^\s+faces:\s+(\d+)",
        "internal_faces": r"^\s+internal faces:\s+(\d+)",
        "cells": r"^\s+cells:\s+(\d+)",
        "boundary_patches": r"^\s+boundary patches:\s+(\d+)",
        "point_zones": r"^\s+point zones:\s+(\d+)",
        "face_zones": r"^\s+face zones:\s+(\d+)",
        "cell_zones": r"^\s+cell zones:\s+(\d+)",
    }
    for key, pattern in stat_patterns.items():
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            result["mesh_stats"][key] = int(m.group(1))

    m = re.search(r"^\s+faces per cell:\s+([\d.]+)", text, re.MULTILINE)
    if m:
        result["mesh_stats"]["faces_per_cell"] = float(m.group(1))

    # --- Cell Type Counts ---
    cell_types = [
        "hexahedra", "prisms", "wedges", "pyramids",
        "tet wedges", "tetrahedra", "polyhedra",
    ]
    for ct in cell_types:
        m = re.search(rf"^\s+{ct}:\s+(\d+)", text, re.MULTILINE)
        if m:
            key = ct.replace(" ", "_")
            result["cell_types"][key] = int(m.group(1))

    # --- Topology Checks ---
    topo_checks = [
        "Boundary definition",
        "Cell to face addressing",
        "Point usage",
        "Upper triangular ordering",
        "Face vertices",
    ]
    for check in topo_checks:
        m = re.search(rf"{check}\s+(OK|FAILED)", text)
        if m:
            key = check.lower().replace(" ", "_")
            result["topology"][key] = m.group(1)

    m = re.search(r"Number of regions:\s+(\d+)", text)
    if m:
        result["topology"]["regions"] = int(m.group(1))

    # --- Geometry Quality Metrics ---
    m = re.search(r"Max cell openness = ([\d.eE+-]+)\s+(OK|[\*]+)", text)
    if m:
        result["geometry"]["max_cell_openness"] = {
            "value": float(m.group(1)),
            "status": "OK" if "OK" in m.group(2) else "FAIL",
        }

    m = re.search(r"Max aspect ratio = ([\d.eE+-]+)\s+(OK|[\*]+)", text)
    if m:
        result["geometry"]["max_aspect_ratio"] = {
            "value": float(m.group(1)),
            "status": "OK" if "OK" in m.group(2) else "FAIL",
        }

    m = re.search(
        r"Minimum face area = ([\deE.+-]+?)\.\s+Maximum face area = ([\deE.+-]+?)\.",
        text,
    )
    if m:
        result["geometry"]["face_area"] = {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
        }

    m = re.search(
        r"Min volume = (-?[\deE.+-]+?)\.\s+Max volume = ([\deE.+-]+?)\.", text
    )
    if m:
        min_vol = float(m.group(1))
        result["geometry"]["volume"] = {
            "min": min_vol,
            "max": float(m.group(2)),
            "has_negative": min_vol <= 0,
        }

    m = re.search(
        r"Mesh non-orthogonality Max: ([\d.eE+-]+)\s+average: ([\d.eE+-]+)",
        text,
    )
    if m:
        result["geometry"]["non_orthogonality"] = {
            "max": float(m.group(1)),
            "average": float(m.group(2)),
        }

    m = re.search(r"Non-orthogonality check (OK|FAILED)", text)
    if m:
        result["geometry"].setdefault("non_orthogonality", {})["status"] = m.group(1)

    m = re.search(r"Max skewness = ([\d.eE+-]+)\s+(OK|[\*]+)", text)
    if m:
        result["geometry"]["max_skewness"] = {
            "value": float(m.group(1)),
            "status": "OK" if "OK" in m.group(2) else "FAIL",
        }

    # --- Extended geometry metrics ---
    m = re.search(
        r"Min/max edge length = ([\d.eE+-]+)\s+([\d.eE+-]+)", text
    )
    if m:
        result["geometry"]["edge_length"] = {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
        }

    m = re.search(r"Min/max cell volume ratio = ([\d.eE+-]+)", text)
    if m:
        result["geometry"]["min_volume_ratio"] = float(m.group(1))

    m = re.search(
        r"Min/max face twist = ([\d.eE+-]+)\s+([\d.eE+-]+)", text
    )
    if m:
        result["geometry"]["face_twist"] = {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
        }

    m = re.search(
        r"Min/max cell determinant = ([\d.eE+-]+)\s+([\d.eE+-]+)", text
    )
    if m:
        result["geometry"]["determinant"] = {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
        }

    m = re.search(
        r"Min/max\(weighted\) cell interpolation weights = ([\d.eE+-]+)\s+([\d.eE+-]+)",
        text,
    )
    if m:
        result["geometry"]["interpolation_weight"] = {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
        }

    # --- Failure detail lines ---
    m = re.search(r"There are (\d+) cells with negative volume", text)
    if m:
        result["geometry"]["negative_volume_cells"] = int(m.group(1))

    m = re.search(
        r"Number of severely non-orthogonal \(> (\d+)\) faces: (\d+)", text
    )
    if m:
        result["geometry"]["severely_non_orthogonal_faces"] = {
            "threshold": int(m.group(1)),
            "count": int(m.group(2)),
        }

    m = re.search(r"Number of non-orthogonality errors: (\d+)", text)
    if m:
        result["geometry"]["non_orthogonality_errors"] = int(m.group(1))

    m = re.search(
        r"Number of cells with high aspect ratio \(> ([\d.]+)\): (\d+)", text
    )
    if m:
        result["geometry"]["high_aspect_ratio_cells"] = {
            "threshold": float(m.group(1)),
            "count": int(m.group(2)),
        }

    # --- Patch topology ---
    patch_pattern = re.compile(
        r"^\s{10,}(\S+)\s+(\d+)\s+(\d+)\s+(.*)", re.MULTILINE
    )
    for pm in patch_pattern.finditer(text):
        if pm.group(1) not in ("Patch", "---"):
            result["patches"].append({
                "name": pm.group(1),
                "faces": int(pm.group(2)),
                "points": int(pm.group(3)),
                "topology": pm.group(4).strip(),
            })

    # --- Overall status ---
    if re.search(r"^Mesh OK\.", text, re.MULTILINE):
        result["overall_status"] = "OK"
    else:
        m = re.search(r"^Failed (\d+) mesh checks\.", text, re.MULTILINE)
        if m:
            result["overall_status"] = f"FAILED ({m.group(1)} checks)"

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_checkmesh.py <checkMesh_log_file_or_->")
        print("  Use '-' to read from stdin")
        sys.exit(1)

    path = sys.argv[1]
    if path == "-":
        text = sys.stdin.read()
    else:
        with open(path) as f:
            text = f.read()

    result = parse_checkmesh(text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
