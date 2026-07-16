# SkillGym

A framework for extracting verified training data from public agent skills.

**Status:** Working paper, not peer-reviewed. Experimental validation planned.

## Paper

**"Public Agent Skills Are Becoming the Next RL Dataset"**

Read the full paper: [skillgym-paper.pdf](./skillgym-paper.pdf)

## Method

1. Grab any SKILL.md from GitHub
2. Generate evals from the skill's own instructions
3. Spin two sub-agents: one WITH the skill, one WITHOUT
4. Run both on the same eval tasks
5. Score both using the generated evals
6. Delta = with-skill pass rate minus without-skill pass rate
7. Better pairs become DPO/GRPO training data

The skill's structure IS the verifier. No synthetic data generation. No external judge models.

## Key Claims

- Any SKILL.md can become a training environment through controlled comparison
- The performance delta isolates the skill's contribution to model behavior
- Eval-generated preferences are grounded in task completion, not model judgment
- Small models (1B-8B params) benefit most from narrow, verified procedural training

## Status

This is a working paper presenting a framework. The following work is planned:

- Proof-of-concept pipeline for 10-20 skills
- SFT, DPO, and GRPO training experiments
- Ecosystem survey of skill density and delta distribution
- Trust and safety testing for adversarial skills

## Repository

```
skill-gym/
  skillgym-paper.pdf   Research paper (PDF)
  README.md            This file
```

## Contact

4M Labs: hello@4mlabs.io
