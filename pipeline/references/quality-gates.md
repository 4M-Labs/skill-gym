# Quality Gates

Quality gates prevent the pipeline from wasting time on data that won't produce a useful model. Each gate has a clear threshold and action.

## Gate 1: Skill Effectiveness (after Step 4 - Scoring)

Check the mean delta in `benchmark_v2.json`.

| Mean Delta | Action | Rationale |
|------------|--------|-----------|
| <= 0 | **ABORT** | Skill does not improve model performance. Revisit the skill itself. |
| 0.001 - 0.02 | **WARN** | Marginal effect. Results may not be reliable for training. Proceed with caution. |
| >= 0.02 | **PROCEED** | Skill shows clear improvement. |

Also check task-level consistency:
- If > 50% of tasks have negative delta, warn that the skill may be inconsistent across task types.
- If < 30% of tasks have positive delta, the skill may only work for narrow use cases.

## Gate 2: Pair Count (after Step 5 - DPO Generation)

Check the number of pairs that passed quality filters in `quality_summary_v2.json`.

| Pair Count | Action | Rationale |
|------------|--------|-----------|
| 0 | **ABORT** | No training pairs passed filters. With-skill and without-skill outputs are not differentiable enough. |
| 1-4 | **WARN + PROCEED** | Very small dataset. Training will likely overfit. Consider generating more eval tasks (use `--num-tasks 20`). |
| 5-9 | **PROCEED with caution** | Usable but small. Note the dataset size in the report. |
| 10+ | **PROCEED** | Sufficient data for meaningful DPO training. |

## Gate 3: Quality Distribution (after Step 5 - DPO Generation)

Check the average chosen and rejected scores in `quality_summary_v2.json`.

| Metric | Threshold | Action |
|--------|-----------|--------|
| Avg chosen score | < 0.40 | WARN: Chosen outputs are not strong enough to learn from |
| Avg rejected score | > 0.60 | WARN: Rejected outputs are too good - the skill's advantage is unclear |
| Avg chosen - rejected | < 0.05 | WARN: Tiny margin. DPO training may not find useful signal. |

## Gate 4: Training Loss (after Step 6 - Fine-Tuning)

Check the training log output.

| Loss Pattern | Action | Rationale |
|--------------|--------|-----------|
| Loss decreased steadily | **PROCEED** | Training converged. Model learned from the data. |
| Loss did not decrease after 1 epoch | **WARN** | DPO data may not contain learnable signal. The chosen/rejected pairs may be too similar. |
| Loss oscillates wildly | **WARN** | Learning rate may be too high for this dataset size. Consider reducing lr. |
| Loss went to NaN | **ABORT** | Training collapsed. Check data quality - may have degenerate examples. |

## Gate 5: Final Report (after Step 7)

Produce the analysis document regardless of other gate outcomes. The report should include:
- Which gates passed/failed/warned
- Specific numbers for each gate
- Recommendations for next steps

## Decision Tree

```
Score outputs
  └─ Gate 1: Mean delta <= 0? ──YES──> ABORT (skill ineffective)
      └─ NO ──> Generate DPO pairs
          └─ Gate 2: 0 pairs? ──YES──> ABORT (no signal)
              └─ NO ──> Gate 3: Quality OK?
                  └─ NO ──> WARN (proceed with caution)
                  └─ YES ──> Train model (if requested)
                      └─ Gate 4: Loss OK?
                          └─ NO ──> WARN (training issues)
                          └─ YES ──> Generate report
                              └─ Gate 5: Always produce report
```

## Overriding Gates

Use `--force` flag on pipeline.py to skip quality gates and proceed regardless. This is useful when:
- You want to see the full pipeline output even with marginal results
- You're debugging a specific step
- You know the data is good despite the automated checks
