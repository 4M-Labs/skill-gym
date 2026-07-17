#!/usr/bin/env python3
"""
Generate DPO training pairs from pipeline results.

KEY FIX: Includes verification criteria in the prompt so the model
learns to satisfy specific criteria, not just generate longer text.

The old generate_dpo_v2.py was broken because it used raw task prompts
without verification criteria. The model learned "longer = better" instead
of "satisfies criteria = better".

This version:
1. Loads task verification criteria from tasks.json
2. Includes criteria in the DPO prompt
3. Uses multi-dimensional scoring (composite) for pair selection
4. Applies quality filters (min delta, min chosen score, etc.)
"""

import argparse
import json
import hashlib
from pathlib import Path
from datetime import datetime


# --- Quality Thresholds ---
MIN_DELTA = 0.05           # with_skill must beat without_skill by at least this much
MIN_CHOSEN_COMPOSITE = 0.3 # chosen must score at least 0.3 overall
MAX_REJECTED_COMPOSITE = 0.7  # rejected should not already be too good
MIN_SPECIFICITY_DELTA = -0.1  # chosen should not be much less specific
MIN_WORD_COUNT = 30         # reject very short outputs


def load_tasks(tasks_file):
    with open(tasks_file) as f:
        return json.load(f)["tasks"]


def load_v2_grading(grading_dir, suffix):
    """Load grading results from score_outputs_v2."""
    path = grading_dir / f"grading_{suffix}_v2.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def prompt_hash(prompt):
    """Hash prompt for deduplication."""
    return hashlib.md5(prompt.encode()).hexdigest()[:12]


def build_prompt_with_criteria(task):
    """
    Build the DPO prompt including verification criteria.
    
    This is the critical fix: the model needs to know WHAT to satisfy.
    Without criteria, it learns to generate longer text.
    With criteria, it learns to satisfy specific requirements.
    """
    base_prompt = task["prompt"]
    criteria = task.get("verification_criteria", [])
    
    if not criteria:
        return base_prompt
    
    criteria_text = "\n\nVERIFICATION CRITERIA:\n"
    for i, c in enumerate(criteria, 1):
        criteria_text += f"{i}. {c}\n"
    
    return base_prompt + criteria_text


def main(results_dir, tasks_file, output_dir):
    output_dir.mkdir(exist_ok=True)
    tasks = load_tasks(tasks_file)
    
    # Build task lookup by ID
    tasks_map = {t["id"]: t for t in tasks}
    
    # Load deltas if available
    deltas_path = results_dir / "task_deltas_v2.json"
    if deltas_path.exists():
        deltas_data = json.loads(deltas_path.read_text())
        deltas_map = {d["task_id"]: d for d in deltas_data}
    else:
        deltas_map = {}
    
    training_pairs = []
    skipped = {"no_grading": 0, "below_min_delta": 0, "chosen_too_low": 0,
               "rejected_too_high": 0, "specificity_issue": 0, "too_short": 0,
               "duplicate_prompt": 0}
    
    seen_prompts = set()
    
    for task in tasks:
        task_id = task["id"]
        skill = task["skill"]
        
        grading_dir = results_dir / task_id
        with_grading = load_v2_grading(grading_dir, "with_skill")
        without_grading = load_v2_grading(grading_dir, "without_skill")
        
        if not with_grading or not without_grading:
            skipped["no_grading"] += 1
            continue
        
        with_scores = with_grading.get("scores", {})
        without_scores = without_grading.get("scores", {})
        
        with_composite = with_scores.get("composite", 0)
        without_composite = without_scores.get("composite", 0)
        delta = with_composite - without_composite
        
        # Filter 1: Minimum delta
        if delta < MIN_DELTA:
            skipped["below_min_delta"] += 1
            continue
        
        # Filter 2: Chosen must be good enough
        if with_composite < MIN_CHOSEN_COMPOSITE:
            skipped["chosen_too_low"] += 1
            continue
        
        # Filter 3: Rejected should not already be great
        if without_composite > MAX_REJECTED_COMPOSITE:
            skipped["rejected_too_high"] += 1
            continue
        
        # Filter 4: Specificity should not be worse with skill
        specificity_delta = with_scores.get("specificity", 0) - without_scores.get("specificity", 0)
        if specificity_delta < MIN_SPECIFICITY_DELTA:
            skipped["specificity_issue"] += 1
            continue
        
        # Filter 5: Minimum word count for both
        with_wc = with_grading.get("scores", {}).get("word_count", 0)
        without_wc = without_grading.get("scores", {}).get("word_count", 0)
        if with_wc < MIN_WORD_COUNT or without_wc < MIN_WORD_COUNT:
            skipped["too_short"] += 1
            continue
        
        # Filter 6: Dedup by prompt
        ph = prompt_hash(task["prompt"])
        if ph in seen_prompts:
            skipped["duplicate_prompt"] += 1
            continue
        seen_prompts.add(ph)
        
        # Read the actual output files
        with_path = results_dir / f"{task_id}_with_skill.md"
        without_path = results_dir / f"{task_id}_without_skill.md"
        
        if not with_path.exists() or not without_path.exists():
            continue
        
        with_text = with_path.read_text(encoding="utf-8")
        without_text = without_path.read_text(encoding="utf-8")
        
        # Build prompt WITH verification criteria
        prompt_with_criteria = build_prompt_with_criteria(task)
        
        training_pairs.append({
            "skill": skill,
            "task_id": task_id,
            "raw_prompt": task["prompt"],
            "prompt_with_criteria": prompt_with_criteria,
            "chosen": with_text,
            "rejected": without_text,
            "chosen_score": with_composite,
            "rejected_score": without_composite,
            "delta": delta,
            "criteria_count": len(task.get("verification_criteria", []))
        })
    
    # Sort by delta (biggest improvements first)
    training_pairs.sort(key=lambda x: x["delta"], reverse=True)
    
    # Save full training data (for analysis)
    full_path = output_dir / "dpo_training_pairs.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(training_pairs, f, indent=2, ensure_ascii=False)
    
    # Save DPO-formatted data (with verification criteria in prompt)
    dpo_format = []
    for pair in training_pairs:
        dpo_format.append({
            "messages": [
                {"role": "user", "content": pair["prompt_with_criteria"]},
                {"role": "assistant", "content": pair["chosen"]}
            ],
            "rejected_messages": [
                {"role": "user", "content": pair["prompt_with_criteria"]},
                {"role": "assistant", "content": pair["rejected"]}
            ]
        })
    
    dpo_path = output_dir / "dpo_format.json"
    with open(dpo_path, "w", encoding="utf-8") as f:
        json.dump(dpo_format, f, indent=2, ensure_ascii=False)
    
    # Quality summary
    quality = {
        "generated_at": datetime.now().isoformat(),
        "fix_applied": "verification_criteria_included_in_prompt",
        "filters": {
            "min_delta": MIN_DELTA,
            "min_chosen_composite": MIN_CHOSEN_COMPOSITE,
            "max_rejected_composite": MAX_REJECTED_COMPOSITE,
            "min_specificity_delta": MIN_SPECIFICITY_DELTA,
            "min_word_count": MIN_WORD_COUNT
        },
        "total_pairs": len(training_pairs),
        "total_skipped": sum(skipped.values()),
        "skip_reasons": skipped,
        "by_skill": {},
        "quality_stats": {
            "avg_delta": sum(p["delta"] for p in training_pairs) / max(len(training_pairs), 1),
            "avg_chosen_score": sum(p["chosen_score"] for p in training_pairs) / max(len(training_pairs), 1),
            "avg_rejected_score": sum(p["rejected_score"] for p in training_pairs) / max(len(training_pairs), 1),
            "avg_criteria_count": sum(p["criteria_count"] for p in training_pairs) / max(len(training_pairs), 1)
        }
    }
    
    # Per-skill breakdown
    for pair in training_pairs:
        s = pair["skill"]
        if s not in quality["by_skill"]:
            quality["by_skill"][s] = {"count": 0, "avg_delta": 0, "avg_chosen": 0, "avg_rejected": 0}
        quality["by_skill"][s]["count"] += 1
        quality["by_skill"][s]["avg_delta"] += pair["delta"]
        quality["by_skill"][s]["avg_chosen"] += pair["chosen_score"]
        quality["by_skill"][s]["avg_rejected"] += pair["rejected_score"]
    
    for s in quality["by_skill"]:
        n = quality["by_skill"][s]["count"]
        quality["by_skill"][s]["avg_delta"] /= n
        quality["by_skill"][s]["avg_chosen"] /= n
        quality["by_skill"][s]["avg_rejected"] /= n
    
    quality_path = output_dir / "quality_summary.json"
    with open(quality_path, "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2)
    
    # Print summary
    print(f"=== DPO PAIR GENERATION (FIXED) ===")
    print(f"Fix applied: verification criteria included in prompt")
    print(f"Generated: {len(training_pairs)} pairs")
    print(f"Skipped: {sum(skipped.values())} total")
    for reason, count in skipped.items():
        if count > 0:
            print(f"  {reason}: {count}")
    
    print(f"\nQuality stats:")
    print(f"  Avg delta: {quality['quality_stats']['avg_delta']:+.3f}")
    print(f"  Avg chosen: {quality['quality_stats']['avg_chosen_score']:.3f}")
    print(f"  Avg rejected: {quality['quality_stats']['avg_rejected_score']:.3f}")
    print(f"  Avg criteria count: {quality['quality_stats']['avg_criteria_count']:.1f}")
    
    print(f"\nBy skill:")
    for s, data in quality["by_skill"].items():
        print(f"  {s}: {data['count']} pairs, avg delta={data['avg_delta']:+.3f}, chosen={data['avg_chosen']:.3f}, rejected={data['avg_rejected']:.3f}")
    
    print(f"\nSaved:")
    print(f"  Full data: {full_path}")
    print(f"  DPO format: {dpo_path}")
    print(f"  Quality summary: {quality_path}")
    
    # Show sample prompt
    if training_pairs:
        sample = training_pairs[0]
        print(f"\n=== SAMPLE PROMPT (with criteria) ===")
        print(sample["prompt_with_criteria"][:500])
        print("...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate DPO pairs with verification criteria")
    parser.add_argument("--results-dir", type=Path, required=True, help="Directory containing scored results")
    parser.add_argument("--tasks-file", type=Path, required=True, help="Path to tasks.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="Where to write DPO training data")
    args = parser.parse_args()
    
    main(args.results_dir, args.tasks_file, args.output_dir)
