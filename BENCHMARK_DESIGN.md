# ChatCFD Autonomous Benchmark Test Agent Design

## Executive Summary

This document proposes an autonomous benchmark testing framework for ChatCFD that systematically evaluates its ability to generate correct OpenFOAM cases from natural language descriptions. The benchmark leverages the existing 205 OpenFOAM tutorial cases in `datasets/` as ground truth and measures multiple quality dimensions beyond simple pass/fail.

---

## 1. Understanding ChatCFD's Pipeline

### 1.1 End-to-End Workflow
```
PDF/Text Description + Mesh File
    ↓
[LLM Analysis] Extract: solver, turbulence model, BCs, ICs, physical params
    ↓
[File Generation] Generate OpenFOAM case files (0/, constant/, system/)
    ↓
[Mesh Conversion] fluent3DMeshToFoam or use polyMesh directly
    ↓
[OpenFOAM Execution] Run solver (simpleFoam, rhoPimpleFoam, etc.)
    ↓
[ICOT Loop] If error → analyze → fix → retry (max 30 rounds by default)
    ↓
Success or Failure
```

### 1.2 Key Components
- **LLM Models**: DeepSeek-V3 (fast generation), DeepSeek-R1 (reasoning/reflection)
- **Knowledge Base**: `database_OFv24/` contains 14MB of OpenFOAM tutorial cases as reference
- **ICOT (Iterative Correction of OpenFOAM Tests)**: Self-healing loop with reflection
- **Reflextion Module**: Meta-learning from repeated failures

### 1.3 Current Metrics (from README)
- **Execution Success Rate**: 82% on 315 basic cases
- **Physical Fidelity**: 59% (cases that run AND produce physically correct results)
- **Cost**: $0.20/case average

---

## 2. Quality Dimensions to Benchmark

### 2.1 Primary Metrics (Must-Have)

| Metric | Definition | How to Measure |
|--------|-----------|----------------|
| **Success Rate** | % of cases that complete without OpenFOAM errors | `case_run_info == "case run success."` |
| **ICOT Rounds** | Number of correction iterations needed | Count loops in `main_run_chatcfd.py:102-217` |
| **First-Try Success** | % of cases that succeed on test_round=0 | `test_time == 0 and success` |
| **Convergence Rate** | % of cases that eventually succeed within max rounds | Final success after ≤30 rounds |

### 2.2 Secondary Metrics (Quality)

| Metric | Definition | How to Measure |
|--------|-----------|----------------|
| **File Completeness** | All required files generated | Compare `config.case_info.file_structure` vs actual files |
| **Boundary Condition Accuracy** | BCs match ground truth | Parse generated `0/U`, `0/p` vs reference |
| **Solver Selection Accuracy** | Correct solver chosen | Compare `system/controlDict:application` |
| **Turbulence Model Accuracy** | Correct turbulence model | Check `constant/turbulenceProperties` |
| **Physical Parameter Accuracy** | Re, Ma, viscosity, etc. match | Parse `constant/transportProperties`, `0/` fields |

### 2.3 Efficiency Metrics

| Metric | Definition | How to Measure |
|--------|-----------|----------------|
| **Token Usage** | Total prompt + completion tokens | Sum from `qa_logs.jsonl` |
| **API Cost** | Estimated $ cost | Tokens × model pricing |
| **Wall-Clock Time** | Total execution time | `time.time()` start to finish |
| **LLM Call Count** | Number of API requests | Count entries in `qa_logs.jsonl` |

### 2.4 Robustness Metrics

| Metric | Definition | How to Measure |
|--------|-----------|----------------|
| **Error Recovery Rate** | % of errors successfully fixed by ICOT | `(failures_fixed / total_failures)` |
| **Reflection Effectiveness** | Does Reflextion improve success? | Compare success rate with/without reflection |
| **Repeated Error Rate** | % of cases stuck in same error loop | Count `config.error_history` duplicates |

---

## 3. Test Dataset Design

### 3.1 Available Ground Truth
- **Location**: `datasets/of_case_description/` (205 text files)
- **Meshes**: `datasets/of_case_grids/` (205 polyMesh directories)
- **Coverage**:
  - Basic solvers: laplacianFoam, potentialFoam, simpleFoam, scalarTransportFoam
  - Combustion: reactingFoam, rhoReactingFoam
  - Compressible: rhoCentralFoam, rhoPimpleFoam, sonicFoam
  - Multiphase: interFoam, multiphaseEulerFoam
  - Heat transfer: buoyantSimpleFoam, chtMultiRegionFoam

### 3.2 Test Stratification

**Tier 1: Basic Cases (50 cases)**
- Simple solvers (simpleFoam, potentialFoam)
- Single-phase, incompressible
- Standard boundary conditions
- Expected success rate: >90%

**Tier 2: Intermediate Cases (100 cases)**
- Turbulence models (k-epsilon, k-omega SST, Spalart-Allmaras)
- Compressible flows
- Heat transfer
- Expected success rate: 70-85%

**Tier 3: Advanced Cases (55 cases)**
- Combustion (chemical reactions)
- Multiphase flows
- Complex physics (buoyancy, radiation)
- Expected success rate: 40-60%

### 3.3 Validation Strategy

For each test case, we have:
1. **Input**: Natural language description from `of_case_description/*.txt`
2. **Mesh**: Pre-converted polyMesh from `of_case_grids/*/constant/polyMesh`
3. **Ground Truth**: Original OpenFOAM tutorial case (can extract from `database_OFv24/processed_merged_OF_cases.json`)

---

## 4. Autonomous Benchmark Agent Architecture

### 4.1 Agent Components

```
┌─────────────────────────────────────────────────────────┐
│         Benchmark Orchestrator (Main Agent)             │
│  - Load test cases from datasets/                       │
│  - Dispatch to ChatCFD                                   │
│  - Collect metrics                                       │
│  - Generate reports                                      │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Test Runner  │  │   Validator  │  │   Reporter   │
│              │  │              │  │              │
│ - Run cases  │  │ - Compare    │  │ - Aggregate  │
│ - Timeout    │  │   outputs    │  │   metrics    │
│ - Retry      │  │ - Parse logs │  │ - Visualize  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 4.2 Test Execution Flow

```python
for case in test_dataset:
    # 1. Setup
    case_name = case['name']
    description = load_description(case['txt_file'])
    mesh_path = case['polyMesh_path']

    # 2. Run ChatCFD
    start_time = time.time()
    result = run_chatcfd(
        description=description,
        mesh_path=mesh_path,
        case_name=case_name,
        max_rounds=30,
        timeout=600  # 10 min per case
    )
    wall_time = time.time() - start_time

    # 3. Collect Metrics
    metrics = {
        'success': result.success,
        'icot_rounds': result.test_rounds,
        'wall_time': wall_time,
        'tokens': parse_qa_logs(result.output_path),
        'errors': result.error_history,
        'files_generated': list_files(result.output_path)
    }

    # 4. Validate Against Ground Truth
    if result.success:
        validation = validate_case(
            generated_path=result.output_path,
            reference_case=case['reference']
        )
        metrics.update(validation)

    # 5. Store Results
    save_result(case_name, metrics)
```

### 4.3 Validation Logic

```python
def validate_case(generated_path, reference_case):
    """Compare generated case against ground truth"""

    # 1. File completeness
    required_files = reference_case['file_structure']
    generated_files = list_case_files(generated_path)
    file_completeness = len(set(generated_files) & set(required_files)) / len(required_files)

    # 2. Solver correctness
    gen_solver = parse_controlDict(f"{generated_path}/system/controlDict")['application']
    ref_solver = reference_case['solver']
    solver_correct = (gen_solver == ref_solver)

    # 3. Boundary condition accuracy
    bc_score = compare_boundary_conditions(
        generated=f"{generated_path}/0/",
        reference=reference_case['boundary_conditions']
    )

    # 4. Physical parameters
    param_score = compare_physical_params(
        generated=f"{generated_path}/constant/",
        reference=reference_case['physical_params']
    )

    return {
        'file_completeness': file_completeness,
        'solver_correct': solver_correct,
        'bc_accuracy': bc_score,
        'param_accuracy': param_score,
        'physical_fidelity': (solver_correct and bc_score > 0.8 and param_score > 0.8)
    }
```

---

## 5. Implementation Plan

### 5.1 File Structure

```
benchmark/
├── benchmark_agent.py          # Main orchestrator
├── test_runner.py              # Executes individual cases
├── validator.py                # Compares against ground truth
├── metrics_collector.py        # Parses logs, computes metrics
├── reporter.py                 # Generates HTML/JSON reports
├── config.py                   # Benchmark configuration
└── utils/
    ├── case_loader.py          # Load test cases from datasets/
    ├── ground_truth_parser.py  # Extract reference from database
    ├── log_parser.py           # Parse qa_logs.jsonl, error_history.txt
    └── openfoam_parser.py      # Parse OpenFOAM dictionaries
```

### 5.2 Configuration

```python
# benchmark/config.py
BENCHMARK_CONFIG = {
    'test_dataset': 'datasets/',
    'output_dir': 'benchmark_results/',
    'max_rounds': 30,
    'timeout_per_case': 600,  # 10 min
    'parallel_workers': 4,     # Run 4 cases in parallel
    'tiers': {
        'basic': {'count': 50, 'expected_success': 0.90},
        'intermediate': {'count': 100, 'expected_success': 0.75},
        'advanced': {'count': 55, 'expected_success': 0.50}
    },
    'validation': {
        'check_files': True,
        'check_solver': True,
        'check_bcs': True,
        'check_params': True
    }
}
```

### 5.3 Output Format

```json
{
  "benchmark_id": "chatcfd_bench_20260312_001",
  "timestamp": "2026-03-12T15:30:00Z",
  "config": {...},
  "summary": {
    "total_cases": 205,
    "success_rate": 0.82,
    "physical_fidelity": 0.59,
    "avg_icot_rounds": 2.3,
    "avg_wall_time": 180.5,
    "total_cost": 41.00,
    "first_try_success": 0.45
  },
  "by_tier": {
    "basic": {"success": 0.92, "fidelity": 0.78, ...},
    "intermediate": {"success": 0.81, "fidelity": 0.58, ...},
    "advanced": {"success": 0.52, "fidelity": 0.35, ...}
  },
  "by_solver": {
    "simpleFoam": {"cases": 45, "success": 0.89, ...},
    "rhoPimpleFoam": {"cases": 32, "success": 0.75, ...},
    ...
  },
  "failures": [
    {
      "case": "combustion_reactingFoam_laminar_counterFlowFlame2D",
      "reason": "Missing reactions file after 30 rounds",
      "final_error": "...",
      "icot_rounds": 30
    },
    ...
  ],
  "detailed_results": [...]
}
```

---

## 6. Key Design Decisions

### 6.1 Why Autonomous?

1. **Repeatability**: Same test suite, deterministic evaluation
2. **Regression Detection**: Run after each code change to catch regressions
3. **Ablation Studies**: Test with/without Reflextion, different LLMs, etc.
4. **Continuous Improvement**: Track metrics over time

### 6.2 Why These Metrics?

- **Success Rate**: Core functionality (does it work?)
- **Physical Fidelity**: Quality (is it correct?)
- **ICOT Rounds**: Efficiency (how much self-correction needed?)
- **Cost**: Practical concern (API usage)
- **First-Try Success**: Measures initial generation quality (less reliance on ICOT)

### 6.3 Handling Ground Truth

The 205 cases in `datasets/` are extracted from OpenFOAM tutorials, so we can:
1. Use the text descriptions as input
2. Use the polyMesh as mesh input
3. Compare generated cases against the original tutorial cases in `database_OFv24/processed_merged_OF_cases.json`

### 6.4 Parallelization Strategy

- Run 4 cases in parallel (configurable)
- Each case isolated in its own directory
- Timeout per case to prevent hangs
- Aggregate results at the end

---

## 7. Advanced Features (Future)

### 7.1 Ablation Studies
- Test with/without Reflextion module
- Test with different LLMs (V3 only, R1 only, mixed)
- Test with different max_rounds (5, 10, 30)
- Test with different knowledge base sizes

### 7.2 Adversarial Testing
- Intentionally ambiguous descriptions
- Missing information (no Re number, no BC details)
- Contradictory requirements

### 7.3 Regression Testing
- Store baseline results
- Alert if success rate drops >5%
- Track metric trends over time

### 7.4 Interactive Debugging
- For failed cases, provide detailed diff vs ground truth
- Suggest which LLM prompt needs improvement
- Identify common failure patterns

---

## 8. Expected Outcomes

### 8.1 Baseline Benchmark
- Establish current performance across all 205 cases
- Identify weak areas (which solvers/physics fail most?)
- Quantify cost and time

### 8.2 Continuous Monitoring
- Run benchmark weekly/monthly
- Track improvements from code changes
- Detect regressions early

### 8.3 Research Insights
- Which cases benefit most from Reflextion?
- What's the optimal max_rounds vs cost tradeoff?
- Can we predict which cases will fail based on description complexity?

---

## 9. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] Implement test_runner.py (run single case, collect metrics)
- [ ] Implement case_loader.py (load 205 cases from datasets/)
- [ ] Implement log_parser.py (parse qa_logs.jsonl, error_history.txt)
- [ ] Basic metrics: success rate, ICOT rounds, wall time

### Phase 2: Validation (Week 2)
- [ ] Implement ground_truth_parser.py (extract from database_OFv24/)
- [ ] Implement validator.py (compare files, solver, BCs)
- [ ] Add physical fidelity metric

### Phase 3: Reporting (Week 3)
- [ ] Implement reporter.py (JSON + HTML reports)
- [ ] Add visualizations (success by tier, by solver, ICOT distribution)
- [ ] Add failure analysis

### Phase 4: Automation (Week 4)
- [ ] Implement benchmark_agent.py (orchestrate full run)
- [ ] Add parallelization
- [ ] Add timeout handling
- [ ] Add resume capability (for interrupted runs)

### Phase 5: Advanced Features (Future)
- [ ] Ablation studies
- [ ] Regression detection
- [ ] Interactive debugging UI

---

## 10. Conclusion

This autonomous benchmark agent will provide:

1. **Objective Evaluation**: Systematic testing of all 205 cases
2. **Multi-Dimensional Metrics**: Beyond pass/fail, measure quality and efficiency
3. **Continuous Improvement**: Track progress over time
4. **Research Tool**: Enable ablation studies and optimization

The design leverages ChatCFD's existing infrastructure (datasets, logs, ICOT loop) and adds a comprehensive evaluation layer on top.
