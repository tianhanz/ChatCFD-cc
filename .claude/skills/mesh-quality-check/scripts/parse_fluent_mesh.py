#!/usr/bin/env python3
"""Parse ANSYS Fluent mesh quality output into structured JSON."""

import re
import json
import sys


def parse_fluent_mesh(text: str) -> dict:
    """Parse Fluent mesh check / quality report output."""
    result = {
        "solver": "Fluent",
        "domain_extents": {},
        "volume_stats": {},
        "face_area_stats": {},
        "quality_metrics": {},
        "overall_status": "UNKNOWN",
    }

    # --- Domain Extents ---
    for axis in ("x", "y", "z"):
        m = re.search(
            rf"{axis}-coordinate:.*min.*=\s*([\d.eE+-]+).*max.*=\s*([\d.eE+-]+)",
            text,
        )
        if m:
            result["domain_extents"][axis] = {
                "min": float(m.group(1)),
                "max": float(m.group(2)),
            }

    # --- Volume Statistics ---
    m = re.search(r"minimum volume.*:\s*([\d.eE+-]+)", text)
    if m:
        result["volume_stats"]["min"] = float(m.group(1))
    m = re.search(r"maximum volume.*:\s*([\d.eE+-]+)", text)
    if m:
        result["volume_stats"]["max"] = float(m.group(1))
    m = re.search(r"total volume.*:\s*([\d.eE+-]+)", text)
    if m:
        result["volume_stats"]["total"] = float(m.group(1))

    # --- Face Area Statistics ---
    m = re.search(r"minimum face area.*:\s*([\d.eE+-]+)", text)
    if m:
        result["face_area_stats"]["min"] = float(m.group(1))
    m = re.search(r"maximum face area.*:\s*([\d.eE+-]+)", text)
    if m:
        result["face_area_stats"]["max"] = float(m.group(1))

    # --- Quality Metrics ---
    metric_patterns = {
        "orthogonal_quality_min": r"Minimum Orthogonal Quality\s*=\s*([\d.eE+-]+)",
        "orthogonal_quality_max": r"Maximum Orthogonal Quality\s*=\s*([\d.eE+-]+)",
        "orthogonal_quality_mean": r"Mean Orthogonal Quality\s*=\s*([\d.eE+-]+)",
        "aspect_ratio_max": r"Maximum Aspect Ratio\s*=\s*([\d.eE+-]+)",
        "aspect_ratio_mean": r"Mean Aspect Ratio\s*=\s*([\d.eE+-]+)",
        "skewness_max": r"Maximum (?:Cell )?Skewness\s*=\s*([\d.eE+-]+)",
        "skewness_mean": r"Mean (?:Cell )?Skewness\s*=\s*([\d.eE+-]+)",
        "cell_squish_max": r"Maximum Cell Squish.*=\s*([\d.eE+-]+)",
        "cell_quality_min": r"Minimum Cell Quality\s*=\s*([\d.eE+-]+)",
        "volume_change_max": r"(?:Maximum )?Volume Change\s*=\s*([\d.eE+-]+)",
    }
    for key, pattern in metric_patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result["quality_metrics"][key] = float(m.group(1))

    # Volume ratio from min/max volumes (fallback if Volume Change not reported)
    vs = result["volume_stats"]
    if "volume_change_max" not in result["quality_metrics"] and vs.get("min") and vs.get("max"):
        if vs["min"] > 0:
            ratio = vs["max"] / vs["min"]
            result["quality_metrics"]["volume_change_max"] = ratio

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_fluent_mesh.py <fluent_quality_log_or_->")
        print("  Use '-' to read from stdin")
        sys.exit(1)

    path = sys.argv[1]
    if path == "-":
        text = sys.stdin.read()
    else:
        with open(path) as f:
            text = f.read()

    result = parse_fluent_mesh(text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
