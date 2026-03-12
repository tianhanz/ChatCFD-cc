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

# Import validators
from bc_validator import BCValidator
from solver_validator import SolverValidator
from fidelity_analyzer import FidelityAnalyzer


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
        # Validation metrics
        self.bc_accuracy = None
        self.solver_correctness = None
        self.physical_fidelity = None
        self.validation_issues = []

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
            "case_dir": self.case_dir,
            "bc_accuracy": self.bc_accuracy,
            "solver_correctness": self.solver_correctness,
            "physical_fidelity": self.physical_fidelity,
            "validation_issues": self.validation_issues
        }


class TestRunner:
    """Runs ChatCFD on test cases and collects metrics"""

    def __init__(self, output_dir: str = "benchmark/results", enable_validation: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TestResult] = []
        self.enable_validation = enable_validation

        # Initialize validators
        if self.enable_validation:
            self.bc_validator = BCValidator()
            self.solver_validator = SolverValidator()
            self.fidelity_analyzer = FidelityAnalyzer()

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
            # For polyMesh format, grid_path should point to the polyMesh directory
            config.path_cfg.grid_path = test_case.mesh_path + "/constant/polyMesh"

            # Configure test parameters
            config.max_running_test_round = max_rounds
            config.run_cfg.run_time = run_time

            # Set grid type to polyMesh (our test cases use OpenFOAM format)
            config.grid_type = "polyMesh"

            # Set case info from test case
            config.case_info.case_name = test_case.name
            config.case_info.case_solver = test_case.solver
            # Try to detect turbulence model from description
            config.case_info.turbulence_model = self._detect_turbulence_model(test_case)

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
            result.case_dir = str(config.path_cfg.case_dir)

            # Run validation if enabled and case succeeded
            if self.enable_validation and result.success and result.case_dir:
                print(f"\nRunning validation for {test_case.name}...")
                self._validate_case(result, test_case)

            print(f"\n{'='*80}")
            print(f"Test completed: {test_case.name}")
            print(f"Success: {result.success}, ICOT rounds: {result.icot_rounds}, Duration: {result.duration:.1f}s")
            if result.bc_accuracy is not None:
                print(f"Validation - BC: {result.bc_accuracy:.1f}%, Solver: {result.solver_correctness:.1f}%, Fidelity: {result.physical_fidelity:.1f}%")
            print(f"{'='*80}\n")

        except Exception as e:
            result.end_time = datetime.now().isoformat()
            result.success = False
            result.error_messages.append(str(e))
            print(f"ERROR running {test_case.name}: {e}")
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")

        self.results.append(result)
        return result

    def _detect_turbulence_model(self, test_case) -> str:
        """Detect turbulence model from description file"""
        # Solvers that don't use turbulence models
        non_turbulent_solvers = [
            'laplacianFoam', 'potentialFoam', 'scalarTransportFoam',
            'solidFoam', 'boundaryFoam', 'dnsFoam'
        ]

        if test_case.solver in non_turbulent_solvers:
            return 'laminar'  # Use 'laminar' instead of empty string

        try:
            with open(test_case.description_path, 'r') as f:
                content = f.read().lower()

            # Common turbulence models
            if 'komegasst' in content or 'k-omega-sst' in content or 'k-ω-sst' in content:
                return 'kOmegaSST'
            elif 'kepsilon' in content or 'k-epsilon' in content or 'k-ε' in content:
                return 'kEpsilon'
            elif 'spalart' in content or 'sa' in content:
                return 'SpalartAllmaras'
            elif 'laminar' in content:
                return 'laminar'
            else:
                return 'laminar'  # Default to laminar
        except:
            return 'laminar'

    def _validate_case(self, result: TestResult, test_case) -> None:
        """Run validation on a completed case"""
        try:
            # Get ground truth directory
            root_dir = Path(__file__).parent.parent.parent
            ground_truth_dir = root_dir / "datasets" / "of_case_grids" / test_case.name

            # Validate boundary conditions
            try:
                bc_results = self.bc_validator.validate_case(
                    result.case_dir,
                    str(ground_truth_dir) if ground_truth_dir.exists() else None
                )
                result.bc_accuracy = bc_results.get('bc_accuracy', 0.0)

                # Collect BC issues
                if bc_results.get('mismatches'):
                    result.validation_issues.extend([
                        f"BC: {m}" for m in bc_results['mismatches'][:3]  # Limit to 3
                    ])
            except Exception as e:
                print(f"  BC validation failed: {e}")
                result.bc_accuracy = 0.0

            # Validate solver configuration
            try:
                solver_results = self.solver_validator.validate_case(
                    result.case_dir,
                    test_case.solver
                )
                result.solver_correctness = solver_results.get('solver_correctness', 0.0)

                # Collect solver issues
                if solver_results.get('issues'):
                    result.validation_issues.extend([
                        f"Solver: {i}" for i in solver_results['issues'][:3]  # Limit to 3
                    ])
            except Exception as e:
                print(f"  Solver validation failed: {e}")
                result.solver_correctness = 0.0

            # Analyze physical fidelity
            try:
                fidelity_results = self.fidelity_analyzer.analyze_case(result.case_dir)
                result.physical_fidelity = fidelity_results.get('physical_fidelity', 0.0)

                # Collect fidelity issues
                if fidelity_results.get('convergence_issues'):
                    result.validation_issues.extend([
                        f"Convergence: {i}" for i in fidelity_results['convergence_issues'][:2]
                    ])
                if fidelity_results.get('physical_issues'):
                    result.validation_issues.extend([
                        f"Physical: {i}" for i in fidelity_results['physical_issues'][:2]
                    ])
            except Exception as e:
                print(f"  Fidelity analysis failed: {e}")
                result.physical_fidelity = 0.0

            print(f"  Validation complete - BC: {result.bc_accuracy:.1f}%, "
                  f"Solver: {result.solver_correctness:.1f}%, "
                  f"Fidelity: {result.physical_fidelity:.1f}%")

        except Exception as e:
            print(f"  Validation error: {e}")
            result.validation_issues.append(f"Validation error: {str(e)}")

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

        # Calculate validation averages
        bc_scores = [r.bc_accuracy for r in self.results if r.bc_accuracy is not None]
        solver_scores = [r.solver_correctness for r in self.results if r.solver_correctness is not None]
        fidelity_scores = [r.physical_fidelity for r in self.results if r.physical_fidelity is not None]

        avg_bc = sum(bc_scores) / len(bc_scores) if bc_scores else 0
        avg_solver = sum(solver_scores) / len(solver_scores) if solver_scores else 0
        avg_fidelity = sum(fidelity_scores) / len(fidelity_scores) if fidelity_scores else 0

        print(f"\n{'='*80}")
        print(f"BENCHMARK SUMMARY")
        print(f"{'='*80}")
        print(f"Total cases: {total}")
        print(f"Successful: {successful} ({success_rate:.1f}%)")
        print(f"Failed: {total - successful}")
        print(f"Average duration: {avg_duration:.1f}s")
        print(f"Average ICOT rounds: {avg_rounds:.1f}")
        print(f"Total time: {total_duration:.1f}s ({total_duration/60:.1f} min)")

        if bc_scores or solver_scores or fidelity_scores:
            print(f"\nValidation Metrics:")
            if bc_scores:
                print(f"  Average BC Accuracy: {avg_bc:.1f}%")
            if solver_scores:
                print(f"  Average Solver Correctness: {avg_solver:.1f}%")
            if fidelity_scores:
                print(f"  Average Physical Fidelity: {avg_fidelity:.1f}%")

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
