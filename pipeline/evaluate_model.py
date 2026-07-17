#!/usr/bin/env python3
"""
Model Evaluation Script for SkillGym.

Runs both the base model and the DPO-trained model on eval tasks,
scores all outputs, and produces a comparison report.

This is the real experiment: does RL (DPO) training actually improve the model?

DPO = Direct Preference Optimization (RL method)
- Trained on preference pairs: (prompt, chosen, rejected)
- Chosen = with-skill output, Rejected = without-skill output
- Model learns to prefer skill-guided outputs over unguided ones
"""

import argparse
import json
import os
import re
import sys
import time
import warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

import torch
from pathlib import Path
from datetime import datetime

# Import scoring functions from score_outputs_v2
sys.path.insert(0, str(Path(__file__).parent))
from score_outputs_v2 import (
    compute_criteria_pass_rate,
    compute_specificity,
    compute_actionability,
    compute_structure,
    compute_depth,
    compute_voice,
    count_words,
    WEIGHTS,
    BANNED_PHRASES,
)


def load_tasks(tasks_file):
    with open(tasks_file) as f:
        return json.load(f)["tasks"]


def load_model(model_name, adapter_path=None, device="cuda"):
    """Load a HuggingFace model + tokenizer, optionally with LoRA adapter."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    print(f"Loading model: {model_name}")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        dtype=torch.float16,
    )
    if adapter_path:
        model = PeftModel.from_pretrained(base_model, adapter_path)
        print(f"Loaded DPO adapter from: {adapter_path}")
    else:
        model = base_model
        print("Loaded base model (no RL adapter)")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


def generate_response(model, tokenizer, prompt, max_new_tokens=1024, temperature=0.7):
    """Generate a response from the model."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Complete the task thoroughly and precisely."},
        {"role": "user", "content": prompt},
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=1024).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    # Decode only the new tokens
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return response.strip()


def score_output(text, task):
    """Score a single output across all 6 dimensions."""
    criteria = task.get("verification_criteria", [])

    criteria_rate, criteria_grades = compute_criteria_pass_rate(text, criteria)
    specificity = compute_specificity(text, task)
    actionability = compute_actionability(text, task)
    structure = compute_structure(text, task)
    depth = compute_depth(text, task)
    voice = compute_voice(text, task)

    composite = (
        criteria_rate * WEIGHTS["criteria_pass_rate"]
        + specificity * WEIGHTS["specificity"]
        + actionability * WEIGHTS["actionability"]
        + structure * WEIGHTS["structure"]
        + depth * WEIGHTS["depth"]
        + voice * WEIGHTS["voice"]
    )

    return {
        "criteria_pass_rate": criteria_rate,
        "specificity": specificity,
        "actionability": actionability,
        "structure": structure,
        "depth": depth,
        "voice": voice,
        "composite": composite,
        "criteria_grades": criteria_grades,
        "word_count": count_words(text),
    }


def run_evaluation(model, tokenizer, tasks, model_name, output_dir, max_new_tokens=1024):
    """Run model on all tasks and score outputs. Skips tasks already completed."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    skipped = 0
    for i, task in enumerate(tasks):
        task_id = task["id"]

        # Resume: skip if scores file already exists
        scores_file = output_dir / f"{task_id}_scores.json"
        if scores_file.exists():
            try:
                existing = json.loads(scores_file.read_text(encoding="utf-8"))
                output_file = output_dir / f"{task_id}_output.md"
                results.append({
                    "task_id": task_id,
                    "skill": task["skill"],
                    "scores": existing,
                    "gen_time_seconds": 0,
                    "output_file": str(output_file),
                })
                skipped += 1
                continue
            except (json.JSONDecodeError, KeyError):
                pass

        prompt = task["prompt"]

        print(f"  [{i+1}/{len(tasks)}] {task_id}...", end=" ", flush=True)

        start_time = time.time()
        response = generate_response(model, tokenizer, prompt, max_new_tokens=max_new_tokens)
        gen_time = time.time() - start_time

        if not response:
            print("EMPTY - skipping")
            continue

        scores = score_output(response, task)

        # Save output
        output_file = output_dir / f"{task_id}_output.md"
        header = f"# Task: {task_id}\n# Model: {model_name}\n\n---\n\n"
        output_file.write_text(header + response, encoding="utf-8")

        # Save scores
        scores_file.write_text(json.dumps(scores, indent=2), encoding="utf-8")

        results.append({
            "task_id": task_id,
            "skill": task["skill"],
            "scores": scores,
            "gen_time_seconds": gen_time,
            "output_file": str(output_file),
        })

        print(f"composite={scores['composite']:.3f} ({gen_time:.1f}s)")

    if skipped:
        print(f"  (Resumed {skipped} completed tasks)")

    return results


def compare_results(base_results, ft_results):
    """Compare base model vs fine-tuned model results."""
    comparison = {
        "base": {},
        "fine_tuned": {},
        "deltas": {},
        "per_task": [],
        "per_skill": {},
    }

    # Aggregate by dimension
    dimensions = ["criteria_pass_rate", "specificity", "actionability", "structure", "depth", "voice", "composite"]

    for dim in dimensions:
        base_vals = [r["scores"][dim] for r in base_results]
        ft_vals = [r["scores"][dim] for r in ft_results]

        comparison["base"][dim] = {
            "mean": sum(base_vals) / len(base_vals) if base_vals else 0,
            "min": min(base_vals) if base_vals else 0,
            "max": max(base_vals) if base_vals else 0,
        }
        comparison["fine_tuned"][dim] = {
            "mean": sum(ft_vals) / len(ft_vals) if ft_vals else 0,
            "min": min(ft_vals) if ft_vals else 0,
            "max": max(ft_vals) if ft_vals else 0,
        }
        comparison["deltas"][dim] = comparison["fine_tuned"][dim]["mean"] - comparison["base"][dim]["mean"]

    # Per-task comparison
    base_by_id = {r["task_id"]: r for r in base_results}
    ft_by_id = {r["task_id"]: r for r in ft_results}

    for task_id in base_by_id:
        if task_id in ft_by_id:
            base_r = base_by_id[task_id]
            ft_r = ft_by_id[task_id]
            task_delta = ft_r["scores"]["composite"] - base_r["scores"]["composite"]
            comparison["per_task"].append({
                "task_id": task_id,
                "skill": base_r["skill"],
                "base_composite": base_r["scores"]["composite"],
                "ft_composite": ft_r["scores"]["composite"],
                "delta": task_delta,
                "base_time": base_r["gen_time_seconds"],
                "ft_time": ft_r["gen_time_seconds"],
            })

    # Per-skill aggregation
    skills = set(r["skill"] for r in base_results)
    for skill in skills:
        base_skill = [r for r in base_results if r["skill"] == skill]
        ft_skill = [r for r in ft_results if r["skill"] == skill]

        base_composites = [r["scores"]["composite"] for r in base_skill]
        ft_composites = [r["scores"]["composite"] for r in ft_skill]

        comparison["per_skill"][skill] = {
            "base_mean": sum(base_composites) / len(base_composites) if base_composites else 0,
            "ft_mean": sum(ft_composites) / len(ft_composites) if ft_composites else 0,
            "delta": (sum(ft_composites) / len(ft_composites) if ft_composites else 0) - (sum(base_composites) / len(base_composites) if base_composites else 0),
            "n_tasks": len(base_skill),
            "positive_deltas": sum(1 for b, f in zip(base_composites, ft_composites) if f > b),
        }

    # Overall metrics
    all_base = [r["scores"]["composite"] for r in base_results]
    all_ft = [r["scores"]["composite"] for r in ft_results]
    comparison["overall"] = {
        "base_mean": sum(all_base) / len(all_base) if all_base else 0,
        "ft_mean": sum(all_ft) / len(all_ft) if all_ft else 0,
        "delta": (sum(all_ft) / len(all_ft) if all_ft else 0) - (sum(all_base) / len(all_base) if all_base else 0),
        "base_total_time": sum(r["gen_time_seconds"] for r in base_results),
        "ft_total_time": sum(r["gen_time_seconds"] for r in ft_results),
        "n_tasks": len(base_results),
        "positive_deltas": sum(1 for b, f in zip(all_base, all_ft) if f > b),
        "negative_deltas": sum(1 for b, f in zip(all_base, all_ft) if f < b),
        "neutral_deltas": sum(1 for b, f in zip(all_base, all_ft) if f == b),
    }

    return comparison


def generate_report(comparison, model_name, adapter_path, output_dir):
    """Generate a markdown comparison report."""
    report_dir = Path(output_dir) / "analysis"
    report_dir.mkdir(parents=True, exist_ok=True)

    o = comparison["overall"]
    dims = comparison["deltas"]

    report = f"""# SkillGym Model Evaluation Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Base model:** {model_name}
**Fine-tuned model:** {model_name} + {adapter_path or 'N/A'}
**Tasks evaluated:** {o['n_tasks']}

## Overall Results

| Metric | Base Model | Fine-Tuned | Delta |
|--------|-----------|------------|-------|
| **Composite Score** | {o['base_mean']:.3f} | {o['ft_mean']:.3f} | **{o['delta']:+.3f}** |
| Positive deltas | - | - | {o['positive_deltas']}/{o['n_tasks']} tasks |
| Negative deltas | - | - | {o['negative_deltas']}/{o['n_tasks']} tasks |
| Neutral deltas | - | - | {o['neutral_deltas']}/{o['n_tasks']} tasks |
| Total generation time | {o['base_total_time']:.1f}s | {o['ft_total_time']:.1f}s | - |

## Per-Dimension Breakdown

| Dimension | Base | Fine-Tuned | Delta |
|-----------|------|------------|-------|
| Criteria Pass Rate (0.25) | {dims['criteria_pass_rate']:+.3f} | - | {dims['criteria_pass_rate']:+.3f} |
| Specificity (0.20) | {dims['specificity']:+.3f} | - | {dims['specificity']:+.3f} |
| Actionability (0.20) | {dims['actionability']:+.3f} | - | {dims['actionability']:+.3f} |
| Structure (0.15) | {dims['structure']:+.3f} | - | {dims['structure']:+.3f} |
| Depth (0.10) | {dims['depth']:+.3f} | - | {dims['depth']:+.3f} |
| Voice (0.10) | {dims['voice']:+.3f} | - | {dims['voice']:+.3f} |

## Per-Skill Breakdown

| Skill | Base | Fine-Tuned | Delta | Pos/Total |
|-------|------|------------|-------|-----------|
"""

    for skill, data in comparison["per_skill"].items():
        report += f"| {skill} | {data['base_mean']:.3f} | {data['ft_mean']:.3f} | {data['delta']:+.3f} | {data['positive_deltas']}/{data['n_tasks']} |\n"

    report += f"""
## Per-Task Results

| Task | Base | Fine-Tuned | Delta | Time (base) | Time (ft) |
|------|------|------------|-------|-------------|-----------|
"""

    for task in sorted(comparison["per_task"], key=lambda x: x["delta"], reverse=True):
        report += f"| {task['task_id']} | {task['base_composite']:.3f} | {task['ft_composite']:.3f} | {task['delta']:+.3f} | {task['base_time']:.1f}s | {task['ft_time']:.1f}s |\n"

    # Top improvements
    top_improved = sorted(comparison["per_task"], key=lambda x: x["delta"], reverse=True)[:5]
    report += f"""
## Top 5 Improvements

"""
    for t in top_improved:
        report += f"1. **{t['task_id']}** ({t['skill']}): {t['delta']:+.3f} delta ({t['base_composite']:.3f} -> {t['ft_composite']:.3f})\n"

    # Top regressions
    top_regressed = sorted(comparison["per_task"], key=lambda x: x["delta"])[:5]
    report += f"""
## Top 5 Regressions

"""
    for t in top_regressed:
        report += f"1. **{t['task_id']}** ({t['skill']}): {t['delta']:+.3f} delta ({t['base_composite']:.3f} -> {t['ft_composite']:.3f})\n"

    # Verdict
    delta = o['delta']
    if delta > 0.05:
        verdict = "STRONG IMPROVEMENT"
        explanation = "The fine-tuned model significantly outperforms the base model. DPO training was effective."
    elif delta > 0.02:
        verdict = "MODERATE IMPROVEMENT"
        explanation = "The fine-tuned model shows clear improvement. More training data or epochs could help."
    elif delta > 0:
        verdict = "MARGINAL IMPROVEMENT"
        explanation = "The fine-tuned model is slightly better. The signal may be too weak for reliable training."
    elif delta == 0:
        verdict = "NO CHANGE"
        explanation = "The fine-tuned model performs identically to the base. DPO training had no effect."
    else:
        verdict = "REGRESSION"
        explanation = "The fine-tuned model performs worse. The DPO data may be noisy or the training config needs adjustment."

    report += f"""
## Verdict

**{verdict}**

{explanation}

Overall delta: **{delta:+.3f}** ({o['positive_deltas']} tasks improved, {o['negative_deltas']} regressed, {o['neutral_deltas']} unchanged)

## Training Details

- Base model: {model_name}
- Adapter: {adapter_path or 'N/A'}
- DPO pairs used: 17 (from 3 skills: CRO, copywriting, cold-email)
- Training: 10 epochs, DPO beta=0.05, LoRA r=4 alpha=8, reference_free=True
- Final training loss: 11.82 (170 steps total)
- Training time: ~4 minutes
- Key fix: prompts now include VERIFICATION CRITERIA (v1 had none)
"""

    report_path = report_dir / "model-evaluation-report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Evaluate base vs fine-tuned model")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-1.5B-Instruct",
                        help="HuggingFace model name")
    parser.add_argument("--adapter-path", default=None,
                        help="Path to LoRA adapter (fine-tuned model)")
    parser.add_argument("--tasks-file", required=True,
                        help="Path to tasks.json")
    parser.add_argument("--output-dir", required=True,
                        help="Directory to save results")
    parser.add_argument("--max-new-tokens", type=int, default=1024,
                        help="Max new tokens to generate (default: 1024)")
    parser.add_argument("--max-tasks", type=int, default=None,
                        help="Max tasks to evaluate (for quick testing)")
    parser.add_argument("--skip-base", action="store_true",
                        help="Skip base model evaluation (use existing results)")
    parser.add_argument("--skip-ft", action="store_true",
                        help="Skip fine-tuned model evaluation (use existing results)")
    args = parser.parse_args()

    tasks = load_tasks(args.tasks_file)
    if args.max_tasks:
        tasks = tasks[:args.max_tasks]

    output_dir = Path(args.output_dir)
    base_dir = output_dir / "base_model"
    rl_dir = output_dir / "rl_trained_model"

    # Run base model evaluation
    if not args.skip_base:
        print("\n=== Evaluating BASE MODEL ===")
        base_model, tokenizer = load_model(args.model_name, adapter_path=None)
        base_results = run_evaluation(base_model, tokenizer, tasks, "base", base_dir, max_new_tokens=args.max_new_tokens)

        # Save raw results
        (output_dir / "base_results.json").write_text(
            json.dumps(base_results, indent=2), encoding="utf-8"
        )

        # Free memory
        del base_model
        torch.cuda.empty_cache()
    else:
        print("\n=== Loading existing BASE results ===")
        base_results = json.loads((output_dir / "base_results.json").read_text(encoding="utf-8"))

    # Run DPO-trained model evaluation
    if not args.skip_ft:
        print("\n=== Evaluating DPO-TRAINED MODEL ===")
        rl_model, tokenizer = load_model(args.model_name, adapter_path=args.adapter_path)
        rl_results = run_evaluation(rl_model, tokenizer, tasks, "dpo_trained", rl_dir, max_new_tokens=args.max_new_tokens)

        # Save raw results
        (output_dir / "rl_results.json").write_text(
            json.dumps(rl_results, indent=2), encoding="utf-8"
        )

        # Free memory
        del rl_model
        torch.cuda.empty_cache()
    else:
        print("\n=== Loading existing DPO-TRAINED results ===")
        rl_results = json.loads((output_dir / "rl_results.json").read_text(encoding="utf-8"))

    # Compare and generate report
    print("\n=== Comparing Results ===")
    comparison = compare_results(base_results, rl_results)

    # Save comparison
    (output_dir / "comparison.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )

    # Generate report
    report_path = generate_report(comparison, args.model_name, args.adapter_path, output_dir)

    # Print summary
    o = comparison["overall"]
    print(f"\n{'='*50}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*50}")
    print(f"Base model composite:    {o['base_mean']:.3f}")
    print(f"Fine-tuned composite:    {o['ft_mean']:.3f}")
    print(f"Delta:                   {o['delta']:+.3f}")
    print(f"Tasks improved:          {o['positive_deltas']}/{o['n_tasks']}")
    print(f"Tasks regressed:         {o['negative_deltas']}/{o['n_tasks']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
