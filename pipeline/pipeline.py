#!/usr/bin/env python3
"""
SkillGym Pipeline - Master Orchestrator

Chains all pipeline steps for evaluating and fine-tuning a skill:
  1. Parse skill (extract name, create directories)
  2. Generate evals (call generate_evals.py)
  3. Run comparisons (instructions for subagent agent)
  4. Score outputs (call score_outputs_v2.py)
  5. Generate DPO pairs (call generate_dpo_v2.py)
  6. Fine-tune (call train_dpo.py)
  7. Generate report

Usage:
  python pipeline.py --skill-path <path/to/SKILL.md> [--num-tasks 10] [--skip-training] [--force]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


# --- Directory Layout ---
# All paths relative to the pipeline/ directory
PIPELINE_DIR = Path(__file__).parent.resolve()
EVALS_BASE = PIPELINE_DIR / "evals"
RESULTS_BASE = PIPELINE_DIR / "results"
DPO_BASE = PIPELINE_DIR / "dpo-data"
MODELS_BASE = PIPELINE_DIR / "models"
ANALYSIS_BASE = PIPELINE_DIR / "analysis"


def extract_skill_name(skill_path):
    """Extract skill name from SKILL.md filename."""
    name = skill_path.stem
    # Strip common suffixes
    for suffix in ["-skill", "_skill", "-SKILL", "_SKILL"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.lower().replace(" ", "-").replace("_", "-")


def run_script(script_name, args, description):
    """Run a pipeline script as a subprocess."""
    script_path = PIPELINE_DIR / script_name
    if not script_path.exists():
        print(f"  ERROR: {script_name} not found at {script_path}")
        return False

    cmd = [sys.executable, str(script_path)] + args
    print(f"  Running: {' '.join(cmd)}")
    print(f"  ---")

    result = subprocess.run(cmd, cwd=str(PIPELINE_DIR))

    if result.returncode != 0:
        print(f"  ---")
        print(f"  ERROR: {script_name} failed with exit code {result.returncode}")
        return False

    print(f"  ---")
    return True


def check_file(path, label):
    """Check if a file exists and print status."""
    if path.exists():
        print(f"  [OK] {label}: {path}")
        return True
    else:
        print(f"  [--] {label}: not found")
        return False


def is_step_complete(results_dir, tasks_file):
    """Check if scoring step is already done."""
    benchmark = results_dir / "benchmark_v2.json"
    deltas = results_dir / "task_deltas_v2.json"
    return benchmark.exists() and deltas.exists()


def is_dpo_complete(dpo_dir):
    """Check if DPO generation is already done."""
    summary = dpo_dir / "quality_summary_v2.json"
    dpo_format = dpo_dir / "dpo_format_v2.json"
    return summary.exists() and dpo_format.exists()


def is_training_complete(models_dir):
    """Check if training produced output."""
    if not models_dir.exists():
        return False
    # Check for adapter files (LoRA saves adapter_model.bin or adapter_model.safetensors)
    has_adapter = any(models_dir.glob("adapter_model.*"))
    has_config = (models_dir / "adapter_config.json").exists()
    return has_adapter or has_config


def read_benchmark_delta(results_dir):
    """Read mean delta from benchmark_v2.json."""
    benchmark_path = results_dir / "benchmark_v2.json"
    if not benchmark_path.exists():
        return None
    try:
        data = json.loads(benchmark_path.read_text())
        return data["overall"]["delta_mean"]
    except (json.JSONDecodeError, KeyError):
        return None


def read_dpo_pair_count(dpo_dir):
    """Read pair count from quality_summary_v2.json."""
    summary_path = dpo_dir / "quality_summary_v2.json"
    if not summary_path.exists():
        return None
    try:
        data = json.loads(summary_path.read_text())
        return data["total_pairs"]
    except (json.JSONDecodeError, KeyError):
        return None


def generate_report(skill_name, skill_path, results_dir, dpo_dir, models_dir, analysis_dir):
    """Generate a markdown report summarizing the pipeline run."""
    analysis_dir.mkdir(parents=True, exist_ok=True)
    report_path = analysis_dir / "report.md"

    lines = [
        f"# SkillGym Pipeline Report: {skill_name}",
        f"",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Skill**: [{skill_name}]({skill_path})",
        f"",
        f"## Directory Structure",
        f"",
        f"```",
        f"evals/{skill_name}/tasks.json",
        f"results/{skill_name}/",
        f"dpo-data/{skill_name}/",
        f"models/{skill_name}/",
        f"analysis/{skill_name}/report.md",
        f"```",
        f"",
    ]

    # Scoring results
    delta = read_benchmark_delta(results_dir)
    if delta is not None:
        direction = "POSITIVE" if delta > 0 else "NEGATIVE"
        lines.extend([
            f"## Scoring Results",
            f"",
            f"- **Mean composite delta**: {delta:+.3f} ({direction})",
            f"- **Benchmark file**: `results/{skill_name}/benchmark_v2.json`",
            f"",
        ])
    else:
        lines.extend([
            f"## Scoring Results",
            f"",
            f"- Not completed",
            f"",
        ])

    # DPO results
    pair_count = read_dpo_pair_count(dpo_dir)
    if pair_count is not None:
        lines.extend([
            f"## DPO Training Pairs",
            f"",
            f"- **Total pairs**: {pair_count}",
            f"- **DPO format file**: `dpo-data/{skill_name}/dpo_format_v2.json`",
            f"",
        ])
    else:
        lines.extend([
            f"## DPO Training Pairs",
            f"",
            f"- Not completed",
            f"",
        ])

    # Training results
    if is_training_complete(models_dir):
        lines.extend([
            f"## Fine-tuning",
            f"",
            f"- **Model saved**: `models/{skill_name}/`",
            f"",
        ])
    else:
        lines.extend([
            f"## Fine-tuning",
            f"",
            f"- Not completed or skipped",
            f"",
        ])

    report_path.write_text("\n".join(lines))
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="SkillGym Pipeline - Master Orchestrator"
    )
    parser.add_argument(
        "--skill-path",
        type=Path,
        required=True,
        help="Path to the SKILL.md file to evaluate"
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=10,
        help="Number of eval tasks to generate (default: 10)"
    )
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Skip the fine-tuning step"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rerun of all steps, even if already complete"
    )
    args = parser.parse_args()

    # Resolve skill path
    skill_path = args.skill_path.resolve()
    if not skill_path.exists():
        print(f"ERROR: Skill file not found: {skill_path}")
        sys.exit(1)

    skill_name = extract_skill_name(skill_path)
    print(f"=" * 60)
    print(f"SKILLGYM PIPELINE: {skill_name}")
    print(f"=" * 60)
    print(f"Skill file: {skill_path}")
    print(f"Skill name: {skill_name}")
    print(f"Num tasks: {args.num_tasks}")
    print(f"Skip training: {args.skip_training}")
    print(f"Force rerun: {args.force}")
    print()

    # --- Create directory structure ---
    evals_dir = EVALS_BASE / skill_name
    results_dir = RESULTS_BASE / skill_name
    dpo_dir = DPO_BASE / skill_name
    models_dir = MODELS_BASE / skill_name
    analysis_dir = ANALYSIS_BASE / skill_name

    for d in [evals_dir, results_dir, dpo_dir, models_dir, analysis_dir]:
        d.mkdir(parents=True, exist_ok=True)

    tasks_file = evals_dir / "tasks.json"

    # --- Step 1: Parse Skill ---
    print("=" * 60)
    print("STEP 1: Parse Skill")
    print("=" * 60)

    if skill_path.exists():
        print(f"  [OK] Skill file: {skill_path}")
    else:
        print(f"  [!!] Skill file not found: {skill_path}")
        print(f"       Continuing anyway (evals may fail)")

    # --- Step 2: Generate Evals ---
    print()
    print("=" * 60)
    print("STEP 2: Generate Evals")
    print("=" * 60)

    if tasks_file.exists() and not args.force:
        print(f"  [SKIP] Tasks already generated: {tasks_file}")
        print(f"         Use --force to regenerate")
    else:
        success = run_script(
            "generate_evals.py",
            [
                "--skill-path", str(skill_path),
                "--output", str(tasks_file),
                "--num-tasks", str(args.num_tasks),
            ],
            "Generating eval tasks"
        )
        if not success:
            print()
            print("ERROR: Evals generation failed. Stopping pipeline.")
            sys.exit(1)

    print(f"  Tasks file: {tasks_file}")

    # --- Step 3: Run Comparisons (subagent instructions) ---
    print()
    print("=" * 60)
    print("STEP 3: Run Comparisons (Subagent)")
    print("=" * 60)
    print()
    print("  NOW RUN SUBAGENT COMPARISONS")
    print(f"  Save all outputs to: {results_dir}")
    print()
    print("  Instructions:")
    print("  - Read tasks from:", tasks_file)
    print("  - For each task, run with_skill and without_skill")
    print("  - Save outputs as: {task_id}_with_skill.md and {task_id}_without_skill.md")
    print("  - Max 4 concurrent subagents")
    print()
    print("  Press Ctrl+C to stop here and run comparisons manually.")
    print("  Re-run this script after comparisons are done to continue.")
    print()

    # Check if results already exist
    with_skill_files = list(results_dir.glob("*_with_skill.md"))
    if with_skill_files:
        print(f"  Found {len(with_skill_files)} with_skill output files")
    else:
        print(f"  No output files found yet. Run comparisons first.")
        print()
        print("  Waiting for results... (re-run this script after comparisons)")
        sys.exit(0)

    # --- Step 4: Score Outputs ---
    print()
    print("=" * 60)
    print("STEP 4: Score Outputs")
    print("=" * 60)

    if is_step_complete(results_dir, tasks_file) and not args.force:
        print(f"  [SKIP] Scoring already complete: {results_dir / 'benchmark_v2.json'}")
        print(f"         Use --force to rescore")
    else:
        success = run_script(
            "score_outputs_v2.py",
            [
                "--results-dir", str(results_dir),
                "--tasks-file", str(tasks_file),
                "--output-dir", str(results_dir),
            ],
            "Scoring outputs"
        )
        if not success:
            print()
            print("ERROR: Scoring failed. Stopping pipeline.")
            sys.exit(1)

    # Quality gate: check mean delta
    delta = read_benchmark_delta(results_dir)
    if delta is not None:
        print()
        if delta <= 0:
            print(f"  WARNING: Mean composite delta is {delta:+.3f} (non-positive)")
            print(f"  The skill may not be improving outputs on average.")
            print(f"  DPO training may not produce useful pairs.")
            print()
            response = input("  Continue anyway? [y/N] ").strip().lower()
            if response != "y":
                print("  Pipeline stopped by user.")
                sys.exit(0)
        else:
            print(f"  Quality gate PASSED: mean delta = {delta:+.3f}")

    # --- Step 5: Generate DPO Pairs ---
    print()
    print("=" * 60)
    print("STEP 5: Generate DPO Pairs")
    print("=" * 60)

    if is_dpo_complete(dpo_dir) and not args.force:
        print(f"  [SKIP] DPO pairs already generated: {dpo_dir / 'quality_summary_v2.json'}")
        print(f"         Use --force to regenerate")
    else:
        success = run_script(
            "generate_dpo_v2.py",
            [
                "--results-dir", str(results_dir),
                "--tasks-file", str(tasks_file),
                "--output-dir", str(dpo_dir),
            ],
            "Generating DPO pairs"
        )
        if not success:
            print()
            print("ERROR: DPO generation failed. Stopping pipeline.")
            sys.exit(1)

    # Quality gate: check pair count
    pair_count = read_dpo_pair_count(dpo_dir)
    if pair_count is not None:
        if pair_count == 0:
            print()
            print("  ERROR: 0 DPO training pairs generated.")
            print("  Cannot proceed with training.")
            print("  Check quality filters or re-run comparisons with better outputs.")
            sys.exit(1)
        else:
            print(f"  Quality gate PASSED: {pair_count} training pairs")

    # --- Step 6: Fine-tune ---
    print()
    print("=" * 60)
    print("STEP 6: Fine-tune")
    print("=" * 60)

    if args.skip_training:
        print("  [SKIP] Training skipped (--skip-training flag)")
    elif is_training_complete(models_dir) and not args.force:
        print(f"  [SKIP] Model already trained: {models_dir}")
        print(f"         Use --force to retrain")
    else:
        dpo_format_file = dpo_dir / "dpo_format_v2.json"
        if not dpo_format_file.exists():
            print(f"  ERROR: DPO format file not found: {dpo_format_file}")
            print(f"  Run DPO generation first.")
            sys.exit(1)

        success = run_script(
            "train_dpo.py",
            [
                "--data-file", str(dpo_format_file),
                "--output-dir", str(models_dir),
            ],
            "Fine-tuning model"
        )
        if not success:
            print()
            print("ERROR: Training failed. Stopping pipeline.")
            sys.exit(1)

    # --- Step 7: Generate Report ---
    print()
    print("=" * 60)
    print("STEP 7: Generate Report")
    print("=" * 60)

    report_path = generate_report(
        skill_name, skill_path, results_dir, dpo_dir, models_dir, analysis_dir
    )
    print(f"  Report saved: {report_path}")

    # --- Final Summary ---
    print()
    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print()
    print(f"Skill: {skill_name}")
    print()
    print("Files produced:")

    check_file(tasks_file, "Tasks")
    check_file(results_dir / "benchmark_v2.json", "Benchmark")
    check_file(results_dir / "task_deltas_v2.json", "Task deltas")
    check_file(dpo_dir / "dpo_format_v2.json", "DPO format")
    check_file(dpo_dir / "quality_summary_v2.json", "DPO summary")
    check_file(models_dir / "adapter_config.json", "Model adapter")
    check_file(report_path, "Report")

    print()
    print("Directory structure:")
    print(f"  pipeline/evals/{skill_name}/")
    print(f"  pipeline/results/{skill_name}/")
    print(f"  pipeline/dpo-data/{skill_name}/")
    print(f"  pipeline/models/{skill_name}/")
    print(f"  pipeline/analysis/{skill_name}/")


if __name__ == "__main__":
    main()
