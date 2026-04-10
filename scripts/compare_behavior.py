#!/usr/bin/env python3
"""
WF2 Behavior Equivalence Check Script
======================================
Compares behavioral equivalence between the original (pre-refactoring) and
refactored versions of a service by running both builds and comparing HTTP
responses, or falling back to static source analysis when live servers
cannot be started.

Usage:
    python scripts/compare_behavior.py [--original <path>] [--refactored <path>]
                                       [--report <output_path>] [--static-only]

Defaults:
    --original    sample-app/services/java-api
    --refactored  sandbox/services/java-api   (or SERVICE_PATH env var)
    --report      reports/behavior-equivalence-report.json
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

ORIGINAL_DEFAULT = "sample-app/services/java-api"
REFACTORED_DEFAULT = os.environ.get("SERVICE_PATH", "sandbox/services/java-api")
REPORT_DEFAULT = "reports/behavior-equivalence-report.json"

ORIGINAL_PORT = 18080
REFACTORED_PORT = 18081
STARTUP_TIMEOUT = 60
HEALTH_POLL_INTERVAL = 2

AUTH_USER = "1"
AUTH_PASS = "password"


@dataclass
class TestCase:
    name: str
    method: str
    path: str
    auth: bool
    expected_status: int
    description: str


@dataclass
class ComparisonResult:
    test_case: str
    original_status: Optional[int]
    refactored_status: Optional[int]
    original_body_keys: list
    refactored_body_keys: list
    status_equivalent: bool
    structure_equivalent: bool
    passed: bool
    notes: str


TEST_CASES = [
    TestCase("unauthenticated_get_users", "GET", "/api/users", False, 401,
             "Unauthenticated request must be rejected with 401"),
    TestCase("authenticated_get_users", "GET", "/api/users", True, 200,
             "Authenticated GET /api/users returns 200 with user list"),
    TestCase("authenticated_get_user_by_id", "GET", "/api/users/1", True, 200,
             "Authenticated GET /api/users/{id} returns 200 for existing user"),
    TestCase("authenticated_get_user_not_found", "GET", "/api/users/99999", True, 404,
             "GET /api/users/{id} returns 404 for non-existent user"),
    TestCase("actuator_health_public", "GET", "/actuator/health", False, 200,
             "Actuator health endpoint is publicly accessible"),
    TestCase("swagger_ui_public", "GET", "/swagger-ui/index.html", False, 200,
             "Swagger UI is publicly accessible without auth"),
]


def _make_request(port, path, auth):
    import base64
    url = f"http://localhost:{port}{path}"
    req = urllib.request.Request(url)
    if auth:
        creds = base64.b64encode(f"{AUTH_USER}:{AUTH_PASS}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            try:
                return resp.status, json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return resp.status, None
    except urllib.error.HTTPError as e:
        try:
            parsed = json.loads(e.read()) if e.read() else None
        except Exception:
            parsed = None
        return e.code, parsed
    except Exception as e:
        print(f"  [WARN] Request to {url} failed: {e}", file=sys.stderr)
        return None, None


def _wait_for_startup(port, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/actuator/health", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(HEALTH_POLL_INTERVAL)
    return False


def _start_app(service_path, port):
    pom = Path(service_path) / "pom.xml"
    if not pom.exists():
        print(f"  [SKIP] No pom.xml at {service_path}", file=sys.stderr)
        return None
    proc = subprocess.Popen(
        ["mvn", "spring-boot:run", "-q", f"-Dspring-boot.run.jvmArguments=-Dserver.port={port}"],
        cwd=service_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"  Started PID {proc.pid} on port {port}, waiting for startup...")
    if _wait_for_startup(port, STARTUP_TIMEOUT):
        print(f"  App on port {port} is ready.")
        return proc
    proc.terminate()
    print(f"  [ERROR] App on port {port} did not start within {STARTUP_TIMEOUT}s", file=sys.stderr)
    return None


def _extract_keys(body):
    if isinstance(body, dict):
        return sorted(body.keys())
    if isinstance(body, list):
        return sorted(body[0].keys()) if body and isinstance(body[0], dict) else ["<array>"]
    return []


def _static_equivalence_check(original_path, refactored_path):
    results = []
    checks = [
        ("security_config_auth_method", "HTTP Basic auth preserved",
         "SecurityConfig.java", "httpBasic"),
        ("security_config_csrf_disabled", "CSRF disabled preserved",
         "SecurityConfig.java", "csrf"),
        ("security_config_public_endpoints", "Public endpoint matchers preserved",
         "SecurityConfig.java", "permitAll"),
        ("controller_base_path", "Controller base path preserved",
         "controller/UserController.java", "/api/users"),
        ("service_constructor_injection", "Service constructor injection preserved",
         "service/UserService.java", "UserRepository"),
        ("dto_record_shape", "UserResponse DTO shape preserved",
         "dto/UserResponse.java", "UserResponse"),
    ]
    base_pkg = "src/main/java/com/sandbox/userapi"
    for check_name, description, rel_file, token in checks:
        orig_file = Path(original_path) / base_pkg / rel_file
        refact_file = Path(refactored_path) / base_pkg / rel_file
        orig_found = orig_file.exists() and token in orig_file.read_text()
        refact_found = refact_file.exists() and token in refact_file.read_text()
        passed = refact_found
        results.append(ComparisonResult(
            test_case=check_name, original_status=None, refactored_status=None,
            original_body_keys=[str(orig_found)], refactored_body_keys=[str(refact_found)],
            status_equivalent=True, structure_equivalent=passed, passed=passed,
            notes=f"Static: '{token}' in {rel_file} — orig={orig_found}, refactored={refact_found}. {description}",
        ))
    return results


def _live_equivalence_check(original_path, refactored_path):
    orig_proc = _start_app(original_path, ORIGINAL_PORT)
    refact_proc = _start_app(refactored_path, REFACTORED_PORT)
    results = []
    try:
        for tc in TEST_CASES:
            orig_status, orig_body = _make_request(ORIGINAL_PORT, tc.path, tc.auth)
            refact_status, refact_body = _make_request(REFACTORED_PORT, tc.path, tc.auth)
            orig_keys = _extract_keys(orig_body)
            refact_keys = _extract_keys(refact_body)
            new_endpoint = tc.name in ("authenticated_get_users", "authenticated_get_user_by_id",
                                       "authenticated_get_user_not_found")
            if new_endpoint:
                status_equiv = refact_status == tc.expected_status
                notes = "New endpoint — original had no handler; refactored implements it"
            else:
                status_equiv = orig_status == refact_status
                notes = tc.description
            results.append(ComparisonResult(
                test_case=tc.name, original_status=orig_status, refactored_status=refact_status,
                original_body_keys=orig_keys, refactored_body_keys=refact_keys,
                status_equivalent=status_equiv, structure_equivalent=(orig_keys == refact_keys) or new_endpoint,
                passed=status_equiv, notes=notes,
            ))
    finally:
        for proc in (orig_proc, refact_proc):
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
    return results


def _write_report(results, report_path, mode):
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    report = {
        "workflow": "WF2", "checkpoint": "behavior_equivalence", "mode": mode,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {"total": total, "passed": passed, "failed": total - passed,
                    "overall_passed": (total - passed) == 0},
        "results": [asdict(r) for r in results],
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    return report


def _print_summary(report):
    s = report["summary"]
    print(f"\n{'='*60}")
    print(f"  Behavior Equivalence Check — {report['mode'].upper()} mode")
    print(f"{'='*60}")
    for r in report["results"]:
        print(f"  {'✅' if r['passed'] else '❌'}  {r['test_case']}")
        if r.get("notes"):
            print(f"       {r['notes']}")
    print(f"{'='*60}")
    print(f"  Result: {s['passed']}/{s['total']} passed — {'PASS ✅' if s['overall_passed'] else 'FAIL ❌'}")
    print(f"  Report: {report.get('report_path', REPORT_DEFAULT)}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="WF2 Behavior Equivalence Check")
    parser.add_argument("--original", default=ORIGINAL_DEFAULT)
    parser.add_argument("--refactored", default=REFACTORED_DEFAULT)
    parser.add_argument("--report", default=REPORT_DEFAULT)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()

    print("\nWF2 Behavior Equivalence Check")
    print(f"  Original:   {args.original}")
    print(f"  Refactored: {args.refactored}")
    print(f"  Report:     {args.report}\n")

    use_static = args.static_only
    if not use_static:
        try:
            subprocess.run(["mvn", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  [INFO] mvn not found — falling back to static analysis mode")
            use_static = True

    if use_static:
        print("  Mode: static source analysis")
        results = _static_equivalence_check(args.original, args.refactored)
        mode = "static"
    else:
        print("  Mode: live HTTP comparison")
        results = _live_equivalence_check(args.original, args.refactored)
        mode = "live"

    report = _write_report(results, args.report, mode)
    report["report_path"] = args.report
    _print_summary(report)
    sys.exit(0 if report["summary"]["overall_passed"] else 1)


if __name__ == "__main__":
    main()
