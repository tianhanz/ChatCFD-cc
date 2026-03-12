#!/usr/bin/env python3
"""
Solver Configuration Validator for OpenFOAM cases
Validates solver settings, schemes, and solution parameters
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional


class SolverValidator:
    """Validates solver configuration in OpenFOAM cases"""

    def __init__(self):
        # Expected solver configurations for different case types
        self.solver_expectations = {
            'simpleFoam': {
                'steady': True,
                'required_schemes': ['ddtSchemes', 'gradSchemes', 'divSchemes', 'laplacianSchemes'],
                'required_solvers': ['p', 'U'],
                'algorithm': 'SIMPLE'
            },
            'pimpleFoam': {
                'steady': False,
                'required_schemes': ['ddtSchemes', 'gradSchemes', 'divSchemes', 'laplacianSchemes'],
                'required_solvers': ['p', 'U'],
                'algorithm': 'PIMPLE'
            },
            'potentialFoam': {
                'steady': True,
                'required_schemes': ['gradSchemes', 'laplacianSchemes'],
                'required_solvers': ['p'],
                'algorithm': None
            },
            'laplacianFoam': {
                'steady': False,
                'required_schemes': ['ddtSchemes', 'gradSchemes', 'laplacianSchemes'],
                'required_solvers': ['T'],
                'algorithm': None
            },
            'scalarTransportFoam': {
                'steady': False,
                'required_schemes': ['ddtSchemes', 'gradSchemes', 'divSchemes', 'laplacianSchemes'],
                'required_solvers': ['T'],
                'algorithm': None
            }
        }

    def parse_control_dict(self, case_dir: str) -> Dict:
        """Parse system/controlDict"""
        control_dict_path = os.path.join(case_dir, 'system', 'controlDict')
        if not os.path.exists(control_dict_path):
            return {}

        try:
            with open(control_dict_path, 'r') as f:
                content = f.read()

            # Remove comments
            content = re.sub(r'//.*?\n', '\n', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

            config = {}

            # Extract key parameters
            params = ['application', 'startFrom', 'startTime', 'stopAt', 'endTime',
                     'deltaT', 'writeControl', 'writeInterval', 'adjustTimeStep',
                     'maxCo', 'runTimeModifiable']

            for param in params:
                match = re.search(rf'{param}\s+(\S+);', content)
                if match:
                    value = match.group(1).strip()
                    # Convert to appropriate type
                    if value.lower() in ['yes', 'true']:
                        config[param] = True
                    elif value.lower() in ['no', 'false']:
                        config[param] = False
                    elif value.replace('.', '').replace('-', '').replace('e', '').isdigit():
                        config[param] = float(value) if '.' in value or 'e' in value.lower() else int(value)
                    else:
                        config[param] = value

            return config

        except Exception as e:
            print(f"Error parsing controlDict: {e}")
            return {}

    def parse_fv_schemes(self, case_dir: str) -> Dict:
        """Parse system/fvSchemes"""
        fv_schemes_path = os.path.join(case_dir, 'system', 'fvSchemes')
        if not os.path.exists(fv_schemes_path):
            return {}

        try:
            with open(fv_schemes_path, 'r') as f:
                content = f.read()

            # Remove comments
            content = re.sub(r'//.*?\n', '\n', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

            schemes = {}

            # Extract scheme sections
            sections = ['ddtSchemes', 'gradSchemes', 'divSchemes', 'laplacianSchemes',
                       'interpolationSchemes', 'snGradSchemes']

            for section in sections:
                section_match = re.search(rf'{section}\s*\{{([^}}]*)\}}', content)
                if section_match:
                    section_content = section_match.group(1)
                    schemes[section] = {}

                    # Extract entries
                    for line in section_content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('//'):
                            match = re.match(r'(\S+)\s+(.+);', line)
                            if match:
                                key = match.group(1)
                                value = match.group(2).strip()
                                schemes[section][key] = value

            return schemes

        except Exception as e:
            print(f"Error parsing fvSchemes: {e}")
            return {}

    def parse_fv_solution(self, case_dir: str) -> Dict:
        """Parse system/fvSolution"""
        fv_solution_path = os.path.join(case_dir, 'system', 'fvSolution')
        if not os.path.exists(fv_solution_path):
            return {}

        try:
            with open(fv_solution_path, 'r') as f:
                content = f.read()

            # Remove comments
            content = re.sub(r'//.*?\n', '\n', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

            solution = {}

            # Extract solvers section - find matching braces
            solvers_start = content.find('solvers')
            if solvers_start != -1:
                # Find the opening brace
                brace_start = content.find('{', solvers_start)
                if brace_start != -1:
                    # Find matching closing brace
                    brace_count = 1
                    pos = brace_start + 1
                    while pos < len(content) and brace_count > 0:
                        if content[pos] == '{':
                            brace_count += 1
                        elif content[pos] == '}':
                            brace_count -= 1
                        pos += 1

                    if brace_count == 0:
                        solvers_content = content[brace_start+1:pos-1]
                        solution['solvers'] = {}

                        # Parse each solver entry - simpler approach
                        lines = solvers_content.split('\n')
                        i = 0
                        while i < len(lines):
                            line = lines[i].strip()
                            i += 1

                            if not line or line.startswith('//'):
                                continue

                            # Check if this is a solver name (followed by {)
                            if i < len(lines) and '{' in lines[i]:
                                solver_name = line.strip('"')
                                solver_dict = {}
                                i += 1  # Skip the { line

                                # Read until we find the closing }
                                while i < len(lines):
                                    solver_line = lines[i].strip()
                                    i += 1

                                    if '}' in solver_line:
                                        break

                                    if solver_line and not solver_line.startswith('//'):
                                        match = re.match(r'(\w+)\s+(.+);', solver_line)
                                        if match:
                                            solver_dict[match.group(1)] = match.group(2).strip()

                                solution['solvers'][solver_name] = solver_dict

            # Extract algorithm section (SIMPLE, PIMPLE, PISO)
            for algo in ['SIMPLE', 'PIMPLE', 'PISO']:
                algo_match = re.search(rf'{algo}\s*\{{([^}}]*)\}}', content)
                if algo_match:
                    solution['algorithm'] = algo
                    algo_content = algo_match.group(1)
                    solution[algo] = {}

                    for line in algo_content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('//'):
                            match = re.match(r'(\w+)\s+(.+);', line)
                            if match:
                                key = match.group(1)
                                value = match.group(2).strip()
                                # Convert to appropriate type
                                if value.lower() in ['yes', 'true']:
                                    value = True
                                elif value.lower() in ['no', 'false']:
                                    value = False
                                elif value.replace('.', '').replace('-', '').isdigit():
                                    value = float(value) if '.' in value else int(value)
                                solution[algo][key] = value

            # Extract relaxation factors
            relax_match = re.search(r'relaxationFactors\s*\{(.*?)\n\}(?:\n|$)', content, re.DOTALL)
            if relax_match:
                solution['relaxationFactors'] = {}
                relax_content = relax_match.group(1)

                # Parse fields and equations subsections
                for subsection in ['fields', 'equations']:
                    sub_match = re.search(rf'{subsection}\s*\{{([^}}]*)\}}', relax_content)
                    if sub_match:
                        solution['relaxationFactors'][subsection] = {}
                        for line in sub_match.group(1).split('\n'):
                            line = line.strip()
                            if line and not line.startswith('//'):
                                match = re.match(r'(\S+)\s+(\S+);', line)
                                if match:
                                    solution['relaxationFactors'][subsection][match.group(1)] = float(match.group(2))

            return solution

        except Exception as e:
            print(f"Error parsing fvSolution: {e}")
            return {}

    def validate_case(self, case_dir: str, expected_solver: Optional[str] = None) -> Dict:
        """
        Validate solver configuration

        Args:
            case_dir: Path to OpenFOAM case
            expected_solver: Expected solver name (optional)

        Returns:
            Dictionary with validation results
        """
        results = {
            'solver_correctness': 0.0,
            'issues': [],
            'warnings': [],
            'solver_detected': None,
            'schemes_valid': False,
            'solution_valid': False,
            'control_valid': False
        }

        # Parse configuration files
        control_dict = self.parse_control_dict(case_dir)
        fv_schemes = self.parse_fv_schemes(case_dir)
        fv_solution = self.parse_fv_solution(case_dir)

        if not control_dict:
            results['issues'].append("controlDict missing or invalid")
            return results

        results['control_valid'] = True
        results['solver_detected'] = control_dict.get('application')

        # Check if system files exist
        if not fv_schemes:
            results['issues'].append("fvSchemes missing or invalid")
        else:
            results['schemes_valid'] = True

        if not fv_solution:
            results['issues'].append("fvSolution missing or invalid")
        else:
            results['solution_valid'] = True

        # Validate against expected solver
        solver = expected_solver or results['solver_detected']
        if solver and solver in self.solver_expectations:
            expectations = self.solver_expectations[solver]

            # Check schemes
            if fv_schemes:
                for required_scheme in expectations['required_schemes']:
                    if required_scheme not in fv_schemes:
                        results['issues'].append(f"Missing required scheme section: {required_scheme}")

                # Check if steady/transient matches
                if 'ddtSchemes' in fv_schemes:
                    ddt_default = fv_schemes['ddtSchemes'].get('default', '')
                    is_steady = 'steadyState' in ddt_default
                    if expectations['steady'] and not is_steady:
                        results['warnings'].append(f"{solver} is steady but ddtSchemes not set to steadyState")
                    elif not expectations['steady'] and is_steady:
                        results['warnings'].append(f"{solver} is transient but ddtSchemes set to steadyState")

            # Check solution
            if fv_solution:
                if 'solvers' in fv_solution:
                    for required_solver in expectations['required_solvers']:
                        # Check if solver is defined (may use regex patterns)
                        found = False
                        for solver_key in fv_solution['solvers'].keys():
                            # Direct match
                            if required_solver == solver_key:
                                found = True
                                break
                            # Pattern match (e.g., "U.*" matches U, "(k|omega)" matches k or omega)
                            try:
                                # Remove quotes from pattern
                                pattern = solver_key.strip('"')
                                if re.match(pattern, required_solver):
                                    found = True
                                    break
                            except re.error:
                                # Not a valid regex, skip
                                pass
                        if not found:
                            results['issues'].append(f"Missing solver configuration for: {required_solver}")

                # Check algorithm
                if expectations['algorithm']:
                    if fv_solution.get('algorithm') != expectations['algorithm']:
                        results['warnings'].append(
                            f"Expected {expectations['algorithm']} algorithm, found {fv_solution.get('algorithm')}"
                        )

        # Validate numerical parameters
        if fv_solution and 'solvers' in fv_solution:
            for solver_name, solver_config in fv_solution['solvers'].items():
                # Check for reasonable tolerances
                if 'tolerance' in solver_config:
                    try:
                        tol = float(solver_config['tolerance'])
                        if tol > 1e-3:
                            results['warnings'].append(f"Solver {solver_name} has loose tolerance: {tol}")
                        elif tol < 1e-12:
                            results['warnings'].append(f"Solver {solver_name} has very tight tolerance: {tol}")
                    except ValueError:
                        pass

        # Check time step settings for transient cases
        if control_dict.get('adjustTimeStep'):
            if 'maxCo' not in control_dict:
                results['warnings'].append("adjustTimeStep enabled but maxCo not set")
            else:
                max_co = control_dict.get('maxCo', 0)
                if max_co > 1.0:
                    results['warnings'].append(f"maxCo is high: {max_co} (may cause instability)")

        # Calculate correctness score
        total_checks = 3  # control, schemes, solution
        passed_checks = sum([results['control_valid'], results['schemes_valid'], results['solution_valid']])

        # Deduct points for issues
        issue_penalty = len(results['issues']) * 10
        warning_penalty = len(results['warnings']) * 5

        base_score = (passed_checks / total_checks) * 100
        results['solver_correctness'] = max(0, base_score - issue_penalty - warning_penalty)

        return results


def main():
    """Test the solver validator"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: solver_validator.py <case_dir> [expected_solver]")
        sys.exit(1)

    validator = SolverValidator()
    case_dir = sys.argv[1]
    expected_solver = sys.argv[2] if len(sys.argv) > 2 else None

    results = validator.validate_case(case_dir, expected_solver)

    print(f"\nSolver Validation Results:")
    print(f"  Correctness Score: {results['solver_correctness']:.1f}%")
    print(f"  Solver Detected: {results['solver_detected']}")
    print(f"  Control Valid: {results['control_valid']}")
    print(f"  Schemes Valid: {results['schemes_valid']}")
    print(f"  Solution Valid: {results['solution_valid']}")

    if results['issues']:
        print(f"\n  Issues ({len(results['issues'])}):")
        for issue in results['issues']:
            print(f"    - {issue}")

    if results['warnings']:
        print(f"\n  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"    - {warning}")


if __name__ == "__main__":
    main()
