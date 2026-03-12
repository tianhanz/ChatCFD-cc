#!/usr/bin/env python3
"""
Visualization utilities for ChatCFD benchmark results
Generates standalone charts and visualizations
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib")


class BenchmarkVisualizer:
    """Creates visualizations from benchmark results"""

    def __init__(self, results_file: str):
        """
        Initialize visualizer

        Args:
            results_file: Path to benchmark results JSON file
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for visualization")

        self.results_file = Path(results_file)
        with open(self.results_file, 'r') as f:
            self.data = json.load(f)

        self.results = self.data.get('results', [])
        self.charts_dir = Path(__file__).parent.parent / "reports" / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_charts(self, prefix: str = "") -> Dict[str, str]:
        """
        Generate all available charts

        Args:
            prefix: Prefix for output filenames

        Returns:
            Dictionary mapping chart names to file paths
        """
        charts = {}

        chart_functions = [
            ('success_rate_by_tier', self.plot_success_rate_by_tier),
            ('icot_rounds_distribution', self.plot_icot_rounds_distribution),
            ('validation_metrics', self.plot_validation_metrics),
            ('duration_vs_rounds', self.plot_duration_vs_rounds),
            ('error_distribution', self.plot_error_distribution),
            ('solver_distribution', self.plot_solver_distribution),
        ]

        for chart_name, chart_func in chart_functions:
            try:
                filename = f"{prefix}{chart_name}.png" if prefix else f"{chart_name}.png"
                output_path = self.charts_dir / filename
                chart_func(str(output_path))
                charts[chart_name] = str(output_path)
                print(f"Generated: {output_path}")
            except Exception as e:
                print(f"Warning: Failed to generate {chart_name}: {e}")

        return charts

    def plot_success_rate_by_tier(self, output_path: str):
        """Plot success rate grouped by tier"""
        # Group by tier
        tier_data = {}
        for result in self.results:
            case_name = result.get('case_name', '')
            tier = self._extract_tier(case_name)

            if tier not in tier_data:
                tier_data[tier] = {'total': 0, 'success': 0}

            tier_data[tier]['total'] += 1
            if result.get('success'):
                tier_data[tier]['success'] += 1

        # Calculate success rates
        tiers = sorted(tier_data.keys())
        success_rates = [(tier_data[t]['success'] / tier_data[t]['total'] * 100) if tier_data[t]['total'] > 0 else 0
                        for t in tiers]
        totals = [tier_data[t]['total'] for t in tiers]

        # Create chart
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0']
        bars = ax.bar(tiers, success_rates, color=colors[:len(tiers)], alpha=0.8, edgecolor='black')

        ax.set_ylabel('Success Rate (%)', fontsize=13, fontweight='bold')
        ax.set_xlabel('Tier', fontsize=13, fontweight='bold')
        ax.set_title('Success Rate by Tier', fontsize=16, fontweight='bold', pad=20)
        ax.set_ylim(0, 105)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # Add value labels on bars
        for bar, rate, total in zip(bars, success_rates, totals):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                   f'{rate:.1f}%\n({total} cases)',
                   ha='center', va='bottom', fontweight='bold', fontsize=10)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def plot_icot_rounds_distribution(self, output_path: str):
        """Plot histogram of ICOT rounds"""
        rounds = [r.get('icot_rounds', 0) for r in self.results if r.get('icot_rounds') is not None]

        if not rounds:
            print("No ICOT rounds data available")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        # Create histogram
        n, bins, patches = ax.hist(rounds, bins=30, color='#2196F3', edgecolor='black', alpha=0.7)

        # Color bars based on value
        for i, patch in enumerate(patches):
            if bins[i] < 10:
                patch.set_facecolor('#4CAF50')
            elif bins[i] < 20:
                patch.set_facecolor('#2196F3')
            else:
                patch.set_facecolor('#FF9800')

        ax.set_xlabel('ICOT Rounds', fontsize=13, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=13, fontweight='bold')
        ax.set_title('ICOT Rounds Distribution', fontsize=16, fontweight='bold', pad=20)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # Add statistics
        mean_rounds = np.mean(rounds)
        median_rounds = np.median(rounds)
        ax.axvline(mean_rounds, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_rounds:.1f}')
        ax.axvline(median_rounds, color='orange', linestyle='--', linewidth=2, label=f'Median: {median_rounds:.1f}')
        ax.legend(fontsize=11)

        # Add text box with stats
        stats_text = f'Total Cases: {len(rounds)}\nMin: {min(rounds)}\nMax: {max(rounds)}\nStd: {np.std(rounds):.1f}'
        ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def plot_validation_metrics(self, output_path: str):
        """Plot validation metrics comparison"""
        bc_scores = [r.get('bc_accuracy', 0) for r in self.results if r.get('bc_accuracy') is not None]
        solver_scores = [r.get('solver_correctness', 0) for r in self.results if r.get('solver_correctness') is not None]
        fidelity_scores = [r.get('physical_fidelity', 0) for r in self.results if r.get('physical_fidelity') is not None]

        if not (bc_scores or solver_scores or fidelity_scores):
            print("No validation metrics available")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Left plot: Average scores
        metrics = []
        averages = []
        colors_list = []

        if bc_scores:
            metrics.append('BC\nAccuracy')
            averages.append(np.mean(bc_scores))
            colors_list.append('#4CAF50')

        if solver_scores:
            metrics.append('Solver\nCorrectness')
            averages.append(np.mean(solver_scores))
            colors_list.append('#2196F3')

        if fidelity_scores:
            metrics.append('Physical\nFidelity')
            averages.append(np.mean(fidelity_scores))
            colors_list.append('#FF9800')

        bars = ax1.bar(metrics, averages, color=colors_list, alpha=0.8, edgecolor='black')
        ax1.set_ylabel('Average Score (%)', fontsize=12, fontweight='bold')
        ax1.set_title('Average Validation Metrics', fontsize=14, fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')

        # Add value labels
        for bar, val in zip(bars, averages):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'{val:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)

        # Right plot: Box plots
        data_to_plot = []
        labels = []

        if bc_scores:
            data_to_plot.append(bc_scores)
            labels.append('BC')

        if solver_scores:
            data_to_plot.append(solver_scores)
            labels.append('Solver')

        if fidelity_scores:
            data_to_plot.append(fidelity_scores)
            labels.append('Fidelity')

        bp = ax2.boxplot(data_to_plot, labels=labels, patch_artist=True)

        # Color box plots
        for patch, color in zip(bp['boxes'], colors_list):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax2.set_ylabel('Score (%)', fontsize=12, fontweight='bold')
        ax2.set_title('Validation Metrics Distribution', fontsize=14, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.grid(axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def plot_duration_vs_rounds(self, output_path: str):
        """Plot duration vs ICOT rounds scatter plot"""
        durations = []
        rounds = []
        success_status = []

        for r in self.results:
            if r.get('duration') and r.get('icot_rounds') is not None:
                durations.append(r['duration'])
                rounds.append(r['icot_rounds'])
                success_status.append(r.get('success', False))

        if not durations:
            print("No duration data available")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        # Separate success and failure
        success_rounds = [r for r, s in zip(rounds, success_status) if s]
        success_durations = [d for d, s in zip(durations, success_status) if s]
        fail_rounds = [r for r, s in zip(rounds, success_status) if not s]
        fail_durations = [d for d, s in zip(durations, success_status) if not s]

        # Plot
        ax.scatter(success_rounds, success_durations, c='#4CAF50', alpha=0.6, s=60, label='Success', edgecolors='black')
        ax.scatter(fail_rounds, fail_durations, c='#f44336', alpha=0.6, s=60, label='Failed', edgecolors='black')

        ax.set_xlabel('ICOT Rounds', fontsize=13, fontweight='bold')
        ax.set_ylabel('Duration (seconds)', fontsize=13, fontweight='bold')
        ax.set_title('Duration vs ICOT Rounds', fontsize=16, fontweight='bold', pad=20)
        ax.grid(alpha=0.3, linestyle='--')
        ax.legend(fontsize=11, loc='upper left')

        # Add trend line
        if len(rounds) > 1:
            z = np.polyfit(rounds, durations, 1)
            p = np.poly1d(z)
            ax.plot(sorted(rounds), p(sorted(rounds)), "r--", alpha=0.5, linewidth=2, label='Trend')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def plot_error_distribution(self, output_path: str):
        """Plot distribution of error types"""
        failed_cases = [r for r in self.results if not r.get('success')]

        if not failed_cases:
            print("No failures to analyze")
            return

        # Collect error types
        error_types = {}
        for result in failed_cases:
            issues = result.get('validation_issues', [])
            errors = result.get('error_messages', [])

            for issue in issues:
                error_type = issue.split(':')[0] if ':' in issue else 'Other'
                error_types[error_type] = error_types.get(error_type, 0) + 1

            if not issues and errors:
                error_types['Runtime Error'] = error_types.get('Runtime Error', 0) + 1

        if not error_types:
            error_types['Unknown'] = len(failed_cases)

        # Sort by frequency
        sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [e[0] for e in sorted_errors]
        values = [e[1] for e in sorted_errors]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.Set3(range(len(labels)))
        bars = ax.barh(labels, values, color=colors, edgecolor='black', alpha=0.8)

        ax.set_xlabel('Frequency', fontsize=13, fontweight='bold')
        ax.set_title('Top 10 Error Types', fontsize=16, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        # Add value labels
        for bar, val in zip(bars, values):
            width = bar.get_width()
            ax.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                   f'{val}', ha='left', va='center', fontweight='bold', fontsize=10)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def plot_solver_distribution(self, output_path: str):
        """Plot distribution of solvers used"""
        solver_counts = {}
        solver_success = {}

        for result in self.results:
            solver = result.get('solver_detected', 'Unknown')
            if solver:
                solver_counts[solver] = solver_counts.get(solver, 0) + 1
                if result.get('success'):
                    solver_success[solver] = solver_success.get(solver, 0) + 1

        if not solver_counts:
            print("No solver data available")
            return

        # Sort by frequency
        sorted_solvers = sorted(solver_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        solvers = [s[0] for s in sorted_solvers]
        totals = [s[1] for s in sorted_solvers]
        successes = [solver_success.get(s, 0) for s in solvers]
        failures = [t - s for t, s in zip(totals, successes)]

        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(solvers))
        width = 0.6

        # Stacked bar chart
        p1 = ax.bar(x, successes, width, label='Success', color='#4CAF50', edgecolor='black')
        p2 = ax.bar(x, failures, width, bottom=successes, label='Failed', color='#f44336', edgecolor='black')

        ax.set_ylabel('Number of Cases', fontsize=13, fontweight='bold')
        ax.set_xlabel('Solver', fontsize=13, fontweight='bold')
        ax.set_title('Solver Distribution and Success Rate', fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(solvers, rotation=45, ha='right')
        ax.legend(fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # Add success rate labels
        for i, (total, success) in enumerate(zip(totals, successes)):
            rate = (success / total * 100) if total > 0 else 0
            ax.text(i, total + 0.5, f'{rate:.0f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def _extract_tier(self, case_name: str) -> str:
        """Extract tier from case name"""
        case_lower = case_name.lower()
        if 'tier1' in case_lower or case_name.startswith('1_'):
            return 'Tier 1'
        elif 'tier2' in case_lower or case_name.startswith('2_'):
            return 'Tier 2'
        elif 'tier3' in case_lower or case_name.startswith('3_'):
            return 'Tier 3'
        else:
            return 'Unknown'


def main():
    """CLI interface for visualizer"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate visualizations from benchmark results')
    parser.add_argument('results_file', help='Path to benchmark results JSON file')
    parser.add_argument('-p', '--prefix', default='', help='Prefix for output filenames')
    parser.add_argument('-c', '--chart', help='Generate specific chart only')

    args = parser.parse_args()

    visualizer = BenchmarkVisualizer(args.results_file)

    if args.chart:
        # Generate specific chart
        chart_method = getattr(visualizer, f'plot_{args.chart}', None)
        if chart_method:
            output_path = visualizer.charts_dir / f"{args.prefix}{args.chart}.png"
            chart_method(str(output_path))
            print(f"Generated: {output_path}")
        else:
            print(f"Unknown chart: {args.chart}")
    else:
        # Generate all charts
        charts = visualizer.generate_all_charts(args.prefix)
        print(f"\nGenerated {len(charts)} charts in: {visualizer.charts_dir}")


if __name__ == "__main__":
    main()
