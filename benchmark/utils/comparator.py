#!/usr/bin/env python3
"""
Comparison tool for ChatCFD benchmark results
Compares two benchmark runs and generates diff reports
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple


class BenchmarkComparator:
    """Compares two benchmark runs and generates comparison reports"""

    def __init__(self, baseline_file: str, current_file: str):
        """
        Initialize comparator

        Args:
            baseline_file: Path to baseline benchmark results JSON
            current_file: Path to current benchmark results JSON
        """
        self.baseline_file = Path(baseline_file)
        self.current_file = Path(current_file)

        with open(self.baseline_file, 'r') as f:
            self.baseline_data = json.load(f)

        with open(self.current_file, 'r') as f:
            self.current_data = json.load(f)

        self.baseline_results = {r['case_name']: r for r in self.baseline_data.get('results', [])}
        self.current_results = {r['case_name']: r for r in self.current_data.get('results', [])}

    def compare(self) -> Dict[str, Any]:
        """
        Compare the two benchmark runs

        Returns:
            Dictionary containing comparison results
        """
        comparison = {
            'baseline_file': str(self.baseline_file.name),
            'current_file': str(self.current_file.name),
            'baseline_timestamp': self.baseline_data.get('timestamp'),
            'current_timestamp': self.current_data.get('timestamp'),
            'summary': self._compare_summary(),
            'status_changes': self._find_status_changes(),
            'metric_changes': self._compare_metrics(),
            'new_cases': self._find_new_cases(),
            'removed_cases': self._find_removed_cases(),
        }

        return comparison

    def _compare_summary(self) -> Dict[str, Any]:
        """Compare high-level summary metrics"""
        baseline_total = self.baseline_data.get('total_cases', 0)
        current_total = self.current_data.get('total_cases', 0)

        baseline_success = self.baseline_data.get('successful_cases', 0)
        current_success = self.current_data.get('successful_cases', 0)

        baseline_rate = (baseline_success / baseline_total * 100) if baseline_total > 0 else 0
        current_rate = (current_success / current_total * 100) if current_total > 0 else 0

        # Calculate average metrics
        baseline_metrics = self._calculate_averages(self.baseline_results.values())
        current_metrics = self._calculate_averages(self.current_results.values())

        return {
            'total_cases': {
                'baseline': baseline_total,
                'current': current_total,
                'change': current_total - baseline_total
            },
            'successful_cases': {
                'baseline': baseline_success,
                'current': current_success,
                'change': current_success - baseline_success
            },
            'success_rate': {
                'baseline': baseline_rate,
                'current': current_rate,
                'change': current_rate - baseline_rate
            },
            'avg_icot_rounds': {
                'baseline': baseline_metrics['avg_rounds'],
                'current': current_metrics['avg_rounds'],
                'change': current_metrics['avg_rounds'] - baseline_metrics['avg_rounds']
            },
            'avg_duration': {
                'baseline': baseline_metrics['avg_duration'],
                'current': current_metrics['avg_duration'],
                'change': current_metrics['avg_duration'] - baseline_metrics['avg_duration']
            },
            'avg_bc_accuracy': {
                'baseline': baseline_metrics['avg_bc'],
                'current': current_metrics['avg_bc'],
                'change': current_metrics['avg_bc'] - baseline_metrics['avg_bc']
            },
            'avg_solver_correctness': {
                'baseline': baseline_metrics['avg_solver'],
                'current': current_metrics['avg_solver'],
                'change': current_metrics['avg_solver'] - baseline_metrics['avg_solver']
            },
            'avg_physical_fidelity': {
                'baseline': baseline_metrics['avg_fidelity'],
                'current': current_metrics['avg_fidelity'],
                'change': current_metrics['avg_fidelity'] - baseline_metrics['avg_fidelity']
            }
        }

    def _calculate_averages(self, results) -> Dict[str, float]:
        """Calculate average metrics from results"""
        results_list = list(results)

        rounds = [r.get('icot_rounds', 0) for r in results_list]
        avg_rounds = sum(rounds) / len(rounds) if rounds else 0

        durations = [r.get('duration', 0) for r in results_list if r.get('duration')]
        avg_duration = sum(durations) / len(durations) if durations else 0

        bc_scores = [r.get('bc_accuracy', 0) for r in results_list if r.get('bc_accuracy') is not None]
        avg_bc = sum(bc_scores) / len(bc_scores) if bc_scores else 0

        solver_scores = [r.get('solver_correctness', 0) for r in results_list if r.get('solver_correctness') is not None]
        avg_solver = sum(solver_scores) / len(solver_scores) if solver_scores else 0

        fidelity_scores = [r.get('physical_fidelity', 0) for r in results_list if r.get('physical_fidelity') is not None]
        avg_fidelity = sum(fidelity_scores) / len(fidelity_scores) if fidelity_scores else 0

        return {
            'avg_rounds': avg_rounds,
            'avg_duration': avg_duration,
            'avg_bc': avg_bc,
            'avg_solver': avg_solver,
            'avg_fidelity': avg_fidelity
        }

    def _find_status_changes(self) -> Dict[str, List[Dict]]:
        """Find cases that changed success/failure status"""
        improvements = []  # Failed -> Success
        regressions = []   # Success -> Failed

        common_cases = set(self.baseline_results.keys()) & set(self.current_results.keys())

        for case_name in common_cases:
            baseline = self.baseline_results[case_name]
            current = self.current_results[case_name]

            baseline_success = baseline.get('success', False)
            current_success = current.get('success', False)

            if not baseline_success and current_success:
                improvements.append({
                    'case_name': case_name,
                    'baseline_rounds': baseline.get('icot_rounds', 0),
                    'current_rounds': current.get('icot_rounds', 0),
                    'baseline_error': baseline.get('error_messages', [''])[0] if baseline.get('error_messages') else 'Unknown'
                })

            elif baseline_success and not current_success:
                regressions.append({
                    'case_name': case_name,
                    'baseline_rounds': baseline.get('icot_rounds', 0),
                    'current_rounds': current.get('icot_rounds', 0),
                    'current_error': current.get('error_messages', [''])[0] if current.get('error_messages') else 'Unknown'
                })

        return {
            'improvements': improvements,
            'regressions': regressions
        }

    def _compare_metrics(self) -> List[Dict]:
        """Compare metrics for cases present in both runs"""
        metric_changes = []

        common_cases = set(self.baseline_results.keys()) & set(self.current_results.keys())

        for case_name in common_cases:
            baseline = self.baseline_results[case_name]
            current = self.current_results[case_name]

            # Only compare if both succeeded
            if baseline.get('success') and current.get('success'):
                changes = {
                    'case_name': case_name,
                    'icot_rounds': {
                        'baseline': baseline.get('icot_rounds', 0),
                        'current': current.get('icot_rounds', 0),
                        'change': current.get('icot_rounds', 0) - baseline.get('icot_rounds', 0)
                    },
                    'duration': {
                        'baseline': baseline.get('duration', 0),
                        'current': current.get('duration', 0),
                        'change': current.get('duration', 0) - baseline.get('duration', 0)
                    }
                }

                # Add validation metrics if available
                if baseline.get('bc_accuracy') is not None and current.get('bc_accuracy') is not None:
                    changes['bc_accuracy'] = {
                        'baseline': baseline.get('bc_accuracy'),
                        'current': current.get('bc_accuracy'),
                        'change': current.get('bc_accuracy') - baseline.get('bc_accuracy')
                    }

                if baseline.get('solver_correctness') is not None and current.get('solver_correctness') is not None:
                    changes['solver_correctness'] = {
                        'baseline': baseline.get('solver_correctness'),
                        'current': current.get('solver_correctness'),
                        'change': current.get('solver_correctness') - baseline.get('solver_correctness')
                    }

                if baseline.get('physical_fidelity') is not None and current.get('physical_fidelity') is not None:
                    changes['physical_fidelity'] = {
                        'baseline': baseline.get('physical_fidelity'),
                        'current': current.get('physical_fidelity'),
                        'change': current.get('physical_fidelity') - baseline.get('physical_fidelity')
                    }

                # Only include if there are significant changes
                has_significant_change = (
                    abs(changes['icot_rounds']['change']) > 0 or
                    abs(changes['duration']['change']) > 1.0 or
                    (changes.get('bc_accuracy') and abs(changes['bc_accuracy']['change']) > 5.0)
                )

                if has_significant_change:
                    metric_changes.append(changes)

        # Sort by most significant changes
        metric_changes.sort(key=lambda x: abs(x['icot_rounds']['change']), reverse=True)

        return metric_changes[:20]  # Top 20 changes

    def _find_new_cases(self) -> List[str]:
        """Find cases in current run but not in baseline"""
        new_cases = set(self.current_results.keys()) - set(self.baseline_results.keys())
        return sorted(list(new_cases))

    def _find_removed_cases(self) -> List[str]:
        """Find cases in baseline but not in current run"""
        removed_cases = set(self.baseline_results.keys()) - set(self.current_results.keys())
        return sorted(list(removed_cases))

    def generate_report(self, output_file: str = None) -> str:
        """
        Generate HTML comparison report

        Args:
            output_file: Output filename (default: comparison_TIMESTAMP.html)

        Returns:
            Path to generated report
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"comparison_{timestamp}.html"

        # Create reports directory
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = reports_dir / output_file

        # Get comparison data
        comparison = self.compare()

        # Generate HTML
        html = self._generate_html(comparison)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"Comparison report generated: {output_path}")
        return str(output_path)

    def _generate_html(self, comparison: Dict) -> str:
        """Generate HTML comparison report"""
        summary = comparison['summary']
        status_changes = comparison['status_changes']
        metric_changes = comparison['metric_changes']

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatCFD Benchmark Comparison</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ChatCFD Benchmark Comparison</h1>
            <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <div class="file-info">
                <p><strong>Baseline:</strong> {comparison['baseline_file']} ({comparison['baseline_timestamp']})</p>
                <p><strong>Current:</strong> {comparison['current_file']} ({comparison['current_timestamp']})</p>
            </div>
        </header>

        {self._generate_summary_section(summary)}
        {self._generate_status_changes_section(status_changes)}
        {self._generate_metric_changes_section(metric_changes)}
        {self._generate_new_removed_section(comparison)}

        <footer>
            <p>ChatCFD Autonomous Benchmark Framework - Comparison Tool</p>
        </footer>
    </div>
</body>
</html>"""

    def _get_css(self) -> str:
        """Return inline CSS styles"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #2196F3;
        }

        h1 {
            color: #2196F3;
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        h2 {
            color: #1976D2;
            font-size: 1.8em;
            margin: 30px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #E3F2FD;
        }

        h3 {
            color: #1565C0;
            font-size: 1.3em;
            margin: 20px 0 10px 0;
        }

        .timestamp {
            color: #666;
            font-size: 0.9em;
        }

        .file-info {
            margin-top: 15px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 4px;
            text-align: left;
        }

        .file-info p {
            margin: 5px 0;
            font-size: 0.9em;
        }

        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        .comparison-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .comparison-card h3 {
            margin-top: 0;
            font-size: 1em;
            color: #666;
        }

        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0;
        }

        .metric-values {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .value {
            font-size: 1.5em;
            font-weight: bold;
        }

        .change {
            font-size: 1.2em;
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 4px;
        }

        .change.positive {
            color: #4CAF50;
            background: #E8F5E9;
        }

        .change.negative {
            color: #f44336;
            background: #FFEBEE;
        }

        .change.neutral {
            color: #666;
            background: #f5f5f5;
        }

        .status-section {
            margin: 30px 0;
        }

        .status-list {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }

        .status-item {
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 4px solid #2196F3;
        }

        .status-item.improvement {
            border-left-color: #4CAF50;
        }

        .status-item.regression {
            border-left-color: #f44336;
        }

        .case-name {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
        }

        .case-details {
            font-size: 0.9em;
            color: #666;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9em;
        }

        thead {
            background: #2196F3;
            color: white;
        }

        th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }

        tbody tr:hover {
            background: #f5f5f5;
        }

        .arrow-up {
            color: #4CAF50;
        }

        .arrow-down {
            color: #f44336;
        }

        footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #666;
            font-size: 0.9em;
        }

        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            h1 {
                font-size: 1.8em;
            }
            .comparison-grid {
                grid-template-columns: 1fr;
            }
        }
        """

    def _generate_summary_section(self, summary: Dict) -> str:
        """Generate summary comparison section"""
        cards = []

        metrics = [
            ('success_rate', 'Success Rate', '%', True),
            ('avg_icot_rounds', 'Avg ICOT Rounds', '', False),
            ('avg_duration', 'Avg Duration', 's', False),
            ('avg_bc_accuracy', 'BC Accuracy', '%', True),
            ('avg_solver_correctness', 'Solver Correctness', '%', True),
            ('avg_physical_fidelity', 'Physical Fidelity', '%', True),
        ]

        for key, label, unit, higher_is_better in metrics:
            data = summary.get(key, {})
            baseline = data.get('baseline', 0)
            current = data.get('current', 0)
            change = data.get('change', 0)

            # Determine change class
            if abs(change) < 0.01:
                change_class = 'neutral'
                arrow = '='
            elif (change > 0 and higher_is_better) or (change < 0 and not higher_is_better):
                change_class = 'positive'
                arrow = '↑'
            else:
                change_class = 'negative'
                arrow = '↓'

            cards.append(f"""
                <div class="comparison-card">
                    <h3>{label}</h3>
                    <div class="metric-row">
                        <div>
                            <div style="font-size: 0.85em; color: #666;">Baseline → Current</div>
                            <div class="value">{baseline:.1f}{unit} → {current:.1f}{unit}</div>
                        </div>
                        <div class="change {change_class}">
                            {arrow} {abs(change):.1f}{unit}
                        </div>
                    </div>
                </div>
            """)

        return f"""
        <section id="summary">
            <h2>Summary Comparison</h2>
            <div class="comparison-grid">
                {''.join(cards)}
            </div>
        </section>
        """

    def _generate_status_changes_section(self, status_changes: Dict) -> str:
        """Generate status changes section"""
        improvements = status_changes.get('improvements', [])
        regressions = status_changes.get('regressions', [])

        improvements_html = []
        for item in improvements:
            improvements_html.append(f"""
                <div class="status-item improvement">
                    <div class="case-name">✓ {item['case_name']}</div>
                    <div class="case-details">
                        Failed ({item['baseline_rounds']} rounds) → Success ({item['current_rounds']} rounds)
                    </div>
                </div>
            """)

        regressions_html = []
        for item in regressions:
            regressions_html.append(f"""
                <div class="status-item regression">
                    <div class="case-name">✗ {item['case_name']}</div>
                    <div class="case-details">
                        Success ({item['baseline_rounds']} rounds) → Failed ({item['current_rounds']} rounds)
                    </div>
                </div>
            """)

        return f"""
        <section id="status-changes" class="status-section">
            <h2>Status Changes</h2>

            <h3 style="color: #4CAF50;">Improvements ({len(improvements)})</h3>
            <div class="status-list">
                {''.join(improvements_html) if improvements_html else '<p>No improvements</p>'}
            </div>

            <h3 style="color: #f44336;">Regressions ({len(regressions)})</h3>
            <div class="status-list">
                {''.join(regressions_html) if regressions_html else '<p>No regressions</p>'}
            </div>
        </section>
        """

    def _generate_metric_changes_section(self, metric_changes: List[Dict]) -> str:
        """Generate metric changes table"""
        if not metric_changes:
            return """
            <section id="metric-changes">
                <h2>Metric Changes</h2>
                <p>No significant metric changes detected.</p>
            </section>
            """

        rows = []
        for change in metric_changes:
            case_name = change['case_name']
            rounds_change = change['icot_rounds']['change']
            duration_change = change['duration']['change']

            rounds_arrow = '↑' if rounds_change > 0 else '↓' if rounds_change < 0 else '='
            duration_arrow = '↑' if duration_change > 0 else '↓' if duration_change < 0 else '='

            rounds_class = 'arrow-down' if rounds_change < 0 else 'arrow-up' if rounds_change > 0 else ''
            duration_class = 'arrow-down' if duration_change < 0 else 'arrow-up' if duration_change > 0 else ''

            rows.append(f"""
                <tr>
                    <td>{case_name}</td>
                    <td class="{rounds_class}">{rounds_arrow} {abs(rounds_change):.0f}</td>
                    <td class="{duration_class}">{duration_arrow} {abs(duration_change):.1f}s</td>
                </tr>
            """)

        return f"""
        <section id="metric-changes">
            <h2>Top Metric Changes (Successful Cases)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Case Name</th>
                        <th>ICOT Rounds Change</th>
                        <th>Duration Change</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </section>
        """

    def _generate_new_removed_section(self, comparison: Dict) -> str:
        """Generate new/removed cases section"""
        new_cases = comparison.get('new_cases', [])
        removed_cases = comparison.get('removed_cases', [])

        if not new_cases and not removed_cases:
            return ""

        new_html = '<ul>' + ''.join([f'<li>{case}</li>' for case in new_cases]) + '</ul>' if new_cases else '<p>None</p>'
        removed_html = '<ul>' + ''.join([f'<li>{case}</li>' for case in removed_cases]) + '</ul>' if removed_cases else '<p>None</p>'

        return f"""
        <section id="case-changes">
            <h2>Case Changes</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                <div>
                    <h3 style="color: #4CAF50;">New Cases ({len(new_cases)})</h3>
                    {new_html}
                </div>
                <div>
                    <h3 style="color: #f44336;">Removed Cases ({len(removed_cases)})</h3>
                    {removed_html}
                </div>
            </div>
        </section>
        """

    def print_summary(self):
        """Print comparison summary to console"""
        comparison = self.compare()
        summary = comparison['summary']
        status_changes = comparison['status_changes']

        print("\n" + "="*80)
        print("BENCHMARK COMPARISON SUMMARY")
        print("="*80)
        print(f"Baseline: {comparison['baseline_file']}")
        print(f"Current:  {comparison['current_file']}")
        print("="*80)

        print(f"\nSuccess Rate: {summary['success_rate']['baseline']:.1f}% → {summary['success_rate']['current']:.1f}% "
              f"({summary['success_rate']['change']:+.1f}%)")

        print(f"Avg ICOT Rounds: {summary['avg_icot_rounds']['baseline']:.1f} → {summary['avg_icot_rounds']['current']:.1f} "
              f"({summary['avg_icot_rounds']['change']:+.1f})")

        print(f"Avg Duration: {summary['avg_duration']['baseline']:.1f}s → {summary['avg_duration']['current']:.1f}s "
              f"({summary['avg_duration']['change']:+.1f}s)")

        print(f"\nStatus Changes:")
        print(f"  Improvements: {len(status_changes['improvements'])}")
        print(f"  Regressions:  {len(status_changes['regressions'])}")

        print("="*80 + "\n")


def main():
    """CLI interface for comparator"""
    import argparse

    parser = argparse.ArgumentParser(description='Compare two benchmark runs')
    parser.add_argument('baseline', help='Path to baseline benchmark results JSON')
    parser.add_argument('current', help='Path to current benchmark results JSON')
    parser.add_argument('-o', '--output', help='Output HTML filename')
    parser.add_argument('--summary-only', action='store_true', help='Print summary only, no HTML report')

    args = parser.parse_args()

    comparator = BenchmarkComparator(args.baseline, args.current)

    if args.summary_only:
        comparator.print_summary()
    else:
        comparator.print_summary()
        output_path = comparator.generate_report(args.output)
        print(f"\nComparison report generated: {output_path}")
        print(f"Open in browser: file://{output_path}")


if __name__ == "__main__":
    main()
