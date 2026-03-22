#!/usr/bin/env python3
"""Evaluate parsed mesh quality data and generate a report."""

import json
import sys
import math

# ============================================================
# OpenFOAM thresholds
# ============================================================
OF_CRITERIA = {
    "non_orthogonality_max": {
        "pass": 65, "warn": 80,
        "unit": "°", "direction": "lower_better",
        "label": "Non-Orthogonality (max)",
    },
    "non_orthogonality_avg": {
        "pass": 15, "warn": 30,
        "unit": "°", "direction": "lower_better",
        "label": "Non-Orthogonality (avg)",
    },
    "max_skewness": {
        "pass": 4.0, "warn": 8.0,
        "unit": "", "direction": "lower_better",
        "label": "Skewness (max)",
    },
    "max_aspect_ratio": {
        "pass": 100, "warn": 1000,
        "unit": "", "direction": "lower_better",
        "label": "Aspect Ratio (max)",
    },
    "min_volume_ratio": {
        "pass": 0.1, "warn": 0.01,
        "unit": "", "direction": "higher_better",
        "label": "Volume Ratio (min)",
    },
    "min_determinant": {
        "pass": 0.1, "warn": 0.001,
        "unit": "", "direction": "higher_better",
        "label": "Determinant (min)",
    },
    "min_face_weight": {
        "pass": 0.2, "warn": 0.05,
        "unit": "", "direction": "higher_better",
        "label": "Interpolation Weight (min)",
    },
}

# ============================================================
# Fluent thresholds
# ============================================================
FL_CRITERIA = {
    "orthogonal_quality_min": {
        "pass": 0.3, "warn": 0.1,
        "unit": "", "direction": "higher_better",
        "label": "Orthogonal Quality (min)",
    },
    "skewness_max": {
        "pass": 0.85, "warn": 0.95,
        "unit": "", "direction": "lower_better",
        "label": "Skewness (max)",
    },
    "aspect_ratio_max": {
        "pass": 20, "warn": 100,
        "unit": "", "direction": "lower_better",
        "label": "Aspect Ratio (max)",
    },
    "cell_squish_max": {
        "pass": 0.5, "warn": 0.8,
        "unit": "", "direction": "lower_better",
        "label": "Cell Squish (max)",
    },
    "volume_change_max": {
        "pass": 5, "warn": 10,
        "unit": "", "direction": "lower_better",
        "label": "Volume Change (max)",
    },
}

REMEDIES = {
    "non_orthogonality_max": "Improve mesh smoothing. Use nSmoothPatch in snappyHexMesh. Consider hex-dominant meshing for curved surfaces. Add non-orthogonal correctors (nNonOrthogonalCorrectors 2-3) in fvSolution.",
    "non_orthogonality_avg": "Overall mesh quality is poor. Consider re-meshing with tighter quality controls or using a different meshing strategy.",
    "max_skewness": "Refine transitions between different cell sizes. Avoid sharp angles in blocking topology. Use size gradients < 1.2.",
    "max_aspect_ratio": "Reduce boundary layer growth ratio. Check for very thin cells in narrow gaps. High AR is acceptable in boundary layers but not in the core flow.",
    "min_volume_ratio": "Smooth size transitions between regions. Keep growth ratio <= 1.2. Check for sudden refinement level jumps.",
    "min_determinant": "Cells are severely deformed. Re-mesh affected regions with better quality constraints.",
    "min_face_weight": "Asymmetric interpolation detected. Improve mesh uniformity or add gradient limiters.",
    "orthogonal_quality_min": "Improve mesh smoothing. Avoid highly warped cells near curved surfaces. Consider hex-dominant meshing. Increase under-relaxation factors if convergence issues arise.",
    "skewness_max": "Refine cells near sharp geometric features. Improve transition ratios. Use size gradients < 1.2.",
    "aspect_ratio_max": "Reduce boundary layer growth ratio. Check for very thin cells in narrow gaps.",
    "cell_squish_max": "Cells are excessively compressed. Re-mesh with better quality controls. Check geometry for pinch points.",
    "volume_change_max": "Adjacent cell volume ratio too large. Smooth size transitions; keep growth ratio <= 1.2. Large volume jumps degrade interpolation accuracy and multigrid solver efficiency.",
    "negative_volumes": "Inverted cells detected — re-mesh the affected region. Check geometry for self-intersections or overlapping surfaces.",
}


def classify(value, criterion):
    """Return PASS, WARNING, or FAIL for a given value and criterion."""
    if criterion["direction"] == "lower_better":
        if value <= criterion["pass"]:
            return "PASS"
        elif value <= criterion["warn"]:
            return "WARNING"
        else:
            return "FAIL"
    else:  # higher_better
        if value >= criterion["pass"]:
            return "PASS"
        elif value >= criterion["warn"]:
            return "WARNING"
        else:
            return "FAIL"


def _openfoam_notes(geom: dict) -> list:
    """Generate advisory notes about data completeness and context."""
    notes = []
    # Warn if extended metrics are missing
    extended_keys = ("min_volume_ratio", "determinant", "interpolation_weight", "face_twist")
    if not any(k in geom for k in extended_keys):
        notes.append("Extended metrics not available. Rerun: checkMesh -allGeometry -allTopology")
    # Report high-AR cell count if available
    har = geom.get("high_aspect_ratio_cells")
    if har:
        notes.append(f"{har['count']} cells exceed aspect ratio {har['threshold']}. "
                      "Check if these are in boundary layers (acceptable) or core flow (problematic).")
    # Report severely non-orthogonal face count
    sno = geom.get("severely_non_orthogonal_faces")
    if sno:
        notes.append(f"{sno['count']} faces exceed {sno['threshold']}° non-orthogonality.")
    return notes


def evaluate_openfoam(data: dict) -> dict:
    """Evaluate OpenFOAM parsed data against criteria."""
    geom = data.get("geometry", {})
    results = []
    overall = "PASS"

    # Map parsed keys to criteria keys
    checks = []

    if "non_orthogonality" in geom:
        no = geom["non_orthogonality"]
        if "max" in no:
            checks.append(("non_orthogonality_max", no["max"]))
        if "average" in no:
            checks.append(("non_orthogonality_avg", no["average"]))

    if "max_skewness" in geom:
        checks.append(("max_skewness", geom["max_skewness"]["value"]))

    if "max_aspect_ratio" in geom:
        checks.append(("max_aspect_ratio", geom["max_aspect_ratio"]["value"]))

    if "min_volume_ratio" in geom:
        checks.append(("min_volume_ratio", geom["min_volume_ratio"]))

    if "determinant" in geom:
        checks.append(("min_determinant", geom["determinant"]["min"]))

    if "interpolation_weight" in geom:
        checks.append(("min_face_weight", geom["interpolation_weight"]["min"]))

    for key, value in checks:
        if key in OF_CRITERIA:
            crit = OF_CRITERIA[key]
            status = classify(value, crit)
            results.append({
                "metric": crit["label"],
                "value": value,
                "unit": crit["unit"],
                "status": status,
                "pass_threshold": crit["pass"],
                "warn_threshold": crit["warn"],
                "remedy": REMEDIES.get(key, "") if status != "PASS" else "",
            })
            if status == "FAIL":
                overall = "FAIL"
            elif status == "WARNING" and overall != "FAIL":
                overall = "WARNING"

    # Negative volume check
    has_neg = geom.get("volume", {}).get("has_negative", False)
    neg_count = geom.get("negative_volume_cells", 0)
    if has_neg or neg_count > 0:
        overall = "FAIL"
        results.append({
            "metric": "Negative Volumes",
            "value": neg_count if neg_count > 0 else "detected",
            "unit": "cells",
            "status": "FAIL",
            "pass_threshold": 0,
            "warn_threshold": 0,
            "remedy": REMEDIES["negative_volumes"],
        })

    return {"solver": "OpenFOAM", "overall": overall, "metrics": results,
            "notes": _openfoam_notes(geom)}


def evaluate_fluent(data: dict) -> dict:
    """Evaluate Fluent parsed data against criteria."""
    qm = data.get("quality_metrics", {})
    results = []
    overall = "PASS"

    for key, crit in FL_CRITERIA.items():
        if key in qm:
            value = qm[key]
            status = classify(value, crit)
            results.append({
                "metric": crit["label"],
                "value": value,
                "unit": crit["unit"],
                "status": status,
                "pass_threshold": crit["pass"],
                "warn_threshold": crit["warn"],
                "remedy": REMEDIES.get(key, "") if status != "PASS" else "",
            })
            if status == "FAIL":
                overall = "FAIL"
            elif status == "WARNING" and overall != "FAIL":
                overall = "WARNING"

    # Check for negative/zero volumes
    vol = data.get("volume_stats", {})
    if "min" in vol and vol["min"] <= 0:
        overall = "FAIL"
        results.append({
            "metric": "Negative Volumes",
            "value": vol["min"],
            "unit": "",
            "status": "FAIL",
            "pass_threshold": "> 0",
            "warn_threshold": "> 0",
            "remedy": REMEDIES["negative_volumes"],
        })

    return {"solver": "Fluent", "overall": overall, "metrics": results}


STATUS_ICON = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}


def format_report(evaluation: dict, raw_data: dict) -> str:
    """Format evaluation results into a markdown report."""
    lines = ["# Mesh Quality Report", ""]

    solver = evaluation["solver"]
    overall = evaluation["overall"]
    icon = STATUS_ICON.get(overall, "❓")

    # Summary
    lines.append("## Summary")
    lines.append(f"- **Overall verdict**: {icon} **{overall}**")
    lines.append(f"- **Solver**: {solver}")

    if solver == "OpenFOAM":
        stats = raw_data.get("mesh_stats", {})
        if "cells" in stats:
            lines.append(f"- **Total cells**: {stats['cells']:,}")
        ct = raw_data.get("cell_types", {})
        if ct:
            parts = [f"{k}: {v:,}" for k, v in ct.items() if v > 0]
            if parts:
                lines.append(f"- **Cell types**: {', '.join(parts)}")
    elif solver == "Fluent":
        vol = raw_data.get("volume_stats", {})
        if "total" in vol:
            lines.append(f"- **Total volume**: {vol['total']:.6e}")

    lines.append("")

    # Quality Metrics Table
    lines.append("## Quality Metrics")
    lines.append("")
    lines.append("| Metric | Value | Status | Pass Threshold | Warn Threshold |")
    lines.append("|--------|-------|--------|---------------|----------------|")
    for m in evaluation["metrics"]:
        icon = STATUS_ICON.get(m["status"], "")
        val_str = f"{m['value']}" if not isinstance(m["value"], float) else f"{m['value']:.4g}"
        if m["unit"]:
            val_str += f" {m['unit']}"
        lines.append(
            f"| {m['metric']} | {val_str} | {icon} {m['status']} | {m['pass_threshold']} | {m['warn_threshold']} |"
        )
    lines.append("")

    # Topology Checks (OpenFOAM only)
    if solver == "OpenFOAM":
        topo = raw_data.get("topology", {})
        if topo:
            lines.append("## Topology Checks")
            for key, val in topo.items():
                label = key.replace("_", " ").title()
                topo_icon = "✅" if val == "OK" or (key == "regions" and val == 1) else "❌"
                lines.append(f"- {label}: {topo_icon} {val}")
            lines.append("")

    # Notes (data completeness, context)
    notes = evaluation.get("notes", [])
    if notes:
        lines.append("## Notes")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")

    # Recommendations
    remedies = [m for m in evaluation["metrics"] if m.get("remedy")]
    if remedies:
        lines.append("## Recommendations")
        lines.append("")
        for m in remedies:
            lines.append(f"### {STATUS_ICON.get(m['status'], '')} {m['metric']} ({m['status']})")
            lines.append(f"{m['remedy']}")
            lines.append("")
    else:
        lines.append("## Recommendations")
        lines.append("All metrics within acceptable range. No action needed.")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: evaluate_quality.py <parsed_json> [--report]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    solver = data.get("solver", "")
    if solver == "OpenFOAM":
        evaluation = evaluate_openfoam(data)
    elif solver == "Fluent":
        evaluation = evaluate_fluent(data)
    else:
        print(f"Error: Unknown solver '{solver}'. Expected 'OpenFOAM' or 'Fluent'.")
        sys.exit(1)

    if "--report" in sys.argv:
        print(format_report(evaluation, data))
    else:
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
