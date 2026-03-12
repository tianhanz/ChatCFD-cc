#!/usr/bin/env python3
"""
Load test cases from datasets/ directory
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
import re


class TestCase:
    """Represents a single test case"""
    def __init__(self, name: str, description_path: str, mesh_path: str):
        self.name = name
        self.description_path = description_path
        self.mesh_path = mesh_path
        self.solver = self._extract_solver()
        self.category = self._extract_category()
        self.tier = None  # Will be assigned during stratification

    def _extract_solver(self) -> str:
        """Extract solver name from case name"""
        # Format: category_solver_caseName
        parts = self.name.split('_')
        if len(parts) >= 2:
            return parts[1]
        return "unknown"

    def _extract_category(self) -> str:
        """Extract category from case name"""
        parts = self.name.split('_')
        if len(parts) >= 1:
            return parts[0]
        return "unknown"

    def __repr__(self):
        return f"TestCase(name={self.name}, solver={self.solver}, category={self.category})"


class CaseLoader:
    """Load and organize test cases from datasets/"""

    def __init__(self, datasets_dir: str):
        self.datasets_dir = Path(datasets_dir)
        self.description_dir = self.datasets_dir / "of_case_description"
        self.grids_dir = self.datasets_dir / "of_case_grids"
        self.cases: List[TestCase] = []

    def load_all_cases(self) -> List[TestCase]:
        """Load all test cases from datasets/"""
        if not self.description_dir.exists():
            raise FileNotFoundError(f"Description directory not found: {self.description_dir}")

        if not self.grids_dir.exists():
            raise FileNotFoundError(f"Grids directory not found: {self.grids_dir}")

        # Find all description files
        description_files = sorted(self.description_dir.glob("*.txt"))

        for desc_file in description_files:
            case_name = desc_file.stem  # Remove .txt extension
            mesh_path = self.grids_dir / case_name / "constant" / "polyMesh"

            # Only include cases that have both description and mesh
            if mesh_path.exists():
                case = TestCase(
                    name=case_name,
                    description_path=str(desc_file),
                    mesh_path=str(mesh_path.parent.parent)  # Point to case root (contains constant/)
                )
                self.cases.append(case)
            else:
                print(f"Warning: Mesh not found for {case_name}, skipping")

        print(f"Loaded {len(self.cases)} test cases")
        return self.cases

    def stratify_cases(self) -> Dict[str, List[TestCase]]:
        """Stratify cases into Tier 1 (basic), Tier 2 (intermediate), Tier 3 (advanced)"""

        # Tier 1: Basic solvers (simple, incompressible, single-phase)
        tier1_solvers = ['laplacianFoam', 'potentialFoam', 'simpleFoam', 'scalarTransportFoam']
        tier1_categories = ['basic']

        # Tier 3: Advanced (combustion, multiphase, complex physics)
        tier3_categories = ['combustion', 'multiphase', 'lagrangian']
        tier3_keywords = ['reacting', 'multiphase', 'euler', 'cht', 'radiation']

        # Everything else is Tier 2

        tiers = {'tier1': [], 'tier2': [], 'tier3': []}

        for case in self.cases:
            # Check Tier 1
            if case.category in tier1_categories or case.solver in tier1_solvers:
                case.tier = 1
                tiers['tier1'].append(case)
            # Check Tier 3
            elif case.category in tier3_categories or any(kw in case.name.lower() for kw in tier3_keywords):
                case.tier = 3
                tiers['tier3'].append(case)
            # Default to Tier 2
            else:
                case.tier = 2
                tiers['tier2'].append(case)

        print(f"Stratification: Tier 1={len(tiers['tier1'])}, Tier 2={len(tiers['tier2'])}, Tier 3={len(tiers['tier3'])}")
        return tiers

    def get_cases_by_solver(self) -> Dict[str, List[TestCase]]:
        """Group cases by solver"""
        by_solver = {}
        for case in self.cases:
            if case.solver not in by_solver:
                by_solver[case.solver] = []
            by_solver[case.solver].append(case)
        return by_solver

    def get_cases_by_category(self) -> Dict[str, List[TestCase]]:
        """Group cases by category"""
        by_category = {}
        for case in self.cases:
            if case.category not in by_category:
                by_category[case.category] = []
            by_category[case.category].append(case)
        return by_category

    def filter_cases(self, tier: Optional[int] = None, solver: Optional[str] = None,
                    category: Optional[str] = None, limit: Optional[int] = None) -> List[TestCase]:
        """Filter cases by various criteria"""
        filtered = self.cases

        if tier is not None:
            filtered = [c for c in filtered if c.tier == tier]

        if solver is not None:
            filtered = [c for c in filtered if c.solver == solver]

        if category is not None:
            filtered = [c for c in filtered if c.category == category]

        if limit is not None:
            filtered = filtered[:limit]

        return filtered


def main():
    """Test the case loader"""
    import sys

    # Assume we're in benchmark/utils/
    root_dir = Path(__file__).parent.parent.parent
    datasets_dir = root_dir / "datasets"

    loader = CaseLoader(str(datasets_dir))
    cases = loader.load_all_cases()

    print(f"\nTotal cases: {len(cases)}")
    print(f"\nFirst 5 cases:")
    for case in cases[:5]:
        print(f"  {case}")

    # Stratify
    tiers = loader.stratify_cases()
    print(f"\nTier 1 (first 3): {tiers['tier1'][:3]}")
    print(f"Tier 2 (first 3): {tiers['tier2'][:3]}")
    print(f"Tier 3 (first 3): {tiers['tier3'][:3]}")

    # By solver
    by_solver = loader.get_cases_by_solver()
    print(f"\nSolvers found: {list(by_solver.keys())}")
    print(f"simpleFoam cases: {len(by_solver.get('simpleFoam', []))}")


if __name__ == "__main__":
    main()
