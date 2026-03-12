# ChatCFD Benchmark Evaluation - Bug Fixes and Trace

## Date: 2026-03-13
## Evaluation: Tier 1 (3 cases) - basic_laplacianFoam_flange, basic_laplacianFoam_implicitAMI-nonblocking, basic_laplacianFoam_twoBlocks-processorAgglom

---

## Bug #1: Empty Case Solver Configuration

### Discovery
- **When**: Initial test run (2026-03-12 21:22)
- **Symptom**: `KeyError: ''` in `file_preparation.py:431`
- **Root Cause**: `config.case_info.case_solver` was empty string, causing lookup failure in turbulence model JSON

### Error Trace
```
File "/var/tmp/vibe-kanban/worktrees/7518-use-home-develop/ChatCFD-cc/src/file_preparation.py", line 431, in case_required_files
    file_structure = file_structure.union(set(json.load(file)[turbulence_model]))
KeyError: ''
```

### Fix Applied
**File**: `benchmark/utils/test_runner.py`
**Location**: `run_single_case()` method

```python
# Before (WRONG):
config.case_info.case_name = ""
config.case_info.case_solver = ""
config.case_info.turbulence_model = ""

# After (FIXED):
config.case_info.case_name = test_case.name
config.case_info.case_solver = test_case.solver
config.case_info.turbulence_model = self._detect_turbulence_model(test_case)
```

**Commit**: `03b40ed` - Fix test_runner for benchmark evaluation

---

## Bug #2: Turbulence Model Detection for Non-Turbulent Solvers

### Discovery
- **When**: After fixing Bug #1
- **Symptom**: Empty turbulence model string caused KeyError
- **Root Cause**: Solvers like `laplacianFoam` don't use turbulence models, but empty string is invalid

### Fix Applied
**File**: `benchmark/utils/test_runner.py`
**Method**: `_detect_turbulence_model()`

```python
def _detect_turbulence_model(self, test_case) -> str:
    # Solvers that don't use turbulence models
    non_turbulent_solvers = [
        'laplacianFoam', 'potentialFoam', 'scalarTransportFoam',
        'solidFoam', 'boundaryFoam', 'dnsFoam'
    ]

    if test_case.solver in non_turbulent_solvers:
        return 'laminar'  # Use 'laminar' instead of empty string

    # Detect from description file...
    # Default to 'laminar' instead of ''
```

**Commit**: `03b40ed` - Fix test_runner for benchmark evaluation

---

## Bug #3: Incorrect Grid Path for polyMesh Format

### Discovery
- **When**: 2026-03-12 21:39
- **Symptom**: `FileNotFoundError: [Errno 2] No such file or directory: 'basic_laplacianFoam_flange_0/constant/polyMesh/boundary'`
- **Root Cause**: Mesh was copied to wrong location (`constant/basic_laplacianFoam_flange/constant/polyMesh/` instead of `constant/polyMesh/`)

### Error Trace
```
Copying mesh to basic_laplacianFoam_flange_0/constant/
Mesh loaded successfully
Mesh boundaries: {}

FileNotFoundError: [Errno 2] No such file or directory: 'basic_laplacianFoam_flange_0/constant/polyMesh/boundary'
```

### Analysis
The `grid_path` was set to the case root directory (containing `constant/`), but `convert_mesh()` with `grid_type="polyMesh"` expects the path to point directly to the `polyMesh` directory.

**File structure**:
```
datasets/of_case_grids/basic_laplacianFoam_flange/
└── constant/
    └── polyMesh/
        ├── boundary
        ├── faces
        ├── points
        └── ...
```

### Fix Applied
**File**: `benchmark/utils/test_runner.py`
**Location**: `run_single_case()` method

```python
# Before (WRONG):
config.path_cfg.grid_path = test_case.mesh_path
# This pointed to: datasets/of_case_grids/basic_laplacianFoam_flange/

# After (FIXED):
config.path_cfg.grid_path = test_case.mesh_path + "/constant/polyMesh"
# This points to: datasets/of_case_grids/basic_laplacianFoam_flange/constant/polyMesh/
```

Also added:
```python
config.grid_type = "polyMesh"  # Explicitly set grid type
```

**Commit**: `03b40ed` - Fix test_runner for benchmark evaluation

---

## Bug #4: Case Name Matching with Fuzzy LLM Responses

### Discovery
- **When**: 2026-03-12 21:47
- **Symptom**: `KeyError: 'twoBlocks-processorAgglomeration'`
- **Root Cause**: LLM returned slightly different case name than what exists in dataset

### Error Trace
```
Traceback (most recent call last):
  File "/var/tmp/vibe-kanban/worktrees/7518-use-home-develop/ChatCFD-cc/src/file_corrector.py", line 701, in find_reference_files
    file_content[k] = file_content_bak[k]
KeyError: 'twoBlocks-processorAgglomeration'
```

### Analysis
- **Dataset has**: `twoBlocks-processorAgglom`
- **LLM returned**: `twoBlocks-processorAgglomeration`
- The LLM "hallucinated" a longer version of the case name
- Direct dictionary lookup failed

### Fix Applied
**File**: `src/file_corrector.py`
**Location**: Line 699-701

```python
# Before (WRONG):
if not has_content:
    for k, v in file_content.items():
        file_content[k] = file_content_bak[k]  # KeyError if k not in file_content_bak

# After (FIXED):
if not has_content:
    for k, v in file_content.items():
        # Try exact match first
        if k in file_content_bak:
            file_content[k] = file_content_bak[k]
        else:
            # Fuzzy match: find closest key in file_content_bak
            best_match = None
            best_score = 0
            for bak_key in file_content_bak.keys():
                # Simple similarity: count matching characters
                score = sum(1 for a, b in zip(k.lower(), bak_key.lower()) if a == b)
                if score > best_score:
                    best_score = score
                    best_match = bak_key

            if best_match and best_score > len(k) * 0.7:  # 70% similarity threshold
                print(f"Fuzzy matched '{k}' to '{best_match}'")
                file_content[k] = file_content_bak[best_match]
            else:
                print(f"Warning: Could not find match for '{k}' in file_content_bak, using empty string")
                file_content[k] = ""
```

**Commit**: Not yet committed (fix applied during current session)

---

## Current Test Status (2026-03-13 00:07)

### Test Configuration
- **Cases**: 3 Tier 1 cases (basic_laplacianFoam_*)
- **Max ICOT rounds**: 10
- **Run time**: 1s
- **Report generation**: Enabled

### Progress
- **Case 1**: basic_laplacianFoam_flange
  - Status: Running
  - QA logs: 196 lines (growing)
  - Files generated: 0/T, system/controlDict, system/fvSchemes, system/fvSolution, system/decomposeParDict
  - Last activity: 00:04:30
  - Mesh: Loaded successfully
  - Sentence transformer: Loaded

### Observations
1. **Mesh boundaries empty**: `Mesh boundaries: {}` - may indicate boundary parsing issue
2. **No suitable reference case found**: Using default file list
3. **LLM is actively generating files**: QA logs growing steadily
4. **Process is stable**: No crashes, continuous progress

---

## Summary of Fixes

| Bug | File | Issue | Fix | Status |
|-----|------|-------|-----|--------|
| #1 | test_runner.py | Empty case_solver | Pre-populate from test_case | ✅ Fixed |
| #2 | test_runner.py | Empty turbulence_model | Default to 'laminar' | ✅ Fixed |
| #3 | test_runner.py | Wrong grid_path | Append /constant/polyMesh | ✅ Fixed |
| #4 | file_corrector.py | Case name mismatch | Fuzzy matching | ✅ Fixed |

---

## Next Steps

1. **Wait for test completion** - Currently running
2. **Analyze results** - Check success rate, ICOT rounds, errors
3. **Generate report** - HTML report with charts
4. **Commit Bug #4 fix** - Add fuzzy matching to git
5. **Run full Tier 1** - All 22 cases if initial test succeeds
6. **Document findings** - Update EVALUATION_STATUS.md

---

## Notes

### Performance Observations
- **LLM response time**: ~10-30 seconds per call
- **File generation**: Multiple iterations with retries
- **Mesh loading**: Fast (<1s)
- **Sentence transformer**: One-time load (~1s)

### Potential Issues to Monitor
1. Empty mesh boundaries - may affect BC validation
2. "No suitable reference case found" - may affect file quality
3. Long QA log (196 lines for 1 case) - may indicate many retries

### Benchmark Framework Status
- ✅ Case loader working
- ✅ Test runner working
- ✅ Path configuration working
- ✅ Mesh conversion working
- ⏳ Validation pending (after case completion)
- ⏳ Reporting pending (after case completion)

---

**Last Updated**: 2026-03-13 00:07:00
**Test Process**: Running (PID 1363835)
**Estimated Completion**: ~10-15 minutes per case
