---
name: mesh-quality-check
description: >
  Check and evaluate CFD mesh quality for OpenFOAM and ANSYS Fluent simulations.
  Use this skill whenever the user asks to check mesh quality, evaluate a mesh,
  parse checkMesh output, review mesh metrics, or diagnose mesh-related simulation
  issues. Also trigger when the user mentions mesh non-orthogonality, skewness,
  aspect ratio, y+, negative volumes, or any mesh quality concern — even if they
  don't explicitly say "check mesh quality". Covers both OpenFOAM (checkMesh) and
  Fluent (Mesh Check / Examine Mesh) workflows.
---

# Mesh Quality Check

A comprehensive skill for evaluating CFD mesh quality against industry-standard criteria. Supports both OpenFOAM `checkMesh` output parsing and ANSYS Fluent mesh quality metrics.

## When to Use

- User provides `checkMesh` log output or a log file path
- User asks to run `checkMesh` on an OpenFOAM case
- User provides Fluent mesh quality metrics
- User asks about mesh quality thresholds or best practices
- User has convergence issues that might be mesh-related
- User wants a mesh quality report before starting a simulation

## Workflow

### Step 1: Identify the Mesh Source

Determine whether the user is working with:
- **OpenFOAM**: Look for `checkMesh` logs, `polyMesh/` directory, or `.blockMeshDict`
- **Fluent**: Look for `.msh` files, `.cas` files, or Fluent TUI output
- **Raw metrics**: User provides individual metric values directly

### Step 2: Collect Mesh Quality Data

**For OpenFOAM cases:**

If the user has an OpenFOAM case directory, run checkMesh to collect data:
```bash
checkMesh -case /path/to/case 2>&1
# For extended metrics:
checkMesh -case /path/to/case -allGeometry -allTopology 2>&1
```

If the user provides a checkMesh log, parse it directly using `scripts/parse_checkmesh.py`:
```bash
python /home/developer/.claude/skills/mesh-quality-check/scripts/parse_checkmesh.py /path/to/checkMesh.log
```

The parser outputs a structured JSON with all extracted metrics.

**For Fluent meshes:**

If the user provides Fluent mesh quality output text, parse it using `scripts/parse_fluent_mesh.py`:
```bash
python /home/developer/.claude/skills/mesh-quality-check/scripts/parse_fluent_mesh.py /path/to/fluent_quality.log
```

### Step 3: Evaluate Against Quality Criteria

Use the thresholds defined below to classify each metric as PASS / WARNING / FAIL.

Run the evaluation script to produce a quality report:
```bash
python /home/developer/.claude/skills/mesh-quality-check/scripts/evaluate_quality.py <parsed_json>
```

Or evaluate manually using the criteria tables in `references/quality_criteria.md`.

### Step 4: Generate Report

Present findings as a structured report. The report script produces both a summary table and detailed recommendations:
```bash
python /home/developer/.claude/skills/mesh-quality-check/scripts/evaluate_quality.py <parsed_json> --report
```

## Quality Criteria Quick Reference

### OpenFOAM Metrics

| Metric | PASS | WARNING | FAIL |
|--------|------|---------|------|
| Non-orthogonality (max) | < 65° | 65°–80° | > 80° |
| Non-orthogonality (avg) | < 15° | 15°–30° | > 30° |
| Skewness | < 4.0 | 4.0–8.0 | > 8.0 |
| Aspect ratio | < 100 | 100–1000 | > 1000 |
| Min volume | > 0 | — | ≤ 0 (negative volumes) |
| Volume ratio | > 0.01 | 0.001–0.01 | < 0.001 |
| Min determinant | > 0.1 | 0.001–0.1 | < 0.001 |
| Min face weight | > 0.2 | 0.05–0.2 | < 0.05 |

### Fluent Metrics

| Metric | PASS | WARNING | FAIL |
|--------|------|---------|------|
| Orthogonal Quality (min) | > 0.3 | 0.1–0.3 | < 0.1 |
| Skewness (max) | < 0.85 | 0.85–0.95 | > 0.95 |
| Aspect Ratio (max) | < 20 | 20–100 | > 100 |
| Volume Change | < 5 | 5–10 | > 10 |
| Cell Squish | < 0.5 | 0.5–0.8 | > 0.8 |

### Boundary Layer / y+ Requirements

| Turbulence Model | Target y+ | First Layer Thickness Strategy |
|-----------------|-----------|-------------------------------|
| k-ε (standard wall functions) | 30 < y+ < 300 | Coarser near wall, use wall functions |
| k-ε (enhanced wall treatment) | y+ ≈ 1 | Fine near wall, resolve viscous sublayer |
| k-ω SST | y+ ≈ 1 (recommended) | Fine near wall for accurate separation prediction |
| Spalart-Allmaras | y+ ≈ 1 | Fine near wall |
| LES / DES | y+ ≈ 1 | Very fine; also need streamwise/spanwise resolution |

For detailed thresholds, conversion formulas, and remediation guidance, see `references/quality_criteria.md`.

## Report Format

Always structure the mesh quality report as:

```
# Mesh Quality Report

## Summary
- Overall verdict: PASS / WARNING / FAIL
- Mesh type: [OpenFOAM / Fluent]
- Total cells: [N]
- Cell types: [hex/tet/prism/poly breakdown]

## Quality Metrics
| Metric | Value | Status | Threshold |
|--------|-------|--------|-----------|
| ...    | ...   | ✅/⚠️/❌ | ...     |

## Topology Checks
- Boundary closure: [OK / FAIL]
- Negative volumes: [count]
- Disconnected regions: [count]

## Recommendations
[Specific, actionable recommendations for any WARNING or FAIL metrics]
```

## Common Mesh Issues and Remedies

When metrics fail, provide specific guidance:

- **High non-orthogonality / low orthogonal quality**: Improve mesh smoothing; avoid highly warped cells near curved surfaces; consider hex-dominant meshing
- **High skewness**: Refine transitions between different cell sizes; avoid sharp angles in blocking topology; use size gradients < 1.2
- **High aspect ratio**: Reduce boundary layer growth ratio; check for very thin cells in narrow gaps
- **Negative volumes**: Indicates inverted cells — re-mesh the affected region; check geometry for self-intersections
- **Poor volume ratio**: Smooth size transitions between regions; keep growth ratio ≤ 1.2
- **y+ out of range**: Adjust first layer height using the formula: `y = y+ × μ / (ρ × u_τ)` where `u_τ = √(τ_w / ρ)`

## Solver-Specific Notes

**For LES/DES simulations**: Mesh quality requirements are significantly stricter. Target non-orthogonality < 40°, skewness < 2.0, and ensure isotropic cells in the core flow region. Poor mesh quality causes excessive numerical dissipation that damps resolved turbulence.

**For multiphase/VOF simulations**: Keep cells near the interface as uniform as possible. Avoid sudden size changes across the free surface region. Aspect ratio should be close to 1 near interfaces.
