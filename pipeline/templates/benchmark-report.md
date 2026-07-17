# SkillGym Benchmark Report: {skill_name}

## Skill Overview
- **Name**: {skill_name}
- **Description**: {skill_description}
- **Domain**: {domain}
- **Date generated**: {date}
- **Pipeline version**: 1.0

## Eval Summary
- Total tasks generated: {total_tasks}
- Tasks completed: {completed_tasks}
- Tasks skipped: {skipped_tasks} ({skip_reasons})

## Performance Summary
- **Mean delta**: {mean_delta}
- **Median delta**: {median_delta}
- **Positive delta count**: {positive_count}/{total_tasks} tasks
- **Negative delta count**: {negative_count}/{total_tasks} tasks

## Per-Dimension Analysis

| Dimension | With Skill | Without Skill | Delta |
|-----------|------------|---------------|-------|
| Criteria Pass Rate | {cpr_with} | {cpr_without} | {cpr_delta} |
| Specificity | {spec_with} | {spec_without} | {spec_delta} |
| Actionability | {act_with} | {act_without} | {act_delta} |
| Structure | {struct_with} | {struct_without} | {struct_delta} |
| Depth | {depth_with} | {depth_without} | {depth_delta} |
| Voice | {voice_with} | {voice_without} | {voice_delta} |

## Top Improvements
{#each top_improvements}
- **{task_id}** (delta: {delta}): {description}
{/#each}

## Areas of Concern
{#each concerns}
- **{task_id}** (delta: {delta}): {description}
{/#each}

## DPO Training Data
- Pairs generated: {total_pairs}
- Pairs after quality filtering: {filtered_pairs}
- Average delta: {avg_pair_delta}
- Average chosen score: {avg_chosen}
- Average rejected score: {avg_rejected}

## Trained Model (if applicable)
- Model path: `models/{skill_name}-dpo/`
- Training epochs: {epochs}
- Final loss: {final_loss}
- Training time: {training_time}

## Quality Gates
| Gate | Status | Details |
|------|--------|---------|
| Skill Effectiveness | {gate1_status} | Mean delta: {mean_delta} |
| Pair Count | {gate2_status} | {filtered_pairs} pairs |
| Quality Distribution | {gate3_status} | Chosen: {avg_chosen}, Rejected: {avg_rejected} |
| Training Loss | {gate4_status} | Final loss: {final_loss} |

## Recommendations
{#each recommendations}
- {text}
{/#each}
