# Phase 3: Reporting and Visualization

Comprehensive reporting tools for ChatCFD benchmark results.

## Overview

Phase 3 provides three main tools:
1. **Report Generator** - Creates comprehensive HTML reports with embedded visualizations
2. **Visualizer** - Generates standalone chart images
3. **Comparator** - Compares two benchmark runs and highlights differences

## Quick Start

### Generate Report After Benchmark Run

```bash
# Run benchmark with automatic report generation
python run_benchmark.py --tier 1 --report

# Run with comparison to baseline
python run_benchmark.py --tier 1 --report --compare benchmark/results/baseline.json
```

### Generate Report from Existing Results

```bash
# Generate HTML report
python -m utils.report_generator benchmark/results/benchmark_tier1_20260312_123456.json

# With custom output name
python -m utils.report_generator benchmark/results/results.json -o custom_report.html
```

### Generate Standalone Charts

```bash
# Generate all charts
python -m utils.visualizer benchmark/results/results.json

# Generate specific chart
python -m utils.visualizer benchmark/results/results.json -c success_rate_by_tier

# With filename prefix
python -m utils.visualizer benchmark/results/results.json -p tier1_
```

### Compare Two Benchmark Runs

```bash
# Generate comparison report
python -m utils.comparator benchmark/results/baseline.json benchmark/results/current.json

# Print summary only (no HTML)
python -m utils.comparator baseline.json current.json --summary-only

# Custom output filename
python -m utils.comparator baseline.json current.json -o my_comparison.html
```

## Report Generator

### Features

- **Executive Summary**: High-level metrics (success rate, avg rounds, validation scores)
- **Interactive Charts**: Embedded visualizations (success by tier, rounds distribution, validation metrics)
- **Detailed Results Table**: Sortable, filterable table with all test cases
- **Validation Analysis**: Common validation issues and error patterns
- **Error Analysis**: Top error messages and failure patterns
- **CSV Export**: Export results table to CSV
- **Self-Contained**: All CSS/JS/images embedded (no external dependencies)
- **Mobile-Friendly**: Responsive design
- **Print-Ready**: Optimized for printing

### Output

Reports are saved to `benchmark/reports/report_TIMESTAMP.html`

### Report Sections

1. **Executive Summary**
   - Total cases, success rate, avg ICOT rounds, avg duration
   - Validation metrics (BC accuracy, solver correctness, physical fidelity)
   - Total cost and time

2. **Visualizations**
   - Success rate by tier (bar chart)
   - ICOT rounds distribution (histogram)
   - Validation metrics comparison (bar chart)
   - Duration vs rounds scatter plot

3. **Detailed Results**
   - Sortable table with all cases
   - Filter by case name or status
   - Export to CSV

4. **Validation Analysis**
   - Common validation issues
   - Issue frequency

5. **Error Analysis**
   - Top error messages
   - Failure patterns

## Visualizer

### Available Charts

1. **success_rate_by_tier** - Bar chart showing success rate for each tier
2. **icot_rounds_distribution** - Histogram of ICOT rounds with mean/median
3. **validation_metrics** - Average validation scores and distributions
4. **duration_vs_rounds** - Scatter plot with success/failure coloring
5. **error_distribution** - Top 10 error types
6. **solver_distribution** - Solver usage and success rates

### Output

Charts are saved to `benchmark/reports/charts/` as PNG files (150 DPI)

### Usage in Code

```python
from visualizer import BenchmarkVisualizer

visualizer = BenchmarkVisualizer('benchmark/results/results.json')

# Generate all charts
charts = visualizer.generate_all_charts(prefix='tier1_')

# Generate specific chart
visualizer.plot_success_rate_by_tier('output.png')
```

## Comparator

### Features

- **Summary Comparison**: High-level metric changes
- **Status Changes**: Cases that changed from success to failure (or vice versa)
- **Metric Changes**: Detailed changes for successful cases
- **New/Removed Cases**: Cases added or removed between runs
- **Visual Indicators**: Color-coded improvements/regressions
- **HTML Report**: Comprehensive comparison report

### Output

Comparison reports are saved to `benchmark/reports/comparison_TIMESTAMP.html`

### Comparison Sections

1. **Summary Comparison**
   - Success rate change
   - Average metrics change
   - Overall improvements/regressions

2. **Status Changes**
   - Improvements (failed → success)
   - Regressions (success → failed)

3. **Metric Changes**
   - Top 20 cases with significant metric changes
   - ICOT rounds and duration changes

4. **Case Changes**
   - New cases in current run
   - Removed cases from baseline

### Usage in Code

```python
from comparator import BenchmarkComparator

comparator = BenchmarkComparator('baseline.json', 'current.json')

# Print summary to console
comparator.print_summary()

# Generate HTML report
report_path = comparator.generate_report()

# Get comparison data
comparison = comparator.compare()
```

## Dependencies

### Required

- Python 3.7+
- Standard library only (json, pathlib, datetime, etc.)

### Optional

- **matplotlib** - For chart generation (highly recommended)
  ```bash
  pip install matplotlib
  ```

If matplotlib is not installed:
- Report generator will show "Charts unavailable" message
- Visualizer will not work
- Comparator will work but without charts

## File Structure

```
benchmark/
├── reports/                    # Generated reports
│   ├── report_*.html          # HTML reports
│   ├── comparison_*.html      # Comparison reports
│   └── charts/                # Standalone chart images
│       ├── success_rate_by_tier.png
│       ├── icot_rounds_distribution.png
│       └── ...
├── results/                    # Benchmark results (JSON)
│   ├── benchmark_tier1_*.json
│   └── ...
└── utils/
    ├── report_generator.py    # HTML report generator
    ├── visualizer.py          # Chart generator
    └── comparator.py          # Comparison tool
```

## Examples

### Complete Workflow

```bash
# 1. Run baseline benchmark
python run_benchmark.py --tier 1 --output baseline.json

# 2. Make changes to ChatCFD

# 3. Run new benchmark with comparison
python run_benchmark.py --tier 1 --report --compare benchmark/results/baseline.json

# 4. Open reports in browser
# - benchmark/reports/report_TIMESTAMP.html
# - benchmark/reports/comparison_TIMESTAMP.html
```

### Batch Processing

```bash
# Generate reports for all results
for file in benchmark/results/*.json; do
    python -m utils.report_generator "$file"
done

# Generate all charts for a result
python -m utils.visualizer benchmark/results/tier1_full.json -p tier1_
```

### Integration with CI/CD

```bash
# Run benchmark and generate report (exit code reflects success)
python run_benchmark.py --tier 1 --report

# Compare with baseline and fail if regressions
python -m utils.comparator baseline.json current.json --summary-only
```

## Color Coding

### Reports

- **Green**: Good metrics (>80%), improvements, successes
- **Yellow**: Warning metrics (60-80%)
- **Red**: Bad metrics (<60%), regressions, failures
- **Blue**: Informational

### Charts

- **Green (#4CAF50)**: Success, Tier 1, positive metrics
- **Blue (#2196F3)**: Tier 2, neutral metrics
- **Orange (#FF9800)**: Tier 3, warnings
- **Red (#f44336)**: Failures, errors

## Tips

1. **Always generate reports** - Use `--report` flag for better insights
2. **Compare runs** - Track progress over time with `--compare`
3. **Export to CSV** - Use the export button in HTML reports for further analysis
4. **Print reports** - Reports are optimized for printing (use browser print)
5. **Share reports** - HTML reports are self-contained and can be shared via email/web
6. **Archive baselines** - Keep baseline results for long-term tracking

## Troubleshooting

### Charts not showing in report

- Install matplotlib: `pip install matplotlib`
- Check console for error messages

### Report generation fails

- Verify JSON file is valid
- Check file permissions
- Ensure `benchmark/reports/` directory is writable

### Comparison shows no changes

- Verify both files contain results for the same cases
- Check that case names match exactly
- Ensure both files are valid benchmark results

## Future Enhancements

Potential additions for Phase 4:
- Interactive web dashboard
- Time-series tracking across multiple runs
- Automated regression detection
- Cost analysis and optimization suggestions
- Performance profiling integration
- Export to other formats (PDF, Excel)
