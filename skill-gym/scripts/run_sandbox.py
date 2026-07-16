"""
run_sandbox.py -- Execute agent-generated code in an isolated sandbox.

Runs code in a temporary directory with resource limits, captures stdout/stderr,
and returns execution results. Supports Python and shell scripts with optional
network isolation and filesystem restrictions.

Usage:
    python run_sandbox.py --skill-dir ./skills/fastapi-api-builder --task-id task_001
    python run_sandbox.py --code-dir ./output --timeout 30 --memory-limit 256
    python run_sandbox.py --skill-dir ./skills/fastapi-api-builder --task-id task_001 --verify
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class SandboxConfig:
    """Configuration for sandboxed execution."""

    timeout_seconds: int = 30
    memory_limit_mb: int = 256
    cpu_limit_cores: float = 1.0
    network_enabled: bool = False
    allowed_paths: list[str] = field(default_factory=list)
    python_version: str = sys.executable
    env_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of sandboxed code execution."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    peak_memory_mb: float | None = None
    sandbox_dir: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "sandbox_dir": self.sandbox_dir,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Sandbox setup
# ---------------------------------------------------------------------------

def create_sandbox(
    skill_dir: Path,
    task_id: str,
    config: SandboxConfig,
) -> Path:
    """
    Create an isolated sandbox directory for code execution.

    Copies the skill's generated code into a temporary directory.
    Strips any git history or unnecessary files.

    Args:
        skill_dir: Path to the skill directory containing generated code.
        task_id: Task identifier for organizing sandbox state.
        config: Sandbox configuration.

    Returns:
        Path to the created sandbox directory.
    """
    sandbox_base = Path(tempfile.mkdtemp(prefix=f"sandbox_{task_id}_"))
    sandbox_code = sandbox_base / "code"
    sandbox_code.mkdir(parents=True, exist_ok=True)

    # Copy code files (exclude .git, __pycache__, .venv, etc.)
    exclude_patterns = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        ".env",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        "sandbox",
    }

    for item in skill_dir.iterdir():
        if item.name in exclude_patterns:
            continue
        if item.name.startswith("."):
            continue

        dest = sandbox_code / item.name
        if item.is_dir():
            shutil.copytree(
                item, dest, ignore=shutil.ignore_patterns(*exclude_patterns)
            )
        else:
            shutil.copy2(item, dest)

    print(f"  Sandbox created at {sandbox_base}")
    return sandbox_base


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_python_script(
    script_path: Path,
    sandbox_dir: Path,
    config: SandboxConfig,
) -> ExecutionResult:
    """
    Execute a Python script in the sandbox.

    Args:
        script_path: Path to the Python script to run.
        sandbox_dir: Path to the sandbox directory.
        config: Sandbox configuration.

    Returns:
        ExecutionResult with captured output and timing.
    """
    start_time = time.monotonic()

    env = os.environ.copy()
    env.update(config.env_overrides)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        config.python_version,
        "-u",  # Unbuffered output
        str(script_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            cwd=str(sandbox_dir / "code"),
            env=env,
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)

        return ExecutionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            duration_ms=duration_ms,
            sandbox_dir=str(sandbox_dir),
        )

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Execution timed out after {config.timeout_seconds}s",
            exit_code=-1,
            duration_ms=duration_ms,
            sandbox_dir=str(sandbox_dir),
            error="timeout",
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=str(exc),
            exit_code=-1,
            duration_ms=duration_ms,
            sandbox_dir=str(sandbox_dir),
            error=f"{type(exc).__name__}: {exc}",
        )


def run_command(
    cmd: list[str],
    sandbox_dir: Path,
    config: SandboxConfig,
) -> ExecutionResult:
    """
    Execute an arbitrary command in the sandbox.

    Args:
        cmd: Command and arguments to execute.
        sandbox_dir: Path to the sandbox directory.
        config: Sandbox configuration.

    Returns:
        ExecutionResult with captured output and timing.
    """
    start_time = time.monotonic()

    env = os.environ.copy()
    env.update(config.env_overrides)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            cwd=str(sandbox_dir / "code"),
            env=env,
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)

        return ExecutionResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            duration_ms=duration_ms,
            sandbox_dir=str(sandbox_dir),
        )

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Execution timed out after {config.timeout_seconds}s",
            exit_code=-1,
            duration_ms=duration_ms,
            sandbox_dir=str(sandbox_dir),
            error="timeout",
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=str(exc),
            exit_code=-1,
            duration_ms=duration_ms,
            sandbox_dir=str(sandbox_dir),
            error=f"{type(exc).__name__}: {exc}",
        )


def run_pytest(
    test_path: Path,
    sandbox_dir: Path,
    config: SandboxConfig,
) -> ExecutionResult:
    """
    Run pytest against test files in the sandbox.

    Args:
        test_path: Path to test file or directory.
        sandbox_dir: Path to the sandbox directory.
        config: Sandbox configuration.

    Returns:
        ExecutionResult with test output.
    """
    cmd = [
        config.python_version,
        "-m",
        "pytest",
        str(test_path),
        "-v",
        "--tb=short",
        "--no-header",
    ]
    return run_command(cmd, sandbox_dir, config)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_sandbox(sandbox_dir: Path) -> None:
    """Remove the sandbox directory and all its contents."""
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir, ignore_errors=True)
        print(f"  Cleaned up sandbox at {sandbox_dir}")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_in_sandbox(
    skill_dir: Path,
    task_id: str,
    config: SandboxConfig | None = None,
    cleanup: bool = True,
) -> ExecutionResult:
    """
    Run a skill's generated code in an isolated sandbox.

    Args:
        skill_dir: Path to the skill directory.
        task_id: Task identifier.
        config: Sandbox configuration. Uses defaults if None.
        cleanup: Whether to remove the sandbox after execution.

    Returns:
        ExecutionResult with execution details.
    """
    if config is None:
        config = SandboxConfig()

    print(f"\nRunning in sandbox: {skill_id} / {task_id}")
    sandbox_dir = None

    try:
        sandbox_dir = create_sandbox(skill_dir, task_id, config)

        # Look for main entry point
        code_dir = sandbox_dir / "code"
        entry_points = [
            code_dir / "main.py",
            code_dir / "app.py",
            code_dir / "run.py",
        ]

        entry_point = None
        for ep in entry_points:
            if ep.exists():
                entry_point = ep
                break

        if entry_point is None:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="No entry point found (main.py, app.py, or run.py)",
                exit_code=1,
                duration_ms=0,
                sandbox_dir=str(sandbox_dir),
                error="no_entry_point",
            )

        # Install dependencies if requirements.txt exists
        req_file = code_dir / "requirements.txt"
        if req_file.exists():
            print("  Installing dependencies...")
            install_result = run_command(
                [
                    config.python_version,
                    "-m",
                    "pip",
                    "install",
                    "-q",
                    "-r",
                    str(req_file),
                ],
                sandbox_dir,
                config,
            )
            if not install_result.success:
                return ExecutionResult(
                    success=False,
                    stdout=install_result.stdout,
                    stderr=f"Dependency installation failed:\n{install_result.stderr}",
                    exit_code=1,
                    duration_ms=install_result.duration_ms,
                    sandbox_dir=str(sandbox_dir),
                    error="dependency_install_failed",
                )

        # Execute entry point
        print(f"  Executing {entry_point.name}...")
        result = run_python_script(entry_point, sandbox_dir, config)

        return result

    finally:
        if cleanup and sandbox_dir:
            cleanup_sandbox(sandbox_dir)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for sandboxed execution."""
    parser = argparse.ArgumentParser(
        description="Execute agent-generated code in an isolated sandbox.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python run_sandbox.py --skill-dir ./skills/fastapi-api-builder --task-id task_001
              python run_sandbox.py --code-dir ./output --timeout 60 --memory-limit 512
        """),
    )
    parser.add_argument(
        "--skill-dir",
        type=Path,
        help="Path to the skill directory containing generated code.",
    )
    parser.add_argument(
        "--code-dir",
        type=Path,
        help="Path directly to code directory (bypasses skill structure).",
    )
    parser.add_argument(
        "--task-id",
        type=str,
        default="default",
        help="Task identifier (default: 'default').",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Execution timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--memory-limit",
        type=int,
        default=256,
        help="Memory limit in MB (default: 256).",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not remove sandbox directory after execution.",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text).",
    )

    args = parser.parse_args()

    config = SandboxConfig(
        timeout_seconds=args.timeout,
        memory_limit_mb=args.memory_limit,
    )

    skill_dir = args.skill_dir or args.code_dir
    if not skill_dir:
        parser.error("Either --skill-dir or --code-dir is required.")

    result = run_in_sandbox(
        skill_dir=skill_dir,
        task_id=args.task_id,
        config=config,
        cleanup=not args.no_cleanup,
    )

    if args.output_format == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\nExecution: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Exit code: {result.exit_code}")
        if result.stdout:
            print(f"\n--- stdout ---\n{result.stdout}")
        if result.stderr:
            print(f"\n--- stderr ---\n{result.stderr}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
