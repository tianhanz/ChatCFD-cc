#!/usr/bin/env python3
"""
Validation test for benchmark framework
Tests all components without running actual ChatCFD
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "utils"))

from case_loader import CaseLoader


def test_case_loader():
    """Test case loader functionality"""
    print("Testing case loader...")

    root_dir = Path(__file__).parent.parent
    datasets_dir = root_dir / "datasets"

    loader = CaseLoader(str(datasets_dir))
    cases = loader.load_all_cases()

    assert len(cases) == 205, f"Expected 205 cases, got {len(cases)}"
    print(f"✓ Loaded {len(cases)} cases")

    # Test stratification
    tiers = loader.stratify_cases()
    tier1_count = len(tiers['tier1'])
    tier2_count = len(tiers['tier2'])
    tier3_count = len(tiers['tier3'])

    print(f"✓ Stratification: Tier1={tier1_count}, Tier2={tier2_count}, Tier3={tier3_count}")
    assert tier1_count + tier2_count + tier3_count == 205

    # Test filtering
    simpleFoam_cases = loader.filter_cases(solver='simpleFoam')
    print(f"✓ Found {len(simpleFoam_cases)} simpleFoam cases")

    tier1_limited = loader.filter_cases(tier=1, limit=3)
    assert len(tier1_limited) == 3, f"Expected 3 cases, got {len(tier1_limited)}"
    print(f"✓ Filtering works correctly")

    # Test case attributes
    test_case = cases[0]
    assert hasattr(test_case, 'name')
    assert hasattr(test_case, 'solver')
    assert hasattr(test_case, 'category')
    assert hasattr(test_case, 'description_path')
    assert hasattr(test_case, 'mesh_path')
    print(f"✓ Case attributes correct")

    # Verify paths exist
    assert Path(test_case.description_path).exists(), f"Description not found: {test_case.description_path}"
    assert Path(test_case.mesh_path).exists(), f"Mesh not found: {test_case.mesh_path}"
    print(f"✓ File paths valid")

    print("\n✅ Case loader validation PASSED\n")
    return True


def test_directory_structure():
    """Test benchmark directory structure"""
    print("Testing directory structure...")

    root_dir = Path(__file__).parent.parent

    # Check required directories
    required_dirs = [
        root_dir / "benchmark",
        root_dir / "benchmark" / "utils",
        root_dir / "datasets",
        root_dir / "datasets" / "of_case_description",
        root_dir / "datasets" / "of_case_grids"
    ]

    for dir_path in required_dirs:
        assert dir_path.exists(), f"Missing directory: {dir_path}"
        print(f"✓ {dir_path.name}/ exists")

    # Check required files
    required_files = [
        root_dir / "benchmark" / "run_benchmark.py",
        root_dir / "benchmark" / "utils" / "case_loader.py",
        root_dir / "benchmark" / "utils" / "test_runner.py",
        root_dir / "benchmark" / "utils" / "log_parser.py",
        root_dir / "benchmark" / "README.md",
        root_dir / "BENCHMARK_DESIGN.md"
    ]

    for file_path in required_files:
        assert file_path.exists(), f"Missing file: {file_path}"
        print(f"✓ {file_path.name} exists")

    # Create results directory if needed
    results_dir = root_dir / "benchmark" / "results"
    results_dir.mkdir(exist_ok=True)
    print(f"✓ results/ directory ready")

    print("\n✅ Directory structure validation PASSED\n")
    return True


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")

    try:
        from case_loader import CaseLoader, TestCase
        print("✓ case_loader imports")

        from test_runner import TestRunner, TestResult
        print("✓ test_runner imports")

        from log_parser import LogParser, BatchLogParser
        print("✓ log_parser imports")

        print("\n✅ Import validation PASSED\n")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def main():
    """Run all validation tests"""
    print("="*80)
    print("BENCHMARK FRAMEWORK VALIDATION")
    print("="*80 + "\n")

    tests = [
        ("Directory Structure", test_directory_structure),
        ("Module Imports", test_imports),
        ("Case Loader", test_case_loader)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED: {e}\n")

    print("="*80)
    print(f"VALIDATION SUMMARY: {passed}/{len(tests)} tests passed")
    print("="*80 + "\n")

    if failed == 0:
        print("✅ All validation tests passed! Benchmark framework is ready.")
        print("\nNext steps:")
        print("  1. Run quick test: python benchmark/run_benchmark.py --quick")
        print("  2. Run Tier 1: python benchmark/run_benchmark.py --tier1")
        print("  3. Run full benchmark: python benchmark/run_benchmark.py --full")
        return 0
    else:
        print(f"❌ {failed} test(s) failed. Please fix issues before running benchmark.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
