#!/usr/bin/env python3
"""
Test runner for executing ChatCFD on individual test cases
"""
import os
import sys
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import config
from main_run_chatcfd import run_case


class TestResult:
    """Stores results from a single test run"""
    def __init__(self, case_name: str):
        self.case_name = case_name
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.success = False
        self.icot_rounds = 0
        self.final_status = None
        self.error_messages = []
        self.tokens_used = 0
        self.cost = 0.0
        self.solver_detected = None
        self.turbulence_model_detected = None
        self.case_dir = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "case_name": self.case_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "success": self.success,
            "icot_rounds": self.icot_rounds,
            "final_status": self.final_status,
            "error_messages": self.error_messages,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "solver_detected": self.solver_detected,
            "turbulence_model_detected": self.turbulence_model_detected,
            "case_dir": self.case_dir
        }


class TestRunner:
    """Runs ChatCFD on test cases and collects metrics"""

    def __init__(self, output_dir: str = "benchmark/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TestResult] = []

    def run_single_case(self, test_case, max_rounds: int = 30, run_time: int = 1) -> TestResult:
        """Run ChatCFD on a single test case"""
        result = TestResult(test_case.name)
        result.start_time = datetime.now().isoformat()

        print(f"\n{'='*80}")
        print(f"Running test case: {test_case.name}")
        print(f"Solver: {test_case.solver}, Category: {test_case.category}, Tier: {test_case.tier}")
        print(f"{'='*80}\n")

        try:
            # Set up paths
            config.path_cfg.document_path = test_case.description_path
            config.path_cfg.grid_path = test_case.mesh_path

            # Configure test parameters
            config.max_running_test_round = max_rounds
            config.run_cfg.run_time = run_time

            # Clear previous case info
            config.case_info.case_name = ""
            config.case_info.case_solver = ""
            config.case_info.turbulence_model = ""

            # Run the case
            start = time.time()
            results = run_case()
            end = time.time()

            result.duration = end - start
            result.end_time = datetime.now().isoformat()

            # Parse results
            if results and len(results) > 0:
                result.final_status = results[0]
                result.success = (results[0] == "Success")
                result.icot_rounds = len(results) - 1  # First element is final status

            # Extract detected solver and turbulence model
            result.solver_detected = config.case_info.case_solver
            result.turbulence_model_detected = config.case_info.turbulence_model

            # Get case directory
            result.case_dir = str(config.path_cfg.case_path)

            print(f"\n{'='*80}")
            print(f"Test completed: {test_case.name}")
            print(f"Success: {result.success}, ICOT rounds: {result.icot_rounds}, Duration: {result.duration:.1f}s")
            print(f"{'='*80}\n")

        except Exception as e:
            result.end_time = datetime.now().isoformat()
            result.success = False
            result.error_messages.append(str(e))
            print(f"ERROR running {test_case.name}: {e}")

        self.results.append(result)
        return result

    def run_batch(self, test_cases: List, max_rounds: int = 30, run_time: int = 1,
                  save_interval: int = 5) -> List[TestResult]:
        """Run multiple test cases in batch"""
        print(f"\nStarting batch run: {len(test_cases)} cases")
        print(f"Max ICOT rounds: {max_rounds}, Run time: {run_time}s")
        print(f"Results will be saved every {save_interval} cases\n")

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] Processing: {test_case.name}")

            result = self.run_single_case(test_case, max_rounds, run_time)

            # Save intermediate results
            if i % save_interval == 0:
                self.save_results(f"batch_progress_{i}.json")

        # Save final results
        self.save_results("batch_final.json")
        return self.results

    def save_results(self, filename: str):
        """Save results to JSON file"""
        output_path = self.output_dir / filename
        results_dict = {
            "timestamp": datetime.now().isoformat(),
            "total_cases": len(self.results),
            "successful_cases": sum(1 for r in self.results if r.success),
            "results": [r.to_dict() for r in self.results]
        }

        with open(output_path, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"\nResults saved to: {output_path}")

    def print_summary(self):
        """Print summary statistics"""
        if not self.results:
            print("No results to summarize")
            return

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        success_rate = (successful / total) * 100 if total > 0 else 0

        total_duration = sum(r.duration for r in self.results if r.duration)
        avg_duration = total_duration / total if total > 0 else 0

        total_rounds = sum(r.icot_rounds for r in self.results)
        avg_rounds = total_rounds / total if total > 0 else 0

        print(f"\n{'='*80}")
        print(f"BENCHMARK SUMMARY")
        print(f"{'='*80}")
        print(f"Total cases: {total}")
        print(f"Successful: {successful} ({success_rate:.1f}%)")
        print(f"Failed: {total - successful}")
        print(f"Average duration: {avg_duration:.1f}s")
        print(f"Average ICOT rounds: {avg_rounds:.1f}")
        print(f"Total time: {total_duration:.1f}s ({total_duration/60:.1f} min)")
        print(f"{'='*80}\n")


def main():
    """Test the runner with a single case"""
    from case_loader import CaseLoader

    root_dir = Path(__file__).parent.parent.parent
    datasets_dir = root_dir / "datasets"

    # Load cases
    loader = CaseLoader(str(datasets_dir))
    cases = loader.load_all_cases()
    tiers = loader.stratify_cases()

    # Run a single Tier 1 case for testing
    runner = TestRunner()
    if tiers['tier1']:
        test_case = tiers['tier1'][0]
        result = runner.run_single_case(test_case, max_rounds=5, run_time=1)
        runner.save_results("test_single.json")
        runner.print_summary()


if __name__ == "__main__":
    main()
