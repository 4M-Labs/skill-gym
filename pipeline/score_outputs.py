#!/usr/bin/env python3
"""
Score all pipeline outputs against verification criteria from tasks.json.
Reads each with_skill and without_skill file, compares against criteria,
and generates grading.json for each pair + aggregated benchmark.json.
"""

import json
import os
import re
from pathlib import Path

RESULTS_DIR = Path("results/iteration-1")
TASKS_FILE = Path("evals/tasks.json")

def load_tasks():
    with open(TASKS_FILE) as f:
        data = json.load(f)
    return data["tasks"]

def read_file(path):
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def check_criterion(text, criterion):
    """Check if a criterion is met in the text. Returns (passed, evidence)."""
    text_lower = text.lower()
    crit_lower = criterion.lower()
    
    # Word count check
    if "under" in crit_lower and "words" in crit_lower:
        numbers = re.findall(r'(\d+)\s*words', crit_lower)
        if numbers:
            limit = int(numbers[0])
            word_count = len(text.split())
            passed = word_count <= limit
            return passed, f"Word count: {word_count} (limit: {limit})"
    
    if "over" in crit_lower and "words" in crit_lower:
        numbers = re.findall(r'(\d+)\s*words', crit_lower)
        if numbers:
            limit = int(numbers[0])
            word_count = len(text.split())
            passed = word_count >= limit
            return passed, f"Word count: {word_count} (minimum: {limit})"
    
    # Negative checks (should NOT contain)
    if "no " in crit_lower[:3] or "not " in crit_lower[:4] or "absent" in crit_lower:
        # Check for banned phrases
        banned = [
            "i hope this email finds you well",
            "i came across your profile",
            "i noticed your",
            "leverage", "synergy", "best-in-class", "leading provider",
            "circle back", "just checking in", "just following up",
            "my name is", "i work at",
            "utilize", "facilitate", "streamline", "optimize",
            "innovative", "cutting-edge", "next-generation",
            "revolutionize", "transform"
        ]
        for phrase in banned:
            if phrase in text_lower:
                return False, f"Contains banned phrase: '{phrase}'"
        # If we get here, no banned phrases found
        if "no exclamation" in crit_lower:
            if "!" in text:
                return False, "Contains exclamation points"
        return True, "No banned phrases found"
    
    # Positive checks (should contain)
    if "subject line" in crit_lower and ("2-4 words" in crit_lower or "lowercase" in crit_lower):
        lines = text.strip().split("\n")
        subject = ""
        for line in lines:
            if line.lower().startswith("subject"):
                subject = line.split(":", 1)[-1].strip() if ":" in line else ""
                break
        if not subject and lines:
            subject = lines[0]
        words = subject.split()
        is_lower = subject == subject.lower()
        has_2_to_4 = 2 <= len(words) <= 4
        passed = is_lower and has_2_to_4
        return passed, f"Subject: '{subject}' ({len(words)} words, lowercase={is_lower})"
    
    if "contractions" in crit_lower:
        contractions = ["don't", "won't", "can't", "it's", "we're", "you're", "they're", "i'm", "isn't", "doesn't", "haven't", "hasn't"]
        found = [c for c in contractions if c in text_lower]
        passed = len(found) >= 2
        return passed, f"Contractions found: {found[:5]}"
    
    if "you/your" in crit_lower or "you your" in crit_lower:
        you_count = len(re.findall(r'\byou\b|\byour\b|\byours\b', text_lower))
        i_count = len(re.findall(r'\bi\b|\bwe\b|\bour\b|\bus\b', text_lower))
        passed = you_count > i_count
        return passed, f"you/your: {you_count}, I/we/our: {i_count}"
    
    if "annotations" in crit_lower or "explain" in crit_lower:
        has_annotations = "annotation" in text_lower or "why" in text_lower or "rationale" in text_lower
        return has_annotations, "Has explanations/annotations" if has_annotations else "Missing annotations"
    
    if "alternatives" in crit_lower or "alternative" in crit_lower:
        has_alt = "alternative" in text_lower or "option 2" in text_lower or "headline 2" in text_lower or "variation" in text_lower
        return has_alt, "Has alternatives" if has_alt else "Missing alternatives"
    
    if "cta" in crit_lower and ("unique" in crit_lower or "different" in crit_lower):
        # Check for variety in CTAs
        cta_words = re.findall(r'(?:start|get|try|see|find|download|claim|unlock|access|begin)\s+\w+', text_lower)
        passed = len(set(cta_words)) >= 3
        return passed, f"Unique CTAs found: {len(set(cta_words))}"
    
    # Generic containment check
    # Try to extract key terms from the criterion
    key_terms = [w for w in crit_lower.split() if len(w) > 4 and w not in ["should", "must", "contains", "includes", "checks", "verify"]]
    if key_terms:
        found_terms = [t for t in key_terms if t in text_lower]
        coverage = len(found_terms) / len(key_terms) if key_terms else 0
        passed = coverage >= 0.5
        return passed, f"Term coverage: {coverage:.0%} ({len(found_terms)}/{len(key_terms)})"
    
    return True, "Criterion checked (default pass)"

def score_task(task, text_with, text_without):
    """Score a single task's with_skill and without_skill outputs."""
    criteria = task.get("verification_criteria", [])
    
    with_grades = []
    without_grades = []
    
    for criterion in criteria:
        w_pass, w_evidence = check_criterion(text_with, criterion)
        wo_pass, wo_evidence = check_criterion(text_without, criterion)
        
        with_grades.append({
            "text": criterion,
            "passed": w_pass,
            "evidence": w_evidence
        })
        without_grades.append({
            "text": criterion,
            "passed": wo_pass,
            "evidence": wo_evidence
        })
    
    with_pass_rate = sum(1 for g in with_grades if g["passed"]) / len(with_grades) if with_grades else 0
    without_pass_rate = sum(1 for g in without_grades if g["passed"]) / len(without_grades) if without_grades else 0
    
    return {
        "with_skill": {
            "grades": with_grades,
            "pass_rate": with_pass_rate,
            "passed_count": sum(1 for g in with_grades if g["passed"]),
            "total_count": len(with_grades)
        },
        "without_skill": {
            "grades": without_grades,
            "pass_rate": without_pass_rate,
            "passed_count": sum(1 for g in without_grades if g["passed"]),
            "total_count": len(without_grades)
        },
        "delta": with_pass_rate - without_pass_rate
    }

def main():
    tasks = load_tasks()
    results = {}
    
    for task in tasks:
        task_id = task["id"]
        skill = task["skill"]
        
        with_path = RESULTS_DIR / f"{task_id}_with_skill.md"
        without_path = RESULTS_DIR / f"{task_id}_without_skill.md"
        
        text_with = read_file(with_path)
        text_without = read_file(without_path)
        
        if not text_with or not text_without:
            print(f"SKIP {task_id}: missing files")
            continue
        
        scoring = score_task(task, text_with, text_without)
        
        # Save individual grading
        grading_dir = RESULTS_DIR / task_id
        grading_dir.mkdir(exist_ok=True)
        
        with_grading = {
            "eval_id": task_id,
            "run_id": f"{task_id}_with_skill",
            "expectations": with_grades_to_expectations(scoring["with_skill"]["grades"]),
            "pass_rate": scoring["with_skill"]["pass_rate"]
        }
        
        without_grading = {
            "eval_id": task_id,
            "run_id": f"{task_id}_without_skill",
            "expectations": with_grades_to_expectations(scoring["without_skill"]["grades"]),
            "pass_rate": scoring["without_skill"]["pass_rate"]
        }
        
        (grading_dir / "grading_with_skill.json").write_text(json.dumps(with_grading, indent=2))
        (grading_dir / "grading_without_skill.json").write_text(json.dumps(without_grading, indent=2))
        
        results[task_id] = {
            "skill": skill,
            "with_skill_pass_rate": scoring["with_skill"]["pass_rate"],
            "without_skill_pass_rate": scoring["without_skill"]["pass_rate"],
            "delta": scoring["delta"]
        }
        
        print(f"{task_id}: with={scoring['with_skill']['pass_rate']:.0%} without={scoring['without_skill']['pass_rate']:.0%} delta={scoring['delta']:+.0%}")
    
    # Aggregate by skill
    skills = {}
    for task_id, r in results.items():
        skill = r["skill"]
        if skill not in skills:
            skills[skill] = {"with_rates": [], "without_rates": [], "deltas": []}
        skills[skill]["with_rates"].append(r["with_skill_pass_rate"])
        skills[skill]["without_rates"].append(r["without_skill_pass_rate"])
        skills[skill]["deltas"].append(r["delta"])
    
    import statistics
    
    benchmark = {
        "overall": {
            "with_skill_mean": statistics.mean([r["with_skill_pass_rate"] for r in results.values()]),
            "without_skill_mean": statistics.mean([r["without_skill_pass_rate"] for r in results.values()]),
            "delta_mean": statistics.mean([r["delta"] for r in results.values()]),
            "task_count": len(results)
        },
        "by_skill": {},
        "per_task": results
    }
    
    for skill, data in skills.items():
        benchmark["by_skill"][skill] = {
            "with_skill_mean": statistics.mean(data["with_rates"]),
            "without_skill_mean": statistics.mean(data["without_rates"]),
            "delta_mean": statistics.mean(data["deltas"]),
            "task_count": len(data["with_rates"])
        }
    
    # Save benchmark
    benchmark_path = RESULTS_DIR / "benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark, indent=2))
    
    # Print summary
    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Overall: with={benchmark['overall']['with_skill_mean']:.0%} without={benchmark['overall']['without_skill_mean']:.0%} delta={benchmark['overall']['delta_mean']:+.0%}")
    for skill, data in benchmark["by_skill"].items():
        print(f"  {skill}: with={data['with_skill_mean']:.0%} without={data['without_skill_mean']:.0%} delta={data['delta_mean']:+.0%}")

def with_grades_to_expectations(grades):
    return [{"text": g["text"], "passed": g["passed"], "evidence": g["evidence"]} for g in grades]

if __name__ == "__main__":
    main()
