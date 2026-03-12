# ChatCFD Autonomous Benchmark Agent

Automated testing framework for evaluating ChatCFD's ability to generate correct OpenFOAM cases from natural language descriptions.

## Quick Start

```bash
# Quick test (3 Tier 1 cases) with report
python benchmark/run_benchmark.py --quick --report

# Run all Tier 1 cases with report
python benchmark/run_benchmark.py --tier1 --report

# Run with comparison to baseline
python benchmark/run_benchmark.py --tier 1 --report --compare benchmark/results/baseline.json

# Run specific solver
python benchmark/run_benchmark.py --solver simpleFoam --limit 10

# Custom run
python benchmark/run_benchmark.py --tier 2 --limit 20 --max-rounds 15
```

## Architecture

```
benchmark/
├── run_benchmark.py       # Main orchestrator
├── test_reporting.py      # Test suite for reporting tools
├── utils/
│   ├── case_loader.py     # Load 205 test cases from datasets/
│   ├── test_runner.py     # Execute ChatCFD on individual cases
│   ├── log_parser.py      # Parse logs and extract metrics
│   ├── bc_validator.py    # Boundary condition validator
│   ├── solver_validator.py # Solver configuration validator
│   ├── fidelity_analyzer.py # Physical fidelity analyzer
│   ├── report_generator.py # HTML report generator
│   ├── visualizer.py      # Chart generator
│   └── comparator.py      # Comparison tool
├── results/               # Benchmark results (JSON)
└── reports/               # Generated HTML reports and charts
    ├── report_*.html
    ├── comparison_*.html
    └── charts/
```

## Test Dataset

- **Total cases**: 205 OpenFOAM tutorial cases
- **Tier 1** (22 cases): Basic solvers (laplacianFoam, potentialFoam, simpleFoam)
- **Tier 2** (85 cases): Intermediate (compressible, buoyant, transient)
- **Tier 3** (98 cases): Advanced (combustion, multiphase, complex physics)

## Metrics Collected

### Primary Metrics
- Success rate (% cases that run without errors)
- ICOT rounds (iterations needed for correction)
- Duration per case

### Validation Metrics (Phase 2)
- BC accuracy (boundary condition correctness)
- Solver correctness (configuration accuracy)
- Physical fidelity (physical accuracy)

### Secondary Metrics
- Token usage (V3 vs R1)
- Cost per case
- Error types and patterns
- Convergence quality

### Efficiency Metrics
- Average tokens per case
- Average cost per case
- Time per case

### Robustness Metrics
- Error recovery rate
- Reflection trigger frequency
- Repeated error patterns

## Usage Examples

### Quick Test (3 cases)
```bash
python benchmark/run_benchmark.py --quick --report
```

### Tier 1 Benchmark (all basic cases)
```bash
python benchmark/run_benchmark.py --tier1 --report
```

### Full Benchmark (all 205 cases)
```bash
python benchmark/run_benchmark.py --full
```

### Custom Filters
```bash
# Run first 10 simpleFoam cases
python benchmark/run_benchmark.py --solver simpleFoam --limit 10

# Run Tier 2 with custom ICOT limit
python benchmark/run_benchmark.py --tier 2 --max-rounds 15

# Run specific tier with limit and report
python benchmark/run_benchmark.py --tier 1 --limit 5 --output my_test.json --report
```

### Reporting and Comparison

```bash
# Generate report from existing results
python -m utils.report_generator benchmark/results/results.json

# Generate charts
python -m utils.visualizer benchmark/results/results.json

# Compare two runs
python -m utils.comparator benchmark/results/baseline.json benchmark/results/current.json
```

## Output Format

Results are saved as JSON in `benchmark/results/`:

```json
{
  "timestamp": "2026-03-12T10:30:00",
  "total_cases": 22,
  "successful_cases": 18,
  "results": [
    {
      "case_name": "basic_simpleFoam_pitzDaily",
      "success": true,
      "icot_rounds": 2,
      "duration": 45.3,
      "solver_detected": "simpleFoam",
      "turbulence_model_detected": "kOmegaSST",
      "bc_accuracy": 95.0,
      "solver_correctness": 90.0,
      "physical_fidelity": 85.0,
      "validation_issues": [],
      "tokens_used": 12500,
      "cost": 0.18
    }
  ]
}
```

## Implementation Status

✅ **Phase 1: Core Infrastructure** (COMPLETE)
- Case loader with 205 test cases
- Test runner with batch execution
- Log parser for metrics extraction
- Main orchestrator with CLI

✅ **Phase 2: Validation** (COMPLETE)
- BC/IC accuracy checker
- Solver correctness validator
- Physical fidelity analyzer

✅ **Phase 3: Reporting** (COMPLETE)
- HTML report generator with embedded charts
- Standalone chart generator (6 chart types)
- Comparison tool for tracking progress
- Integrated with run_benchmark.py

⏳ **Phase 4: Automation** (TODO)
- Continuous monitoring
- Regression detection
- Automated alerts

⏳ **Phase 5: Advanced Features** (TODO)
- Parallel execution
- Incremental testing
- Performance profiling

## Phase 3: Reporting Tools

### HTML Report Generator
Generates comprehensive, self-contained HTML reports with:
- Executive summary (success rate, avg metrics, validation scores)
- Embedded interactive charts
- Sortable/filterable results table
- Validation and error analysis
- CSV export

### Visualizer
Creates standalone chart images:
- Success rate by tier
- ICOT rounds distribution
- Validation metrics comparison
- Duration vs rounds scatter plot
- Error distribution
- Solver distribution

### Comparator
Compares two benchmark runs:
- Summary metric changes
- Status changes (improvements/regressions)
- Detailed metric changes
- New/removed cases

### Documentation
- `REPORTING.md` - Comprehensive reporting guide
- `QUICK_REFERENCE.md` - Command cheat sheet
- `PHASE3_SUMMARY.md` - Implementation summary

### Testing
```bash
cd benchmark
python3 test_reporting.py
```

## Dependencies

### Required
- Python 3.7+
- Standard library

### Optional
- **matplotlib** (for charts, highly recommended)
  ```bash
  pip install matplotlib
  ```

## Design Document

See `BENCHMARK_DESIGN.md` for full design specification.
