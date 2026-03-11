#!/usr/bin/env python3
"""
Simple ChatCFD test case - NACA0012 airfoil with simpleFoam + kOmegaSST
Based on the sample run in run_chatcfd/sample_NACA0012_AOA10_kOmegaSST
"""
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import config
from main_run_chatcfd import run_case

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(root_dir, "pdf", "sun_2023_naca0012.pdf")
    grid_path = os.path.join(root_dir, "grids", "naca0012.msh")

    print("=" * 60)
    print("ChatCFD Simple Test Case")
    print(f"PDF:  {pdf_path} (exists={os.path.exists(pdf_path)})")
    print(f"Grid: {grid_path} (exists={os.path.exists(grid_path)})")
    print("=" * 60)

    # Update global path_cfg with actual file paths
    config.path_cfg.document_path = pdf_path
    config.path_cfg.grid_path = grid_path
    config.path_cfg.output_path = os.path.join(root_dir, "run_chatcfd", "test_output")

    # Set case info (normally populated by LLM via chatbot UI)
    config.case_info.case_name = "NACA0012_AOA10_kOmegaSST"
    config.case_info.case_solver = "simpleFoam"
    config.case_info.turbulence_model = "kOmegaSST"
    config.case_info.other_physical_model = "none"
    config.case_info.case_description = (
        "Steady-state RANS simulation of NACA0012 airfoil at Mach=0.15, "
        "Re=6e6 with 10-degree angle of attack using kOmegaSST turbulence model."
    )

    # Limit iterations for testing
    config.max_running_test_round = 5
    config.run_cfg.run_time = 1

    print("\nCase: simpleFoam + kOmegaSST, NACA0012 AOA=10deg")
    print("Starting ChatCFD case generation...\n")

    try:
        results = run_case()
        print("\n" + "=" * 60)
        print("Test Results:", results)
        print("=" * 60)
    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
