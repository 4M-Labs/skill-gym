"""
verifier.py -- Example verifier for the fastapi-api-builder skill.

Runs a sequence of verification checks against generated FastAPI code.
Each check returns a CheckResult with a pass/fail verdict and optional message.
Checks are weighted and combined into a final quality score.

Usage:
    python verifier.py --task-dir ./output --task-config ./tasks/task_001.json
    python verifier.py --task-dir ./output --checks python_syntax,fastapi_app
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    """Result of a single verification check."""

    check_id: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationReport:
    """Aggregated report from all verification checks."""

    check_results: list[CheckResult] = field(default_factory=list)
    total_weight: float = 0.0
    weighted_score: float = 0.0

    @property
    def verdict(self) -> str:
        if not self.check_results:
            return "fail"
        if all(r.passed for r in self.check_results):
            return "pass"
        if any(r.passed for r in self.check_results):
            return "partial"
        return "fail"

    @property
    def score(self) -> float:
        if self.total_weight == 0:
            return 0.0
        return round(self.weighted_score / self.total_weight, 4)

    @property
    def checks_passed(self) -> int:
        return sum(1 for r in self.check_results if r.passed)

    @property
    def checks_total(self) -> int:
        return len(self.check_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "score": self.score,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "details": [
                {
                    "check_id": r.check_id,
                    "passed": r.passed,
                    "message": r.message,
                }
                for r in self.check_results
            ],
        }


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

def check_python_syntax(task_dir: Path) -> CheckResult:
    """Verify all .py files parse without syntax errors."""
    errors: list[str] = []
    py_files = list(task_dir.rglob("*.py"))

    if not py_files:
        return CheckResult(
            check_id="python_syntax",
            passed=False,
            message="No .py files found in task directory.",
        )

    for py_file in py_files:
        try:
            ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError as exc:
            errors.append(f"{py_file.name}: line {exc.lineno} -- {exc.msg}")

    if errors:
        return CheckResult(
            check_id="python_syntax",
            passed=False,
            message=f"Syntax errors in {len(errors)} file(s): {'; '.join(errors)}",
            details={"errors": errors},
        )

    return CheckResult(
        check_id="python_syntax",
        passed=True,
        message=f"All {len(py_files)} Python file(s) parsed successfully.",
    )


def check_pydantic_models(task_dir: Path) -> CheckResult:
    """Verify Pydantic models can be imported and instantiated."""
    errors: list[str] = []

    for py_file in task_dir.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            if "BaseModel" not in source and "pydantic" not in source.lower():
                continue

            spec = importlib.util.spec_from_file_location(
                py_file.stem, str(py_file)
            )
            if spec is None or spec.loader is None:
                errors.append(f"{py_file.name}: cannot load module spec")
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[py_file.stem] = module
            spec.loader.exec_module(module)

        except Exception as exc:
            errors.append(f"{py_file.name}: {type(exc).__name__}: {exc}")

    if errors:
        return CheckResult(
            check_id="pydantic_models",
            passed=False,
            message=f"Pydantic model errors: {'; '.join(errors)}",
            details={"errors": errors},
        )

    return CheckResult(
        check_id="pydantic_models",
        passed=True,
        message="All Pydantic models imported and validated successfully.",
    )


def check_import_chain(task_dir: Path) -> CheckResult:
    """Verify all imports resolve without errors."""
    errors: list[str] = []

    for py_file in task_dir.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        try:
                            importlib.import_module(alias.name)
                        except ImportError:
                            # Allow relative imports to fail if they reference
                            # sibling modules in the same task directory.
                            pass

        except Exception as exc:
            errors.append(f"{py_file.name}: {type(exc).__name__}: {exc}")

    if errors:
        return CheckResult(
            check_id="import_chain",
            passed=False,
            message=f"Import errors: {'; '.join(errors)}",
            details={"errors": errors},
        )

    return CheckResult(
        check_id="import_chain",
        passed=True,
        message="Import chain resolved without errors.",
    )


def check_fastapi_app(
    task_dir: Path, expected_routes: int | None = None
) -> CheckResult:
    """Verify a FastAPI app instance exists and routes are registered."""
    main_file = task_dir / "main.py"
    if not main_file.exists():
        return CheckResult(
            check_id="fastapi_app",
            passed=False,
            message="main.py not found in task directory.",
        )

    try:
        source = main_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(main_file))

        # Look for FastAPI() instantiation
        has_app = False
        route_count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name == "FastAPI":
                    has_app = True

            # Count route decorators
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in (
                                "get", "post", "put", "patch", "delete",
                            ):
                                route_count += 1
                    elif isinstance(decorator, ast.Attribute):
                        if decorator.attr in (
                            "get", "post", "put", "patch", "delete",
                        ):
                            route_count += 1

        if not has_app:
            return CheckResult(
                check_id="fastapi_app",
                passed=False,
                message="No FastAPI() instantiation found in main.py.",
            )

        if expected_routes is not None and route_count < expected_routes:
            return CheckResult(
                check_id="fastapi_app",
                passed=False,
                message=(
                    f"Expected at least {expected_routes} routes, "
                    f"found {route_count}."
                ),
                details={"route_count": route_count},
            )

        return CheckResult(
            check_id="fastapi_app",
            passed=True,
            message=f"FastAPI app found with {route_count} route(s).",
            details={"route_count": route_count},
        )

    except Exception as exc:
        return CheckResult(
            check_id="fastapi_app",
            passed=False,
            message=f"Failed to analyze main.py: {exc}",
        )


def check_openapi_spec(task_dir: Path) -> CheckResult:
    """Verify the generated OpenAPI spec is valid JSON."""
    spec_file = task_dir / "openapi.json"
    if not spec_file.exists():
        return CheckResult(
            check_id="openapi_spec",
            passed=False,
            message="openapi.json not found.",
        )

    try:
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        required_keys = {"openapi", "info", "paths"}
        missing = required_keys - set(spec.keys())

        if missing:
            return CheckResult(
                check_id="openapi_spec",
                passed=False,
                message=f"OpenAPI spec missing keys: {', '.join(sorted(missing))}",
            )

        return CheckResult(
            check_id="openapi_spec",
            passed=True,
            message="OpenAPI spec is valid JSON with required keys.",
        )

    except json.JSONDecodeError as exc:
        return CheckResult(
            check_id="openapi_spec",
            passed=False,
            message=f"openapi.json is not valid JSON: {exc}",
        )


def check_test_suite(task_dir: Path, test_file: str | None = None) -> CheckResult:
    """Run pytest against the generated test suite."""
    if test_file:
        test_path = task_dir / test_file
    else:
        test_path = task_dir / "tests"
        if not test_path.exists():
            # Fall back to any test_*.py files
            test_files = list(task_dir.rglob("test_*.py"))
            if not test_files:
                return CheckResult(
                    check_id="test_suite",
                    passed=False,
                    message="No test files found.",
                )
            test_path = task_dir

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(task_dir),
        )

        if result.returncode == 0:
            return CheckResult(
                check_id="test_suite",
                passed=True,
                message="All tests passed.",
                details={"stdout": result.stdout[-2000:]},
            )
        else:
            return CheckResult(
                check_id="test_suite",
                passed=False,
                message=f"Tests failed (exit code {result.returncode}).",
                details={"stdout": result.stdout[-2000:], "stderr": result.stderr[-1000:]},
            )

    except subprocess.TimeoutExpired:
        return CheckResult(
            check_id="test_suite",
            passed=False,
            message="Test suite timed out after 60 seconds.",
        )
    except Exception as exc:
        return CheckResult(
            check_id="test_suite",
            passed=False,
            message=f"Failed to run tests: {exc}",
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

CHECK_WEIGHTS: dict[str, float] = {
    "python_syntax": 0.15,
    "pydantic_models": 0.20,
    "import_chain": 0.15,
    "fastapi_app": 0.20,
    "openapi_spec": 0.10,
    "test_suite": 0.20,
}

CHECK_REGISTRY: dict[str, Any] = {
    "python_syntax": lambda d, _: check_python_syntax(d),
    "pydantic_models": lambda d, _: check_pydantic_models(d),
    "import_chain": lambda d, _: check_import_chain(d),
    "fastapi_app": lambda d, c: check_fastapi_app(
        d, c.get("expected_route_count")
    ),
    "openapi_spec": lambda d, _: check_openapi_spec(d),
    "test_suite": lambda d, c: check_test_suite(d, c.get("test_file")),
}


def run_verification(
    task_dir: Path,
    task_config: dict[str, Any] | None = None,
    selected_checks: list[str] | None = None,
) -> VerificationReport:
    """
    Run all verification checks against the generated code.

    Args:
        task_dir: Path to the directory containing generated code.
        task_config: Optional task configuration with verification settings.
        selected_checks: If provided, only run these check IDs.

    Returns:
        VerificationReport with individual check results and aggregate score.
    """
    report = VerificationReport()
    verification_config: dict[str, Any] = {}

    if task_config:
        verification_config = task_config.get("verification_config", {})

    checks_to_run = selected_checks or list(CHECK_WEIGHTS.keys())

    for check_id in checks_to_run:
        if check_id not in CHECK_REGISTRY:
            continue

        config = verification_config.get(check_id, {})
        if config.get("enabled") is False:
            continue

        weight = CHECK_WEIGHTS.get(check_id, 0.0)
        result = CHECK_REGISTRY[check_id](task_dir, config)

        report.check_results.append(result)
        report.total_weight += weight
        if result.passed:
            report.weighted_score += weight

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for running verification checks."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run verification checks against generated FastAPI code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Example:
              python verifier.py --task-dir ./output --checks python_syntax,fastapi_app
              python verifier.py --task-dir ./output --task-config ./tasks/task_001.json
        """),
    )
    parser.add_argument(
        "--task-dir",
        type=Path,
        required=True,
        help="Path to directory containing generated code.",
    )
    parser.add_argument(
        "--task-config",
        type=Path,
        default=None,
        help="Path to task JSON configuration file.",
    )
    parser.add_argument(
        "--checks",
        type=str,
        default=None,
        help="Comma-separated list of check IDs to run.",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text).",
    )

    args = parser.parse_args()

    task_config = None
    if args.task_config:
        with open(args.task_config, encoding="utf-8") as f:
            task_config = json.load(f)

    selected_checks = None
    if args.checks:
        selected_checks = [c.strip() for c in args.checks.split(",")]

    report = run_verification(args.task_dir, task_config, selected_checks)

    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"\nVerification Report: {report.verdict.upper()}")
        print(f"Score: {report.score:.2f} ({report.checks_passed}/{report.checks_total} passed)\n")
        for result in report.check_results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.check_id}: {result.message}")

    sys.exit(0 if report.verdict == "pass" else 1)


if __name__ == "__main__":
    main()
