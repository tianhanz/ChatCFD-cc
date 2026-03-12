# Phase 2: Validation Components

This document describes the validation framework added in Phase 2 of the benchmark system.

## Overview

The validation framework analyzes ChatCFD's output quality across three dimensions:
1. **Boundary Conditions (BC)** - Correctness of boundary condition setup
2. **Solver Configuration** - Validity of solver settings and schemes
3. **Physical Fidelity** - Convergence and physical consistency of results

## Components

### 1. BC Validator (`benchmark/utils/bc_validator.py`)

Validates boundary conditions in generated OpenFOAM cases.

**Features:**
- Parses OpenFOAM field files (U, p, k, omega, etc.)
- Extracts boundary conditions for all patches
- Compares against ground truth from `datasets/of_case_grids/`
- Checks patch names, BC types, and values

**Metrics:**
- `bc_accuracy`: 0-100 score based on correct BCs
- Detailed mismatch reporting

**Usage:**
```bash
python3 bc_validator.py <generated_case_dir> [ground_truth_dir]
```

**Example:**
```bash
cd benchmark/utils
python3 bc_validator.py ../../run_chatcfd/test_output/case_name ../../datasets/of_case_grids/case_name
```

### 2. Solver Validator (`benchmark/utils/solver_validator.py`)

Validates solver configuration files (controlDict, fvSchemes, fvSolution).

**Features:**
- Parses system/controlDict for solver settings
- Parses system/fvSchemes for discretization schemes
- Parses system/fvSolution for linear solvers and algorithms
- Validates against expected configurations for each solver type
- Checks for reasonable numerical parameters

**Metrics:**
- `solver_correctness`: 0-100 score
- Issues and warnings list

**Usage:**
```bash
python3 solver_validator.py <case_dir> [expected_solver]
```

**Example:**
```bash
cd benchmark/utils
python3 solver_validator.py ../../run_chatcfd/test_output/case_name simpleFoam
```

### 3. Fidelity Analyzer (`benchmark/utils/fidelity_analyzer.py`)

Analyzes physical fidelity of simulation results.

**Features:**
- Parses OpenFOAM log files for residuals and convergence
- Extracts final residuals for all fields
- Checks continuity errors
- Validates field values are within physical bounds
- Detects convergence issues and oscillations

**Metrics:**
- `physical_fidelity`: 0-100 score (50% convergence + 50% physical consistency)
- Convergence quality: excellent/good/acceptable/poor
- Final residuals for all fields
- Physical issues and warnings

**Usage:**
```bash
python3 fidelity_analyzer.py <case_dir>
```

**Example:**
```bash
cd benchmark/utils
python3 fidelity_analyzer.py ../../run_chatcfd/test_output/case_name
```

## Integration with Test Runner

The validators are automatically integrated into `test_runner.py`:

```python
from test_runner import TestRunner

# Create runner with validation enabled (default)
runner = TestRunner(enable_validation=True)

# Run test case - validation runs automatically after success
result = runner.run_single_case(test_case)

# Access validation metrics
print(f"BC Accuracy: {result.bc_accuracy}%")
print(f"Solver Correctness: {result.solver_correctness}%")
print(f"Physical Fidelity: {result.physical_fidelity}%")
print(f"Issues: {result.validation_issues}")
```

## Validation Metrics in Results

The `TestResult.to_dict()` output now includes:

```json
{
  "case_name": "basic_simpleFoam_pitzDaily",
  "success": true,
  "bc_accuracy": 95.5,
  "solver_correctness": 100.0,
  "physical_fidelity": 85.0,
  "validation_issues": [
    "BC: U/outlet: Type mismatch - expected zeroGradient, got inletOutlet",
    "Convergence: p did not converge: final residual 5.2e-04"
  ]
}
```

## Performance

Validation is designed to be fast:
- BC validation: < 1s per case
- Solver validation: < 0.5s per case
- Fidelity analysis: < 2s per case
- **Total overhead: < 5s per case**

## Scoring System

### BC Accuracy (0-100%)
- 100%: All BCs match ground truth perfectly
- Deductions: Missing patches, wrong BC types, incorrect values

### Solver Correctness (0-100%)
- Base: 100% if all required files present
- Deductions: -10 per missing required section, -5 per warning

### Physical Fidelity (0-100%)
- Convergence (50 points):
  - Excellent: All residuals < 1e-5 (50 pts)
  - Good: All residuals < 1e-4 (45 pts)
  - Acceptable: All residuals < 1e-4 (40 pts)
  - Poor: Some residuals > 1e-4 (20 pts)
- Physical Consistency (50 points):
  - Start: 50 points
  - Deductions: -15 per major issue, -5 per warning

## Ground Truth Comparison

When ground truth is available (`datasets/of_case_grids/<case_name>`):
- BC validator compares against reference boundary conditions
- Detailed mismatch reporting for debugging

When ground truth is not available:
- BC validator checks structural consistency
- Solver validator checks against solver-specific expectations
- Fidelity analyzer checks convergence and physical bounds

## Future Enhancements

Potential improvements for Phase 3:
- Mesh quality validation
- Force/coefficient comparison with reference data
- Field distribution analysis (velocity profiles, pressure contours)
- Turbulence model appropriateness checking
- Time step stability analysis for transient cases
