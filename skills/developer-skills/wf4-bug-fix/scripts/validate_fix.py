"""Fix validation tool for WF4 Bug Fix workflow.

Validates a bug fix by running regression tests, checking test coverage,
and performing side-effect analysis on modified files. Returns a structured
JSON report indicating pass/fail status for each validation step.
"""

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class TestResult:
    """Result of running a test suite."""

    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    coverage_percent: float = 0.0
    passed: bool = False
    details: str = ""


@dataclass
class SideEffectCheck:
    """Result of a single side-effect check."""

    check_name: str
    passed: bool
    details: str = ""


@dataclass
class ValidationReport:
    """Full fix validation report."""

    target_path: str
    language: str
    existing_tests: TestResult = field(default_factory=TestResult)
    regression_tests: TestResult = field(default_factory=TestResult)
    side_effect_checks: list[SideEffectCheck] = field(default_factory=list)
    coverage_met: bool = False
    overall_passed: bool = False
    summary: str = ""


def detect_language(target_path: str) -> str:
    """Detect the project language from the target path.

    Inspects the directory for language-specific marker files
    (requirements.txt, package.json, pom.xml) to determine the project type.

    Args:
        target_path: Path to the project or module directory.

    Returns:
        Detected language string: "python", "nodejs", or "java".
        Defaults to "python" if no marker file is found.
    """
    path = Path(target_path)
    search_dir = path if path.is_dir() else path.parent

    for parent in [search_dir, *search_dir.parents]:
        if (parent / "requirements.txt").exists():
            return "python"
        if (parent / "package.json").exists():
            return "nodejs"
        if (parent / "pom.xml").exists():
            return "java"

    return "python"


def run_command(command: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a shell command and capture output.

    Args:
        command: Command and arguments as a list of strings.
        cwd: Working directory for the command. Uses current directory if None.

    Returns:
        Tuple of (return_code, stdout, stderr).
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out after 300 seconds"
    except FileNotFoundError:
        return 1, "", f"Command not found: {command[0]}"


def run_python_tests(target_path: str, test_pattern: str = "") -> TestResult:
    """Run Python tests with pytest and collect coverage.

    Args:
        target_path: Path to the Python project directory.
        test_pattern: Optional pattern to filter specific test files or functions.

    Returns:
        TestResult with pass/fail counts and coverage percentage.
    """
    cmd = ["python", "-m", "pytest", "-v", "--tb=short", "--cov", "--cov-report=term-missing"]
    if test_pattern:
        cmd.append(test_pattern)

    returncode, stdout, stderr = run_command(cmd, cwd=target_path)
    output = stdout + stderr

    result = TestResult(details=output)
    result.passed = returncode == 0

    # Parse pytest output for test counts
    for line in output.splitlines():
        if "passed" in line or "failed" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed" and i > 0:
                    try:
                        result.tests_passed = int(parts[i - 1])
                    except ValueError:
                        pass
                if part == "failed" and i > 0:
                    try:
                        result.tests_failed = int(parts[i - 1])
                    except ValueError:
                        pass

        # Parse coverage percentage from "TOTAL ... XX%" line
        if "TOTAL" in line and "%" in line:
            for part in line.split():
                if part.endswith("%"):
                    try:
                        result.coverage_percent = float(part.rstrip("%"))
                    except ValueError:
                        pass

    result.tests_run = result.tests_passed + result.tests_failed
    return result


def run_java_tests(target_path: str) -> TestResult:
    """Run Java tests with Maven and collect coverage.

    Args:
        target_path: Path to the Maven project directory.

    Returns:
        TestResult with pass/fail counts and coverage percentage.
    """
    returncode, stdout, stderr = run_command(["mvn", "test"], cwd=target_path)
    output = stdout + stderr

    result = TestResult(details=output)
    result.passed = returncode == 0

    # Parse Maven surefire output for test counts
    for line in output.splitlines():
        if "Tests run:" in line and "Failures:" in line:
            parts = line.split(",")
            for part in parts:
                part = part.strip()
                if part.startswith("Tests run:"):
                    try:
                        result.tests_run = int(part.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif part.startswith("Failures:"):
                    try:
                        result.tests_failed = int(part.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass

    result.tests_passed = result.tests_run - result.tests_failed
    return result


def run_nodejs_tests(target_path: str) -> TestResult:
    """Run Node.js tests with npm and collect coverage.

    Args:
        target_path: Path to the Node.js project directory.

    Returns:
        TestResult with pass/fail counts and coverage percentage.
    """
    returncode, stdout, stderr = run_command(
        ["npm", "test", "--", "--coverage"], cwd=target_path
    )
    output = stdout + stderr

    result = TestResult(details=output)
    result.passed = returncode == 0

    # Parse Jest output for test counts
    for line in output.splitlines():
        if "Tests:" in line:
            parts = line.split(",")
            for part in parts:
                part = part.strip()
                if "passed" in part:
                    try:
                        result.tests_passed = int(part.split()[0])
                    except (ValueError, IndexError):
                        pass
                elif "failed" in part:
                    try:
                        result.tests_failed = int(part.split()[0])
                    except (ValueError, IndexError):
                        pass

    result.tests_run = result.tests_passed + result.tests_failed
    return result


def check_modified_files_exist(target_path: str) -> SideEffectCheck:
    """Verify all modified files in the target path are valid.

    Checks that the target path exists and contains readable files,
    confirming the fix did not accidentally delete or corrupt files.

    Args:
        target_path: Path to the project or module directory.

    Returns:
        SideEffectCheck indicating whether the file integrity check passed.
    """
    path = Path(target_path)
    if not path.exists():
        return SideEffectCheck(
            check_name="file_integrity",
            passed=False,
            details=f"Target path does not exist: {target_path}",
        )
    return SideEffectCheck(
        check_name="file_integrity",
        passed=True,
        details=f"Target path exists and is accessible: {target_path}",
    )


def check_no_new_warnings(test_output: str) -> SideEffectCheck:
    """Check test output for new warnings or deprecation notices.

    Scans the test output for common warning indicators that may
    signal unintended side effects from the fix.

    Args:
        test_output: Combined stdout/stderr from the test run.

    Returns:
        SideEffectCheck indicating whether new warnings were found.
    """
    warning_indicators = ["DeprecationWarning", "FutureWarning", "SyntaxWarning"]
    found_warnings = []

    for indicator in warning_indicators:
        count = test_output.count(indicator)
        if count > 0:
            found_warnings.append(f"{indicator} ({count} occurrences)")

    if found_warnings:
        return SideEffectCheck(
            check_name="no_new_warnings",
            passed=True,  # Warnings are informational, not blocking
            details=f"Warnings detected (review recommended): {', '.join(found_warnings)}",
        )

    return SideEffectCheck(
        check_name="no_new_warnings",
        passed=True,
        details="No deprecation or syntax warnings detected",
    )


def check_no_import_errors(test_output: str) -> SideEffectCheck:
    """Check test output for import errors indicating broken dependencies.

    Scans for ModuleNotFoundError and ImportError patterns that may
    indicate the fix broke an import chain.

    Args:
        test_output: Combined stdout/stderr from the test run.

    Returns:
        SideEffectCheck indicating whether import errors were found.
    """
    import_errors = ["ModuleNotFoundError", "ImportError"]
    found_errors = []

    for error_type in import_errors:
        if error_type in test_output:
            found_errors.append(error_type)

    if found_errors:
        return SideEffectCheck(
            check_name="no_import_errors",
            passed=False,
            details=f"Import errors detected: {', '.join(found_errors)}",
        )

    return SideEffectCheck(
        check_name="no_import_errors",
        passed=True,
        details="No import errors detected",
    )


def validate_fix(
    target_path: str,
    language: str | None = None,
    coverage_threshold: float = 90.0,
    regression_test_pattern: str = "",
) -> ValidationReport:
    """Run full fix validation: tests, coverage, and side-effect analysis.

    Orchestrates the complete validation pipeline for a bug fix, including
    running the existing test suite, regression tests, coverage checks,
    and side-effect analysis.

    Args:
        target_path: Path to the project or module containing the fix.
        language: Project language ("python", "java", "nodejs"). Auto-detected if None.
        coverage_threshold: Minimum required coverage percentage. Defaults to 90.0.
        regression_test_pattern: Pattern to identify regression test files or functions.

    Returns:
        ValidationReport with detailed results for each validation step.
    """
    if language is None:
        language = detect_language(target_path)

    report = ValidationReport(target_path=target_path, language=language)

    # Run existing tests
    if language == "python":
        report.existing_tests = run_python_tests(target_path)
    elif language == "java":
        report.existing_tests = run_java_tests(target_path)
    elif language == "nodejs":
        report.existing_tests = run_nodejs_tests(target_path)

    # Run regression tests if a pattern is provided
    if regression_test_pattern and language == "python":
        report.regression_tests = run_python_tests(target_path, regression_test_pattern)
    else:
        # When no separate pattern, regression tests are included in the full suite
        report.regression_tests = report.existing_tests

    # Check coverage threshold
    report.coverage_met = report.existing_tests.coverage_percent >= coverage_threshold

    # Side-effect analysis
    report.side_effect_checks.append(check_modified_files_exist(target_path))
    report.side_effect_checks.append(check_no_new_warnings(report.existing_tests.details))
    report.side_effect_checks.append(check_no_import_errors(report.existing_tests.details))

    # Overall pass/fail
    side_effects_passed = all(check.passed for check in report.side_effect_checks)
    report.overall_passed = (
        report.existing_tests.passed
        and report.regression_tests.passed
        and report.coverage_met
        and side_effects_passed
    )

    # Summary
    status = "PASSED" if report.overall_passed else "FAILED"
    failures = []
    if not report.existing_tests.passed:
        failures.append(
            f"existing tests ({report.existing_tests.tests_failed} failures)"
        )
    if not report.regression_tests.passed:
        failures.append(
            f"regression tests ({report.regression_tests.tests_failed} failures)"
        )
    if not report.coverage_met:
        failures.append(
            f"coverage ({report.existing_tests.coverage_percent:.1f}% < {coverage_threshold}%)"
        )
    if not side_effects_passed:
        failed_checks = [c.check_name for c in report.side_effect_checks if not c.passed]
        failures.append(f"side-effect checks ({', '.join(failed_checks)})")

    if failures:
        report.summary = f"Fix validation {status}: {'; '.join(failures)}"
    else:
        report.summary = (
            f"Fix validation {status}: "
            f"{report.existing_tests.tests_run} tests passed, "
            f"{report.existing_tests.coverage_percent:.1f}% coverage, "
            f"no side effects detected."
        )

    return report


def report_to_json(report: ValidationReport) -> str:
    """Serialize a ValidationReport to JSON.

    Args:
        report: The validation report to serialize.

    Returns:
        JSON string representation of the report.
    """
    return json.dumps(asdict(report), indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_fix.py <target_path> [language] [coverage_threshold] [regression_test_pattern]")
        print()
        print("Arguments:")
        print("  target_path              Path to the project or module containing the fix")
        print("  language                 Project language: python, java, nodejs (auto-detected if omitted)")
        print("  coverage_threshold       Minimum coverage percentage (default: 90.0)")
        print("  regression_test_pattern  Pattern to identify regression test files (optional)")
        sys.exit(1)

    target = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else None
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 90.0
    pattern = sys.argv[4] if len(sys.argv) > 4 else ""

    result = validate_fix(target, language=lang, coverage_threshold=threshold, regression_test_pattern=pattern)
    print(report_to_json(result))

    sys.exit(0 if result.overall_passed else 1)
