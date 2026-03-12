# Phase 3 Reporting - Quick Reference

## Command Cheat Sheet

### Run Benchmark with Report
```bash
# Basic run with report
python3 run_benchmark.py --tier 1 --report

# Run with comparison to baseline
python3 run_benchmark.py --tier 1 --report --compare benchmark/results/baseline.json

# Quick test with report
python3 run_benchmark.py --quick --report
```

### Generate Report from Existing Results
```bash
# Generate HTML report
python3 -m utils.report_generator benchmark/results/your_results.json

# Custom output name
python3 -m utils.report_generator benchmark/results/your_results.json -o my_report.html
```

### Generate Charts
```bash
# All charts
python3 -m utils.visualizer benchmark/results/your_results.json

# Specific chart
python3 -m utils.visualizer benchmark/results/your_results.json -c success_rate_by_tier

# With prefix
python3 -m utils.visualizer benchmark/results/your_results.json -p tier1_
```

### Compare Two Runs
```bash
# Full comparison report
python3 -m utils.comparator benchmark/results/baseline.json benchmark/results/current.json

# Summary only
python3 -m utils.comparator baseline.json current.json --summary-only

# Custom output
python3 -m utils.comparator baseline.json current.json -o comparison.html
```

## Available Charts

1. **success_rate_by_tier** - Success rate for each tier
2. **icot_rounds_distribution** - Histogram of ICOT rounds
3. **validation_metrics** - Validation scores (BC, Solver, Fidelity)
4. **duration_vs_rounds** - Duration vs ICOT rounds scatter
5. **error_distribution** - Top error types
6. **solver_distribution** - Solver usage and success rates

## Report Features

### HTML Report Includes:
- Executive summary with key metrics
- Interactive charts (embedded)
- Sortable/filterable results table
- Validation analysis
- Error analysis
- CSV export button

### Comparison Report Includes:
- Summary metric changes
- Status changes (improvements/regressions)
- Detailed metric changes
- New/removed cases

## File Locations

```
benchmark/
├── reports/
│   ├── report_TIMESTAMP.html          # Main reports
│   ├── comparison_TIMESTAMP.html      # Comparison reports
│   └── charts/
│       └── *.png                      # Chart images
├── results/
│   └── *.json                         # Benchmark results
└── utils/
    ├── report_generator.py
    ├── visualizer.py
    └── comparator.py
```

## Testing

```bash
# Run test suite
cd benchmark
python3 test_reporting.py

# This creates:
# - benchmark/reports/test_report.html
# - benchmark/reports/test_comparison.html
# - benchmark/reports/charts/test_*.png
```

## Tips

1. Always use `--report` flag for better insights
2. Keep baseline results for tracking progress
3. Use comparison reports to identify regressions
4. Export to CSV for custom analysis
5. Reports are self-contained and shareable

## Dependencies

- **Required**: Python 3.7+
- **Optional**: matplotlib (for charts)
  ```bash
  pip install matplotlib
  ```

## Color Coding

- **Green**: Good (>80%), improvements, success
- **Yellow**: Warning (60-80%)
- **Red**: Bad (<60%), regressions, failures
- **Blue**: Informational

## Common Workflows

### Track Progress Over Time
```bash
# 1. Run baseline
python3 run_benchmark.py --tier 1 --output baseline.json

# 2. Make improvements

# 3. Run new benchmark with comparison
python3 run_benchmark.py --tier 1 --report --compare benchmark/results/baseline.json
```

### Batch Report Generation
```bash
# Generate reports for all results
for file in benchmark/results/*.json; do
    python3 -m utils.report_generator "$file"
done
```

### CI/CD Integration
```bash
# Run and compare (exit code reflects success)
python3 run_benchmark.py --tier 1 --report --compare baseline.json
```
