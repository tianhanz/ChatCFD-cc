# Mesh Quality Criteria — Detailed Reference

## Table of Contents
1. [OpenFOAM checkMesh Criteria](#openfoam-checkmesh-criteria)
2. [Fluent Mesh Quality Criteria](#fluent-mesh-quality-criteria)
3. [y+ and Boundary Layer Guidelines](#y-and-boundary-layer-guidelines)
4. [Metric Conversion Between Solvers](#metric-conversion-between-solvers)
5. [Simulation-Type-Specific Requirements](#simulation-type-specific-requirements)

---

## OpenFOAM checkMesh Criteria

### Non-Orthogonality (degrees)

Measures the angle between the face normal and the vector connecting neighboring cell centers. A perfectly orthogonal mesh has 0°.

| Range | Status | Impact |
|-------|--------|--------|
| < 65° | PASS | Accurate gradient calculation |
| 65°–70° | WARNING | May need non-orthogonal correctors (1–2) |
| 70°–80° | WARNING (severe) | Needs 2–3 non-orthogonal correctors; accuracy degrades |
| > 80° | FAIL | Solver instability; > 90° is geometrically invalid |

**Remediation**: Improve mesh smoothing; use `snappyHexMesh` with `nSmoothPatch` and `nSmoothNormals`; reduce feature angle sensitivity; consider hex-dominant approaches for curved geometries.

### Skewness

Measures how far the face interpolation point deviates from the face center. Lower is better.

| Range | Status | Impact |
|-------|--------|--------|
| < 4.0 | PASS | Accurate face interpolation |
| 4.0–8.0 | WARNING | Interpolation errors; use skewness correction |
| > 8.0 | FAIL | Significant interpolation errors |
| > 20.0 | CRITICAL | Boundary face threshold exceeded |

**Remediation**: Refine cells near sharp geometric features; improve transition ratios; avoid very thin wedge-shaped cells.

### Aspect Ratio

Ratio of the longest to the shortest cell dimension.

| Range | Status | Impact |
|-------|--------|--------|
| < 100 | PASS | Normal operation |
| 100–1000 | WARNING | Acceptable in boundary layers only |
| > 1000 | FAIL | Numerical diffusion; poor convergence |

**Note**: High aspect ratio cells are expected and acceptable in boundary layers where the flow gradient is primarily in the wall-normal direction. The WARNING/FAIL thresholds apply to the flow core region.

### Cell Volume

| Condition | Status | Impact |
|-----------|--------|--------|
| All volumes > 0 | PASS | Valid mesh |
| Any volume ≤ 0 | FAIL | Inverted cells; solver will crash or produce garbage |

**Remediation**: Negative volumes indicate inverted cells. Check geometry for self-intersections, re-run meshing with tighter quality controls, or manually fix the affected region.

### Volume Ratio (from -allGeometry)

Ratio of smallest to largest neighboring cell volumes.

| Range | Status | Impact |
|-------|--------|--------|
| > 0.1 | PASS | Smooth volume transition |
| 0.01–0.1 | WARNING | Steep transitions; may cause interpolation errors |
| < 0.01 | FAIL | Extreme size jumps; numerical instability |

### Interpolation Weight (from -allGeometry)

Interpolation weight balance between cells sharing a face. Also referred to as "face weight" in some OpenFOAM versions.

| Range | Status | Impact |
|-------|--------|--------|
| > 0.2 | PASS | Balanced interpolation |
| 0.05–0.2 | WARNING | Asymmetric interpolation |
| < 0.05 | FAIL | Highly asymmetric; accuracy loss |

### Determinant (from -allGeometry)

Measures cell deformation relative to a perfect hex. Range 0–1.

| Range | Status | Impact |
|-------|--------|--------|
| > 0.1 | PASS | Well-shaped cells |
| 0.001–0.1 | WARNING | Deformed cells |
| < 0.001 | FAIL | Degenerate cells |

### Face Twist (from -allGeometry)

Measures face non-planarity. 1.0 = perfectly flat.

| Range | Status | Impact |
|-------|--------|--------|
| > 0.5 | PASS | Essentially flat faces |
| 0.02–0.5 | WARNING | Non-planar faces |
| < 0.02 | FAIL | Severely twisted faces |

---

## Fluent Mesh Quality Criteria

### Orthogonal Quality

Computed from the dot product of the face normal and the cell-center-to-cell-center vector. Range 0–1, where 1 is perfect.

| Range | Status | Impact |
|-------|--------|--------|
| > 0.3 | PASS | Acceptable for most simulations |
| 0.1–0.3 | WARNING | May cause convergence issues; increase under-relaxation |
| < 0.1 | FAIL | Likely to cause divergence |

**Relationship to OpenFOAM**: `Orthogonal Quality ≈ cos(non-orthogonality angle)`. So 0.3 ≈ 72.5°, and 0.1 ≈ 84.3°.

### Skewness (Equilateral Volume-Based)

Range 0–1, where 0 is ideal (equilateral) and 1 is degenerate.

| Range | Status | Impact |
|-------|--------|--------|
| < 0.85 | PASS | Acceptable cell shape |
| 0.85–0.95 | WARNING | Poor cell shape; risk of inaccurate results |
| > 0.95 | FAIL | Degenerate cells; will likely cause divergence |

### Aspect Ratio

| Range | Status | Impact |
|-------|--------|--------|
| < 20 | PASS | Good for most flows |
| 20–100 | WARNING | Acceptable in boundary layers only |
| > 100 | FAIL | Excessive anisotropy |

### Volume Change (adjacent cell volume ratio)

| Range | Status | Impact |
|-------|--------|--------|
| < 5 | PASS | Smooth size transition |
| 5–10 | WARNING | Steep gradient; may affect accuracy |
| > 10 | FAIL | Size jump too large |

### Cell Squish

Measures cell compression. Range 0–1.

| Range | Status | Impact |
|-------|--------|--------|
| < 0.5 | PASS | Acceptable cell shape |
| 0.5–0.8 | WARNING | Compressed cells |
| > 0.8 | FAIL | Severely squished; affects gradient calculation |

---

## y+ and Boundary Layer Guidelines

### y+ Definition

y+ = y × u_τ / ν

Where:
- y = distance from wall to first cell center
- u_τ = friction velocity = √(τ_w / ρ)
- ν = kinematic viscosity

### First Layer Height Estimation

Δy₁ = y⁺_target × μ / (ρ × u_τ)

For an initial estimate without knowing u_τ:

Δy₁ ≈ y⁺_target × L / (Re_L × √(C_f / 2))

Where C_f ≈ 0.058 × Re_L^(-0.2) for turbulent flat plate.

### Model-Specific y+ Requirements

| Model | Target y+ | Growth Ratio | Min Layers | Notes |
|-------|-----------|-------------|------------|-------|
| k-ε + standard wall functions | 30–300 | 1.2 | 5 | First cell must be in log-law region |
| k-ε + enhanced wall treatment | ≈ 1 | 1.2 | 15–20 | Resolve viscous sublayer |
| k-ω SST | ≈ 1 | 1.2 | 15–20 | Best practice for separation prediction |
| Spalart-Allmaras | ≈ 1 | 1.2 | 15–20 | Designed for wall-resolved simulations |
| LES (wall-resolved) | ≈ 1 | 1.1–1.15 | 20+ | Also need Δx⁺ ≈ 50–100, Δz⁺ ≈ 15–40 |
| DES / DDES | ≈ 1 | 1.2 | 15–20 | RANS near wall, LES away |

### Boundary Layer Growth Ratio

Recommended growth ratio between successive layers: **1.1 – 1.2**

- 1.1: Conservative, more cells, better accuracy
- 1.2: Standard, good balance of accuracy and cell count
- > 1.3: Aggressive, risk of high volume ratio and interpolation errors

---

## Metric Conversion Between Solvers

| OpenFOAM Metric | Fluent Equivalent | Conversion |
|----------------|-------------------|------------|
| Non-orthogonality (degrees) | Orthogonal Quality (0–1) | OQ ≈ cos(non-ortho°) |
| Skewness (0–∞) | Skewness (0–1) | Not directly comparable; different definitions |
| Aspect ratio | Aspect ratio | Similar definition |
| Volume ratio | Volume Change | Fluent uses max neighbor ratio; OpenFOAM uses min/max |
| Determinant | — | No direct Fluent equivalent |
| Interpolation weight | — | No direct Fluent equivalent |

**Cross-solver consistency note**: The OpenFOAM non-orthogonality WARNING threshold of 65° corresponds to `cos(65°) ≈ 0.42` in Fluent's Orthogonal Quality scale. Fluent's PASS threshold is 0.3, so a mesh at 72° non-orthogonality would be WARNING in OpenFOAM but still PASS in Fluent. Engineers working across both solvers should be aware of this gap and use the stricter criterion when in doubt.

**Aspect ratio discrepancy**: OpenFOAM PASS < 100 vs. Fluent PASS < 20. The OpenFOAM threshold accommodates highly anisotropic boundary layer cells (which are normal in wall-resolved simulations). The Fluent threshold is more conservative and intended for the bulk flow region. When evaluating boundary layer meshes in Fluent, high aspect ratio cells near walls should be assessed in context rather than flagged as failures.

---

## Simulation-Type-Specific Requirements

### RANS (Steady-State)

Standard thresholds apply. Focus on:
- Non-orthogonality / Orthogonal Quality
- y+ for chosen wall treatment
- Smooth size transitions

### LES / DES

Stricter requirements:
- Max non-orthogonality < 40° (Orthogonal Quality > 0.75)
- Max skewness < 2.0 (OpenFOAM) / < 0.5 (Fluent)
- Isotropic cells in turbulence-resolving regions
- Cell aspect ratio ≈ 1 in LES zone
- Very fine near-wall resolution (y+ ≈ 1, Δx+ ≈ 50–100, Δz+ ≈ 15–40)

### Multiphase (VOF)

- Uniform cells near free surface interface
- Aspect ratio ≈ 1 near interface
- Fine mesh at interface (cell size ≤ interface thickness)
- Smooth size transition away from interface

### Combustion / Reacting Flows

- Fine mesh in flame zone / reaction zone
- Smooth size transitions to avoid artificial flame anchoring
- Moderate aspect ratio throughout (< 5 in reaction zone)

### Conjugate Heat Transfer

- Matching cell size at fluid-solid interface
- Fine cells in thermal boundary layer
- 1:1 face mapping preferred at interface for accuracy
