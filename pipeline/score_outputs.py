#!/usr/bin/env python3
"""
V2 Scoring Pipeline for SkillGym.
Adds multi-dimensional quality scoring beyond binary criteria pass/fail.

Dimensions:
  1. Criteria Pass Rate (original, kept for compatibility)
  2. Specificity - concrete numbers, examples, named tools/brands
  3. Actionability - specific recommended changes, not vague advice
  4. Structure - follows requested format, scannable, organized
  5. Depth - word count, detail level, thoroughness
  6. Voice - matches requested tone, avoids banned patterns
  7. Insight Quality - goes beyond surface-level observations

Composite score = weighted average of all dimensions.
"""

import argparse
import json
import os
import re
import statistics
from pathlib import Path
from datetime import datetime

# --- Dimension Weights ---
WEIGHTS = {
    "criteria_pass_rate": 0.25,
    "specificity": 0.20,
    "actionability": 0.20,
    "structure": 0.15,
    "depth": 0.10,
    "voice": 0.10,
}

# --- Helpers ---

def load_tasks(tasks_file):
    with open(tasks_file) as f:
        return json.load(f)["tasks"]

def read_file(path):
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def count_words(text):
    return len(text.split())

def count_sentences(text):
    sentences = re.split(r'[.!?]+', text)
    return max(1, len([s for s in sentences if s.strip()]))

# --- Criteria Pass Rate (original logic, improved) ---

BANNED_PHRASES = [
    "i hope this email finds you well",
    "i came across your profile",
    "i noticed your",
    "i wanted to reach out",
    "i wanted to introduce",
    "leverage", "synergy", "best-in-class", "leading provider",
    "circle back", "just checking in", "just following up",
    "my name is", "i work at",
    "utilize", "facilitate", "streamline",
    "innovative", "cutting-edge", "next-generation",
    "revolutionize", "game-changing",
    "i hope this helps", "looking forward to hearing from you",
    "please don't hesitate to reach out",
    "at your earliest convenience",
]

def check_criterion(text, criterion):
    """Check if a criterion is met. Returns (passed, evidence)."""
    text_lower = text.lower()
    crit_lower = criterion.lower()

    # Word count checks
    if "under" in crit_lower and "words" in crit_lower:
        numbers = re.findall(r'(\d+)\s*words', crit_lower)
        if numbers:
            limit = int(numbers[0])
            wc = count_words(text)
            return wc <= limit, f"Word count: {wc} (limit: {limit})"

    if "over" in crit_lower and "words" in crit_lower:
        numbers = re.findall(r'(\d+)\s*words', crit_lower)
        if numbers:
            minimum = int(numbers[0])
            wc = count_words(text)
            return wc >= minimum, f"Word count: {wc} (min: {minimum})"

    # Negative checks
    if crit_lower.startswith("no ") or crit_lower.startswith("not ") or "absent" in crit_lower:
        for phrase in BANNED_PHRASES:
            if phrase in text_lower:
                return False, f"Banned phrase: '{phrase}'"
        if "no exclamation" in crit_lower:
            if "!" in text:
                return False, "Contains exclamation points"
        return True, "No banned phrases found"

    # Subject line checks
    if "subject line" in crit_lower:
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

    # Contractions check
    if "contractions" in crit_lower:
        contractions = ["don't", "won't", "can't", "it's", "we're", "you're", "they're",
                        "i'm", "isn't", "doesn't", "haven't", "hasn't", "wouldn't", "couldn't"]
        found = [c for c in contractions if c in text_lower]
        passed = len(found) >= 2
        return passed, f"Contractions found: {found[:5]}"

    # You/your focus
    if "you/your" in crit_lower or "you your" in crit_lower:
        you_count = len(re.findall(r'\byou\b|\byour\b|\byours\b', text_lower))
        i_count = len(re.findall(r'\bi\b|\bwe\b|\bour\b|\bus\b', text_lower))
        passed = you_count > i_count
        return passed, f"you/your: {you_count}, I/we/our: {i_count}"

    # Annotations / explain
    if "annotations" in crit_lower or "explain" in crit_lower:
        has_annotations = ("annotation" in text_lower or "why" in text_lower
                          or "rationale" in text_lower or "reasoning" in text_lower)
        return has_annotations, "Has explanations" if has_annotations else "Missing annotations"

    # Alternatives
    if "alternative" in crit_lower or "variation" in crit_lower:
        has_alt = ("alternative" in text_lower or "option 2" in text_lower
                  or "headline 2" in text_lower or "variation" in text_lower
                  or "alternative a" in text_lower or "alternative b" in text_lower)
        return has_alt, "Has alternatives" if has_alt else "Missing alternatives"

    # CTA variety
    if "cta" in crit_lower and ("unique" in crit_lower or "different" in crit_lower):
        cta_words = re.findall(r'(?:start|get|try|see|find|download|claim|unlock|access|begin)\s+\w+', text_lower)
        passed = len(set(cta_words)) >= 3
        return passed, f"Unique CTAs found: {len(set(cta_words))}"

    # Generic containment check
    key_terms = [w for w in crit_lower.split()
                 if len(w) > 4 and w not in ["should", "must", "contains", "includes",
                                              "checks", "verify", "output", "follows"]]
    if key_terms:
        found_terms = [t for t in key_terms if t in text_lower]
        coverage = len(found_terms) / len(key_terms) if key_terms else 0
        passed = coverage >= 0.5
        return passed, f"Term coverage: {coverage:.0%} ({len(found_terms)}/{len(key_terms)})"

    return True, "Criterion checked (default pass)"


def compute_criteria_pass_rate(text, criteria):
    """Compute pass rate on verification criteria."""
    if not criteria:
        return 1.0, []
    grades = []
    for criterion in criteria:
        passed, evidence = check_criterion(text, criterion)
        grades.append({"text": criterion, "passed": passed, "evidence": evidence})
    pass_rate = sum(1 for g in grades if g["passed"]) / len(grades)
    return pass_rate, grades


# --- Dimension 2: Specificity ---

# Numbers, percentages, dollar amounts, named tools, proper nouns
def compute_specificity(text, task):
    """Score how specific the output is (0-1)."""
    score = 0.0

    # Concrete numbers
    numbers = re.findall(r'\b\d+(?:\.\d+)?[%xkKmM]?\b', text)
    score += min(len(numbers) / 15, 0.3)  # cap at 0.3

    # Named entities (brands, tools, companies)
    named = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', text)
    unique_named = set(named) - {"The", "This", "That", "When", "What", "How", "Why",
                                  "Where", "Who", "Which", "Current", "Output", "Page",
                                  "Section", "Headline", "Features", "Note", "Example",
                                  "Based", "Include", "Check", "Option", "Format",
                                  "Content", "Copy", "CTA", "Hero", "Primary", "Subheadline"}
    score += min(len(unique_named) / 20, 0.25)  # cap at 0.25

    # Specific recommendations (imperative verbs + specific nouns)
    specific_recs = len(re.findall(
        r'(?:add|remove|replace|change|rewrite|reduce|simplify|test|create|implement|include)\s+'
        r'(?:a |an |the |your |the )?\w+(?:\s+\w+){0,4}',
        text.lower()
    ))
    score += min(specific_recs / 20, 0.25)  # cap at 0.25

    # Dollar amounts and timeframes
    dollar_amounts = re.findall(r'\$[\d,]+(?:\.\d+)?[kKmM]?', text)
    timeframes = re.findall(r'\b(?:day|week|month|quarter|year|hour|minute)s?\b', text.lower())
    score += min((len(dollar_amounts) + len(timeframes)) / 10, 0.2)  # cap at 0.2

    return min(score, 1.0)


# --- Dimension 3: Actionability ---

def compute_actionability(text, task):
    """Score how actionable the recommendations are (0-1)."""
    score = 0.0

    # Imperative verbs (strong action signals)
    imperatives = len(re.findall(
        r'^(?:Replace|Change|Add|Remove|Reduce|Simplify|Test|Create|Implement|Include|'
        r'Do|Use|Try|Start|Stop|Rewrite|Update|Fix|Move|Split|Combine|Write|Build|'
        r'Set up|Roll out|Prioritize|Focus on|Introduce|Launch)\b',
        text, re.MULTILINE | re.IGNORECASE
    ))
    score += min(imperatives / 15, 0.3)

    # Specific before/after examples
    before_after = len(re.findall(r'(?:before|current|control|now)\s*[:\-]\s*.{10,}', text.lower()))
    score += min(before_after / 5, 0.2)

    # Estimated impact (numbers attached to recommendations)
    impact_numbers = len(re.findall(
        r'(?:\+[\d]+%|[\d]+[%x]?\s*(?:improvement|increase|lift|reduction|decrease|faster|better))',
        text.lower()
    ))
    score += min(impact_numbers / 8, 0.25)

    # Priority labels (P0, P1, P2, high/medium/low impact)
    priority_labels = len(re.findall(r'\b(?:p0|p1|p2|p3|priority|impact:\s*(?:high|medium|low|very high))\b', text.lower()))
    score += min(priority_labels / 6, 0.15)

    # Steps or numbered lists
    numbered_steps = len(re.findall(r'^\s*\d+[\.\)]\s', text, re.MULTILINE))
    score += min(numbered_steps / 10, 0.1)

    return min(score, 1.0)


# --- Dimension 4: Structure ---

def compute_structure(text, task):
    """Score how well-structured the output is (0-1)."""
    score = 0.0

    # Markdown headers
    headers = re.findall(r'^#{1,4}\s+', text, re.MULTILINE)
    score += min(len(headers) / 10, 0.3)

    # Tables
    tables = len(re.findall(r'\|.*\|.*\|', text))
    score += min(tables / 5, 0.2)

    # Bullet lists
    bullets = len(re.findall(r'^[\s]*[-*+]\s', text, re.MULTILINE))
    score += min(bullets / 15, 0.2)

    # Bold/emphasis for key terms
    bold = len(re.findall(r'\*\*[^*]+\*\*', text))
    score += min(bold / 10, 0.15)

    # Clear section separation (blank lines between sections)
    blank_runs = len(re.findall(r'\n{3,}', text))
    score += min(blank_runs / 5, 0.15)

    return min(score, 1.0)


# --- Dimension 5: Depth ---

def compute_depth(text, task):
    """Score the depth/thoroughness of the output (0-1)."""
    wc = count_words(text)
    sc = count_sentences(text)

    # Word count scoring (more is better, with diminishing returns)
    if wc < 100:
        wc_score = 0.1
    elif wc < 300:
        wc_score = 0.3
    elif wc < 600:
        wc_score = 0.5
    elif wc < 1000:
        wc_score = 0.7
    elif wc < 1500:
        wc_score = 0.85
    else:
        wc_score = 1.0

    # Sentence variety (longer avg sentence = more thought)
    avg_sentence_len = wc / max(sc, 1)
    variety_score = min(avg_sentence_len / 25, 1.0)  # 25 words avg = max score

    # Multiple analysis dimensions covered (subsections within sections)
    sub_analysis = len(re.findall(r'^#{2,4}\s+', text, re.MULTILINE))
    structure_depth = min(sub_analysis / 12, 1.0)

    return wc_score * 0.5 + variety_score * 0.25 + structure_depth * 0.25


# --- Dimension 6: Voice ---

def compute_voice(text, task):
    """Score voice/tone match and absence of anti-patterns (0-1)."""
    score = 1.0  # Start perfect, deduct for problems

    text_lower = text.lower()

    # Deduct for banned phrases
    banned_found = [p for p in BANNED_PHRASES if p in text_lower]
    score -= len(banned_found) * 0.15

    # Deduct for exclamation points in body (some tasks allow in CTA only)
    excl_count = text.count("!")
    score -= min(excl_count * 0.05, 0.2)

    # Deduct for overly formal/corporate language
    corporate_words = ["furthermore", "moreover", "additionally", "consequently",
                       "notwithstanding", "herein", "aforementioned", "hereby"]
    corporate_found = [w for w in corporate_words if w in text_lower]
    score -= len(corporate_found) * 0.05

    # Deduct for ALL CAPS words (shouting)
    caps_words = re.findall(r'\b[A-Z]{3,}\b', text)
    real_caps = [w for w in caps_words if w not in {"HTML", "CSS", "API", "CTA", "FAQ",
                                                      "URL", "SEO", "PPC", "SaaS", "B2B",
                                                      "CTO", "VP", "CEO", "CFO", "COO",
                                                      "CEO", "AI", "UX", "UI", "KPI",
                                                      "ROI", "CRM", "ERP", "SOC", "SLA",
                                                      "SSO", "JWT", "AWS", "GCP", "SQL",
                                                      "NLP", "DTC", "AUM", "ROAS",
                                                      "FlowBoard", "NestHub", "DataPulse",
                                                      "SecureVault", "TaskPilot"}]
    score -= min(len(real_caps) * 0.03, 0.15)

    return max(score, 0.0)


# --- Composite Scoring ---

def score_task_v2(task, text_with, text_without):
    """Score a task using all dimensions."""
    criteria = task.get("verification_criteria", [])

    # --- WITH SKILL ---
    criteria_rate_w, criteria_grades_w = compute_criteria_pass_rate(text_with, criteria)
    specificity_w = compute_specificity(text_with, task)
    actionability_w = compute_actionability(text_with, task)
    structure_w = compute_structure(text_with, task)
    depth_w = compute_depth(text_with, task)
    voice_w = compute_voice(text_with, task)

    composite_w = (
        criteria_rate_w * WEIGHTS["criteria_pass_rate"]
        + specificity_w * WEIGHTS["specificity"]
        + actionability_w * WEIGHTS["actionability"]
        + structure_w * WEIGHTS["structure"]
        + depth_w * WEIGHTS["depth"]
        + voice_w * WEIGHTS["voice"]
    )

    with_scores = {
        "criteria_pass_rate": criteria_rate_w,
        "specificity": specificity_w,
        "actionability": actionability_w,
        "structure": structure_w,
        "depth": depth_w,
        "voice": voice_w,
        "composite": composite_w,
        "criteria_grades": criteria_grades_w,
        "word_count": count_words(text_with),
    }

    # --- WITHOUT SKILL ---
    criteria_rate_wo, criteria_grades_wo = compute_criteria_pass_rate(text_without, criteria)
    specificity_wo = compute_specificity(text_without, task)
    actionability_wo = compute_actionability(text_without, task)
    structure_wo = compute_structure(text_without, task)
    depth_wo = compute_depth(text_without, task)
    voice_wo = compute_voice(text_without, task)

    composite_wo = (
        criteria_rate_wo * WEIGHTS["criteria_pass_rate"]
        + specificity_wo * WEIGHTS["specificity"]
        + actionability_wo * WEIGHTS["actionability"]
        + structure_wo * WEIGHTS["structure"]
        + depth_wo * WEIGHTS["depth"]
        + voice_wo * WEIGHTS["voice"]
    )

    without_scores = {
        "criteria_pass_rate": criteria_rate_wo,
        "specificity": specificity_wo,
        "actionability": actionability_wo,
        "structure": structure_wo,
        "depth": depth_wo,
        "voice": voice_wo,
        "composite": composite_wo,
        "criteria_grades": criteria_grades_wo,
        "word_count": count_words(text_without),
    }

    # Delta per dimension
    deltas = {}
    for dim in ["criteria_pass_rate", "specificity", "actionability", "structure", "depth", "voice", "composite"]:
        deltas[dim] = with_scores[dim] - without_scores[dim]

    return {
        "with_skill": with_scores,
        "without_skill": without_scores,
        "deltas": deltas,
    }


def main(results_dir, tasks_file, output_dir):
    tasks = load_tasks(tasks_file)
    results = {}
    all_task_results = []

    for task in tasks:
        task_id = task["id"]
        skill = task["skill"]

        with_path = results_dir / f"{task_id}_with_skill.md"
        without_path = results_dir / f"{task_id}_without_skill.md"

        text_with = read_file(with_path)
        text_without = read_file(without_path)

        if not text_with or not text_without:
            print(f"SKIP {task_id}: missing files")
            continue

        scoring = score_task_v2(task, text_with, text_without)

        # Save individual grading (v2 format)
        grading_dir = results_dir / task_id
        grading_dir.mkdir(exist_ok=True)

        with_grading = {
            "eval_id": task_id,
            "run_id": f"{task_id}_with_skill",
            "expectations": [{"text": g["text"], "passed": g["passed"], "evidence": g["evidence"]}
                            for g in scoring["with_skill"]["criteria_grades"]],
            "pass_rate": scoring["with_skill"]["criteria_pass_rate"],
            "scores": {
                "specificity": scoring["with_skill"]["specificity"],
                "actionability": scoring["with_skill"]["actionability"],
                "structure": scoring["with_skill"]["structure"],
                "depth": scoring["with_skill"]["depth"],
                "voice": scoring["with_skill"]["voice"],
                "composite": scoring["with_skill"]["composite"],
                "word_count": scoring["with_skill"]["word_count"],
            }
        }

        without_grading = {
            "eval_id": task_id,
            "run_id": f"{task_id}_without_skill",
            "expectations": [{"text": g["text"], "passed": g["passed"], "evidence": g["evidence"]}
                            for g in scoring["without_skill"]["criteria_grades"]],
            "pass_rate": scoring["without_skill"]["criteria_pass_rate"],
            "scores": {
                "specificity": scoring["without_skill"]["specificity"],
                "actionability": scoring["without_skill"]["actionability"],
                "structure": scoring["without_skill"]["structure"],
                "depth": scoring["without_skill"]["depth"],
                "voice": scoring["without_skill"]["voice"],
                "composite": scoring["without_skill"]["composite"],
                "word_count": scoring["without_skill"]["word_count"],
            }
        }

        (grading_dir / "grading_with_skill_v2.json").write_text(json.dumps(with_grading, indent=2))
        (grading_dir / "grading_without_skill_v2.json").write_text(json.dumps(without_grading, indent=2))

        results[task_id] = {
            "skill": skill,
            "with_skill": scoring["with_skill"],
            "without_skill": scoring["without_skill"],
            "deltas": scoring["deltas"],
        }

        d = scoring["deltas"]["composite"]
        w_c = scoring["with_skill"]["composite"]
        wo_c = scoring["without_skill"]["composite"]
        print(f"{task_id}: with={w_c:.2f} without={wo_c:.2f} delta={d:+.2f}")

        all_task_results.append({
            "task_id": task_id,
            "skill": skill,
            "deltas": scoring["deltas"],
            "with_composite": w_c,
            "without_composite": wo_c,
        })

    # --- Aggregate by skill ---
    skills = {}
    for task_id, r in results.items():
        skill = r["skill"]
        if skill not in skills:
            skills[skill] = {
                "with_rates": [], "without_rates": [],
                "with_composites": [], "without_composites": [],
                "deltas": [],
                "dimension_deltas": {dim: [] for dim in ["criteria_pass_rate", "specificity",
                                                          "actionability", "structure", "depth", "voice", "composite"]},
                "task_ids": [],
            }
        skills[skill]["with_rates"].append(r["with_skill"]["criteria_pass_rate"])
        skills[skill]["without_rates"].append(r["without_skill"]["criteria_pass_rate"])
        skills[skill]["with_composites"].append(r["with_skill"]["composite"])
        skills[skill]["without_composites"].append(r["without_skill"]["composite"])
        skills[skill]["deltas"].append(r["deltas"]["composite"])
        skills[skill]["task_ids"].append(task_id)
        for dim, val in r["deltas"].items():
            skills[skill]["dimension_deltas"][dim].append(val)

    # --- Build benchmark ---
    all_composites_with = [r["with_skill"]["composite"] for r in results.values()]
    all_composites_without = [r["without_skill"]["composite"] for r in results.values()]
    all_deltas = [r["deltas"]["composite"] for r in results.values()]

    benchmark = {
        "version": "v2",
        "generated_at": datetime.now().isoformat(),
        "weights": WEIGHTS,
        "overall": {
            "with_skill_mean": statistics.mean(all_composites_with),
            "without_skill_mean": statistics.mean(all_composites_without),
            "delta_mean": statistics.mean(all_deltas),
            "delta_median": statistics.median(all_deltas),
            "delta_stdev": statistics.stdev(all_deltas) if len(all_deltas) > 1 else 0,
            "task_count": len(results),
            "positive_delta_count": sum(1 for d in all_deltas if d > 0),
            "negative_delta_count": sum(1 for d in all_deltas if d < 0),
            "zero_delta_count": sum(1 for d in all_deltas if d == 0),
        },
        "by_skill": {},
        "per_task": {task_id: {
            "skill": r["skill"],
            "with_composite": r["with_skill"]["composite"],
            "without_composite": r["without_skill"]["composite"],
            "delta": r["deltas"]["composite"],
            "dimension_deltas": r["deltas"],
        } for task_id, r in results.items()},
    }

    for skill, data in skills.items():
        dim_avgs = {}
        for dim, vals in data["dimension_deltas"].items():
            dim_avgs[dim] = statistics.mean(vals) if vals else 0

        benchmark["by_skill"][skill] = {
            "with_skill_mean": statistics.mean(data["with_composites"]),
            "without_skill_mean": statistics.mean(data["without_composites"]),
            "delta_mean": statistics.mean(data["deltas"]),
            "delta_median": statistics.median(data["deltas"]),
            "task_count": len(data["with_composites"]),
            "dimension_deltas": dim_avgs,
            "task_ids": data["task_ids"],
        }

    # Save benchmark
    output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_path = output_dir / "benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark, indent=2))

    # Save per-task deltas for DPO generator
    deltas_path = output_dir / "task_deltas.json"
    deltas_path.write_text(json.dumps(all_task_results, indent=2))

    # Print summary
    print("\n=== V2 BENCHMARK SUMMARY ===")
    print(f"Overall: with={benchmark['overall']['with_skill_mean']:.2f} "
          f"without={benchmark['overall']['without_skill_mean']:.2f} "
          f"delta={benchmark['overall']['delta_mean']:+.2f}")
    print(f"Positive deltas: {benchmark['overall']['positive_delta_count']}, "
          f"Negative: {benchmark['overall']['negative_delta_count']}, "
          f"Zero: {benchmark['overall']['zero_delta_count']}")

    print("\n--- By Skill ---")
    for skill, data in benchmark["by_skill"].items():
        print(f"  {skill}: with={data['with_skill_mean']:.2f} "
              f"without={data['without_skill_mean']:.2f} "
              f"delta={data['delta_mean']:+.2f}")
        print(f"    Dimension deltas:")
        for dim, val in data["dimension_deltas"].items():
            print(f"      {dim}: {val:+.2f}")

    # Top improvement pairs
    sorted_tasks = sorted(all_task_results, key=lambda x: x["deltas"]["composite"], reverse=True)
    print("\n--- Top 5 Improvements (with_skill > without_skill) ---")
    for t in sorted_tasks[:5]:
        print(f"  {t['task_id']} ({t['skill']}): delta={t['deltas']['composite']:+.2f}")

    print("\n--- Bottom 5 (without_skill >= with_skill) ---")
    for t in sorted_tasks[-5:]:
        print(f"  {t['task_id']} ({t['skill']}): delta={t['deltas']['composite']:+.2f}")

    return benchmark


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="V2 Scoring Pipeline for SkillGym"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Directory containing with/without skill output files"
    )
    parser.add_argument(
        "--tasks-file",
        type=Path,
        required=True,
        help="Path to tasks.json"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write benchmark.json and task_deltas.json (default: same as results-dir)"
    )
    args = parser.parse_args()

    output_dir = args.output_dir if args.output_dir else args.results_dir
    main(args.results_dir, args.tasks_file, output_dir)
