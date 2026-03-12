#!/usr/bin/env python3
"""
Physical Fidelity Analyzer for OpenFOAM cases
Analyzes simulation results for physical consistency and convergence
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class FidelityAnalyzer:
    """Analyzes physical fidelity of OpenFOAM simulation results"""

    def __init__(self):
        self.residual_threshold = 1e-4  # Acceptable final residual
        self.convergence_threshold = 1e-5  # Good convergence

    def parse_log_file(self, case_dir: str) -> Dict:
        """Parse OpenFOAM log file for residuals and convergence"""
        log_file = os.path.join(case_dir, 'case_run.log')
        if not os.path.exists(log_file):
            # Try alternative log names
            for log_name in ['log.simpleFoam', 'log.pimpleFoam', 'log']:
                alt_log = os.path.join(case_dir, log_name)
                if os.path.exists(alt_log):
                    log_file = alt_log
                    break
            else:
                return {}

        try:
            with open(log_file, 'r') as f:
                content = f.read()

            log_data = {
                'solver': None,
                'turbulence_model': None,
                'time_steps': [],
                'residuals': {},
                'continuity_errors': [],
                'execution_time': None,
                'converged': False,
                'warnings': [],
                'errors': []
            }

            # Extract solver
            solver_match = re.search(r'Exec\s*:\s*(\w+)', content)
            if solver_match:
                log_data['solver'] = solver_match.group(1)

            # Extract turbulence model
            turb_match = re.search(r'Selecting RAS turbulence model (\w+)', content)
            if turb_match:
                log_data['turbulence_model'] = turb_match.group(1)
            else:
                turb_match = re.search(r'Selecting LES turbulence model (\w+)', content)
                if turb_match:
                    log_data['turbulence_model'] = turb_match.group(1)

            # Extract time steps and residuals
            time_pattern = r'Time = ([\d.e+-]+)'
            residual_pattern = r'(smoothSolver|GAMG|PCG|PBiCGStab|diagonal):\s+Solving for (\w+),.*?Final residual = ([\d.e+-]+)'

            current_time = None
            for line in content.split('\n'):
                # Check for time step
                time_match = re.search(time_pattern, line)
                if time_match:
                    current_time = float(time_match.group(1))
                    log_data['time_steps'].append(current_time)

                # Check for residuals
                residual_match = re.search(residual_pattern, line)
                if residual_match and current_time is not None:
                    field = residual_match.group(2)
                    residual = float(residual_match.group(3))

                    if field not in log_data['residuals']:
                        log_data['residuals'][field] = []
                    log_data['residuals'][field].append((current_time, residual))

                # Check for continuity errors
                if 'continuity errors' in line:
                    cont_match = re.search(r'cumulative = ([\d.e+-]+)', line)
                    if cont_match:
                        log_data['continuity_errors'].append(float(cont_match.group(1)))

                # Check for warnings
                if 'bounding' in line.lower():
                    log_data['warnings'].append(line.strip())

                # Check for errors
                if 'error' in line.lower() and 'continuity errors' not in line.lower():
                    if any(err_word in line.lower() for err_word in ['fatal', 'failed', 'cannot']):
                        log_data['errors'].append(line.strip())

            # Extract execution time
            exec_match = re.search(r'ExecutionTime = ([\d.]+) s', content)
            if exec_match:
                log_data['execution_time'] = float(exec_match.group(1))

            # Check convergence
            if log_data['residuals']:
                all_converged = True
                for field, residuals in log_data['residuals'].items():
                    if residuals:
                        final_residual = residuals[-1][1]
                        if final_residual > self.residual_threshold:
                            all_converged = False
                            break
                log_data['converged'] = all_converged

            return log_data

        except Exception as e:
            print(f"Error parsing log file: {e}")
            return {}

    def read_field_file(self, field_path: str) -> Optional[Dict]:
        """Read OpenFOAM field file and extract statistics"""
        if not os.path.exists(field_path):
            return None

        try:
            with open(field_path, 'r') as f:
                content = f.read()

            # Extract internal field values
            internal_match = re.search(r'internalField\s+uniform\s+\(([^)]+)\);', content)
            if internal_match:
                values = [float(x) for x in internal_match.group(1).split()]
                return {'type': 'uniform', 'values': values}

            internal_match = re.search(r'internalField\s+uniform\s+(\S+);', content)
            if internal_match:
                try:
                    value = float(internal_match.group(1))
                    return {'type': 'uniform', 'values': [value]}
                except ValueError:
                    return {'type': 'uniform', 'values': []}

            # For non-uniform fields, just note it exists
            if 'internalField' in content:
                return {'type': 'nonuniform', 'values': []}

            return None

        except Exception as e:
            print(f"Error reading field file {field_path}: {e}")
            return None

    def check_physical_bounds(self, case_dir: str, latest_time: str) -> Dict:
        """Check if field values are within physical bounds"""
        issues = []
        warnings = []

        time_dir = os.path.join(case_dir, latest_time)
        if not os.path.exists(time_dir):
            return {'issues': ['Latest time directory not found'], 'warnings': []}

        # Check velocity
        u_file = os.path.join(time_dir, 'U')
        if os.path.exists(u_file):
            u_data = self.read_field_file(u_file)
            if u_data and u_data['values']:
                u_mag = sum(v**2 for v in u_data['values'])**0.5
                if u_mag > 1000:  # Unreasonably high velocity
                    issues.append(f"Velocity magnitude very high: {u_mag:.2f} m/s")
                elif u_mag > 500:
                    warnings.append(f"Velocity magnitude high: {u_mag:.2f} m/s")

        # Check pressure
        p_file = os.path.join(time_dir, 'p')
        if os.path.exists(p_file):
            p_data = self.read_field_file(p_file)
            if p_data and p_data['values']:
                p_val = p_data['values'][0] if len(p_data['values']) > 0 else 0
                if abs(p_val) > 1e8:  # Unreasonably high pressure
                    issues.append(f"Pressure magnitude very high: {p_val:.2e} Pa")

        # Check turbulence quantities
        k_file = os.path.join(time_dir, 'k')
        if os.path.exists(k_file):
            k_data = self.read_field_file(k_file)
            if k_data and k_data['values']:
                k_val = k_data['values'][0] if len(k_data['values']) > 0 else 0
                if k_val < 0:
                    issues.append(f"Negative turbulent kinetic energy: {k_val}")
                elif k_val > 1000:
                    warnings.append(f"Very high turbulent kinetic energy: {k_val}")

        omega_file = os.path.join(time_dir, 'omega')
        if os.path.exists(omega_file):
            omega_data = self.read_field_file(omega_file)
            if omega_data and omega_data['values']:
                omega_val = omega_data['values'][0] if len(omega_data['values']) > 0 else 0
                if omega_val < 0:
                    issues.append(f"Negative specific dissipation rate: {omega_val}")
                elif omega_val > 1e10:
                    warnings.append(f"Very high specific dissipation rate: {omega_val:.2e}")

        return {'issues': issues, 'warnings': warnings}

    def analyze_convergence(self, log_data: Dict) -> Dict:
        """Analyze convergence behavior"""
        analysis = {
            'converged': False,
            'convergence_quality': 'poor',
            'issues': [],
            'final_residuals': {}
        }

        if not log_data.get('residuals'):
            analysis['issues'].append("No residual data found")
            return analysis

        # Check final residuals
        all_good = True
        for field, residuals in log_data['residuals'].items():
            if residuals:
                final_residual = residuals[-1][1]
                analysis['final_residuals'][field] = final_residual

                if final_residual > self.residual_threshold:
                    all_good = False
                    analysis['issues'].append(f"{field} did not converge: final residual {final_residual:.2e}")

        # Determine convergence quality
        if all_good:
            max_residual = max(analysis['final_residuals'].values()) if analysis['final_residuals'] else 1.0
            if max_residual < self.convergence_threshold:
                analysis['convergence_quality'] = 'excellent'
                analysis['converged'] = True
            elif max_residual < self.residual_threshold:
                analysis['convergence_quality'] = 'good'
                analysis['converged'] = True
            else:
                analysis['convergence_quality'] = 'acceptable'
        else:
            analysis['convergence_quality'] = 'poor'

        # Check for oscillations
        for field, residuals in log_data['residuals'].items():
            if len(residuals) > 5:
                recent_residuals = [r[1] for r in residuals[-5:]]
                if max(recent_residuals) / min(recent_residuals) > 10:
                    analysis['issues'].append(f"{field} residuals oscillating")

        return analysis

    def analyze_case(self, case_dir: str) -> Dict:
        """
        Analyze physical fidelity of simulation results

        Args:
            case_dir: Path to OpenFOAM case

        Returns:
            Dictionary with fidelity analysis results
        """
        results = {
            'physical_fidelity': 0.0,
            'converged': False,
            'convergence_quality': 'unknown',
            'physical_issues': [],
            'convergence_issues': [],
            'warnings': [],
            'final_residuals': {},
            'execution_time': None
        }

        # Parse log file
        log_data = self.parse_log_file(case_dir)
        if not log_data:
            results['physical_issues'].append("No log file found or failed to parse")
            return results

        results['execution_time'] = log_data.get('execution_time')

        # Analyze convergence
        conv_analysis = self.analyze_convergence(log_data)
        results['converged'] = conv_analysis['converged']
        results['convergence_quality'] = conv_analysis['convergence_quality']
        results['convergence_issues'] = conv_analysis['issues']
        results['final_residuals'] = conv_analysis['final_residuals']

        # Check physical bounds
        if log_data.get('time_steps'):
            latest_time = str(max(log_data['time_steps']))
            bounds_check = self.check_physical_bounds(case_dir, latest_time)
            results['physical_issues'].extend(bounds_check['issues'])
            results['warnings'].extend(bounds_check['warnings'])

        # Add log warnings
        results['warnings'].extend(log_data.get('warnings', [])[:5])  # Limit to 5

        # Check for errors
        if log_data.get('errors'):
            results['physical_issues'].extend(log_data['errors'][:3])  # Limit to 3

        # Calculate fidelity score
        score = 100.0

        # Convergence score (50 points)
        if results['converged']:
            if results['convergence_quality'] == 'excellent':
                conv_score = 50
            elif results['convergence_quality'] == 'good':
                conv_score = 45
            else:
                conv_score = 40
        else:
            conv_score = 20

        # Physical consistency score (50 points)
        phys_score = 50
        phys_score -= len(results['physical_issues']) * 15  # Major penalty for issues
        phys_score -= len(results['warnings']) * 5  # Minor penalty for warnings
        phys_score = max(0, phys_score)

        results['physical_fidelity'] = conv_score + phys_score

        return results


def main():
    """Test the fidelity analyzer"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: fidelity_analyzer.py <case_dir>")
        sys.exit(1)

    analyzer = FidelityAnalyzer()
    case_dir = sys.argv[1]

    results = analyzer.analyze_case(case_dir)

    print(f"\nPhysical Fidelity Analysis:")
    print(f"  Fidelity Score: {results['physical_fidelity']:.1f}%")
    print(f"  Converged: {results['converged']}")
    print(f"  Convergence Quality: {results['convergence_quality']}")
    print(f"  Execution Time: {results['execution_time']}s" if results['execution_time'] else "  Execution Time: N/A")

    if results['final_residuals']:
        print(f"\n  Final Residuals:")
        for field, residual in results['final_residuals'].items():
            print(f"    {field}: {residual:.2e}")

    if results['convergence_issues']:
        print(f"\n  Convergence Issues ({len(results['convergence_issues'])}):")
        for issue in results['convergence_issues']:
            print(f"    - {issue}")

    if results['physical_issues']:
        print(f"\n  Physical Issues ({len(results['physical_issues'])}):")
        for issue in results['physical_issues']:
            print(f"    - {issue}")

    if results['warnings']:
        print(f"\n  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings'][:5]:
            print(f"    - {warning}")


if __name__ == "__main__":
    main()
