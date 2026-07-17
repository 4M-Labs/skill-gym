---
name: skillgym-pipeline
description: "Autonomously benchmark any SKILL.md and generate DPO training data. Triggers on 'run skillgym', 'benchmark this skill', 'test if a skill works', 'generate training data from skill', 'fine-tune on skill outputs', 'is this skill effective', 'compare with and without skill', 'skill delta', 'DPO from skill', 'skill evaluation', 'run the pipeline', 'score this skill'. Use this whenever someone wants to measure whether a skill actually improves model outputs, or when they want to create training data from skill-controlled comparisons."
---

# SkillGym Pipeline

A meta-skill that automates the complete SkillGym training data generation pipeline. Given any SKILL.md, it runs controlled comparisons (with-skill vs without-skill), scores outputs across 6 dimensions, generates DPO training pairs, and optionally fine-tunes a small model.

The core insight: a skill's own instructions ARE the evaluation rubric. No synthetic data. No external judge models. The delta between with-skill and without-skill performance IS the training signal.

## Quick Start

```
User: "Run skillgym on my cold-email skill"
You: [Follow steps 1-7 below, using pipeline/skills/cold-email.md]
```

## Prerequisites

- Python 3.10+ with `uv` available
- The SKILL.md file to process
- Access to the `task` tool for spawning subagents (Step 3)
- Pipeline directory: `skill-gym-repo/pipeline/`

---

## Step 1: Parse and Analyze Skill

Read the target SKILL.md and extract:

1. **Skill name** from YAML frontmatter `name` field
2. **Domain** -- marketing, code, writing, design, data, or general
3. **Key behaviors** -- what the skill teaches (from sections like "Framework", "Principles", "Quality Check")
4. **Output format** -- what the skill expects as output (markdown, email, code, etc.)

Save the skill to `pipeline/skills/{skill_name}.md` if not already there.

**How to detect domain:** Marketing skills mention landing pages, CRO, copywriting, emails. Code skills mention debugging, reviewing, deploying. Writing skills mention essays, articles. Design skills mention layouts, components.

**Why this matters:** Domain detection drives eval task generation (Step 2) and subagent role assignment (Step 3). A cold-email skill needs subject line tasks; a CRO skill needs headline analysis tasks.

---

## Step 2: Generate Eval Tasks

```bash
cd skill-gym-repo/pipeline
uv run python generate_evals.py \
  --skill-path <path-to-SKILL.md> \
  --output-dir evals/<skill-name>/ \
  --num-tasks 10
```

Produces `evals/<skill-name>/tasks.json` with 10-20 tasks. Each task has:
- `id` -- unique identifier (e.g., `cro_001`)
- `prompt` -- realistic user request testing the skill
- `verification_criteria` -- 8-12 checkable criteria
- `scoring_rubric` -- pass/fail descriptions

The script is standalone (no API calls). It parses the SKILL.md to extract domain and behaviors, then generates domain-specific tasks from built-in templates.

**If tasks look too generic**, edit `tasks.json` to make prompts more specific to the skill's unique behaviors.

---

## Step 3: Run With/Without Comparisons

For each task, spawn TWO subagents via the `task` tool. Cap at 4 concurrent subagents to avoid memory pressure.

**Set the role based on the skill's domain:**

| Domain | Role |
|--------|------|
| Marketing | "marketing specialist" |
| Cold outreach | "sales outreach specialist" |
| Code | "software engineer" |
| Writing | "professional writer" |
| Design | "UI/UX designer" |
| Data | "data engineer" |
| General | "domain specialist" |

**Agent A (with skill):**
```
subagent_type: "general"
prompt: "You are a {role}. Use the following skill to complete the task.\n\n## SKILL INSTRUCTIONS:\n{full SKILL.md content}\n\n## TASK:\n{task prompt}\n\nProvide your complete response."
```

**Agent B (without skill):**
```
subagent_type: "general"
prompt: "You are a {role}. Complete the following task using only your general knowledge.\n\n## TASK:\n{task prompt}\n\nProvide your complete response."
```

Save outputs to:
- `results/{skill-name}/{task_id}_with_skill.md`
- `results/{skill-name}/{task_id}_without_skill.md`

**Resume:** Skip tasks that already have both output files.

For detailed spawning patterns, batch processing examples, and timing data capture, see `references/subagent-patterns.md`.

---

## Step 4: Score Outputs

```bash
cd skill-gym-repo/pipeline
uv run python score_outputs_v2.py \
  --results-dir results/<skill-name>/ \
  --tasks-file evals/<skill-name>/tasks.json
```

This scores all 60 outputs across 6 weighted dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Criteria Pass Rate | 0.25 | Binary pass/fail on verification criteria |
| Specificity | 0.20 | Concrete numbers, named tools/brands |
| Actionability | 0.20 | Imperative verbs, before/after, impact estimates |
| Structure | 0.15 | Follows requested format, scannable |
| Depth | 0.10 | Word count, detail level, thoroughness |
| Voice | 0.10 | Matches tone, avoids banned patterns |

**Composite** = weighted average. **Delta** = composite_with_skill - composite_without_skill.

**Quality Gate 1:** If mean delta <= 0, stop. The skill does not improve performance. If mean delta > 0 but < 0.02, warn about marginal effect.

For full scoring details, see `references/scoring-rubric.md`.

---

## Step 5: Generate DPO Pairs

```bash
cd skill-gym-repo/pipeline
uv run python generate_dpo_v2.py \
  --results-dir results/<skill-name>/ \
  --tasks-file evals/<skill-name>/tasks.json \
  --output-dir dpo-data/<skill-name>/
```

Quality filters applied:
- Min delta: 0.05 (with-skill must beat without-skill meaningfully)
- Min chosen composite: 0.30 (chosen must be good enough to learn from)
- Max rejected composite: 0.70 (rejected should not already be too good)
- Min word count: 30 (reject very short outputs)

**Quality Gate 2:** If 0 pairs pass, stop. If < 5 pairs, warn about overfitting risk. If 5-10 pairs, proceed with caution. If 10+ pairs, proceed.

For quality distribution checks and decision trees, see `references/quality-gates.md`.

---

## Step 6: Fine-Tune Model (Optional)

Only run if the user explicitly requests training. Ask before proceeding.

```bash
cd skill-gym-repo/pipeline
uv run python train_dpo.py \
  --data-file dpo-data/<skill-name>/dpo_format_v2.json \
  --output-dir models/<skill-name>-dpo/
```

Config: Qwen2.5-1.5B-Instruct, 4-bit NF4, LoRA r=8 alpha=16, DPO beta=0.1, 3 epochs, max_length=512.

**Quality Gate 3:** If loss did not decrease, warn about data quality. If loss oscillates, warn about learning rate.

For training config, model selection, and troubleshooting, see `references/dpo-training.md`.

---

## Step 7: Generate Report

Produce a final analysis document using the template at `templates/benchmark-report.md`. Save to `analysis/{skill-name}/report.md`.

The report includes:
- Skill overview and eval summary
- Performance summary (mean/median delta, positive/negative counts)
- Per-dimension analysis table
- Top improvements and areas of concern
- DPO training data quality metrics
- Quality gate results
- Recommendations

---

## Error Recovery

| Error | Action |
|-------|--------|
| Subagent fails or times out | Skip that task, log the failure, continue |
| CUDA OOM during scoring/training | Reduce batch size or concurrency, retry once |
| Empty output from subagent | Retry once with same prompt, then skip |
| No tasks pass quality gates | Report gate failure with numbers, do not proceed |
| generate_evals.py fails | Report error, suggest manual tasks.json creation |

## Resume Capability

The pipeline resumes from any step by checking for existing output files:
- Steps 1-2: Skip if `tasks.json` exists (unless `--force`)
- Step 3: Skip tasks with both output files
- Steps 4-7: Skip if output files exist (unless `--force`)

## Directory Structure

```
pipeline/
  SKILL.md                          This meta-skill
  generate_evals.py                 Step 2: Eval generation
  score_outputs_v2.py              Step 4: 6-dimension scoring
  generate_dpo_v2.py               Step 5: DPO pair generation
  train_dpo.py                      Step 6: Fine-tuning
  pipeline.py                       Master orchestrator (chains all steps)
  references/
    scoring-rubric.md               Scoring dimension details
    quality-gates.md                Gate logic and decision trees
    subagent-patterns.md            Spawning patterns and concurrency
    dpo-training.md                 Training config and troubleshooting
  templates/
    benchmark-report.md             Report template
    output-header.md                Output file header format
  skills/                           Downloaded SKILL.md files
  evals/{skill-name}/tasks.json     Generated eval tasks
  results/{skill-name}/             Outputs and benchmarks
  dpo-data/{skill-name}/            Training pairs
  models/{skill-name}-dpo/          Trained model
  analysis/{skill-name}/report.md   Final report
```
