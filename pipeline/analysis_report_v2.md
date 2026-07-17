# SkillGym Pipeline v2 - Analysis Report

**Generated:** 2026-07-16
**Pipeline Version:** v2 (multi-dimensional scoring)
**Dataset:** 30 tasks x 2 variants = 60 outputs (iteration-1)

---

## 1. Executive Summary

The v2 scoring pipeline replaces binary pass/fail criteria checking with 6 weighted quality dimensions. This reveals more nuanced skill differences that the original scoring missed.

| Metric | Value |
|--------|-------|
| Tasks scored | 30 |
| Positive delta (with_skill wins) | 20 (67%) |
| Negative delta (without_skill wins) | 10 (33%) |
| Overall composite: with_skill | 0.56 |
| Overall composite: without_skill | 0.53 |
| Overall delta | +0.03 |
| DPO pairs generated (v1, loose filter) | 23 |
| DPO pairs generated (v2, strict filter) | 7 |
| Avg delta per DPO pair (v2) | +0.09 |

---

## 2. Scoring Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Criteria Pass Rate | 25% | Binary criteria from tasks.json (original scoring) |
| Specificity | 20% | Concrete numbers, named brands, specific recommendations |
| Actionability | 20% | Imperative verbs, before/after examples, impact estimates |
| Structure | 15% | Markdown headers, tables, lists, bold emphasis |
| Depth | 10% | Word count, sentence variety, subsection count |
| Voice | 10% | Absence of banned phrases, exclamation points, corporate jargon |

---

## 3. Per-Skill Delta Analysis

### 3.1 CRO (Conversion Rate Optimization)

**Overall:** with=0.75, without=0.71, delta=+0.04

| Dimension | Delta | Interpretation |
|-----------|-------|----------------|
| Criteria Pass Rate | +0.00 | Both pass same criteria (binary check too coarse) |
| Specificity | +0.00 | Both mention similar specific elements |
| Actionability | **+0.22** | With_skill provides significantly more actionable recommendations |
| Structure | +0.00 | Both follow similar structure |
| Depth | -0.00 | Similar thoroughness |
| Voice | -0.03 | Without_skill slightly cleaner voice |

**Key Finding:** CRO skill's biggest impact is on **actionability** (+0.22). The skill teaches the model to provide specific, imperative recommendations with priority labels and impact estimates, rather than just identifying problems.

**Best CRO tasks (largest delta):**
- `cro_009` (GreenLeaf Capital about page): delta=+0.13 -- skill dramatically improved differentiation recommendations
- `cro_007` (TeamCollab signup flow): delta=+0.10 -- skill provided much better form optimization advice
- `cro_001` (FlowBoard landing page): delta=+0.08 -- skill improved specificity of recommendations

**Worst CRO tasks:**
- `cro_008` (WriteRight feature page): delta=-0.05 -- without_skill actually had better structured output
- `cro_006` (FitTrack Pro landing page): delta=-0.02 -- without_skill was slightly more thorough

### 3.2 Copywriting

**Overall:** with=0.54, without=0.50, delta=+0.04

| Dimension | Delta | Interpretation |
|-----------|-------|----------------|
| Criteria Pass Rate | **+0.19** | With_skill passes significantly more task-specific criteria |
| Specificity | +0.01 | Similar specificity levels |
| Actionability | -0.05 | Without_skill slightly more action-oriented |
| Structure | +0.04 | With_skill slightly better organized |
| Depth | **+0.09** | With_skill provides substantially more depth |
| Voice | **-0.17** | Without_skill has noticeably cleaner voice |

**Key Finding:** Copywriting skill's biggest impact is on **criteria pass rate** (+0.19) and **depth** (+0.09). The skill teaches the model to produce longer, more thorough output that hits more of the specific criteria. However, the voice dimension takes a hit (-0.17), likely because the skill encourages more annotations/explanations that sometimes use corporate language.

**Best copywriting tasks (largest delta):**
- `copy_005` (TaskPilot rewrite): delta=+0.18 -- skill massively improved jargon elimination and benefit framing
- `copy_002` (MealPrep AI landing page): delta=+0.08 -- skill better matched ad hook and addressed pain points
- `copy_003` (DesignFlow pricing page): delta=+0.07 -- skill improved competitor differentiation

**Worst copywriting tasks:**
- `copy_006` (CodeBridge about page): delta=-0.06 -- without_skill had better voice and specificity
- `copy_007` (FreshBooks CTAs): delta=-0.02 -- without_skill was slightly more actionable
- `copy_004` (SecureVault hero): delta=-0.02 -- nearly equivalent quality

### 3.3 Cold Email

**Overall:** with=0.39, without=0.39, delta=+0.01

| Dimension | Delta | Interpretation |
|-----------|-------|----------------|
| Criteria Pass Rate | +0.03 | Slightly more criteria met with skill |
| Specificity | +0.00 | Similar specificity |
| Actionability | -0.01 | Nearly identical |
| Structure | +0.05 | With_skill slightly better structured |
| Depth | -0.02 | Without_skill slightly more thorough |
| Voice | -0.01 | Nearly identical |

**Key Finding:** Cold email skill shows the **smallest delta** across all skills. The without_skill model already produces decent cold emails. The skill's main value is in **structure** (+0.05) -- it teaches proper email format and cadence.

**Best cold email tasks:**
- `cold_003` (3-email follow-up sequence): delta=+0.07 -- skill improved cadence and standalone quality
- `cold_008` (Rachel Kim / TalentSync): delta=0.07 -- skill better connected trigger to pain

**Worst cold email tasks:**
- `cold_004` (James Liu / FinScale): delta=-0.03 -- without_skill had better structure
- `cold_002` (Marcus Rodriguez / HealthBridge): delta=-0.03 -- without_skill was more concise

---

## 4. Biggest Skill Improvements (Examples)

### 4.1 copy_005: TaskPilot Feature Page Rewrite (+0.18)

**With Skill (0.56):**
- Eliminated all jargon ("leverage", "cutting-edge", "revolutionize")
- Connected AI feature to specific customer outcome: "prioritize tasks before you ask"
- Added "Who it's for" and "What it is not" sections
- Annotations explain every change with rationale
- CTA: "Start your free trial. Connect your board in two minutes."

**Without Skill (0.39):**
- Still used some jargon ("optimize", "revolutionizes")
- Connected to pain but less specifically
- Missing "What it is not" section
- Fewer annotations
- CTA: "Start Your 14-day free trial -- connect Asana or Trello in under 5 minutes."

**Delta breakdown:** criteria +0.50, specificity +0.37, actionability +0.17, structure +0.20, depth +0.16

### 4.2 cro_009: GreenLeaf Capital About Page (+0.13)

**With Skill (0.80):**
- Identified company-centric vs client-centric framing as core problem
- Recommended specific differentiator section ("Why GreenLeaf vs. other firms")
- Suggested softer CTA ("See Our Approach" instead of "Contact Us")
- Addressed financial advisor referral context
- Provided 3 headline alternatives connecting to investor value

**Without Skill (0.67):**
- Identified same core problem
- Recommendations were more generic
- Less specific about the financial services context
- Fewer headline alternatives

**Delta breakdown:** criteria +0.10, actionability +0.50, voice +0.06

### 4.3 cro_007: TeamCollab Signup Flow (+0.10)

**With Skill (0.86):**
- Provided field-by-field friction analysis table
- Recommended specific field reduction (8 -> 3 essential fields)
- Suggested multi-step form as alternative
- Added benefit-oriented headline alternatives
- Recommended social proof placement near form

**Without Skill (0.76):**
- Identified the problem but with less specific field-by-field analysis
- Recommendations were good but less detailed
- Fewer alternatives

---

## 5. DPO Training Pair Quality

### 5.1 V1 (Original) vs V2 (Filtered)

| Metric | V1 | V2 | Change |
|--------|-----|-----|--------|
| Total pairs | 23 | 7 | -70% |
| Avg delta | +0.03 | +0.09 | +200% |
| Avg chosen score | 0.43 | 0.59 | +37% |
| Avg rejected score | 0.37 | 0.50 | +35% |
| Min delta | -0.10 | +0.06 | All positive |
| Max delta | +0.50 | +0.18 | More realistic |

### 5.2 V2 Pair Quality Summary

| Skill | Pairs | Avg Delta | Avg Chosen | Avg Rejected |
|-------|-------|-----------|------------|--------------|
| Copywriting | 4 | +0.10 | 0.57 | 0.47 |
| CRO | 1 | +0.13 | 0.80 | 0.67 |
| Cold Email | 2 | +0.07 | 0.53 | 0.46 |

### 5.3 Why Fewer Pairs Is Better

The v1 generator included 23 pairs where many had delta=0 (ties) or negative deltas. For DPO training, you want:
- **Chosen >> Rejected:** Strong signal that the skill improves output
- **Chosen is good:** The model learns from quality examples
- **Rejected is mediocre:** The model learns what to avoid
- **No ties:** Ties provide zero training signal

The v2 generator enforces these constraints, producing 7 high-signal pairs instead of 23 noisy ones.

### 5.4 Filters Applied

| Filter | Threshold | Pairs Filtered |
|--------|-----------|----------------|
| Minimum delta | 0.05 | 21 |
| Maximum rejected composite | 0.70 | 2 |
| Minimum chosen composite | 0.30 | 0 |
| Minimum specificity delta | -0.10 | 0 |
| Minimum word count | 30 | 0 |

---

## 6. Recommendations

### 6.1 Scoring Pipeline
1. **The v2 scoring is more informative** -- keep using it alongside v1 for backward compatibility
2. **Voice dimension needs tuning** -- it penalizes annotations/explanations too heavily. Consider splitting into "banned phrases" (hard fail) vs "formality level" (soft penalty)
3. **Actionability dimension is the most discriminating** -- it best separates with-skill from without-skill output

### 6.2 Skill Improvement
1. **CRO skill** should focus more on **actionability** -- teach the model to provide specific priority labels, impact estimates, and before/after examples
2. **Copywriting skill** should focus on **voice** -- reduce corporate jargon in annotations, maintain the depth improvement
3. **Cold-email skill** needs the most work -- the smallest delta suggests the skill isn't adding enough value over the base model

### 6.3 DPO Training
1. **Use v2 pairs** (7 high-quality) over v1 pairs (23 noisy)
2. **Consider lowering the delta threshold** to 0.03 if you need more training data
3. **Monitor for cold-email skill regression** -- some cold-email pairs show negative deltas

### 6.4 Next Iteration
1. Re-run skill generation with focus on cold-email improvements
2. Add more CRO tasks that test actionability specifically
3. Consider adding a "voice coach" sub-skill to copywriting to fix the -0.17 voice delta

---

## 7. Files Generated

| File | Description |
|------|-------------|
| `results/iteration-1/benchmark_v2.json` | Full v2 benchmark with per-dimension scores |
| `results/iteration-1/task_deltas_v2.json` | Per-task delta data for all 30 tasks |
| `results/iteration-1/{task_id}/grading_with_skill_v2.json` | V2 grading for with_skill variant |
| `results/iteration-1/{task_id}/grading_without_skill_v2.json` | V2 grading for without_skill variant |
| `dpo-data/dpo_training_pairs_v2.json` | Full DPO training data with quality metadata |
| `dpo-data/dpo_format_v2.json` | DPO-formatted pairs for fine-tuning |
| `dpo-data/quality_summary_v2.json` | Quality statistics and filter summary |
| `pipeline/analysis_report_v2.md` | This report |

---

## Appendix: Raw Per-Task Scores

| Task ID | Skill | With | Without | Delta | Top Dimension |
|---------|-------|------|---------|-------|---------------|
| copy_005 | copywriting | 0.56 | 0.39 | +0.18 | criteria +0.50 |
| cro_009 | cro | 0.80 | 0.67 | +0.13 | actionability +0.50 |
| cro_007 | cro | 0.86 | 0.76 | +0.10 | actionability +0.65 |
| copy_002 | copywriting | 0.58 | 0.50 | +0.08 | criteria +0.20 |
| cro_001 | cro | 0.82 | 0.74 | +0.08 | actionability +0.40 |
| cold_003 | cold-email | 0.58 | 0.51 | +0.07 | voice +0.30 |
| cold_008 | cold-email | 0.48 | 0.41 | +0.07 | structure +0.60 |
| copy_003 | copywriting | 0.58 | 0.51 | +0.07 | depth +0.15 |
| copy_001 | copywriting | 0.56 | 0.50 | +0.06 | criteria +0.30 |
| cro_003 | cro | 0.77 | 0.72 | +0.05 | actionability +0.27 |
| cro_005 | cro | 0.66 | 0.61 | +0.04 | actionability +0.25 |
| copy_008 | copywriting | 0.62 | 0.57 | +0.04 | depth +0.13 |
| copy_010 | copywriting | 0.45 | 0.41 | +0.04 | criteria +0.30 |
| cro_004 | cro | 0.69 | 0.66 | +0.03 | actionability +0.30 |
| cro_002 | cro | 0.73 | 0.70 | +0.03 | criteria +0.40 |
| cold_005 | cold-email | 0.34 | 0.31 | +0.02 | voice +0.15 |
| cro_010 | cro | 0.70 | 0.68 | +0.02 | criteria +0.10 |
| cold_006 | cold-email | 0.35 | 0.33 | +0.01 | specificity +0.10 |
| cold_001 | cold-email | 0.44 | 0.43 | +0.00 | criteria +0.18 |
| copy_009 | copywriting | 0.50 | 0.50 | +0.00 | criteria +0.10 |
| cold_007 | cold-email | 0.33 | 0.33 | -0.00 | structure +0.37 |
| cold_009 | cold-email | 0.35 | 0.36 | -0.01 | criteria +0.10 |
| cro_006 | cro | 0.80 | 0.81 | -0.02 | -- |
| copy_004 | copywriting | 0.50 | 0.52 | -0.02 | criteria +0.10 |
| copy_007 | copywriting | 0.56 | 0.57 | -0.02 | criteria +0.20 |
| cold_010 | cold-email | 0.33 | 0.36 | -0.02 | depth +0.02 |
| cold_002 | cold-email | 0.40 | 0.43 | -0.03 | criteria +0.09 |
| cold_004 | cold-email | 0.36 | 0.39 | -0.03 | depth +0.01 |
| cro_008 | cro | 0.69 | 0.74 | -0.05 | actionability +0.16 |
| copy_006 | copywriting | 0.47 | 0.53 | -0.06 | structure +0.20 |
