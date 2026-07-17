# SkillGym Model Evaluation Report

**Date:** 2026-07-17 00:37
**Base model:** Qwen/Qwen2.5-1.5B-Instruct
**Fine-tuned model:** Qwen/Qwen2.5-1.5B-Instruct + models/skillgym-marketing-dpo-v3
**Tasks evaluated:** 30

## Overall Results

| Metric | Base Model | Fine-Tuned | Delta |
|--------|-----------|------------|-------|
| **Composite Score** | 0.311 | 0.318 | **+0.007** |
| Positive deltas | - | - | 17/30 tasks |
| Negative deltas | - | - | 13/30 tasks |
| Neutral deltas | - | - | 0/30 tasks |
| Total generation time | 385.0s | 1385.8s | - |

## Per-Dimension Breakdown

| Dimension | Base | Fine-Tuned | Delta |
|-----------|------|------------|-------|
| Criteria Pass Rate (0.25) | +0.013 | - | +0.013 |
| Specificity (0.20) | +0.006 | - | +0.006 |
| Actionability (0.20) | -0.008 | - | -0.008 |
| Structure (0.15) | -0.005 | - | -0.005 |
| Depth (0.10) | -0.005 | - | -0.005 |
| Voice (0.10) | +0.054 | - | +0.054 |

## Per-Skill Breakdown

| Skill | Base | Fine-Tuned | Delta | Pos/Total |
|-------|------|------------|-------|-----------|
| copywriting | 0.311 | 0.290 | -0.021 | 4/10 |
| cold-email | 0.210 | 0.231 | +0.021 | 7/10 |
| cro | 0.412 | 0.432 | +0.020 | 6/10 |

## Per-Task Results

| Task | Base | Fine-Tuned | Delta | Time (base) | Time (ft) |
|------|------|------------|-------|-------------|-----------|
| copy_007 | 0.217 | 0.396 | +0.180 | 0.0s | 87.4s |
| cro_008 | 0.324 | 0.496 | +0.171 | 0.0s | 133.7s |
| cro_009 | 0.297 | 0.424 | +0.126 | 0.0s | 90.6s |
| cold_003 | 0.175 | 0.299 | +0.123 | 13.6s | 72.0s |
| cold_008 | 0.166 | 0.257 | +0.091 | 38.4s | 38.6s |
| cold_001 | 0.206 | 0.295 | +0.089 | 39.1s | 53.2s |
| copy_008 | 0.252 | 0.333 | +0.081 | 0.0s | 45.6s |
| cro_001 | 0.350 | 0.421 | +0.071 | 0.0s | 0.0s |
| cro_006 | 0.329 | 0.385 | +0.056 | 0.0s | 0.0s |
| cold_005 | 0.216 | 0.271 | +0.055 | 37.3s | 68.9s |
| copy_003 | 0.331 | 0.383 | +0.052 | 0.0s | 126.3s |
| cold_007 | 0.205 | 0.256 | +0.051 | 33.3s | 47.1s |
| cro_004 | 0.451 | 0.477 | +0.027 | 0.0s | 0.0s |
| cold_010 | 0.193 | 0.216 | +0.023 | 26.6s | 48.6s |
| cold_002 | 0.155 | 0.170 | +0.015 | 34.8s | 48.8s |
| copy_005 | 0.205 | 0.210 | +0.005 | 0.0s | 25.4s |
| cro_010 | 0.458 | 0.460 | +0.002 | 0.0s | 95.7s |
| copy_010 | 0.263 | 0.260 | -0.002 | 25.4s | 44.1s |
| copy_004 | 0.316 | 0.307 | -0.009 | 0.0s | 64.5s |
| cro_007 | 0.495 | 0.481 | -0.014 | 0.0s | 0.0s |
| cro_002 | 0.474 | 0.451 | -0.023 | 0.0s | 0.0s |
| cold_009 | 0.228 | 0.185 | -0.042 | 29.7s | 48.6s |
| cro_005 | 0.377 | 0.324 | -0.053 | 0.0s | 0.0s |
| cold_006 | 0.223 | 0.148 | -0.075 | 31.6s | 38.5s |
| copy_006 | 0.392 | 0.286 | -0.106 | 0.0s | 55.0s |
| cold_004 | 0.338 | 0.217 | -0.121 | 40.2s | 48.1s |
| copy_009 | 0.371 | 0.245 | -0.126 | 35.1s | 40.4s |
| copy_002 | 0.436 | 0.309 | -0.127 | 0.0s | 35.4s |
| copy_001 | 0.328 | 0.175 | -0.153 | 0.0s | 29.3s |
| cro_003 | 0.560 | 0.400 | -0.159 | 0.0s | 0.0s |

## Top 5 Improvements

1. **copy_007** (copywriting): +0.180 delta (0.217 -> 0.396)
1. **cro_008** (cro): +0.171 delta (0.324 -> 0.496)
1. **cro_009** (cro): +0.126 delta (0.297 -> 0.424)
1. **cold_003** (cold-email): +0.123 delta (0.175 -> 0.299)
1. **cold_008** (cold-email): +0.091 delta (0.166 -> 0.257)

## Top 5 Regressions

1. **cro_003** (cro): -0.159 delta (0.560 -> 0.400)
1. **copy_001** (copywriting): -0.153 delta (0.328 -> 0.175)
1. **copy_002** (copywriting): -0.127 delta (0.436 -> 0.309)
1. **copy_009** (copywriting): -0.126 delta (0.371 -> 0.245)
1. **cold_004** (cold-email): -0.121 delta (0.338 -> 0.217)

## Verdict

**MARGINAL IMPROVEMENT**

The fine-tuned model is slightly better. The signal may be too weak for reliable training.

Overall delta: **+0.007** (17 tasks improved, 13 regressed, 0 unchanged)

## Training Details

- Base model: Qwen/Qwen2.5-1.5B-Instruct
- Adapter: models/skillgym-marketing-dpo-v3
- DPO pairs used: 17 (from 3 skills: CRO, copywriting, cold-email)
- Training: 10 epochs, DPO beta=0.05, LoRA r=4 alpha=8, reference_free=True
- Final training loss: 11.82 (170 steps total)
- Training time: ~4 minutes
- Key fix: prompts now include VERIFICATION CRITERIA (v1 had none)
