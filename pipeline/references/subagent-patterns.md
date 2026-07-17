# Subagent Spawning Patterns

How to run with-skill vs without-skill comparisons using the `task` tool.

## Core Pattern

For each eval task, spawn TWO subagents:

1. **Agent A (with skill)**: Gets the full SKILL.md content + the task prompt
2. **Agent B (without skill)**: Gets only the task prompt (baseline)

Both run on the same task. The delta between their outputs measures the skill's value.

## Concurrency

**Cap at 4 subagents active at a time.** This prevents memory pressure on the host machine. Wait for a batch to complete before spawning the next batch.

For 10 tasks (20 subagents total):
- Batch 1: tasks 1-4 (8 subagents)
- Batch 2: tasks 5-8 (8 subagents)
- Batch 3: tasks 9-10 (4 subagents)

## Domain-Based Role Mapping

Set the subagent role based on the target skill's domain:

| Skill Domain | Role in Prompt | Example |
|--------------|----------------|---------|
| Marketing (CRO, copywriting, ads) | "marketing specialist" | CRO audit, landing page copy |
| Cold outreach (email, DM, calling) | "sales outreach specialist" | Cold email writing, follow-up sequences |
| Code (debugging, reviewing, building) | "software engineer" | Bug fixes, code review, API design |
| Writing (docs, blog, technical) | "professional writer" | Documentation, blog posts, reports |
| Design (UI, visual, branding) | "UI/UX designer" | Landing page design, brand identity |
| Data (analysis, pipelines, ML) | "data engineer" | ETL pipeline, data analysis |
| General / unknown | "domain specialist" | Any skill without clear domain |

## Prompt Templates

### Agent A (with skill)

```
You are a {role}. Use the following skill to complete the task.

## SKILL INSTRUCTIONS:
{full SKILL.md content of the TARGET skill, not this meta-skill}

## TASK:
{task prompt from tasks.json}

Provide your complete response. Be thorough and follow the skill's instructions precisely.
```

### Agent B (without skill)

```
You are a {role}. Complete the following task using only your general knowledge.

## TASK:
{task prompt from tasks.json}

Provide your complete response.
```

## Output File Format

Save each subagent's output with this header:

```markdown
# Task: {task_id}
# Skill: {skill_name}
# Agent: with_skill | without_skill

---

{actual response content from the subagent}
```

**File naming:**
- `results/{skill-name}/{task_id}_with_skill.md`
- `results/{skill-name}/{task_id}_without_skill.md`

## Resume Logic

Before spawning subagents, check for existing output files:
- If both `_with_skill.md` and `_without_skill.md` exist for a task, skip it
- If only one exists, the task was interrupted - re-run the missing one
- If neither exists, run both

This allows the pipeline to resume after interruption without re-running completed tasks.

## Timing Data

When a subagent completes, the task notification includes `total_tokens` and `duration_ms`. Save this to `timing.json` in the output directory:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

This data is only available at completion time - capture it immediately.
