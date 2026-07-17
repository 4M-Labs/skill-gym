# Reproducing the Results

This document explains how to reproduce the SkillGym experiments from the paper.

## Hardware requirements

- GPU with 6GB+ VRAM (tested on RTX 4050)
- 16GB RAM
- 20GB disk space for models

## Software requirements

- Python 3.10+
- PyTorch 2.0+ with CUDA
- ~45 minutes for full reproduction

## Setup

```bash
git clone https://github.com/4M-Labs/skill-gym.git
cd skill-gym
pip install -r requirements.txt
```

## Step 1: Generate evaluation tasks

```bash
python pipeline/generate_evals.py
```

This reads the 3 skills in `pipeline/skills/` and generates 10 tasks per skill (30 total) in `pipeline/evals/tasks.json`.

## Step 2: Run the benchmark

```bash
python pipeline/pipeline.py --all
```

This runs each task with and without the skill, scores both outputs across 6 dimensions, and writes results to `pipeline/results/`.

## Step 3: Generate SFT training data

```bash
python pipeline/generate_sft.py
```

Reads the benchmark results and creates 30 SFT training examples in `pipeline/sft-data/`.

## Step 4: Train the SFT model

```bash
python pipeline/train_sft.py \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --data pipeline/sft-data/sft_format.json \
  --output pipeline/models/skillgym-marketing-sft-v1 \
  --epochs 10 \
  --lr 2e-5 \
  --lora-r 8 \
  --lora-alpha 16
```

Training takes approximately 22 minutes on an RTX 4050.

## Step 5: Generate DPO training data

```bash
python pipeline/generate_dpo.py
```

Creates preference pairs from the benchmark results in `pipeline/dpo-data/`.

## Step 6: Train the DPO model

```bash
python pipeline/train_dpo.py \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --reference-model Qwen/Qwen2.5-1.5B-Instruct \
  --data pipeline/dpo-data/dpo_training_pairs.json \
  --output pipeline/models/skillgym-marketing-dpo-v3 \
  --epochs 3 \
  --lr 5e-5 \
  --lora-r 8 \
  --lora-alpha 16 \
  --max-length 768
```

## Step 7: Evaluate fine-tuned models

```bash
python pipeline/evaluate_model.py \
  --base-model Qwen/Qwen2.5-1.5B-Instruct \
  --finetuned-model pipeline/models/skillgym-marketing-dpo-v3
```

Results are written to `pipeline/evaluation/`.

## Expected results

| Model | Composite Score | Delta | Tasks Improved |
|-------|----------------|-------|----------------|
| Base (Qwen2.5-1.5B) | 0.311 | -- | -- |
| SFT (30 examples) | 0.368 | +0.057 | 20/30 (67%) |
| DPO (17 pairs) | 0.318 | +0.007 | 17/30 (57%) |

## Scoring dimensions

Outputs are scored on 6 weighted dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Criteria pass rate | 0.25 | Fraction of verification criteria met |
| Specificity | 0.20 | Concrete details vs generic advice |
| Actionability | 0.20 | Can the reader execute immediately |
| Structure | 0.15 | Required sections present and organized |
| Depth | 0.10 | Analytical depth beyond surface observations |
| Voice | 0.10 | Matches the skill's prescribed tone |

## Dataset

The complete evaluation dataset (30 tasks x 2 conditions with full outputs and scores) is available in `pipeline/results/dataset.json` (543KB).

## Citation

```bibtex
@misc{horstman2026skillgym,
  title={SkillGym: Public Agent Skills as RL Training Data},
  author={Michiel Horstman and 4M Labs},
  year={2026},
  url={https://github.com/4M-Labs/skill-gym}
}
```
