# SkillGym

**Public agent skills are becoming the next RL dataset.**

Grab any SKILL.md from GitHub, run controlled comparisons, and extract verified training data. No synthetic data generation. No external judge models. The skill's own instructions ARE the evaluation rubric.

[Paper (PDF)](./skillgym-paper.pdf) | [Reproduce](./REPRODUCIBILITY.md) | [Contributing](./CONTRIBUTING.md)

## Key Results

Fine-tuning Qwen2.5-1.5B-Instruct on 30 examples from 3 marketing skills:

| | Base | SFT (30 ex) | DPO (17 pairs) |
|--|------|-------------|----------------|
| **Composite Score** | 0.311 | **0.368** (+18.3%) | 0.318 (+2.3%) |
| **Tasks Improved** | -- | 20/30 (67%) | 17/30 (57%) |

**Per-skill SFT improvement:**

| Skill | Base | SFT | Delta | Improved |
|-------|------|-----|-------|----------|
| Cold-email | 0.210 | 0.318 | **+0.108** | 10/10 (100%) |
| Copywriting | 0.311 | 0.375 | **+0.064** | 6/10 (60%) |
| CRO | 0.412 | 0.410 | -0.001 | 4/10 (40%) |

Cold-email tasks showed 100% improvement rate, proving structured frameworks transfer directly to model competence. CRO showed minimal improvement, suggesting subjective criteria reduce training signal.

## How It Works

```
1. Grab SKILL.md          -- Any agent skill from GitHub
2. Generate evals          -- Skill instructions become test criteria
3. Spin two sub-agents     -- One WITH skill, one WITHOUT
4. Run both on same tasks  -- Controlled comparison
5. Score both              -- 6-dimension weighted scoring
6. Delta = training signal -- With-skill minus without-skill pass rate
7. Better pairs -> DPO     -- Preference data for RL training
```

The skill's structure IS the verifier. Each SKILL.md contains verification criteria, output format requirements, and quality standards. These become the automated scoring rubric -- no human annotation needed.

## Scoring

Outputs are evaluated across 6 weighted dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Criteria pass rate | 0.25 | Fraction of verification criteria met |
| Specificity | 0.20 | Concrete details vs generic advice |
| Actionability | 0.20 | Can the reader execute immediately |
| Structure | 0.15 | Required sections present and organized |
| Depth | 0.10 | Analytical depth beyond surface observations |
| Voice | 0.10 | Matches the skill's prescribed tone |

## Quick Start

```bash
git clone https://github.com/4M-Labs/skill-gym.git
cd skill-gym
pip install -r requirements.txt

# Run the full pipeline on all 3 skills
python pipeline/pipeline.py --all

# Or run on a single skill
python pipeline/pipeline.py --skill cold-email
```

## Training

```bash
# SFT (30 examples, ~22 min on RTX 4050)
python pipeline/train_sft.py \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --data pipeline/sft-data/sft_format.json \
  --output pipeline/models/skillgym-marketing-sft-v1

# DPO (17 preference pairs)
python pipeline/train_dpo.py \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --reference-model Qwen/Qwen2.5-1.5B-Instruct \
  --data pipeline/dpo-data/dpo_training_pairs.json \
  --output pipeline/models/skillgym-marketing-dpo-v3
```

**Hardware:** GPU with 6GB+ VRAM (tested on RTX 4050), 16GB RAM. Full training hyperparameters in the [reproducibility guide](./REPRODUCIBILITY.md).

## Repository Structure

```
skill-gym/
  README.md                       This file
  LICENSE                         MIT
  skillgym-paper.pdf              Full paper with charts
  REPRODUCIBILITY.md              Step-by-step reproduction guide
  CONTRIBUTING.md                 How to add skills and tasks
  pipeline/
    pipeline.py                   Full pipeline orchestrator
    score_outputs.py              6-dimension scoring engine
    generate_evals.py             Evals from SKILL.md
    generate_sft.py               SFT training data
    generate_dpo.py               DPO preference pairs
    train_sft.py                  SFT fine-tuning
    train_dpo.py                  DPO fine-tuning
    evaluate_model.py             Model evaluation
    generate_paper_pdf.py         PDF generation
    skills/                       3 marketing SKILL.md files
    evals/                        30 evaluation tasks
    results/
      dataset.json                Full dataset (30 tasks, 543KB)
      benchmark.json              Aggregated scores
      task_deltas.json            Per-task deltas
    evaluation/                   Fine-tuned model results
    sft-data/                     SFT training examples
    dpo-data/                     DPO preference pairs
```

## Findings

- **Structured skills transfer directly**: Cold-email tasks achieved 100% improvement rate -- the skill's framework (subject lines, opening lines, CTAs) directly improved model outputs
- **Subjective criteria reduce signal**: CRO tasks showed minimal improvement -- conversion optimization relies on judgment that doesn't transfer cleanly through prompts
- **SFT outperforms DPO at small scale**: 30 SFT examples beat 17 DPO pairs (+18.3% vs +2.3%). DPO likely needs hundreds of pairs to show meaningful improvement
- **Voice is the most learnable dimension**: DPO showed +0.054 improvement on voice alignment, the largest single-dimension gain
- **SkillOpt is the differentiator**: Using the skill's own verification criteria as the scoring rubric eliminates the need for external judges or synthetic data

## Acknowledgments

The three marketing skills (cold-email, copywriting, CRO) used in this research are adapted from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) by Corey Haines. These skills served as the real-world agent skills for our evaluation pipeline.

## Citation

```bibtex
@misc{horstman2026skillgym,
  title={SkillGym: Public Agent Skills as RL Training Data},
  author={Michiel Horstman and 4M Labs},
  year={2026},
  url={https://github.com/4M-Labs/skill-gym}
}
```

## License

MIT -- see [LICENSE](./LICENSE)

## Contact

4M Labs -- hello@4mlabs.io
