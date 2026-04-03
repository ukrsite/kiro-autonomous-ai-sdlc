"""Performance benchmark runner for WF2 Autonomous Refactoring workflow.

Compares execution time and memory usage between original and refactored code
to verify performance is not degraded beyond acceptable thresholds.
"""

import importlib.util
import json
import statistics
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    function_name: str
    iterations: int
    mean_time_ms: float
    median_time_ms: float
    stdev_time_ms: float
    min_time_ms: float
    max_time_ms: float
    peak_memory_kb: float


@dataclass
class ComparisonResult:
    """Comparison between original and refactored benchmark results."""

    function_name: str
    original: BenchmarkResult
    refactored: BenchmarkResult
    time_change_percent: float
    memory_change_percent: float
    passed: bool
    details: str


@dataclass
class BenchmarkReport:
    """Full benchmark report comparing original vs refactored code."""

    original_path: str
    refactored_path: str
    tolerance_percent: float
    comparisons: list[ComparisonResult] = field(default_factory=list)
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


def benchmark_function(func, args_list: list[tuple], iterations: int = 100) -> BenchmarkResult:
    """Benchmark a function over multiple iterations with various inputs.

    Args:
        func: The callable to benchmark.
        args_list: List of argument tuples to cycle through.
        iterations: Number of benchmark iterations to run.

    Returns:
        BenchmarkResult with timing and memory statistics.
    """
    times_ms = []
    peak_memory_kb = 0.0

    for i in range(iterations):
        args = args_list[i % len(args_list)]

        tracemalloc.start()
        start = time.perf_counter()

        func(*args)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        times_ms.append(elapsed_ms)
        peak_memory_kb = max(peak_memory_kb, peak / 1024.0)

    return BenchmarkResult(
        function_name=func.__name__,
        iterations=iterations,
        mean_time_ms=statistics.mean(times_ms),
        median_time_ms=statistics.median(times_ms),
        stdev_time_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0,
        min_time_ms=min(times_ms),
        max_time_ms=max(times_ms),
        peak_memory_kb=peak_memory_kb,
    )


def compare_benchmarks(
    original_result: BenchmarkResult,
    refactored_result: BenchmarkResult,
    tolerance_percent: float = 10.0,
) -> ComparisonResult:
    """Compare benchmark results between original and refactored code.

    Args:
        original_result: Benchmark result from the original code.
        refactored_result: Benchmark result from the refactored code.
        tolerance_percent: Maximum allowed performance degradation percentage.

    Returns:
        ComparisonResult indicating whether the refactored code meets the threshold.
    """
    if original_result.mean_time_ms > 0:
        time_change = (
            (refactored_result.mean_time_ms - original_result.mean_time_ms)
            / original_result.mean_time_ms
            * 100.0
        )
    else:
        time_change = 0.0

    if original_result.peak_memory_kb > 0:
        memory_change = (
            (refactored_result.peak_memory_kb - original_result.peak_memory_kb)
            / original_result.peak_memory_kb
            * 100.0
        )
    else:
        memory_change = 0.0

    passed = time_change <= tolerance_percent
    details = (
        f"Time: {time_change:+.2f}% "
        f"(original={original_result.mean_time_ms:.3f}ms, "
        f"refactored={refactored_result.mean_time_ms:.3f}ms). "
        f"Memory: {memory_change:+.2f}% "
        f"(original={original_result.peak_memory_kb:.1f}KB, "
        f"refactored={refactored_result.peak_memory_kb:.1f}KB)."
    )

    if not passed:
        details += f" FAILED: exceeds {tolerance_percent}% tolerance."

    return ComparisonResult(
        function_name=original_result.function_name,
        original=original_result,
        refactored=refactored_result,
        time_change_percent=round(time_change, 2),
        memory_change_percent=round(memory_change, 2),
        passed=passed,
        details=details,
    )


def run_benchmarks(
    original_path: str,
    refactored_path: str,
    function_names: list[str],
    args_list: list[tuple],
    iterations: int = 100,
    tolerance_percent: float = 10.0,
) -> BenchmarkReport:
    """Run benchmarks comparing original and refactored modules.

    Args:
        original_path: Path to the original Python module.
        refactored_path: Path to the refactored Python module.
        function_names: List of function names to benchmark.
        args_list: List of argument tuples to use for benchmarking.
        iterations: Number of iterations per benchmark.
        tolerance_percent: Maximum allowed performance degradation percentage.

    Returns:
        BenchmarkReport with all comparison results.
    """
    original_module = load_module_from_path(original_path, "original_module")
    refactored_module = load_module_from_path(refactored_path, "refactored_module")

    report = BenchmarkReport(
        original_path=original_path,
        refactored_path=refactored_path,
        tolerance_percent=tolerance_percent,
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

        original_result = benchmark_function(original_func, args_list, iterations)
        refactored_result = benchmark_function(refactored_func, args_list, iterations)

        comparison = compare_benchmarks(original_result, refactored_result, tolerance_percent)
        report.comparisons.append(comparison)

        if not comparison.passed:
            report.overall_passed = False

    passed_count = sum(1 for c in report.comparisons if c.passed)
    total_count = len(report.comparisons)
    report.summary = (
        f"Benchmarked {total_count} functions: "
        f"{passed_count} passed, {total_count - passed_count} failed "
        f"(tolerance: {tolerance_percent}%)."
    )

    return report


def report_to_json(report: BenchmarkReport) -> str:
    """Serialize a BenchmarkReport to JSON.

    Args:
        report: The benchmark report to serialize.

    Returns:
        JSON string representation of the report.
    """
    return json.dumps(asdict(report), indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python run_benchmarks.py <original_path> <refactored_path> "
            "<func1,func2,...> [iterations] [tolerance_percent]"
        )
        print()
        print("Arguments:")
        print("  original_path      Path to the original Python module")
        print("  refactored_path    Path to the refactored Python module")
        print("  func1,func2,...    Comma-separated list of function names to benchmark")
        print("  iterations         Number of benchmark iterations (default: 100)")
        print("  tolerance_percent  Max allowed degradation percentage (default: 10.0)")
        sys.exit(1)

    original = sys.argv[1]
    refactored = sys.argv[2]
    functions = sys.argv[3].split(",")
    iters = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    tolerance = float(sys.argv[5]) if len(sys.argv) > 5 else 10.0

    # Use empty args as default; real usage should provide representative inputs
    default_args: list[tuple] = [()]

    result = run_benchmarks(original, refactored, functions, default_args, iters, tolerance)
    print(report_to_json(result))

    sys.exit(0 if result.overall_passed else 1)
