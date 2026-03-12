#!/usr/bin/env python3
"""
Main benchmark orchestrator for ChatCFD autonomous testing
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from case_loader import CaseLoader, TestCase
from test_runner import TestRunner
from log_parser import BatchLogParser


def run_benchmark(tier: int = None, solver: str = None, limit: int = None,
                 max_rounds: int = 30, run_time: int = 1, output_name: str = None):
    """
    Run benchmark tests on ChatCFD

    Args:
        tier: Filter by tier (1, 2, or 3)
        solver: Filter by solver name
        limit: Limit number of cases
        max_rounds: Maximum ICOT rounds per case
        run_time: OpenFOAM simulation time
        output_name: Custom output filename
    """

    # Setup paths
    root_dir = Path(__file__).parent.parent
    datasets_dir = root_dir / "datasets"

    # Load test cases
    print("Loading test cases...")
    loader = CaseLoader(str(datasets_dir))
    all_cases = loader.load_all_cases()
    tiers = loader.stratify_cases()

    # Filter cases
    if tier:
        test_cases = tiers[f'tier{tier}']
        print(f"Selected Tier {tier}: {len(test_cases)} cases")
    else:
        test_cases = all_cases
        print(f"Selected all cases: {len(test_cases)} cases")

    if solver:
        test_cases = [c for c in test_cases if c.solver == solver]
        print(f"Filtered by solver '{solver}': {len(test_cases)} cases")

    if limit:
        test_cases = test_cases[:limit]
        print(f"Limited to first {limit} cases")

    if not test_cases:
        print("No test cases selected!")
        return

    # Generate output filename
    if not output_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tier_str = f"tier{tier}" if tier else "all"
        solver_str = f"_{solver}" if solver else ""
        output_name = f"benchmark_{tier_str}{solver_str}_{timestamp}.json"

    # Run tests
    print(f"\nStarting benchmark run...")
    print(f"Output file: {output_name}")
    print(f"Max ICOT rounds: {max_rounds}")
    print(f"OpenFOAM run time: {run_time}s")
    print(f"{'='*80}\n")

    runner = TestRunner(output_dir="benchmark/results")
    results = runner.run_batch(test_cases, max_rounds=max_rounds,
                              run_time=run_time, save_interval=5)

    # Save final results
    runner.save_results(output_name)
    runner.print_summary()

    print(f"\nBenchmark complete! Results saved to: benchmark/results/{output_name}")


def quick_test():
    """Run a quick test on 3 Tier 1 cases"""
    print("Running quick test (3 Tier 1 cases)...")
    run_benchmark(tier=1, limit=3, max_rounds=5, run_time=1,
                 output_name="quick_test.json")


def tier1_benchmark():
    """Run full Tier 1 benchmark"""
    print("Running Tier 1 benchmark (all basic cases)...")
    run_benchmark(tier=1, max_rounds=30, run_time=1,
                 output_name="tier1_full.json")


def tier2_benchmark():
    """Run full Tier 2 benchmark"""
    print("Running Tier 2 benchmark (all intermediate cases)...")
    run_benchmark(tier=2, max_rounds=30, run_time=1,
                 output_name="tier2_full.json")


def full_benchmark():
    """Run full benchmark on all 205 cases"""
    print("Running FULL benchmark (all 205 cases)...")
    print("WARNING: This will take several hours!")
    response = input("Continue? (yes/no): ")
    if response.lower() == 'yes':
        run_benchmark(max_rounds=30, run_time=1,
                     output_name="full_benchmark.json")
    else:
        print("Cancelled.")


def main():
    parser = argparse.ArgumentParser(
        description="ChatCFD Autonomous Benchmark Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test (3 Tier 1 cases)
  python run_benchmark.py --quick

  # Run all Tier 1 cases
  python run_benchmark.py --tier 1

  # Run first 10 simpleFoam cases
  python run_benchmark.py --solver simpleFoam --limit 10

  # Run full benchmark (all 205 cases)
  python run_benchmark.py --full

  # Custom run
  python run_benchmark.py --tier 2 --limit 20 --max-rounds 15
        """
    )

    # Preset modes
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (3 Tier 1 cases)')
    parser.add_argument('--tier1', action='store_true',
                       help='Run all Tier 1 cases')
    parser.add_argument('--tier2', action='store_true',
                       help='Run all Tier 2 cases')
    parser.add_argument('--full', action='store_true',
                       help='Run full benchmark (all 205 cases)')

    # Custom filters
    parser.add_argument('--tier', type=int, choices=[1, 2, 3],
                       help='Filter by tier (1=basic, 2=intermediate, 3=advanced)')
    parser.add_argument('--solver', type=str,
                       help='Filter by solver name (e.g., simpleFoam)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of cases to run')

    # Test parameters
    parser.add_argument('--max-rounds', type=int, default=30,
                       help='Maximum ICOT rounds per case (default: 30)')
    parser.add_argument('--run-time', type=int, default=1,
                       help='OpenFOAM simulation time in seconds (default: 1)')
    parser.add_argument('--output', type=str,
                       help='Custom output filename')

    args = parser.parse_args()

    # Execute based on arguments
    if args.quick:
        quick_test()
    elif args.tier1:
        tier1_benchmark()
    elif args.tier2:
        tier2_benchmark()
    elif args.full:
        full_benchmark()
    else:
        # Custom run
        run_benchmark(
            tier=args.tier,
            solver=args.solver,
            limit=args.limit,
            max_rounds=args.max_rounds,
            run_time=args.run_time,
            output_name=args.output
        )


if __name__ == "__main__":
    main()
