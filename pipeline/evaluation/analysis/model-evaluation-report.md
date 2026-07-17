# SkillGym Model Evaluation Report

**Date:** 2026-07-16 20:44
**Base model:** Qwen/Qwen2.5-1.5B-Instruct
**Fine-tuned model:** Qwen/Qwen2.5-1.5B-Instruct + N/A
**Tasks evaluated:** 30

## Overall Results

| Metric | Base Model | Fine-Tuned | Delta |
|--------|-----------|------------|-------|
| **Composite Score** | 0.332 | 0.317 | **-0.014** |
| Positive deltas | - | - | 13/30 tasks |
| Negative deltas | - | - | 17/30 tasks |
| Neutral deltas | - | - | 0/30 tasks |
| Total generation time | 1469.0s | 1804.3s | - |

## Per-Dimension Breakdown

| Dimension | Base | Fine-Tuned | Delta |
|-----------|------|------------|-------|
| Criteria Pass Rate (0.25) | -0.033 | - | -0.033 |
| Specificity (0.20) | +0.007 | - | +0.007 |
| Actionability (0.20) | -0.009 | - | -0.009 |
| Structure (0.15) | -0.043 | - | -0.043 |
| Depth (0.10) | +0.013 | - | +0.013 |
| Voice (0.10) | -0.006 | - | -0.006 |

## Per-Skill Breakdown

| Skill | Base | Fine-Tuned | Delta | Pos/Total |
|-------|------|------------|-------|-----------|
| cold-email | 0.231 | 0.224 | -0.008 | 4/10 |
| copywriting | 0.331 | 0.328 | -0.003 | 6/10 |
| cro | 0.433 | 0.401 | -0.032 | 3/10 |

## Per-Task Results

| Task | Base | Fine-Tuned | Delta | Time (base) | Time (ft) |
|------|------|------------|-------|-------------|-----------|
| cold_007 | 0.133 | 0.289 | +0.156 | 38.7s | 49.9s |
| copy_007 | 0.323 | 0.412 | +0.089 | 35.4s | 91.6s |
| copy_003 | 0.392 | 0.476 | +0.083 | 53.3s | 122.3s |
| copy_008 | 0.277 | 0.349 | +0.072 | 31.0s | 56.8s |
| cold_009 | 0.126 | 0.180 | +0.054 | 35.7s | 39.1s |
| copy_006 | 0.397 | 0.449 | +0.052 | 68.4s | 115.5s |
| cro_008 | 0.340 | 0.380 | +0.040 | 66.9s | 105.3s |
| copy_002 | 0.255 | 0.285 | +0.030 | 32.5s | 71.5s |
| copy_009 | 0.286 | 0.299 | +0.013 | 40.0s | 26.1s |
| cro_001 | 0.376 | 0.387 | +0.012 | 61.0s | 71.4s |
| cold_006 | 0.192 | 0.199 | +0.007 | 33.7s | 23.5s |
| cold_004 | 0.274 | 0.278 | +0.004 | 37.0s | 40.1s |
| cro_002 | 0.432 | 0.434 | +0.002 | 57.8s | 50.8s |
| cro_009 | 0.392 | 0.391 | -0.001 | 61.9s | 117.4s |
| cro_007 | 0.504 | 0.493 | -0.011 | 53.6s | 56.5s |
| cro_005 | 0.374 | 0.360 | -0.014 | 56.4s | 41.9s |
| cold_002 | 0.263 | 0.244 | -0.019 | 57.9s | 38.7s |
| copy_010 | 0.367 | 0.347 | -0.020 | 49.6s | 45.4s |
| cold_008 | 0.240 | 0.218 | -0.022 | 28.7s | 41.3s |
| cold_003 | 0.303 | 0.276 | -0.027 | 47.8s | 58.1s |
| cro_004 | 0.468 | 0.441 | -0.027 | 68.4s | 49.9s |
| cro_010 | 0.475 | 0.442 | -0.033 | 65.0s | 138.4s |
| copy_004 | 0.289 | 0.255 | -0.035 | 23.8s | 38.3s |
| cold_001 | 0.253 | 0.205 | -0.048 | 39.0s | 25.0s |
| cold_010 | 0.290 | 0.202 | -0.088 | 33.6s | 33.1s |
| copy_005 | 0.313 | 0.224 | -0.089 | 40.4s | 42.3s |
| cold_005 | 0.242 | 0.145 | -0.097 | 47.8s | 36.7s |
| cro_006 | 0.476 | 0.350 | -0.125 | 59.3s | 60.2s |
| cro_003 | 0.489 | 0.327 | -0.162 | 83.8s | 52.4s |
| copy_001 | 0.414 | 0.188 | -0.226 | 60.3s | 64.8s |

## Top 5 Improvements

1. **cold_007** (cold-email): +0.156 delta (0.133 -> 0.289)
1. **copy_007** (copywriting): +0.089 delta (0.323 -> 0.412)
1. **copy_003** (copywriting): +0.083 delta (0.392 -> 0.476)
1. **copy_008** (copywriting): +0.072 delta (0.277 -> 0.349)
1. **cold_009** (cold-email): +0.054 delta (0.126 -> 0.180)

## Top 5 Regressions

1. **copy_001** (copywriting): -0.226 delta (0.414 -> 0.188)
1. **cro_003** (cro): -0.162 delta (0.489 -> 0.327)
1. **cro_006** (cro): -0.125 delta (0.476 -> 0.350)
1. **cold_005** (cold-email): -0.097 delta (0.242 -> 0.145)
1. **copy_005** (copywriting): -0.089 delta (0.313 -> 0.224)

## Verdict

**REGRESSION**

The fine-tuned model performs worse. The DPO data may be noisy or the training config needs adjustment.

Overall delta: **-0.014** (13 tasks improved, 17 regressed, 0 unchanged)

## Training Details

- Base model: Qwen/Qwen2.5-1.5B-Instruct
- Adapter: N/A
- DPO pairs used: 23 (from 3 skills: CRO, copywriting, cold-email)
- Training: 3 epochs, DPO beta=0.1, LoRA r=8 alpha=16
- Final training loss: 0.1084
- Training time: ~2.5 minutes
