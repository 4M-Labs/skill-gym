# Contributing to SkillGym

SkillGym is a research project. Contributions are welcome in these areas:

- **New skills**: Add SKILL.md files for domains beyond marketing (coding, writing, research, etc.)
- **Evaluation tasks**: Add tasks to `pipeline/evals/tasks.json` for new skill domains
- **Scoring improvements**: Enhance `pipeline/score_outputs.py` with better evaluation dimensions
- **Bug fixes**: Fix issues in the pipeline scripts

## How to contribute

1. Fork the repo
2. Create a branch (`git checkout -b add-python-skill`)
3. Make your changes
4. Run the pipeline on your new skill to verify it works
5. Submit a pull request with your results

## Adding a new skill

1. Create `pipeline/skills/your-skill.md` following the existing format
2. Add 10 evaluation tasks to `pipeline/evals/tasks.json`
3. Run `python pipeline/pipeline.py --skill your-skill`
4. Include the benchmark results in your PR

## Code style

- Python 3.10+
- Type hints on public functions
- `ruff` for linting
