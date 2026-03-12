#!/usr/bin/env python3
"""
Boundary Condition Validator for OpenFOAM cases
Parses and validates boundary conditions against ground truth
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class BCValidator:
    """Validates boundary conditions in OpenFOAM cases"""

    def __init__(self):
        self.field_files = ['U', 'p', 'k', 'omega', 'epsilon', 'nut', 'nuTilda', 'T', 'alpha']

    def parse_foam_file(self, file_path: str) -> Dict:
        """Parse OpenFOAM dictionary file and extract boundary conditions"""
        if not os.path.exists(file_path):
            return {}

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Remove comments
            content = re.sub(r'//.*?\n', '\n', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

            # Extract boundaryField section
            boundary_match = re.search(r'boundaryField\s*\{(.*?)\n\}', content, re.DOTALL)
            if not boundary_match:
                return {}

            boundary_content = boundary_match.group(1)

            # Parse each patch
            patches = {}
            patch_pattern = r'(\w+)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'

            for match in re.finditer(patch_pattern, boundary_content):
                patch_name = match.group(1)
                patch_content = match.group(2)

                # Extract type
                type_match = re.search(r'type\s+(\w+);', patch_content)
                bc_type = type_match.group(1) if type_match else None

                # Extract value if present
                value = None
                value_match = re.search(r'value\s+uniform\s+\(([^)]+)\);', patch_content)
                if value_match:
                    value = value_match.group(1).strip()
                elif re.search(r'value\s+uniform\s+(\S+);', patch_content):
                    value_match = re.search(r'value\s+uniform\s+(\S+);', patch_content)
                    value = value_match.group(1).strip()

                # Extract other parameters
                params = {}
                for param in ['freestreamValue', 'inletValue', 'Uinf', 'pInf']:
                    param_match = re.search(rf'{param}\s+uniform\s+\(([^)]+)\);', patch_content)
                    if param_match:
                        params[param] = param_match.group(1).strip()
                    else:
                        param_match = re.search(rf'{param}\s+uniform\s+(\S+);', patch_content)
                        if param_match:
                            params[param] = param_match.group(1).strip()

                patches[patch_name] = {
                    'type': bc_type,
                    'value': value,
                    'params': params
                }

            return patches

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}

    def parse_boundary_file(self, mesh_dir: str) -> Dict[str, str]:
        """Parse constant/polyMesh/boundary to get patch types"""
        boundary_file = os.path.join(mesh_dir, 'constant', 'polyMesh', 'boundary')
        if not os.path.exists(boundary_file):
            return {}

        try:
            with open(boundary_file, 'r') as f:
                content = f.read()

            # Remove comments
            content = re.sub(r'//.*?\n', '\n', content)

            patches = {}
            patch_pattern = r'(\w+)\s*\{([^}]*)\}'

            for match in re.finditer(patch_pattern, content):
                patch_name = match.group(1)
                patch_content = match.group(2)

                type_match = re.search(r'type\s+(\w+);', patch_content)
                if type_match:
                    patches[patch_name] = type_match.group(1)

            return patches

        except Exception as e:
            print(f"Error parsing boundary file: {e}")
            return {}

    def validate_case(self, generated_case_dir: str, ground_truth_dir: Optional[str] = None) -> Dict:
        """
        Validate boundary conditions in a generated case

        Args:
            generated_case_dir: Path to generated OpenFOAM case
            ground_truth_dir: Path to ground truth case (optional)

        Returns:
            Dictionary with validation results
        """
        results = {
            'bc_accuracy': 0.0,
            'total_bcs': 0,
            'correct_bcs': 0,
            'mismatches': [],
            'missing_fields': [],
            'extra_fields': [],
            'patch_names_match': True,
            'bc_types_correct': 0,
            'bc_values_correct': 0
        }

        # Parse generated case
        gen_zero_dir = os.path.join(generated_case_dir, '0')
        if not os.path.exists(gen_zero_dir):
            results['mismatches'].append("Generated case missing 0/ directory")
            return results

        # Get patch names from mesh
        gen_patches = self.parse_boundary_file(generated_case_dir)

        # Parse all field files in generated case
        gen_fields = {}
        for field in self.field_files:
            field_path = os.path.join(gen_zero_dir, field)
            if os.path.exists(field_path):
                gen_fields[field] = self.parse_foam_file(field_path)

        if not gen_fields:
            results['mismatches'].append("No field files found in generated case")
            return results

        # If ground truth provided, compare
        if ground_truth_dir and os.path.exists(ground_truth_dir):
            gt_zero_dir = os.path.join(ground_truth_dir, '0')
            if os.path.exists(gt_zero_dir):
                results.update(self._compare_with_ground_truth(
                    gen_fields, gen_patches, gt_zero_dir, ground_truth_dir
                ))
            else:
                # No ground truth 0/ directory, just validate structure
                results.update(self._validate_structure(gen_fields, gen_patches))
        else:
            # No ground truth, just validate structure
            results.update(self._validate_structure(gen_fields, gen_patches))

        return results

    def _compare_with_ground_truth(self, gen_fields: Dict, gen_patches: Dict,
                                   gt_zero_dir: str, gt_case_dir: str) -> Dict:
        """Compare generated BCs with ground truth"""
        results = {
            'bc_accuracy': 0.0,
            'total_bcs': 0,
            'correct_bcs': 0,
            'mismatches': [],
            'missing_fields': [],
            'extra_fields': [],
            'patch_names_match': True,
            'bc_types_correct': 0,
            'bc_values_correct': 0
        }

        # Parse ground truth
        gt_patches = self.parse_boundary_file(gt_case_dir)
        gt_fields = {}
        for field in self.field_files:
            field_path = os.path.join(gt_zero_dir, field)
            if os.path.exists(field_path):
                gt_fields[field] = self.parse_foam_file(field_path)

        # Check for missing/extra fields
        gen_field_names = set(gen_fields.keys())
        gt_field_names = set(gt_fields.keys())

        results['missing_fields'] = list(gt_field_names - gen_field_names)
        results['extra_fields'] = list(gen_field_names - gt_field_names)

        # Compare patch names
        gen_patch_names = set(gen_patches.keys())
        gt_patch_names = set(gt_patches.keys())

        if gen_patch_names != gt_patch_names:
            results['patch_names_match'] = False
            missing_patches = gt_patch_names - gen_patch_names
            extra_patches = gen_patch_names - gt_patch_names
            if missing_patches:
                results['mismatches'].append(f"Missing patches: {missing_patches}")
            if extra_patches:
                results['mismatches'].append(f"Extra patches: {extra_patches}")

        # Compare BCs for each field
        for field in gt_field_names & gen_field_names:
            gt_bcs = gt_fields[field]
            gen_bcs = gen_fields[field]

            for patch in gt_bcs:
                results['total_bcs'] += 1

                if patch not in gen_bcs:
                    results['mismatches'].append(f"{field}/{patch}: Missing in generated case")
                    continue

                gt_bc = gt_bcs[patch]
                gen_bc = gen_bcs[patch]

                # Compare BC type
                if gt_bc['type'] == gen_bc['type']:
                    results['bc_types_correct'] += 1
                else:
                    results['mismatches'].append(
                        f"{field}/{patch}: Type mismatch - expected {gt_bc['type']}, got {gen_bc['type']}"
                    )
                    continue

                # Compare values (if applicable)
                if gt_bc['value'] is not None or gen_bc['value'] is not None:
                    if self._values_match(gt_bc['value'], gen_bc['value']):
                        results['bc_values_correct'] += 1
                        results['correct_bcs'] += 1
                    else:
                        results['mismatches'].append(
                            f"{field}/{patch}: Value mismatch - expected {gt_bc['value']}, got {gen_bc['value']}"
                        )
                else:
                    # No value to compare, type match is enough
                    results['correct_bcs'] += 1

        # Calculate accuracy
        if results['total_bcs'] > 0:
            results['bc_accuracy'] = (results['correct_bcs'] / results['total_bcs']) * 100
        else:
            results['bc_accuracy'] = 0.0

        return results

    def _validate_structure(self, gen_fields: Dict, gen_patches: Dict) -> Dict:
        """Validate BC structure without ground truth"""
        results = {
            'bc_accuracy': 100.0,  # Assume correct if no ground truth
            'total_bcs': 0,
            'correct_bcs': 0,
            'mismatches': [],
            'missing_fields': [],
            'extra_fields': [],
            'patch_names_match': True,
            'bc_types_correct': 0,
            'bc_values_correct': 0
        }

        # Check that all patches have BCs defined
        for field, bcs in gen_fields.items():
            for patch in gen_patches:
                results['total_bcs'] += 1
                if patch in bcs:
                    results['correct_bcs'] += 1
                    results['bc_types_correct'] += 1
                else:
                    results['mismatches'].append(f"{field}/{patch}: BC not defined")

        if results['total_bcs'] > 0:
            results['bc_accuracy'] = (results['correct_bcs'] / results['total_bcs']) * 100

        return results

    def _values_match(self, val1: Optional[str], val2: Optional[str], tolerance: float = 1e-6) -> bool:
        """Compare two BC values with tolerance for numerical values"""
        if val1 is None and val2 is None:
            return True
        if val1 is None or val2 is None:
            return False

        # Try numerical comparison
        try:
            # Handle vector values
            nums1 = [float(x) for x in val1.split()]
            nums2 = [float(x) for x in val2.split()]

            if len(nums1) != len(nums2):
                return False

            for n1, n2 in zip(nums1, nums2):
                if abs(n1 - n2) > tolerance:
                    return False
            return True

        except (ValueError, AttributeError):
            # String comparison
            return str(val1).strip() == str(val2).strip()


def main():
    """Test the BC validator"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: bc_validator.py <generated_case_dir> [ground_truth_dir]")
        sys.exit(1)

    validator = BCValidator()
    gen_case = sys.argv[1]
    gt_case = sys.argv[2] if len(sys.argv) > 2 else None

    results = validator.validate_case(gen_case, gt_case)

    print(f"\nBC Validation Results:")
    print(f"  Accuracy: {results['bc_accuracy']:.1f}%")
    print(f"  Total BCs: {results['total_bcs']}")
    print(f"  Correct BCs: {results['correct_bcs']}")
    print(f"  BC Types Correct: {results['bc_types_correct']}")
    print(f"  Patch Names Match: {results['patch_names_match']}")

    if results['missing_fields']:
        print(f"  Missing Fields: {results['missing_fields']}")
    if results['extra_fields']:
        print(f"  Extra Fields: {results['extra_fields']}")

    if results['mismatches']:
        print(f"\n  Mismatches ({len(results['mismatches'])}):")
        for mismatch in results['mismatches'][:10]:  # Show first 10
            print(f"    - {mismatch}")


if __name__ == "__main__":
    main()
