# SkillGym

Turning public agent skills into verified reinforcement learning training environments.

## What This Is

A research paper and framework for compiling SKILL.md files (agent skill definitions hosted on GitHub) into RL training datasets for small language models.

The core thesis: public agent skills already contain the components needed for RL training. SKILL.md is the policy, evals are the task distribution, assertions are the reward function, and GitHub PRs are preference pairs. SkillGym connects these pieces.

## The Paper

**"Public Agent Skills Are Becoming the Next RL Dataset"**

- Full paper: [paper.md](./paper.md)
- Status: Working paper, July 2026

## Key Ideas

- Skill infrastructure maps directly to RL environment components
- Verification against human-authored assertions produces cleaner training signal than synthetic data generation
- Small models (1B-8B params) benefit most from narrow, verified procedural training
- GitHub's contribution model generates preference data through skill version history
- Domains with objective verification (code, schemas, operations) work best

## Repository Structure

```
skill-gym-paper/
  paper.md      Full research paper
  README.md     This file
```

## Contact

4M Labs Research
