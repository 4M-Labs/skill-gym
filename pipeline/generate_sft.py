#!/usr/bin/env python3
"""
Generate SFT training data from SkillGym with_skill outputs.

SFT (Supervised Fine-Tuning) trains the model on "what good looks like"
without needing contrastive pairs. Simpler than DPO, works better with
small datasets.

For each task:
  - System message: the skill content (instructions + verification criteria)
  - User message: the task prompt
  - Assistant message: the with_skill output (the "good" output)

Output: sft_format.json compatible with SFTTrainer from trl.
"""

import argparse
import json
from pathlib import Path


def load_tasks(tasks_file):
    with open(tasks_file) as f:
        return json.load(f)["tasks"]


def load_skill(skill_path):
    """Load skill content from markdown file."""
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""


def build_system_message(skill_content, task):
    """Build system message with skill instructions + verification criteria."""
    parts = []

    if skill_content:
        parts.append(f"## Skill Instructions\n\n{skill_content}")

    criteria = task.get("verification_criteria", [])
    if criteria:
        criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
        parts.append(f"## Verification Criteria\n\nYour output MUST satisfy ALL of the following:\n\n{criteria_text}")

    return "\n\n---\n\n".join(parts) if parts else "You are a helpful marketing assistant."


def generate_sft_data(tasks, results_dir, skills_dir, output_file):
    """Generate SFT training data from with_skill outputs."""
    sft_data = []
    stats = {"total": 0, "found": 0, "missing": 0, "by_skill": {}}

    # Load skills
    skills = {}
    for skill_file in skills_dir.glob("*.md"):
        skill_name = skill_file.stem
        skills[skill_name] = load_skill(skill_file)

    for task in tasks:
        task_id = task["id"]
        skill_name = task["skill"]
        prompt = task["prompt"]

        # Find the with_skill output
        output_path = results_dir / f"{task_id}_with_skill.md"

        stats["total"] += 1

        if not output_path.exists():
            stats["missing"] += 1
            print(f"  MISSING: {task_id}_with_skill.md")
            continue

        output_content = output_path.read_text(encoding="utf-8")
        skill_content = skills.get(skill_name, "")

        # Build the SFT example
        system_message = build_system_message(skill_content, task)

        sft_entry = {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": output_content},
            ],
            "task_id": task_id,
            "skill": skill_name,
        }

        sft_data.append(sft_entry)
        stats["found"] += 1

        if skill_name not in stats["by_skill"]:
            stats["by_skill"][skill_name] = {"found": 0, "missing": 0}
        stats["by_skill"][skill_name]["found"] += 1

    # Save
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sft_data, f, indent=2, ensure_ascii=False)

    # Also save stats
    stats_file = output_file.parent / "sft_generation_stats.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\nSFT Data Generation Complete")
    print(f"  Total tasks: {stats['total']}")
    print(f"  Found outputs: {stats['found']}")
    print(f"  Missing outputs: {stats['missing']}")
    for skill, counts in stats["by_skill"].items():
        print(f"  {skill}: {counts['found']} found, {counts['missing']} missing")
    print(f"  Output: {output_file}")

    return sft_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate SFT training data from SkillGym with_skill outputs"
    )
    parser.add_argument(
        "--tasks-file",
        type=Path,
        default=Path(__file__).parent / "evals" / "tasks.json",
        help="Path to tasks.json",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Directory containing with_skill output files",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path(__file__).parent / "skills",
        help="Directory containing skill markdown files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(__file__).parent / "sft-data" / "sft_format.json",
        help="Output file for SFT training data",
    )
    args = parser.parse_args()

    tasks = load_tasks(args.tasks_file)
    generate_sft_data(tasks, args.results_dir, args.skills_dir, args.output_file)
