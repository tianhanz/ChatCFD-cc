# ChatCFD Autonomous Benchmark Agent

Automated testing framework for evaluating ChatCFD's ability to generate correct OpenFOAM cases from natural language descriptions.

## Quick Start

```bash
# Quick test (3 Tier 1 cases)
python benchmark/run_benchmark.py --quick

# Run all Tier 1 cases (basic)
python benchmark/run_benchmark.py --tier1

# Run specific solver
python benchmark/run_benchmark.py --solver simpleFoam --limit 10

# Custom run
python benchmark/run_benchmark.py --tier 2 --limit 20 --max-rounds 15
```

## Architecture

```
benchmark/
├── run_benchmark.py       # Main orchestrator
├── utils/
│   ├── case_loader.py     # Load 205 test cases from datasets/
│   ├── test_runner.py     # Execute ChatCFD on individual cases
│   └── log_parser.py      # Parse logs and extract metrics
└── results/               # Output directory for results
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
python benchmark/run_benchmark.py --quick
```

### Tier 1 Benchmark (all basic cases)
```bash
python benchmark/run_benchmark.py --tier1
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

# Run specific tier with limit
python benchmark/run_benchmark.py --tier 1 --limit 5 --output my_test.json
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

⏳ **Phase 2: Validation** (TODO)
- BC/IC accuracy checker
- Solver correctness validator
- Physical fidelity analyzer

⏳ **Phase 3: Reporting** (TODO)
- HTML report generator
- Visualization dashboard
- Comparison tools

⏳ **Phase 4: Automation** (TODO)
- Continuous monitoring
- Regression detection
- Automated alerts

⏳ **Phase 5: Advanced Features** (TODO)
- Parallel execution
- Incremental testing
- Performance profiling

## Design Document

See `BENCHMARK_DESIGN.md` for full design specification.
