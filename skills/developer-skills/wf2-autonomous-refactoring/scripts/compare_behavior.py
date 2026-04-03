"""Behavior comparison tool for WF2 Autonomous Refactoring workflow.

Compares outputs of original and refactored code to verify behavior equivalence.
Supports exact matching, approximate matching (for floats), and exception comparison.
"""

import importlib.util
import json
import math
import sys
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class FunctionComparison:
    """Result of comparing a single function's behavior."""

    function_name: str
    inputs_tested: int
    exact_matches: int
    approximate_matches: int
    failures: int
    failure_details: list[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class BehaviorReport:
    """Full behavior equivalence report."""

    original_path: str
    refactored_path: str
    epsilon: float
    comparisons: list[FunctionComparison] = field(default_factory=list)
    overall_passed: bool = True
    summary: str = ""


def load_module_from_path(module_path: str, module_name: str):
    """Dynamically load a Python module from a file path.

    Args:
        module_path: Absolute or relative path to the Python file.
        module_name: Name to assign to the loaded module.

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: If the module file does not exist.
        ImportError: If the module cannot be loaded.
    """
    path = Path(module_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Module not found: {path}")

    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def values_are_equivalent(original, refactored, epsilon: float = 1e-9) -> tuple[bool, str]:
    """Compare two values for equivalence.

    Supports exact match for most types and approximate match for floats.

    Args:
        original: The value from the original code.
        refactored: The value from the refactored code.
        epsilon: Tolerance for floating-point comparison.

    Returns:
        Tuple of (is_equivalent, match_type) where match_type is
        "exact", "approximate", or "mismatch".
    """
    if original is None and refactored is None:
        return True, "exact"

    if type(original) is not type(refactored):
        return False, "mismatch"

    if isinstance(original, float):
        if math.isnan(original) and math.isnan(refactored):
            return True, "exact"
        if math.isinf(original) and math.isinf(refactored):
            return original == refactored, "exact" if original == refactored else "mismatch"
        if abs(original - refactored) < epsilon:
            if original == refactored:
                return True, "exact"
            return True, "approximate"
        return False, "mismatch"

    if isinstance(original, dict):
        if set(original.keys()) != set(refactored.keys()):
            return False, "mismatch"
        for key in original:
            eq, _ = values_are_equivalent(original[key], refactored[key], epsilon)
            if not eq:
                return False, "mismatch"
        return True, "exact"

    if isinstance(original, (list, tuple)):
        if len(original) != len(refactored):
            return False, "mismatch"
        all_exact = True
        for o_item, r_item in zip(original, refactored):
            eq, match_type = values_are_equivalent(o_item, r_item, epsilon)
            if not eq:
                return False, "mismatch"
            if match_type == "approximate":
                all_exact = False
        return True, "exact" if all_exact else "approximate"

    if isinstance(original, set):
        if original == refactored:
            return True, "exact"
        return False, "mismatch"

    if original == refactored:
        return True, "exact"

    return False, "mismatch"


def compare_function_behavior(
    original_func,
    refactored_func,
    args_list: list[tuple],
    epsilon: float = 1e-9,
) -> FunctionComparison:
    """Compare behavior of original and refactored versions of a function.

    Tests both return values and exception behavior for each input set.

    Args:
        original_func: The original function.
        refactored_func: The refactored function.
        args_list: List of argument tuples to test.
        epsilon: Tolerance for floating-point comparison.

    Returns:
        FunctionComparison with detailed results.
    """
    comparison = FunctionComparison(
        function_name=original_func.__name__,
        inputs_tested=len(args_list),
        exact_matches=0,
        approximate_matches=0,
        failures=0,
    )

    for args in args_list:
        original_result = None
        refactored_result = None
        original_error = None
        refactored_error = None

        # Run original
        try:
            original_result = original_func(*args)
        except Exception as exc:
            original_error = exc

        # Run refactored
        try:
            refactored_result = refactored_func(*args)
        except Exception as exc:
            refactored_error = exc

        # Compare exception behavior
        if original_error is not None or refactored_error is not None:
            if type(original_error) is type(refactored_error):
                comparison.exact_matches += 1
            else:
                comparison.failures += 1
                comparison.failure_details.append(
                    f"args={args}: original raised {type(original_error).__name__}, "
                    f"refactored raised {type(refactored_error).__name__ if refactored_error else 'no exception'}"
                )
            continue

        # Compare return values
        equivalent, match_type = values_are_equivalent(original_result, refactored_result, epsilon)

        if equivalent and match_type == "exact":
            comparison.exact_matches += 1
        elif equivalent and match_type == "approximate":
            comparison.approximate_matches += 1
        else:
            comparison.failures += 1
            comparison.failure_details.append(
                f"args={args}: original={original_result!r}, refactored={refactored_result!r}"
            )

    comparison.passed = comparison.failures == 0
    return comparison


def compare_modules(
    original_path: str,
    refactored_path: str,
    function_names: list[str],
    args_list: list[tuple],
    epsilon: float = 1e-9,
) -> BehaviorReport:
    """Compare behavior between original and refactored modules.

    Args:
        original_path: Path to the original Python module.
        refactored_path: Path to the refactored Python module.
        function_names: List of function names to compare.
        args_list: List of argument tuples to test each function with.
        epsilon: Tolerance for floating-point comparison.

    Returns:
        BehaviorReport with all comparison results.
    """
    original_module = load_module_from_path(original_path, "original_module")
    refactored_module = load_module_from_path(refactored_path, "refactored_module")

    report = BehaviorReport(
        original_path=original_path,
        refactored_path=refactored_path,
        epsilon=epsilon,
    )

    for func_name in function_names:
        original_func = getattr(original_module, func_name, None)
        refactored_func = getattr(refactored_module, func_name, None)

        if original_func is None:
            print(f"WARNING: Function '{func_name}' not found in original module, skipping.")
            continue
        if refactored_func is None:
            print(f"WARNING: Function '{func_name}' not found in refactored module, skipping.")
            continue

        comparison = compare_function_behavior(
            original_func, refactored_func, args_list, epsilon
        )
        report.comparisons.append(comparison)

        if not comparison.passed:
            report.overall_passed = False

    total_functions = len(report.comparisons)
    passed_functions = sum(1 for c in report.comparisons if c.passed)
    total_inputs = sum(c.inputs_tested for c in report.comparisons)
    total_failures = sum(c.failures for c in report.comparisons)

    report.summary = (
        f"Compared {total_functions} functions across {total_inputs} input sets: "
        f"{passed_functions} equivalent, {total_functions - passed_functions} divergent, "
        f"{total_failures} total failures."
    )

    return report


def report_to_json(report: BehaviorReport) -> str:
    """Serialize a BehaviorReport to JSON.

    Args:
        report: The behavior report to serialize.

    Returns:
        JSON string representation of the report.
    """
    return json.dumps(asdict(report), indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python compare_behavior.py <original_path> <refactored_path> "
            "<func1,func2,...> [epsilon]"
        )
        print()
        print("Arguments:")
        print("  original_path      Path to the original Python module")
        print("  refactored_path    Path to the refactored Python module")
        print("  func1,func2,...    Comma-separated list of function names to compare")
        print("  epsilon            Float tolerance for approximate matching (default: 1e-9)")
        sys.exit(1)

    original = sys.argv[1]
    refactored = sys.argv[2]
    functions = sys.argv[3].split(",")
    eps = float(sys.argv[4]) if len(sys.argv) > 4 else 1e-9

    # Use empty args as default; real usage should provide representative inputs
    default_args: list[tuple] = [()]

    result = compare_modules(original, refactored, functions, default_args, eps)
    print(report_to_json(result))

    sys.exit(0 if result.overall_passed else 1)
