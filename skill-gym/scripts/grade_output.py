"""
grade_output.py -- Grade agent-generated output against task requirements.

Loads task definitions and verification configs, runs the verification suite,
computes rewards, and produces a graded report. Supports batch grading of
multiple tasks across multiple skills.

Usage:
    python grade_output.py --skill-dir ./skills/fastapi-api-builder --task-id task_001
    python grade_output.py --skill-dir ./skills/fastapi-api-builder --all-tasks
    python grade_output.py --report-dir ./reports --summary
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Relative imports for sibling scripts
sys.path.insert(0, str(Path(__file__).parent))
from run_sandbox import (
    ExecutionResult,
    SandboxConfig,
    cleanup_sandbox,
    create_sandbox,
    run_python_script,
)
from reward import RewardConfig, RewardResult, compute_reward


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class GradedTask:
    """Grading result for a single task."""

    task_id: str
    task_instruction: str
    difficulty: str
    execution: ExecutionResult | None = None
    verification: dict[str, Any] | None = None
    reward: RewardResult | None = None
    grade: str = "ungraded"
    graded_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "task_id": self.task_id,
            "task_instruction": self.task_instruction,
            "difficulty": self.difficulty,
            "grade": self.grade,
            "graded_at": self.graded_at,
        }
        if self.execution:
            result["execution"] = self.execution.to_dict()
        if self.verification:
            result["verification"] = self.verification
        if self.reward:
            result["reward"] = self.reward.to_dict()
        return result


@dataclass
class SkillGradeReport:
    """Aggregated grading report for a skill."""

    skill_id: str
    skill_dir: str
    graded_tasks: list[GradedTask] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_dir": self.skill_dir,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "tasks": [t.to_dict() for t in self.graded_tasks],
        }


# ---------------------------------------------------------------------------
# Task loading
# ---------------------------------------------------------------------------

def load_tasks(skill_dir: Path) -> list[dict[str, Any]]:
    """Load all task definitions from a skill's tasks directory."""
    tasks_dir = skill_dir / "tasks"
    if not tasks_dir.exists():
        return []

    tasks = []
    for task_file in sorted(tasks_dir.glob("task_*.json")):
        with open(task_file, encoding="utf-8") as f:
            tasks.append(json.load(f))

    return tasks


def load_task(skill_dir: Path, task_id: str) -> dict[str, Any] | None:
    """Load a specific task definition by ID."""
    task_file = skill_dir / "tasks" / f"{task_id}.json"
    if not task_file.exists():
        return None

    with open(task_file, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def grade_task(
    skill_dir: Path,
    task: dict[str, Any],
    sandbox_config: SandboxConfig | None = None,
    cleanup: bool = True,
) -> GradedTask:
    """
    Grade a single task by running execution and verification.

    Args:
        skill_dir: Path to the skill directory.
        task: Task definition dict.
        sandbox_config: Sandbox configuration.
        cleanup: Whether to clean up sandbox after execution.

    Returns:
        GradedTask with grading results.
    """
    task_id = task.get("task_id", "unknown")
    difficulty = task.get("difficulty", "medium")

    print(f"\nGrading task: {task_id} (difficulty: {difficulty})")

    graded = GradedTask(
        task_id=task_id,
        task_instruction=task.get("instruction", ""),
        difficulty=difficulty,
        graded_at=datetime.now(timezone.utc).isoformat(),
    )

    # Run in sandbox
    if sandbox_config is None:
        sandbox_config = SandboxConfig()

    try:
        from run_sandbox import run_in_sandbox

        execution = run_in_sandbox(
            skill_dir=skill_dir,
            task_id=task_id,
            config=sandbox_config,
            cleanup=cleanup,
        )
        graded.execution = execution

        if not execution.success:
            graded.grade = "execution_failed"
            return graded

    except Exception as exc:
        graded.grade = "sandbox_error"
        graded.execution = ExecutionResult(
            success=False,
            stdout="",
            stderr=str(exc),
            exit_code=-1,
            duration_ms=0,
            error=str(exc),
        )
        return graded

    # Run verification
    try:
        from verifier import run_verification

        report = run_verification(
            task_dir=Path(execution.sandbox_dir) / "code" if execution.sandbox_dir else skill_dir,
            task_config=task,
        )
        graded.verification = report.to_dict()

        # Compute reward
        reward_result = compute_reward(
            report.to_dict(),
            config=RewardConfig(),
        )
        graded.reward = reward_result

        # Assign grade based on score
        score = report.score
        if score >= 0.9:
            graded.grade = "A"
        elif score >= 0.75:
            graded.grade = "B"
        elif score >= 0.6:
            graded.grade = "C"
        elif score >= 0.4:
            graded.grade = "D"
        else:
            graded.grade = "F"

    except Exception as exc:
        graded.grade = "verification_error"
        graded.verification = {"error": str(exc)}

    return graded


def grade_skill(
    skill_dir: Path,
    task_ids: list[str] | None = None,
    sandbox_config: SandboxConfig | None = None,
) -> SkillGradeReport:
    """
    Grade all tasks (or selected tasks) for a skill.

    Args:
        skill_dir: Path to the skill directory.
        task_ids: Specific task IDs to grade. None = all tasks.
        sandbox_config: Sandbox configuration.

    Returns:
        SkillGradeReport with results for all graded tasks.
    """
    skill_id = skill_dir.name
    print(f"\n{'='*60}")
    print(f"Grading skill: {skill_id}")
    print(f"{'='*60}")

    report = SkillGradeReport(
        skill_id=skill_id,
        skill_dir=str(skill_dir),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    all_tasks = load_tasks(skill_dir)
    if not all_tasks:
        print("  No tasks found.")
        return report

    tasks_to_grade = all_tasks
    if task_ids:
        tasks_to_grade = [t for t in all_tasks if t.get("task_id") in task_ids]

    for task in tasks_to_grade:
        graded = grade_task(skill_dir, task, sandbox_config)
        report.graded_tasks.append(graded)

    # Compute summary
    grades = [t.grade for t in report.graded_tasks]
    rewards = [
        t.reward.total_reward for t in report.graded_tasks if t.reward
    ]

    report.summary = {
        "total_tasks": len(report.graded_tasks),
        "grades": {g: grades.count(g) for g in set(grades)},
        "average_reward": sum(rewards) / len(rewards) if rewards else 0.0,
        "pass_rate": grades.count("A") / len(grades) if grades else 0.0,
        "difficulty_breakdown": {},
    }

    for task in report.graded_tasks:
        diff = task.difficulty
        if diff not in report.summary["difficulty_breakdown"]:
            report.summary["difficulty_breakdown"][diff] = {
                "count": 0,
                "grades": [],
            }
        report.summary["difficulty_breakdown"][diff]["count"] += 1
        report.summary["difficulty_breakdown"][diff]["grades"].append(task.grade)

    return report


# ---------------------------------------------------------------------------
# Report I/O
# ---------------------------------------------------------------------------

def save_report(report: SkillGradeReport, output_dir: Path) -> Path:
    """Save a grading report to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report.skill_id}_grade_{timestamp}.json"
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)

    print(f"\nReport saved to {output_path}")
    return output_path


def load_report(report_path: Path) -> SkillGradeReport:
    """Load a grading report from disk."""
    with open(report_path, encoding="utf-8") as f:
        data = json.load(f)

    report = SkillGradeReport(
        skill_id=data.get("skill_id", ""),
        skill_dir=data.get("skill_dir", ""),
        generated_at=data.get("generated_at", ""),
        summary=data.get("summary", {}),
    )

    for task_data in data.get("tasks", []):
        graded = GradedTask(
            task_id=task_data.get("task_id", ""),
            task_instruction=task_data.get("task_instruction", ""),
            difficulty=task_data.get("difficulty", ""),
            grade=task_data.get("grade", "ungraded"),
            graded_at=task_data.get("graded_at", ""),
            verification=task_data.get("verification"),
        )
        report.graded_tasks.append(graded)

    return report


def print_summary(reports: list[SkillGradeReport]) -> None:
    """Print a summary table across multiple skill reports."""
    print(f"\n{'='*70}")
    print("GRADE SUMMARY")
    print(f"{'='*70}")
    print(f"{'Skill ID':<30} {'Tasks':<8} {'Avg Reward':<12} {'Pass Rate':<10}")
    print("-" * 70)

    for report in reports:
        summary = report.summary
        print(
            f"{report.skill_id:<30} "
            f"{summary.get('total_tasks', 0):<8} "
            f"{summary.get('average_reward', 0):.3f}{'':<7} "
            f"{summary.get('pass_rate', 0):.1%}"
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for grading agent output."""
    parser = argparse.ArgumentParser(
        description="Grade agent-generated output against task requirements.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python grade_output.py --skill-dir ./skills/fastapi-api-builder --task-id task_001
              python grade_output.py --skill-dir ./skills/fastapi-api-builder --all-tasks
              python grade_output.py --report-dir ./reports --summary
        """),
    )
    parser.add_argument(
        "--skill-dir",
        type=Path,
        help="Path to the skill directory.",
    )
    parser.add_argument(
        "--task-id",
        type=str,
        default=None,
        help="Specific task ID to grade.",
    )
    parser.add_argument(
        "--all-tasks",
        action="store_true",
        help="Grade all tasks in the skill.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Execution timeout per task in seconds (default: 30).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./reports"),
        help="Directory to save grade reports (default: ./reports).",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Load and summarize existing reports from this directory.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary of reports in --report-dir.",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not remove sandbox directories after grading.",
    )

    args = parser.parse_args()

    # Summary mode: load existing reports
    if args.summary and args.report_dir:
        reports = []
        for report_file in sorted(args.report_dir.glob("*_grade_*.json")):
            reports.append(load_report(report_file))
        print_summary(reports)
        sys.exit(0)

    if not args.skill_dir:
        parser.error("--skill-dir is required (or use --summary with --report-dir)")

    # Determine tasks to grade
    task_ids = None
    if args.task_id:
        task_ids = [args.task_id]
    elif not args.all_tasks:
        parser.error("Specify --task-id or --all-tasks")

    sandbox_config = SandboxConfig(timeout_seconds=args.timeout)

    report = grade_skill(
        skill_dir=args.skill_dir,
        task_ids=task_ids,
        sandbox_config=sandbox_config,
    )

    # Save report
    save_report(report, args.output_dir)

    # Print summary
    print(f"\nGrade: {report.skill_id}")
    summary = report.summary
    print(f"  Tasks graded: {summary.get('total_tasks', 0)}")
    print(f"  Average reward: {summary.get('average_reward', 0):.3f}")
    print(f"  Pass rate: {summary.get('pass_rate', 0):.1%}")
    print(f"  Grade distribution: {summary.get('grades', {})}")

    sys.exit(0)


if __name__ == "__main__":
    main()
