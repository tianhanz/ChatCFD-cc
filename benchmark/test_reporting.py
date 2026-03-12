#!/usr/bin/env python3
"""
Test script for Phase 3 reporting tools
Creates sample data and tests all reporting functionality
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))


def create_sample_results():
    """Create sample benchmark results for testing"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_cases": 10,
        "successful_cases": 7,
        "results": [
            {
                "case_name": "tier1_cavity_simpleFoam",
                "success": True,
                "icot_rounds": 5,
                "duration": 45.2,
                "solver_detected": "simpleFoam",
                "turbulence_model_detected": "laminar",
                "bc_accuracy": 95.0,
                "solver_correctness": 90.0,
                "physical_fidelity": 85.0,
                "validation_issues": [],
                "error_messages": []
            },
            {
                "case_name": "tier1_pipe_simpleFoam",
                "success": True,
                "icot_rounds": 8,
                "duration": 62.5,
                "solver_detected": "simpleFoam",
                "turbulence_model_detected": "kEpsilon",
                "bc_accuracy": 88.0,
                "solver_correctness": 92.0,
                "physical_fidelity": 90.0,
                "validation_issues": ["BC: inlet velocity mismatch"],
                "error_messages": []
            },
            {
                "case_name": "tier2_airfoil_simpleFoam",
                "success": True,
                "icot_rounds": 12,
                "duration": 98.3,
                "solver_detected": "simpleFoam",
                "turbulence_model_detected": "kOmegaSST",
                "bc_accuracy": 82.0,
                "solver_correctness": 85.0,
                "physical_fidelity": 80.0,
                "validation_issues": ["BC: wall function mismatch", "Solver: turbulence model config"],
                "error_messages": []
            },
            {
                "case_name": "tier2_mixer_pimpleFoam",
                "success": False,
                "icot_rounds": 15,
                "duration": 120.0,
                "solver_detected": "pimpleFoam",
                "turbulence_model_detected": "kEpsilon",
                "bc_accuracy": None,
                "solver_correctness": None,
                "physical_fidelity": None,
                "validation_issues": [],
                "error_messages": ["Solver failed to converge", "Maximum iterations reached"]
            },
            {
                "case_name": "tier1_channel_simpleFoam",
                "success": True,
                "icot_rounds": 6,
                "duration": 52.1,
                "solver_detected": "simpleFoam",
                "turbulence_model_detected": "laminar",
                "bc_accuracy": 93.0,
                "solver_correctness": 95.0,
                "physical_fidelity": 92.0,
                "validation_issues": [],
                "error_messages": []
            },
            {
                "case_name": "tier3_combustion_reactingFoam",
                "success": False,
                "icot_rounds": 20,
                "duration": 180.5,
                "solver_detected": "reactingFoam",
                "turbulence_model_detected": "kEpsilon",
                "bc_accuracy": None,
                "solver_correctness": None,
                "physical_fidelity": None,
                "validation_issues": [],
                "error_messages": ["Chemistry model initialization failed"]
            },
            {
                "case_name": "tier2_heat_exchanger_buoyantSimpleFoam",
                "success": True,
                "icot_rounds": 10,
                "duration": 85.7,
                "solver_detected": "buoyantSimpleFoam",
                "turbulence_model_detected": "kOmegaSST",
                "bc_accuracy": 87.0,
                "solver_correctness": 88.0,
                "physical_fidelity": 83.0,
                "validation_issues": ["Physical: temperature boundary condition"],
                "error_messages": []
            },
            {
                "case_name": "tier1_backward_step_simpleFoam",
                "success": True,
                "icot_rounds": 7,
                "duration": 58.9,
                "solver_detected": "simpleFoam",
                "turbulence_model_detected": "kEpsilon",
                "bc_accuracy": 91.0,
                "solver_correctness": 93.0,
                "physical_fidelity": 89.0,
                "validation_issues": [],
                "error_messages": []
            },
            {
                "case_name": "tier3_multiphase_interFoam",
                "success": False,
                "icot_rounds": 18,
                "duration": 165.2,
                "solver_detected": "interFoam",
                "turbulence_model_detected": "kOmegaSST",
                "bc_accuracy": None,
                "solver_correctness": None,
                "physical_fidelity": None,
                "validation_issues": [],
                "error_messages": ["Phase fraction out of bounds", "Courant number too high"]
            },
            {
                "case_name": "tier2_turbulent_jet_pimpleFoam",
                "success": True,
                "icot_rounds": 11,
                "duration": 92.4,
                "solver_detected": "pimpleFoam",
                "turbulence_model_detected": "kOmegaSST",
                "bc_accuracy": 86.0,
                "solver_correctness": 89.0,
                "physical_fidelity": 87.0,
                "validation_issues": ["BC: turbulence intensity"],
                "error_messages": []
            }
        ]
    }

    return results


def test_report_generator():
    """Test report generator"""
    print("\n" + "="*80)
    print("Testing Report Generator")
    print("="*80)

    try:
        from report_generator import ReportGenerator

        # Create sample data
        sample_data = create_sample_results()

        # Save to temp file
        results_dir = Path("benchmark/results")
        results_dir.mkdir(parents=True, exist_ok=True)

        test_file = results_dir / "test_sample.json"
        with open(test_file, 'w') as f:
            json.dump(sample_data, f, indent=2)

        print(f"Created sample data: {test_file}")

        # Generate report
        generator = ReportGenerator(str(test_file))
        report_path = generator.generate_report("test_report.html")

        print(f"✓ Report generated successfully: {report_path}")
        print(f"  Open in browser: file://{Path(report_path).absolute()}")

        return True

    except Exception as e:
        print(f"✗ Report generator failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visualizer():
    """Test visualizer"""
    print("\n" + "="*80)
    print("Testing Visualizer")
    print("="*80)

    try:
        from visualizer import BenchmarkVisualizer

        test_file = Path("benchmark/results/test_sample.json")
        if not test_file.exists():
            print("✗ Sample data not found. Run report generator test first.")
            return False

        # Generate charts
        visualizer = BenchmarkVisualizer(str(test_file))
        charts = visualizer.generate_all_charts(prefix="test_")

        print(f"✓ Generated {len(charts)} charts:")
        for name, path in charts.items():
            print(f"  - {name}: {path}")

        return True

    except ImportError as e:
        print(f"⚠ Visualizer requires matplotlib: {e}")
        print("  Install with: pip install matplotlib")
        return False
    except Exception as e:
        print(f"✗ Visualizer failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comparator():
    """Test comparator"""
    print("\n" + "="*80)
    print("Testing Comparator")
    print("="*80)

    try:
        from comparator import BenchmarkComparator

        # Create baseline data
        baseline_data = create_sample_results()
        baseline_data['timestamp'] = "2026-03-01T10:00:00"

        # Create current data (with some changes)
        current_data = create_sample_results()
        current_data['timestamp'] = "2026-03-12T15:00:00"
        current_data['successful_cases'] = 8

        # Make some changes
        # Improvement: tier2_mixer_pimpleFoam now succeeds
        current_data['results'][3]['success'] = True
        current_data['results'][3]['bc_accuracy'] = 85.0
        current_data['results'][3]['solver_correctness'] = 87.0
        current_data['results'][3]['physical_fidelity'] = 82.0
        current_data['results'][3]['error_messages'] = []

        # Regression: tier1_channel_simpleFoam now fails
        current_data['results'][4]['success'] = False
        current_data['results'][4]['bc_accuracy'] = None
        current_data['results'][4]['solver_correctness'] = None
        current_data['results'][4]['physical_fidelity'] = None
        current_data['results'][4]['error_messages'] = ["Mesh quality issue"]

        # Save files
        results_dir = Path("benchmark/results")
        baseline_file = results_dir / "test_baseline.json"
        current_file = results_dir / "test_current.json"

        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)

        with open(current_file, 'w') as f:
            json.dump(current_data, f, indent=2)

        print(f"Created baseline: {baseline_file}")
        print(f"Created current: {current_file}")

        # Generate comparison
        comparator = BenchmarkComparator(str(baseline_file), str(current_file))
        comparator.print_summary()

        comparison_path = comparator.generate_report("test_comparison.html")

        print(f"✓ Comparison report generated: {comparison_path}")
        print(f"  Open in browser: file://{Path(comparison_path).absolute()}")

        return True

    except Exception as e:
        print(f"✗ Comparator failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("Phase 3 Reporting Tools - Test Suite")
    print("="*80)

    results = {
        'report_generator': test_report_generator(),
        'visualizer': test_visualizer(),
        'comparator': test_comparator()
    }

    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    for tool, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {tool}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✓ All tests passed!")
        print("\nGenerated files:")
        print("  - benchmark/reports/test_report.html")
        print("  - benchmark/reports/test_comparison.html")
        print("  - benchmark/reports/charts/test_*.png")
        print("\nYou can now use the reporting tools with real benchmark results.")
    else:
        print("\n⚠ Some tests failed. Check error messages above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
