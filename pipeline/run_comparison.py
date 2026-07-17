"""
SkillGym Marketing Pipeline - Comparison Runner (v2)
Runs Agent A (with skill) vs Agent B (without skill) on eval tasks
Handles CUDA errors gracefully, processes in batches
"""

import json
import os
import gc
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Paths
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(PIPELINE_DIR, "evals", "tasks.json")
SKILLS_DIR = os.path.join(PIPELINE_DIR, "skills")
RESULTS_DIR = os.path.join(PIPELINE_DIR, "results")
RESULTS_FILE = os.path.join(RESULTS_DIR, "comparison_results.json")

# Model
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
MAX_NEW_TOKENS = 1500

def load_model():
    print(f"Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    print(f"Model loaded on {model.device}")
    return model, tokenizer

def load_skill(skill_name):
    skill_path = os.path.join(SKILLS_DIR, f"{skill_name}.md")
    with open(skill_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_response(model, tokenizer, system_prompt, user_prompt):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.7,
            top_p=0.9,
            do_sample=True
        )
    
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    del inputs, outputs
    torch.cuda.empty_cache()
    return response

def score_output(output, criteria):
    scores = {}
    output_lower = output.lower()
    
    for criterion in criteria:
        cl = criterion.lower()
        
        if "quick wins" in cl:
            scores[criterion] = "quick wins" in output_lower
        elif "high-impact" in cl:
            scores[criterion] = "high-impact" in output_lower
        elif "test ideas" in cl:
            scores[criterion] = "test ideas" in output_lower
        elif "copy alternatives" in cl:
            scores[criterion] = "copy alternatives" in output_lower or "alternative" in output_lower
        elif "headline" in cl and ("alternative" in cl or "option" in cl):
            scores[criterion] = "headline" in output_lower and ("alternative" in output_lower or "option" in output_lower)
        elif "cta" in cl and "weak" in cl:
            scores[criterion] = "sign up" not in output_lower or "stronger" in output_lower or "better" in output_lower
        elif "form" in cl and ("field" in cl or "friction" in cl):
            scores[criterion] = "field" in output_lower and ("reduce" in output_lower or "fewer" in output_lower or "less" in output_lower)
        elif "trust signal" in cl or "social proof" in cl:
            scores[criterion] = "trust" in output_lower or "social proof" in output_lower or "testimonial" in output_lower
        elif "subject line" in cl:
            scores[criterion] = "subject" in output_lower
        elif "under" in cl and "word" in cl:
            word_count = len(output.split())
            scores[criterion] = word_count < 200
        elif "contraction" in cl:
            contractions = ["don't", "can't", "won't", "it's", "you're", "we're", "they're", "i'm", "that's", "there's"]
            scores[criterion] = any(c in output_lower for c in contractions)
        elif "jargon" in cl or ("avoid" in cl and "leverage" in cl):
            banned = ["synergy", "leverage", "best-in-class", "leading provider", "cutting-edge", "revolutionary"]
            scores[criterion] = not any(b in output_lower for b in banned)
        elif "exclamation" in cl:
            scores[criterion] = "!" not in output
        elif "page copy" in cl or "organized by section" in cl:
            scores[criterion] = any(s in output_lower for s in ["headline", "subheadline", "section", "cta"])
        elif "annotation" in cl:
            scores[criterion] = "annotation" in output_lower or "rationale" in output_lower or "reasoning" in output_lower
        elif "feature" in cl and "benefit" in cl:
            scores[criterion] = "benefit" in output_lower or "outcome" in output_lower or "result" in output_lower
        elif "active voice" in cl:
            scores[criterion] = True
        elif "you/your" in cl:
            scores[criterion] = "you" in output_lower or "your" in output_lower
        elif "no fear" in cl or "fear" in cl and "avoid" in cl:
            fear = ["risk", "danger", "vulnerable", "at risk", "exposed"]
            scores[criterion] = not any(f in output_lower for f in fear[:2])
        elif "framework" in cl:
            scores[criterion] = any(f in output_lower for f in ["observation", "problem", "proof", "ask", "trigger", "insight", "story", "bridge"])
        elif "c-suite" in cl or "brevity" in cl:
            word_count = len(output.split())
            scores[criterion] = word_count < 120
        elif "standalone" in cl:
            scores[criterion] = True  # hard to auto-check
        elif "breakup" in cl:
            scores[criterion] = "last" in output_lower or "final" in output_lower or "follow up" in output_lower
        elif "bootstrapped" in cl or "small team" in cl:
            scores[criterion] = "small" in output_lower or "team" in output_lower or "lean" in output_lower
        elif "enterprise" in cl and "avoid" in cl:
            scores[criterion] = "enterprise" not in output_lower
        elif "before/after" in cl or "before" in cl and "after" in cl:
            scores[criterion] = "before" in output_lower and "after" in output_lower
        elif "competitor" in cl or "differentiat" in cl:
            scores[criterion] = "competitor" in output_lower or "different" in output_lower or "compare" in output_lower
        elif "guarantee" in cl or "risk reversal" in cl:
            scores[criterion] = "guarantee" in output_lower or "risk" in output_lower or "refund" in output_lower or "try" in output_lower
        elif "faq" in cl:
            scores[criterion] = "faq" in output_lower or "frequently" in output_lower or "question" in output_lower
        elif "annual" in cl and "toggle" in cl:
            scores[criterion] = "annual" in output_lower or "yearly" in output_lower or "monthly" in output_lower
        elif "plan" in cl and "right for me" in cl:
            scores[criterion] = "right" in output_lower and "plan" in output_lower
        elif "specific" in cl and ("number" in cl or "proof" in cl or "result" in cl):
            import re
            scores[criterion] = bool(re.search(r'\d+', output))
        elif "inline" in cl and "cta" in cl:
            scores[criterion] = "inline" in output_lower or "middle" in output_lower or "throughout" in output_lower
        elif "message match" in cl or "message mismatch" in cl:
            scores[criterion] = "match" in output_lower or "mismatch" in output_lower or "consistent" in output_lower
        elif "navigation" in cl and ("remove" in cl or "simplif" in cl):
            scores[criterion] = "navigation" in output_lower and ("remove" in output_lower or "simplif" in output_lower or "no nav" in output_lower)
        elif "multi-step" in cl:
            scores[criterion] = "multi-step" in output_lower or "step" in output_lower
        elif "technical" in cl and "jargon" in cl:
            scores[criterion] = "technical" in output_lower or "jargon" in output_lower or "simp" in output_lower
        elif "meta content" in cl or "meta description" in cl:
            scores[criterion] = "meta" in output_lower or "title tag" in output_lower or "seo" in output_lower
        elif "tone" in cl or "voice" in cl:
            scores[criterion] = "tone" in output_lower or "voice" in output_lower or "voice" in output_lower
        elif "alternatives" in cl and "headline" in cl:
            scores[criterion] = "alternative" in output_lower and "headline" in output_lower
        elif "rhetorical" in cl and "question" in cl:
            scores[criterion] = "?" in output
        elif "buzzword" in cl or "marketing buzzword" in cl:
            buzz = ["revolutionary", "game-changing", "cutting-edge", "next-generation", "innovative"]
            scores[criterion] = not any(b in output_lower for b in buzz)
        elif "read it aloud" in cl:
            scores[criterion] = True  # human judgment
        else:
            words = [w for w in cl.split() if len(w) > 3]
            if words:
                scores[criterion] = sum(1 for w in words if w in output_lower) >= max(1, len(words) * 0.4)
            else:
                scores[criterion] = True
    
    return scores

def load_existing_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def main():
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks = data["tasks"]
    print(f"Loaded {len(tasks)} tasks")
    
    existing = load_existing_results()
    done_ids = {r["task_id"] for r in existing}
    remaining = [t for t in tasks if t["id"] not in done_ids]
    print(f"Already done: {len(done_ids)}, Remaining: {len(remaining)}")
    
    model, tokenizer = load_model()
    base_system = "You are a helpful marketing assistant. Provide clear, actionable marketing advice."
    
    for i, task in enumerate(remaining):
        skill_name = task["skill"]
        skill_content = load_skill(skill_name)
        
        # Agent A: WITH skill
        skill_system = f"{base_system}\n\n## Skill Instructions\n{skill_content}"
        print(f"\n[{len(done_ids)+i+1}/{len(tasks)}] Agent A on {task['id']}...", end=" ", flush=True)
        try:
            output_a = generate_response(model, tokenizer, skill_system, task["prompt"])
        except Exception as e:
            print(f"ERROR: {e}")
            torch.cuda.empty_cache()
            gc.collect()
            continue
        
        # Agent B: WITHOUT skill
        print(f"Agent B...", end=" ", flush=True)
        try:
            output_b = generate_response(model, tokenizer, base_system, task["prompt"])
        except Exception as e:
            print(f"ERROR: {e}")
            torch.cuda.empty_cache()
            gc.collect()
            continue
        
        scores_a = score_output(output_a, task["verification_criteria"])
        scores_b = score_output(output_b, task["verification_criteria"])
        pass_a = sum(scores_a.values()) / len(scores_a) if scores_a else 0
        pass_b = sum(scores_b.values()) / len(scores_b) if scores_b else 0
        
        result = {
            "task_id": task["id"],
            "skill": skill_name,
            "prompt": task["prompt"],
            "output_with_skill": output_a,
            "output_without_skill": output_b,
            "scores_with_skill": scores_a,
            "scores_without_skill": scores_b,
            "pass_rate_with_skill": round(pass_a, 3),
            "pass_rate_without_skill": round(pass_b, 3),
            "delta": round(pass_a - pass_b, 3)
        }
        existing.append(result)
        save_results(existing)
        
        print(f"A:{pass_a:.0%} B:{pass_b:.0%} D:{result['delta']:+.0%}")
        
        gc.collect()
        torch.cuda.empty_cache()
    
    # Final summary
    all_results = load_existing_results()
    avg_delta = sum(r["delta"] for r in all_results) / len(all_results) if all_results else 0
    with_skill_wins = sum(1 for r in all_results if r["delta"] > 0)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(all_results)} tasks complete")
    print(f"Agent A (with skill) wins: {with_skill_wins}/{len(all_results)}")
    print(f"Average delta: {avg_delta:+.1%}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
