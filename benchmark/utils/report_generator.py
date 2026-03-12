#!/usr/bin/env python3
"""
HTML Report Generator for ChatCFD Benchmark Results
Generates comprehensive, self-contained HTML reports with embedded visualizations
"""
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import io

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Charts will be disabled.")


class ReportGenerator:
    """Generates comprehensive HTML reports from benchmark results"""

    def __init__(self, results_file: str):
        """
        Initialize report generator

        Args:
            results_file: Path to benchmark results JSON file
        """
        self.results_file = Path(results_file)
        with open(self.results_file, 'r') as f:
            self.data = json.load(f)

        self.results = self.data.get('results', [])
        self.timestamp = self.data.get('timestamp', datetime.now().isoformat())
        self.total_cases = self.data.get('total_cases', len(self.results))
        self.successful_cases = self.data.get('successful_cases',
                                              sum(1 for r in self.results if r.get('success')))

    def generate_report(self, output_file: str = None) -> str:
        """
        Generate comprehensive HTML report

        Args:
            output_file: Output filename (default: report_TIMESTAMP.html)

        Returns:
            Path to generated report
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"report_{timestamp}.html"

        # Create reports directory
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = reports_dir / output_file

        # Generate HTML content
        html = self._generate_html()

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"Report generated: {output_path}")
        return str(output_path)

    def _generate_html(self) -> str:
        """Generate complete HTML document"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatCFD Benchmark Report</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ChatCFD Benchmark Report</h1>
            <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p class="source">Source: {self.results_file.name}</p>
        </header>

        {self._generate_executive_summary()}
        {self._generate_charts_section()}
        {self._generate_results_table()}
        {self._generate_validation_section()}
        {self._generate_error_analysis()}

        <footer>
            <p>ChatCFD Autonomous Benchmark Framework - Phase 3 Reporting</p>
        </footer>
    </div>

    <script>
        {self._get_javascript()}
    </script>
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

        .timestamp, .source {
            color: #666;
            font-size: 0.9em;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        .summary-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .summary-card.success {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }

        .summary-card.warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        .summary-card.info {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }

        .summary-card h3 {
            color: white;
            font-size: 0.9em;
            font-weight: normal;
            margin-bottom: 10px;
        }

        .summary-card .value {
            font-size: 2.5em;
            font-weight: bold;
        }

        .summary-card .subtext {
            font-size: 0.85em;
            opacity: 0.9;
            margin-top: 5px;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin: 30px 0;
        }

        .chart-container {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        .chart-container h3 {
            margin-top: 0;
            margin-bottom: 15px;
        }

        .chart-container img {
            width: 100%;
            height: auto;
            border-radius: 4px;
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
            cursor: pointer;
            user-select: none;
        }

        th:hover {
            background: #1976D2;
        }

        td {
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }

        tbody tr:hover {
            background: #f5f5f5;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .status-success {
            background: #4CAF50;
            color: white;
        }

        .status-fail {
            background: #f44336;
            color: white;
        }

        .metric-good {
            color: #4CAF50;
            font-weight: 600;
        }

        .metric-warning {
            color: #FF9800;
            font-weight: 600;
        }

        .metric-bad {
            color: #f44336;
            font-weight: 600;
        }

        .error-list {
            background: #ffebee;
            border-left: 4px solid #f44336;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }

        .error-item {
            margin: 8px 0;
            padding: 8px;
            background: white;
            border-radius: 4px;
        }

        .error-count {
            font-weight: bold;
            color: #f44336;
        }

        .filter-controls {
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 4px;
        }

        .filter-controls label {
            margin-right: 15px;
        }

        .filter-controls input, .filter-controls select {
            padding: 5px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-right: 10px;
        }

        footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #666;
            font-size: 0.9em;
        }

        @media print {
            body {
                background: white;
                padding: 0;
            }
            .container {
                box-shadow: none;
            }
            .filter-controls {
                display: none;
            }
        }

        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            h1 {
                font-size: 1.8em;
            }
            .summary-grid {
                grid-template-columns: 1fr;
            }
            .charts-grid {
                grid-template-columns: 1fr;
            }
            table {
                font-size: 0.8em;
            }
        }
        """

    def _generate_executive_summary(self) -> str:
        """Generate executive summary section"""
        success_rate = (self.successful_cases / self.total_cases * 100) if self.total_cases > 0 else 0

        # Calculate averages
        durations = [r.get('duration', 0) for r in self.results if r.get('duration')]
        avg_duration = sum(durations) / len(durations) if durations else 0

        rounds = [r.get('icot_rounds', 0) for r in self.results]
        avg_rounds = sum(rounds) / len(rounds) if rounds else 0

        # Validation metrics
        bc_scores = [r.get('bc_accuracy', 0) for r in self.results if r.get('bc_accuracy') is not None]
        avg_bc = sum(bc_scores) / len(bc_scores) if bc_scores else 0

        solver_scores = [r.get('solver_correctness', 0) for r in self.results if r.get('solver_correctness') is not None]
        avg_solver = sum(solver_scores) / len(solver_scores) if solver_scores else 0

        fidelity_scores = [r.get('physical_fidelity', 0) for r in self.results if r.get('physical_fidelity') is not None]
        avg_fidelity = sum(fidelity_scores) / len(fidelity_scores) if fidelity_scores else 0

        total_time = sum(durations)

        return f"""
        <section id="summary">
            <h2>Executive Summary</h2>
            <div class="summary-grid">
                <div class="summary-card info">
                    <h3>Total Cases</h3>
                    <div class="value">{self.total_cases}</div>
                    <div class="subtext">Test cases executed</div>
                </div>
                <div class="summary-card success">
                    <h3>Success Rate</h3>
                    <div class="value">{success_rate:.1f}%</div>
                    <div class="subtext">{self.successful_cases} successful</div>
                </div>
                <div class="summary-card">
                    <h3>Avg ICOT Rounds</h3>
                    <div class="value">{avg_rounds:.1f}</div>
                    <div class="subtext">Iterations per case</div>
                </div>
                <div class="summary-card info">
                    <h3>Avg Duration</h3>
                    <div class="value">{avg_duration:.1f}s</div>
                    <div class="subtext">Total: {total_time/60:.1f} min</div>
                </div>
                <div class="summary-card success">
                    <h3>BC Accuracy</h3>
                    <div class="value">{avg_bc:.1f}%</div>
                    <div class="subtext">Boundary conditions</div>
                </div>
                <div class="summary-card success">
                    <h3>Solver Correctness</h3>
                    <div class="value">{avg_solver:.1f}%</div>
                    <div class="subtext">Configuration accuracy</div>
                </div>
                <div class="summary-card success">
                    <h3>Physical Fidelity</h3>
                    <div class="value">{avg_fidelity:.1f}%</div>
                    <div class="subtext">Physical accuracy</div>
                </div>
                <div class="summary-card warning">
                    <h3>Failed Cases</h3>
                    <div class="value">{self.total_cases - self.successful_cases}</div>
                    <div class="subtext">{100 - success_rate:.1f}% failure rate</div>
                </div>
            </div>
        </section>
        """

    def _generate_charts_section(self) -> str:
        """Generate charts section with embedded images"""
        if not MATPLOTLIB_AVAILABLE:
            return """
            <section id="charts">
                <h2>Visualizations</h2>
                <p style="color: #f44336;">Charts unavailable: matplotlib not installed</p>
            </section>
            """

        charts_html = '<section id="charts"><h2>Visualizations</h2><div class="charts-grid">'

        # Generate each chart
        charts = [
            ('success_rate', 'Success Rate by Tier', self._create_success_rate_chart),
            ('rounds_dist', 'ICOT Rounds Distribution', self._create_rounds_distribution),
            ('validation', 'Validation Metrics', self._create_validation_chart),
            ('duration', 'Duration vs Complexity', self._create_duration_scatter),
        ]

        for chart_id, title, chart_func in charts:
            try:
                img_data = chart_func()
                if img_data:
                    charts_html += f"""
                    <div class="chart-container">
                        <h3>{title}</h3>
                        <img src="data:image/png;base64,{img_data}" alt="{title}">
                    </div>
                    """
            except Exception as e:
                print(f"Warning: Failed to generate {title}: {e}")

        charts_html += '</div></section>'
        return charts_html

    def _create_success_rate_chart(self) -> str:
        """Create success rate by tier bar chart"""
        # Group by tier
        tier_data = {}
        for result in self.results:
            # Extract tier from case name (assuming format like "tier1_case_name")
            case_name = result.get('case_name', '')
            tier = 'Unknown'
            if 'tier1' in case_name.lower() or case_name.startswith('1_'):
                tier = 'Tier 1'
            elif 'tier2' in case_name.lower() or case_name.startswith('2_'):
                tier = 'Tier 2'
            elif 'tier3' in case_name.lower() or case_name.startswith('3_'):
                tier = 'Tier 3'

            if tier not in tier_data:
                tier_data[tier] = {'total': 0, 'success': 0}

            tier_data[tier]['total'] += 1
            if result.get('success'):
                tier_data[tier]['success'] += 1

        # Calculate success rates
        tiers = sorted(tier_data.keys())
        success_rates = [(tier_data[t]['success'] / tier_data[t]['total'] * 100) if tier_data[t]['total'] > 0 else 0
                        for t in tiers]

        # Create chart
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(tiers, success_rates, color=['#4CAF50', '#2196F3', '#FF9800'])

        ax.set_ylabel('Success Rate (%)', fontsize=12)
        ax.set_title('Success Rate by Tier', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels on bars
        for bar, rate in zip(bars, success_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _create_rounds_distribution(self) -> str:
        """Create ICOT rounds distribution histogram"""
        rounds = [r.get('icot_rounds', 0) for r in self.results if r.get('icot_rounds') is not None]

        if not rounds:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(rounds, bins=20, color='#2196F3', edgecolor='black', alpha=0.7)

        ax.set_xlabel('ICOT Rounds', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title('ICOT Rounds Distribution', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        # Add mean line
        mean_rounds = sum(rounds) / len(rounds)
        ax.axvline(mean_rounds, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_rounds:.1f}')
        ax.legend()

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _create_validation_chart(self) -> str:
        """Create validation metrics comparison chart"""
        bc_scores = [r.get('bc_accuracy', 0) for r in self.results if r.get('bc_accuracy') is not None]
        solver_scores = [r.get('solver_correctness', 0) for r in self.results if r.get('solver_correctness') is not None]
        fidelity_scores = [r.get('physical_fidelity', 0) for r in self.results if r.get('physical_fidelity') is not None]

        if not (bc_scores or solver_scores or fidelity_scores):
            return None

        metrics = []
        values = []

        if bc_scores:
            metrics.append('BC Accuracy')
            values.append(sum(bc_scores) / len(bc_scores))

        if solver_scores:
            metrics.append('Solver\nCorrectness')
            values.append(sum(solver_scores) / len(solver_scores))

        if fidelity_scores:
            metrics.append('Physical\nFidelity')
            values.append(sum(fidelity_scores) / len(fidelity_scores))

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(metrics, values, color=['#4CAF50', '#2196F3', '#FF9800'])

        ax.set_ylabel('Score (%)', fontsize=12)
        ax.set_title('Average Validation Metrics', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _create_duration_scatter(self) -> str:
        """Create duration vs ICOT rounds scatter plot"""
        durations = []
        rounds = []
        colors = []

        for r in self.results:
            if r.get('duration') and r.get('icot_rounds') is not None:
                durations.append(r['duration'])
                rounds.append(r['icot_rounds'])
                colors.append('#4CAF50' if r.get('success') else '#f44336')

        if not durations:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(rounds, durations, c=colors, alpha=0.6, s=50)

        ax.set_xlabel('ICOT Rounds', fontsize=12)
        ax.set_ylabel('Duration (seconds)', fontsize=12)
        ax.set_title('Duration vs ICOT Rounds', fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3)

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#4CAF50', label='Success'),
            Patch(facecolor='#f44336', label='Failed')
        ]
        ax.legend(handles=legend_elements)

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

    def _generate_results_table(self) -> str:
        """Generate detailed results table"""
        rows = []
        for i, result in enumerate(self.results, 1):
            case_name = result.get('case_name', 'Unknown')
            success = result.get('success', False)
            status_class = 'status-success' if success else 'status-fail'
            status_text = 'Success' if success else 'Failed'

            duration = result.get('duration', 0)
            rounds = result.get('icot_rounds', 0)
            solver = result.get('solver_detected', 'N/A')

            # Validation metrics
            bc = result.get('bc_accuracy')
            bc_display = f"{bc:.1f}%" if bc is not None else 'N/A'
            bc_class = self._get_metric_class(bc) if bc is not None else ''

            solver_correct = result.get('solver_correctness')
            solver_display = f"{solver_correct:.1f}%" if solver_correct is not None else 'N/A'
            solver_class = self._get_metric_class(solver_correct) if solver_correct is not None else ''

            fidelity = result.get('physical_fidelity')
            fidelity_display = f"{fidelity:.1f}%" if fidelity is not None else 'N/A'
            fidelity_class = self._get_metric_class(fidelity) if fidelity is not None else ''

            rows.append(f"""
                <tr>
                    <td>{i}</td>
                    <td>{case_name}</td>
                    <td><span class="status-badge {status_class}">{status_text}</span></td>
                    <td>{rounds}</td>
                    <td>{duration:.1f}s</td>
                    <td>{solver}</td>
                    <td class="{bc_class}">{bc_display}</td>
                    <td class="{solver_class}">{solver_display}</td>
                    <td class="{fidelity_class}">{fidelity_display}</td>
                </tr>
            """)

        return f"""
        <section id="results">
            <h2>Detailed Results</h2>
            <div class="filter-controls">
                <label>Filter: <input type="text" id="filterInput" placeholder="Search case name..."></label>
                <label>Status:
                    <select id="statusFilter">
                        <option value="all">All</option>
                        <option value="success">Success</option>
                        <option value="fail">Failed</option>
                    </select>
                </label>
                <button onclick="exportToCSV()">Export to CSV</button>
            </div>
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">#</th>
                        <th onclick="sortTable(1)">Case Name</th>
                        <th onclick="sortTable(2)">Status</th>
                        <th onclick="sortTable(3)">ICOT Rounds</th>
                        <th onclick="sortTable(4)">Duration</th>
                        <th onclick="sortTable(5)">Solver</th>
                        <th onclick="sortTable(6)">BC Accuracy</th>
                        <th onclick="sortTable(7)">Solver Correctness</th>
                        <th onclick="sortTable(8)">Physical Fidelity</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </section>
        """

    def _get_metric_class(self, value: float) -> str:
        """Get CSS class based on metric value"""
        if value >= 80:
            return 'metric-good'
        elif value >= 60:
            return 'metric-warning'
        else:
            return 'metric-bad'

    def _generate_validation_section(self) -> str:
        """Generate validation metrics section"""
        # Collect validation issues
        all_issues = []
        for result in self.results:
            issues = result.get('validation_issues', [])
            all_issues.extend(issues)

        if not all_issues:
            return """
            <section id="validation">
                <h2>Validation Analysis</h2>
                <p>No validation issues detected.</p>
            </section>
            """

        # Count issue types
        issue_counts = {}
        for issue in all_issues:
            issue_type = issue.split(':')[0] if ':' in issue else 'Other'
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        issue_rows = []
        for issue_type, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            issue_rows.append(f"""
                <div class="error-item">
                    <span class="error-count">{count}x</span> {issue_type}
                </div>
            """)

        return f"""
        <section id="validation">
            <h2>Validation Analysis</h2>
            <h3>Common Validation Issues</h3>
            <div class="error-list">
                {''.join(issue_rows)}
            </div>
        </section>
        """

    def _generate_error_analysis(self) -> str:
        """Generate error analysis section"""
        failed_cases = [r for r in self.results if not r.get('success')]

        if not failed_cases:
            return """
            <section id="errors">
                <h2>Error Analysis</h2>
                <p style="color: #4CAF50; font-weight: bold;">No failures detected!</p>
            </section>
            """

        # Collect error messages
        error_counts = {}
        for result in failed_cases:
            errors = result.get('error_messages', [])
            for error in errors:
                # Simplify error message
                error_key = error[:100] if len(error) > 100 else error
                error_counts[error_key] = error_counts.get(error_key, 0) + 1

        error_rows = []
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            error_rows.append(f"""
                <div class="error-item">
                    <span class="error-count">{count}x</span> {error}
                </div>
            """)

        return f"""
        <section id="errors">
            <h2>Error Analysis</h2>
            <p><strong>Total Failed Cases:</strong> {len(failed_cases)}</p>
            <h3>Top Error Messages</h3>
            <div class="error-list">
                {''.join(error_rows) if error_rows else '<p>No error messages captured.</p>'}
            </div>
        </section>
        """

    def _get_javascript(self) -> str:
        """Return inline JavaScript for interactivity"""
        return """
        // Table sorting
        function sortTable(columnIndex) {
            const table = document.getElementById('resultsTable');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            rows.sort((a, b) => {
                const aValue = a.cells[columnIndex].textContent.trim();
                const bValue = b.cells[columnIndex].textContent.trim();

                // Try numeric comparison
                const aNum = parseFloat(aValue);
                const bNum = parseFloat(bValue);

                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return bNum - aNum;
                }

                // String comparison
                return aValue.localeCompare(bValue);
            });

            rows.forEach(row => tbody.appendChild(row));
        }

        // Table filtering
        document.addEventListener('DOMContentLoaded', function() {
            const filterInput = document.getElementById('filterInput');
            const statusFilter = document.getElementById('statusFilter');
            const table = document.getElementById('resultsTable');
            const tbody = table.querySelector('tbody');

            function filterTable() {
                const searchText = filterInput.value.toLowerCase();
                const statusValue = statusFilter.value;
                const rows = tbody.querySelectorAll('tr');

                rows.forEach(row => {
                    const caseName = row.cells[1].textContent.toLowerCase();
                    const status = row.cells[2].textContent.toLowerCase();

                    const matchesSearch = caseName.includes(searchText);
                    const matchesStatus = statusValue === 'all' ||
                                        (statusValue === 'success' && status.includes('success')) ||
                                        (statusValue === 'fail' && status.includes('failed'));

                    row.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
                });
            }

            filterInput.addEventListener('input', filterTable);
            statusFilter.addEventListener('change', filterTable);
        });

        // CSV export
        function exportToCSV() {
            const table = document.getElementById('resultsTable');
            const rows = table.querySelectorAll('tr');
            let csv = [];

            rows.forEach(row => {
                const cells = row.querySelectorAll('th, td');
                const rowData = Array.from(cells).map(cell => {
                    let text = cell.textContent.trim();
                    // Escape quotes and wrap in quotes if contains comma
                    if (text.includes(',') || text.includes('"')) {
                        text = '"' + text.replace(/"/g, '""') + '"';
                    }
                    return text;
                });
                csv.push(rowData.join(','));
            });

            const csvContent = csv.join('\\n');
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'benchmark_results.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        }
        """


def main():
    """CLI interface for report generator"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate HTML report from benchmark results')
    parser.add_argument('results_file', help='Path to benchmark results JSON file')
    parser.add_argument('-o', '--output', help='Output HTML filename')

    args = parser.parse_args()

    generator = ReportGenerator(args.results_file)
    output_path = generator.generate_report(args.output)
    print(f"\nReport successfully generated: {output_path}")
    print(f"Open in browser: file://{output_path}")


if __name__ == "__main__":
    main()

