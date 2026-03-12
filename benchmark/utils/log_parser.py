#!/usr/bin/env python3
"""
Parse logs and extract metrics from ChatCFD runs
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class LogParser:
    """Parse qa_logs.jsonl and error_history.txt to extract metrics"""

    def __init__(self, case_dir: str):
        self.case_dir = Path(case_dir)
        self.qa_log_path = self.case_dir / "qa_logs.jsonl"
        self.error_history_path = self.case_dir / "error_history.txt"

    def parse_qa_logs(self) -> Dict:
        """Parse qa_logs.jsonl to extract token usage and costs"""
        metrics = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost": 0.0,
            "api_calls": 0,
            "v3_calls": 0,
            "r1_calls": 0,
            "v3_tokens": 0,
            "r1_tokens": 0,
            "v3_cost": 0.0,
            "r1_cost": 0.0
        }

        if not self.qa_log_path.exists():
            return metrics

        try:
            with open(self.qa_log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        metrics["api_calls"] += 1

                        # Extract token usage
                        usage = entry.get("usage", {})
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)

                        metrics["prompt_tokens"] += prompt_tokens
                        metrics["completion_tokens"] += completion_tokens
                        metrics["total_tokens"] += total_tokens

                        # Determine model type
                        model = entry.get("model", "")
                        if "V3" in model or "v3" in model.lower():
                            metrics["v3_calls"] += 1
                            metrics["v3_tokens"] += total_tokens
                        elif "R1" in model or "r1" in model.lower():
                            metrics["r1_calls"] += 1
                            metrics["r1_tokens"] += total_tokens

                    except json.JSONDecodeError:
                        continue

            # Calculate costs (DeepSeek pricing)
            # V3: $0.27/M input, $1.10/M output
            # R1: $0.55/M input, $2.19/M output
            metrics["v3_cost"] = (metrics["v3_tokens"] * 0.27) / 1_000_000
            metrics["r1_cost"] = (metrics["r1_tokens"] * 2.19) / 1_000_000
            metrics["total_cost"] = metrics["v3_cost"] + metrics["r1_cost"]

        except Exception as e:
            print(f"Error parsing qa_logs.jsonl: {e}")

        return metrics

    def parse_error_history(self) -> Dict:
        """Parse error_history.txt to extract error patterns"""
        error_metrics = {
            "total_errors": 0,
            "unique_errors": 0,
            "error_types": defaultdict(int),
            "repeated_errors": [],
            "reflection_triggered": False
        }

        if not self.error_history_path.exists():
            return error_metrics

        try:
            with open(self.error_history_path, 'r') as f:
                content = f.read()

            # Count total errors (each "Error:" line)
            error_lines = re.findall(r'^Error:.*$', content, re.MULTILINE)
            error_metrics["total_errors"] = len(error_lines)

            # Extract unique error messages
            unique_errors = set(error_lines)
            error_metrics["unique_errors"] = len(unique_errors)

            # Classify error types
            for error in error_lines:
                if "mesh" in error.lower():
                    error_metrics["error_types"]["mesh"] += 1
                elif "boundary" in error.lower() or "patch" in error.lower():
                    error_metrics["error_types"]["boundary_condition"] += 1
                elif "solver" in error.lower():
                    error_metrics["error_types"]["solver"] += 1
                elif "dictionary" in error.lower() or "keyword" in error.lower():
                    error_metrics["error_types"]["dictionary"] += 1
                elif "dimension" in error.lower():
                    error_metrics["error_types"]["dimension"] += 1
                else:
                    error_metrics["error_types"]["other"] += 1

            # Check for repeated errors (same error appearing multiple times)
            error_counts = defaultdict(int)
            for error in error_lines:
                error_counts[error] += 1

            error_metrics["repeated_errors"] = [
                {"error": err, "count": count}
                for err, count in error_counts.items() if count >= 2
            ]

            # Check if reflection was triggered (appears in error_history)
            if "reflection" in content.lower() or "meta-learning" in content.lower():
                error_metrics["reflection_triggered"] = True

        except Exception as e:
            print(f"Error parsing error_history.txt: {e}")

        return error_metrics

    def parse_openfoam_log(self) -> Dict:
        """Parse OpenFOAM log files to check convergence"""
        convergence_metrics = {
            "converged": False,
            "final_residuals": {},
            "iterations": 0
        }

        # Look for log files in case directory
        log_files = list(self.case_dir.glob("log.*"))

        if not log_files:
            return convergence_metrics

        try:
            # Read the most recent log file
            log_file = sorted(log_files)[-1]
            with open(log_file, 'r') as f:
                content = f.read()

            # Extract final residuals
            residual_pattern = r'(\w+):\s+Solving for \w+, Initial residual = ([\d.e-]+), Final residual = ([\d.e-]+)'
            matches = re.findall(residual_pattern, content)

            if matches:
                for field, initial, final in matches:
                    convergence_metrics["final_residuals"][field] = float(final)

            # Count iterations
            iteration_pattern = r'Time = (\d+)'
            iterations = re.findall(iteration_pattern, content)
            if iterations:
                convergence_metrics["iterations"] = int(iterations[-1])

            # Check if converged (all residuals < 1e-4)
            if convergence_metrics["final_residuals"]:
                all_converged = all(r < 1e-4 for r in convergence_metrics["final_residuals"].values())
                convergence_metrics["converged"] = all_converged

        except Exception as e:
            print(f"Error parsing OpenFOAM log: {e}")

        return convergence_metrics

    def get_all_metrics(self) -> Dict:
        """Get all metrics from logs"""
        return {
            "qa_metrics": self.parse_qa_logs(),
            "error_metrics": self.parse_error_history(),
            "convergence_metrics": self.parse_openfoam_log()
        }


class BatchLogParser:
    """Parse logs from multiple test runs"""

    def __init__(self, results_file: str):
        self.results_file = Path(results_file)

    def parse_batch_results(self) -> Dict:
        """Parse batch results and extract aggregate metrics"""
        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_file}")

        with open(self.results_file, 'r') as f:
            data = json.load(f)

        aggregate = {
            "total_cases": data.get("total_cases", 0),
            "successful_cases": data.get("successful_cases", 0),
            "success_rate": 0.0,
            "avg_icot_rounds": 0.0,
            "avg_duration": 0.0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "by_tier": defaultdict(lambda: {"total": 0, "success": 0}),
            "by_solver": defaultdict(lambda: {"total": 0, "success": 0}),
            "error_distribution": defaultdict(int)
        }

        results = data.get("results", [])

        if not results:
            return aggregate

        # Calculate aggregates
        total_rounds = 0
        total_duration = 0
        total_cost = 0
        total_tokens = 0

        for result in results:
            case_name = result["case_name"]
            success = result["success"]
            icot_rounds = result["icot_rounds"]
            duration = result.get("duration", 0)

            total_rounds += icot_rounds
            total_duration += duration if duration else 0

            # Parse case directory for detailed metrics
            case_dir = result.get("case_dir")
            if case_dir:
                parser = LogParser(case_dir)
                metrics = parser.get_all_metrics()

                qa_metrics = metrics["qa_metrics"]
                total_cost += qa_metrics["total_cost"]
                total_tokens += qa_metrics["total_tokens"]

        aggregate["success_rate"] = (aggregate["successful_cases"] / aggregate["total_cases"]) * 100
        aggregate["avg_icot_rounds"] = total_rounds / len(results)
        aggregate["avg_duration"] = total_duration / len(results)
        aggregate["total_cost"] = total_cost
        aggregate["total_tokens"] = total_tokens
        aggregate["avg_cost_per_case"] = total_cost / len(results) if results else 0

        return aggregate


def main():
    """Test the log parser"""
    import sys

    if len(sys.argv) > 1:
        case_dir = sys.argv[1]
        parser = LogParser(case_dir)
        metrics = parser.get_all_metrics()
        print(json.dumps(metrics, indent=2))
    else:
        print("Usage: python log_parser.py <case_directory>")


if __name__ == "__main__":
    main()
