# Scoring Rubric

6-dimension weighted scoring system for evaluating with-skill vs without-skill outputs.

## Dimensions

| Dimension | Weight | What It Measures | Score Range |
|-----------|--------|------------------|-------------|
| Criteria Pass Rate | 0.25 | Binary pass/fail on verification criteria from tasks.json | 0.0 - 1.0 |
| Specificity | 0.20 | Concrete numbers, named tools/brands, specific recommendations | 0.0 - 1.0 |
| Actionability | 0.20 | Imperative verbs, before/after comparisons, impact estimates | 0.0 - 1.0 |
| Structure | 0.15 | Follows requested format, scannable headers, organized sections | 0.0 - 1.0 |
| Depth | 0.10 | Word count relative to task complexity, detail level, subsections | 0.0 - 1.0 |
| Voice | 0.10 | Matches requested tone, avoids banned patterns, no corporate jargon | 0.0 - 1.0 |

## Composite Score

```
composite = (criteria * 0.25) + (specificity * 0.20) + (actionability * 0.20) + (structure * 0.15) + (depth * 0.10) + (voice * 0.10)
```

## Delta

```
delta = composite_with_skill - composite_without_skill
```

Positive delta = skill improved performance. Negative delta = skill hurt performance.

## Per-Dimension Scoring Guidance

### Criteria Pass Rate (0.25)
Compare output against `verification_criteria` in tasks.json. Each criterion is binary (pass/fail). Score = passed / total criteria.

### Specificity (0.20)
- 0.0: Purely generic advice ("improve your headline")
- 0.3: Some specificity but vague ("use numbers in your headline")
- 0.6: Named examples ("change to 'Save 3 Hours Every Week'")
- 1.0: Multiple concrete, testable specifics with numbers and named tools

### Actionability (0.20)
- 0.0: Observations only ("your form is too long")
- 0.3: General recommendations ("reduce form fields")
- 0.6: Specific changes with before/after ("remove Confirm Password and Industry fields, reducing from 8 to 6 fields")
- 1.0: Prioritized changes with estimated impact ("P0: reduce form from 12 to 4 fields, estimated +30-50% completion rate")

### Structure (0.15)
- 0.0: Wall of text, no headers
- 0.3: Some headers but inconsistent formatting
- 0.6: Clear sections matching requested format
- 1.0: Tables, headers, bullet points, scannable at a glance

### Depth (0.10)
- 0.0: Under 100 words for a complex task
- 0.3: Addresses surface only
- 0.6: Covers main areas with supporting detail
- 1.0: Thorough coverage with subsections, examples, edge cases

### Voice (0.10)
- 0.0: Contains banned phrases ("I hope this finds you well", "leverage", "synergy")
- 0.3: Some corporate jargon or exclamation points
- 0.6: Clean voice, matches tone, minor issues
- 1.0: Perfect tone match, zero banned patterns, natural language

## Running the Scorer

```bash
cd skill-gym-repo/pipeline
uv run python score_outputs_v2.py \
  --results-dir results/<skill-name>/ \
  --tasks-file evals/<skill-name>/tasks.json \
  --output-dir results/<skill-name>/
```

Outputs:
- `benchmark_v2.json` - full benchmark with per-dimension breakdowns
- `task_deltas_v2.json` - per-task delta data
- `grading_*_v2.json` - per-task grading files
