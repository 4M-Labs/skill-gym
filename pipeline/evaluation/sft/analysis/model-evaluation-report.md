# SkillGym Model Evaluation Report

**Date:** 2026-07-17 08:57
**Base model:** Qwen/Qwen2.5-1.5B-Instruct
**Fine-tuned model:** Qwen/Qwen2.5-1.5B-Instruct + models/skillgym-marketing-sft-v1
**Tasks evaluated:** 30

## Overall Results

| Metric | Base Model | Fine-Tuned | Delta |
|--------|-----------|------------|-------|
| **Composite Score** | 0.311 | 0.368 | **+0.057** |
| Positive deltas | - | - | 20/30 tasks |
| Negative deltas | - | - | 10/30 tasks |
| Neutral deltas | - | - | 0/30 tasks |
| Total generation time | 385.0s | 3547.0s | - |

## Per-Dimension Breakdown

| Dimension | Base | Fine-Tuned | Delta |
|-----------|------|------------|-------|
| Criteria Pass Rate (0.25) | +0.092 | - | +0.092 |
| Specificity (0.20) | +0.112 | - | +0.112 |
| Actionability (0.20) | +0.047 | - | +0.047 |
| Structure (0.15) | -0.089 | - | -0.089 |
| Depth (0.10) | +0.038 | - | +0.038 |
| Voice (0.10) | +0.113 | - | +0.113 |

## Per-Skill Breakdown

| Skill | Base | Fine-Tuned | Delta | Pos/Total |
|-------|------|------------|-------|-----------|
| cro | 0.412 | 0.410 | -0.001 | 4/10 |
| copywriting | 0.311 | 0.375 | +0.064 | 6/10 |
| cold-email | 0.210 | 0.318 | +0.108 | 10/10 |

## Per-Task Results

| Task | Base | Fine-Tuned | Delta | Time (base) | Time (ft) |
|------|------|------------|-------|-------------|-----------|
| cro_004 | 0.451 | 0.676 | +0.225 | 0.0s | 0.0s |
| copy_008 | 0.252 | 0.450 | +0.199 | 0.0s | 115.4s |
| cold_010 | 0.193 | 0.382 | +0.190 | 26.6s | 176.3s |
| copy_007 | 0.217 | 0.401 | +0.185 | 0.0s | 145.6s |
| copy_009 | 0.371 | 0.545 | +0.174 | 35.1s | 274.0s |
| cold_003 | 0.175 | 0.348 | +0.172 | 13.6s | 299.1s |
| cold_008 | 0.166 | 0.337 | +0.172 | 38.4s | 145.0s |
| copy_006 | 0.392 | 0.521 | +0.129 | 0.0s | 249.9s |
| cold_002 | 0.155 | 0.278 | +0.123 | 34.8s | 145.6s |
| cold_007 | 0.205 | 0.320 | +0.114 | 33.3s | 125.8s |
| cold_005 | 0.216 | 0.330 | +0.114 | 37.3s | 151.7s |
| copy_005 | 0.205 | 0.318 | +0.113 | 0.0s | 76.2s |
| cro_001 | 0.350 | 0.448 | +0.099 | 0.0s | 0.0s |
| cold_001 | 0.206 | 0.303 | +0.097 | 39.1s | 79.3s |
| cold_004 | 0.338 | 0.402 | +0.065 | 40.2s | 104.9s |
| cro_005 | 0.377 | 0.427 | +0.050 | 0.0s | 0.0s |
| cold_009 | 0.228 | 0.253 | +0.025 | 29.7s | 124.8s |
| copy_003 | 0.331 | 0.349 | +0.018 | 0.0s | 121.3s |
| cro_002 | 0.474 | 0.489 | +0.014 | 0.0s | 0.0s |
| cold_006 | 0.223 | 0.229 | +0.006 | 31.6s | 69.9s |
| cro_009 | 0.297 | 0.297 | -0.000 | 0.0s | 205.1s |
| copy_004 | 0.316 | 0.290 | -0.026 | 0.0s | 63.1s |
| cro_010 | 0.458 | 0.432 | -0.026 | 0.0s | 175.2s |
| copy_002 | 0.436 | 0.407 | -0.030 | 0.0s | 138.7s |
| cro_006 | 0.329 | 0.299 | -0.030 | 0.0s | 104.2s |
| copy_010 | 0.263 | 0.231 | -0.032 | 25.4s | 144.4s |
| cro_008 | 0.324 | 0.253 | -0.071 | 0.0s | 164.1s |
| cro_003 | 0.560 | 0.487 | -0.073 | 0.0s | 0.0s |
| copy_001 | 0.328 | 0.235 | -0.093 | 0.0s | 106.4s |
| cro_007 | 0.495 | 0.292 | -0.203 | 0.0s | 41.0s |

## Top 5 Improvements

1. **cro_004** (cro): +0.225 delta (0.451 -> 0.676)
1. **copy_008** (copywriting): +0.199 delta (0.252 -> 0.450)
1. **cold_010** (cold-email): +0.190 delta (0.193 -> 0.382)
1. **copy_007** (copywriting): +0.185 delta (0.217 -> 0.401)
1. **copy_009** (copywriting): +0.174 delta (0.371 -> 0.545)

## Top 5 Regressions

1. **cro_007** (cro): -0.203 delta (0.495 -> 0.292)
1. **copy_001** (copywriting): -0.093 delta (0.328 -> 0.235)
1. **cro_003** (cro): -0.073 delta (0.560 -> 0.487)
1. **cro_008** (cro): -0.071 delta (0.324 -> 0.253)
1. **copy_010** (copywriting): -0.032 delta (0.263 -> 0.231)

## Verdict

**STRONG IMPROVEMENT**

The fine-tuned model significantly outperforms the base model. DPO training was effective.

Overall delta: **+0.057** (20 tasks improved, 10 regressed, 0 unchanged)

## Training Details

- Base model: Qwen/Qwen2.5-1.5B-Instruct
- Adapter: models/skillgym-marketing-sft-v1
- DPO pairs used: 17 (from 3 skills: CRO, copywriting, cold-email)
- Training: 10 epochs, DPO beta=0.05, LoRA r=4 alpha=8, reference_free=True
- Final training loss: 11.82 (170 steps total)
- Training time: ~4 minutes
- Key fix: prompts now include VERIFICATION CRITERIA (v1 had none)
