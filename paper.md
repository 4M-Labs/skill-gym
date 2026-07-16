# Public Agent Skills Are Becoming the Next RL Dataset

**A technical thesis on turning procedural skill definitions into verified reinforcement learning environments for small models.**

Author: 4M Labs Research  
Date: July 2026  
Status: Working paper

---

## Abstract

A quiet shift is happening in the open-source AI ecosystem. Thousands of structured agent skill definitions, files named SKILL.md hosted on GitHub, are accumulating in public repositories. Each one encodes a procedural policy: step-by-step instructions for accomplishing a task, bundled with evaluation scripts, assertions, grading logic, and benchmark infrastructure. These were designed to guide large language models at inference time. But their structure maps, with startling precision, to the components needed for reinforcement learning training environments.

This paper argues that public agent skills are becoming a distributed curriculum for post-training small language models. The mapping is direct: SKILL.md is the policy, evals and assertions are the task distribution, the grader is the reward function, GitHub pull requests are human curriculum generation, rollout traces are training episodes, and pass/fail outcomes are preference pairs or scalar rewards. The infrastructure already exists. What is missing is the compiler that connects these pieces at scale.

We describe SkillGym, a verified skill environment framework that ingests public SKILL.md files, extracts their training signal, and produces structured datasets for supervised fine-tuning (SFT), direct preference optimization (DPO), and group relative policy optimization (GRPO). We discuss which domains benefit most from this approach, the trust and sandboxing requirements for executing public skills, and why narrow procedural competence is exactly what small models need.

---

## 1. Introduction: Why Skills Are More Than Prompts

The agent skills ecosystem emerged from a practical problem: large language models are capable but unfocused. They can write code, but they do not know your deployment process. They can analyze data, but they do not know your schema conventions. Skills solve this by injecting domain-specific procedural knowledge at inference time.

A typical SKILL.md file contains structured instructions (what to do and in what order), bundled scripts (deterministic operations that should not be left to the model), evaluation criteria (how to tell if the output is correct), and references (domain documentation loaded on demand). The Anthropic skill-creator, which seeded much of this ecosystem, added eval pipelines, benchmark aggregation, blind comparison, grading agents, and trigger optimization. What started as prompt engineering became something closer to software engineering with evaluation gates.

Here is the observation that motivates this paper: the components of a skill map directly onto the components of a reinforcement learning environment.

| Skill Component | RL Equivalent |
|----------------|---------------|
| SKILL.md instructions | Policy (what the agent should do) |
| evals.json prompts | Task distribution (what problems to solve) |
| Assertions and expectations | Reward signal (what counts as success) |
| Grader agent | Reward function (scoring mechanism) |
| Rollout transcripts | Training episodes (state-action sequences) |
| Pass/fail outcomes | Preference pairs or scalar rewards |
| GitHub PRs and issues | Human curriculum generation |
| Benchmark comparisons | Policy evaluation |

This is not a metaphor. The structure is literal. A skill directory, with its SKILL.md, evals folder, scripts, and grading infrastructure, is a self-contained RL environment waiting to be compiled into training data.

The implications are significant. We are not talking about synthetic data generation or distillation from larger models, which dominates current post-training discourse. We are talking about a curriculum that was built by thousands of independent contributors solving real problems, tested against real outputs, and iterated on through real feedback loops. The training signal is grounded in actual task completion, not model-generated approximations of what success looks like.

---

## 2. The Current Skill Ecosystem

As of mid-2026, the skill ecosystem spans multiple platforms and communities. Anthropic's Claude ecosystem has the most mature skills infrastructure, with the skill-creator providing evaluation pipelines, benchmark aggregation, and blind comparison tools. Open-source skill repositories on GitHub contain thousands of SKILL.md files across domains: code review, database operations, deployment, document generation, data analysis, API integration, testing, and more.

The structure is remarkably consistent across contributors. Most skills follow the same pattern: YAML frontmatter with name and description, markdown instructions in the body, optional scripts directory for deterministic operations, optional references directory for domain documentation, and an evals directory with test cases and assertions.

What makes this ecosystem valuable for training is not the volume of skills, but the depth of verification infrastructure surrounding them. The skill-creator's pipeline produces: graded evaluation results with pass/fail per assertion, timing and token usage metrics, blind A/B comparisons between skill versions, benchmark aggregations with statistical confidence intervals, and human feedback loops through HTML review interfaces.

Each of these outputs is a training signal. The graded results tell you what the model should have done. The timing data tells you about computational cost. The blind comparisons tell you which approach is better. The human feedback tells you what actually matters to users. The iteration history tells you how skills improve over time.

GitHub's contribution model adds another layer. Skills evolve through pull requests. Each PR is a diff between two versions of a policy, accompanied by evaluation results showing whether the change improved outcomes. This is preference data with structure: before/after pairs, graded by a verifier, with quantitative evidence of improvement.

---

## 3. From SKILL.md to SkillGym

SkillGym is a framework for compiling public agent skills into verified RL training environments. The core insight is that the compilation process is mostly extraction and structuring, not generation. The training signal already exists in the skill infrastructure. It just needs to be connected.

### 3.1 Environment Structure

A SkillGym environment consists of five layers:

**Policy layer**: The SKILL.md file itself, parsed into structured instructions. The model being trained learns to follow these instructions, either through SFT on successful rollouts or through RL with the skill as a constraint.

**Task layer**: The evals.json file, which defines the distribution of problems the skill addresses. Each eval provides a prompt, optional input files, and expected outcomes. This is the task distribution for training.

**Reward layer**: The assertions and grading infrastructure. Assertions define binary pass/fail criteria. The grader evaluates outputs against these criteria. Together they form the reward function: a mapping from (policy, task, output) to a scalar or vector reward.

**Episode layer**: Rollout transcripts from skill execution. When a model follows a skill to complete a task, the transcript records every state, action, and tool call. These are training episodes: sequences of (observation, action, reward) tuples.

**Curriculum layer**: Version history and human feedback. Skills evolve over time. Each version represents a policy improvement. Human feedback on outputs provides additional reward signal beyond automated assertions.

### 3.2 Compilation Pipeline

The compilation pipeline has four stages:

**Extraction**: Parse SKILL.md files, evals.json, assertions, and grading scripts into a standardized intermediate representation. This handles variations in skill structure across different authors and platforms.

**Execution**: Run the skill against its own evals using a base model. Record full transcripts, tool calls, timing, and outcomes. This produces the rollout dataset. Execute in sandboxed environments to prevent code execution risks from public skills.

**Verification**: Grade each rollout using the skill's own assertion infrastructure. Produce labeled outcomes: which assertions passed, which failed, what the reward signal is. This is the critical step that distinguishes SkillGym from synthetic data generation. The verification comes from the skill author's own test suite, not from a judge model.

**Structuring**: Format the verified rollouts into training datasets. For SFT: (prompt, skill, successful_trajectory) tuples. For DPO: (prompt, skill, winning_trajectory, losing_trajectory) pairs. For GRPO: (prompt, skill, trajectory_group, rewards) tuples.

### 3.3 Verification Is the Moat

The key differentiator is verification. Synthetic data generation produces model outputs scored by model judges. This creates a feedback loop where the judge's biases shape the training data, which shapes the next model, which shapes the next judge. Verification against human-authored assertions breaks this loop.

A skill author writes assertions like "the output includes the name John Smith" or "the spreadsheet has a SUM formula in cell B10". These are grounded in the actual task requirements, not in what a judge model thinks the output should look like. When a training example passes these assertions, it has been verified against a human-defined notion of correctness.

This is particularly valuable for procedural tasks where correctness is objective. Code that runs. Schemas that validate. Documents that contain required sections. Deployments that pass health checks. For these domains, automated verification is reliable and the training signal is clean.

---

## 4. Training Pipelines

### 4.1 Supervised Fine-Tuning (SFT)

SFT with skills is straightforward. For each skill, execute the skill against its evals with a base model. Filter to rollouts where all assertions pass. Use these as (prompt, successful_trajectory) training examples.

The quality of SFT data depends on the assertion coverage. Skills with comprehensive assertions produce clean training signal. Skills with sparse assertions produce noisy signal, where "successful" rollouts may still contain suboptimal behavior.

The skill-creator's evaluation infrastructure helps here. Its grading system produces per-assertion pass/fail with evidence, not just aggregate scores. This allows selective training: use only rollouts where specific, high-confidence assertions passed, rather than treating aggregate pass rate as a binary quality filter.

### 4.2 Direct Preference Optimization (DPO)

DPO requires preference pairs: (prompt, preferred_trajectory, dispreferred_trajectory). Skills generate these naturally through their version history.

When a skill author submits a pull request that improves a skill, the before/after versions produce two different trajectories for the same prompts. The version with higher assertion pass rates is the preferred trajectory. The version with lower pass rates is the dispreferred trajectory.

This gives us preference pairs with several desirable properties: the preference is grounded in assertion performance, not model judgment; the pairs share the same prompt and task, isolating the skill improvement as the only variable; and the preference comes from real human curation of skill quality, not synthetic generation.

For skills without version history, preference pairs can be constructed from within-skill variation. Run the skill multiple times with different temperature settings or random seeds. Use assertion pass rates to label which trajectories are preferred.

### 4.3 Group Relative Policy Optimization (GRPO)

GRPO, introduced by DeepSeek, optimizes policy using group-level rewards without a value function. It requires sampling multiple trajectories per prompt, computing rewards for each, and using the group statistics to compute advantage.

Skills are a natural fit. For each eval prompt, sample K trajectories from the current policy. Score each trajectory using the skill's assertion infrastructure. The assertion pass rate serves as the reward signal. GRPO updates the policy to increase the probability of high-reward trajectories relative to the group.

The advantage of GRPO over DPO for skills is that it does not require pre-computed preference pairs. It generates its own training signal from the current policy's outputs, making it more robust to distribution shift as the policy improves.

### 4.4 Reward Shaping

The assertion-based reward can be extended with additional signals from the skill infrastructure:

**Tool usage efficiency**: The metrics.json tracks tool calls. Penalize excessive tool calls for the same operation.

**Token efficiency**: The timing.json tracks token usage. Reward trajectories that accomplish the task with fewer tokens, holding assertion pass rate constant.

**Time efficiency**: Execution time provides a signal about computational cost. Useful for deployment optimization.

**Human feedback**: The feedback.json from the skill-creator's review interface provides additional reward signal beyond automated assertions.

These shaped rewards allow multi-objective optimization: maximize task completion while minimizing cost, or maximize user satisfaction while maintaining assertion pass rates.

---

## 5. Domains That Work

Not all skills are equally suitable for RL training. The approach works best in domains where verification is reliable and the task structure is procedural.

### 5.1 Strong Domains

**Code generation and review**: Code either runs or it does not. Linters catch style violations. Unit tests verify behavior. Skills like code-quality, code-review, and database produce verifiable outputs. The assertion infrastructure maps cleanly to test suites.

**Schema and data operations**: Database migrations either apply cleanly or they do not. Data transformations either preserve invariants or they break them. Skills that operate on structured data have strong automated verification.

**Document generation**: Invoices have required fields. Proposals have structural requirements. Contracts have clause completeness. Skills that generate business documents can verify output structure, required content, and formatting compliance.

**Deployment and operations**: Health checks pass or fail. Services start or crash. Deployments complete or error. Operations skills have the strongest verification because the infrastructure provides ground truth.

**Testing and quality**: Test suites either pass or fail. Coverage metrics are objective. Linting results are deterministic. Skills in the testing domain have built-in verification.

### 5.2 Moderate Domains

**API integration**: API calls either succeed or return errors. Response schemas either validate or they do not. Verification is strong for the mechanics but weaker for the business logic.

**Data analysis**: Analyses can verify data integrity, statistical method correctness, and output format. But the quality of insights is partially subjective.

### 5.3 Weak Domains

**Creative writing**: Style, tone, and quality are subjective. Automated assertions can check structure and presence of elements but not artistic merit.

**Strategy and planning**: The quality of strategic thinking is hard to automate. Assertions can verify completeness of analysis but not the quality of recommendations.

**UX design**: Visual quality and user experience are fundamentally subjective. Automated verification is limited to structural constraints.

The practical implication: focus SkillGym compilation on strong and moderate domains first. These produce the cleanest training signal and the most reliable verification.

---

## 6. The Product Angle

SkillGym is not just a research framework. It has a clear product form: a dataset compiler and benchmark report service.

### 6.1 Dataset Compiler

The compiler ingests public skill repositories and produces training-ready datasets. Inputs: GitHub repositories containing SKILL.md files with eval infrastructure. Outputs: structured datasets for SFT, DPO, and GRPO training, with per-example quality scores based on assertion pass rates.

The compiler handles the messy work: parsing diverse skill structures, executing skills in sandboxed environments, grading rollouts against assertions, deduplicating across similar skills, and filtering by quality thresholds.

A dataset consumer, whether a model lab or an individual fine-tuner, receives a ready-to-use training dataset with metadata: which skill each example came from, what assertions were used for verification, what the pass rate was, and what the computational cost of generating the example was.

### 6.2 Benchmark Reports

The second product form is benchmark reports. For each skill domain, aggregate performance metrics across models: which models follow skills most effectively, where models fail on specific assertion types, how skill complexity correlates with model performance, and what the cost-performance tradeoff looks like.

These reports serve two audiences: skill authors who want to know if their skills work well across models, and model developers who want to know where their models need improvement on procedural tasks.

The benchmark infrastructure from the skill-creator, with its statistical aggregation, variance analysis, and analyst observations, provides the foundation. SkillGym extends it with cross-skill and cross-domain aggregation.

---

## 7. Trust and Sandboxing

Executing public skills for training data compilation raises security concerns that must be taken seriously.

### 7.1 Threat Model

A malicious skill author could include: code that exfiltrates data during execution, code that modifies the host system, prompts that attempt to extract secrets from the execution environment, and assertions that reward harmful behavior.

These are real risks. Public skills are written by unknown contributors. The instruction-following nature of skills means the executing model will attempt to follow instructions in the SKILL.md and execute bundled scripts.

### 7.2 Mitigation

**Sandboxed execution**: All skill execution for training data compilation must happen in isolated environments. Docker containers with no network access, no persistent storage, and no access to host systems. Each eval runs in a fresh container.

**Static analysis**: Before execution, analyze bundled scripts for known dangerous patterns: network calls, file system access outside the working directory, environment variable reads, subprocess execution beyond declared dependencies.

**Assertion auditing**: Review assertions to ensure they do not reward harmful behavior. An assertion like "the output contains the contents of /etc/passwd" is a red flag.

**Content scanning**: Scan SKILL.md files for prompt injection attempts: instructions that ask the executing model to ignore its safety guidelines, exfiltrate data, or take unauthorized actions.

**Rate limiting and monitoring**: Limit execution time and resource usage. Monitor for anomalous behavior: unexpected network connections, excessive file writes, or resource consumption patterns that indicate abuse.

### 7.3 Trust Levels

Not all skills require the same trust level. Skills with no bundled scripts, only markdown instructions, are lower risk. Skills with Python scripts that do data transformation are moderate risk. Skills with scripts that access external services or the filesystem broadly are high risk.

The compilation pipeline should assign trust levels and apply appropriate sandboxing. Low-trust skills get basic isolation. High-trust skills get full sandboxing with monitoring.

---

## 8. Small Model Advantage

The current post-training discourse focuses on large models: scaling laws, massive RL runs on frontier models, and reinforcement learning from human feedback at billion-parameter scale. SkillGym targets the opposite end: small models (1B to 8B parameters) that need narrow procedural competence.

### 8.1 Why Small Models

Large models are generalists. They can do almost anything, but they are expensive to run, slow to serve, and overkill for many applications. A model that only needs to generate database migrations, review pull requests, or format invoices does not need 70B parameters.

Small models are cheap to fine-tune. A 3B parameter model can be fine-tuned on a single GPU in hours. This makes iterative training feasible: compile a skill dataset, train, evaluate, improve the dataset, repeat.

Small models are cheap to serve. A fine-tuned 3B model on a single GPU costs orders of magnitude less to serve than a general-purpose 70B model. For applications where the task distribution is narrow and well-defined, this cost advantage is decisive.

### 8.2 Why Skills Fit Small Models

Skills encode narrow competence. A skill for database migrations teaches the model to do one thing well. A skill for invoice generation teaches the model to follow a specific format. This is exactly what small models need: focused training signal on a specific task distribution, not broad generalization across all possible tasks.

The verification infrastructure ensures training quality. Small models have less capacity to recover from noisy training data. Clean, verified training examples are more important for small models than for large ones, which can average out noise through scale.

The curriculum structure enables progressive training. Start with simple skills (format a document), move to moderate skills (generate a migration), then to complex skills (deploy a service). This progression builds capability incrementally, which is more effective for small models than attempting everything at once.

### 8.3 The Economics

The economics are compelling. A small model lab can: compile a skill dataset from public repositories for near-zero cost (compute for execution and grading), fine-tune a 3B model on a single GPU for a few dollars, serve the model at a fraction of the cost of a general-purpose API, and iterate on the training loop in hours, not weeks.

Compare this to the alternative: training a general-purpose model from scratch, which costs millions, or fine-tuning on synthetic data, which requires a judge model and produces lower-quality signal. SkillGym offers a third path: leverage the distributed curriculum that the open-source community has already built.

---

## 9. Related Work

The closest existing work falls into several categories:

**Skill and tool learning**: Prior work on tool use in language models (Toolformer, Gorilla, ToolLLM) focuses on teaching models to call external APIs. Skills are broader: they encode procedural knowledge about how to accomplish tasks, not just how to call tools.

**Self-improvement and self-play**: Self-play methods (SPIN, Self-Rewarding LM) use the model's own outputs as training signal. SkillGym differs by using human-authored verification infrastructure, not model self-evaluation.

**Constitutional AI and RLAIF**: CAI uses AI-generated feedback for RL training. SkillGym uses human-authored assertions, which are more grounded but less scalable.

**Code generation benchmarks**: HumanEval, MBPP, and SWE-bench evaluate code generation with execution-based verification. SkillGym extends this pattern beyond code to any domain with verifiable assertions.

**Open-source datasets**: OpenHermes, UltraChat, and similar datasets provide training data from diverse sources. SkillGym is distinct in that its data comes from a structured, verified source with built-in quality signals.

The gap in existing work is the connection between the skill ecosystem and RL training. Skills were designed for inference-time guidance. Recognizing them as training environments is the contribution of this paper.

---

## 10. Conclusion: Skills as Executable Curricula

The agent skills ecosystem has accumulated something valuable without realizing it: a distributed curriculum for training models. Each SKILL.md file is a policy. Each eval suite is a task distribution. Each assertion is a reward signal. Each GitHub PR is a preference pair. Each grading result is a verified outcome.

SkillGym connects these pieces. It compiles public skills into verified RL training environments, producing clean training signal for SFT, DPO, and GRPO. It targets small models that need narrow procedural competence, not broad generalization. It leverages human-authored verification infrastructure to avoid the feedback loops of synthetic data generation.

The practical outcome is a new training paradigm: compile skills into datasets, train small models on those datasets, evaluate against the same skill assertions, and iterate. The curriculum is already written. The verification is already done. The infrastructure is already built. The compiler is what is missing.

For model labs, SkillGym offers a cost-effective path to training small, specialized models. For skill authors, it offers recognition that their work has value beyond inference-time guidance. For the open-source AI ecosystem, it offers a demonstration that distributed, community-built infrastructure can produce training resources that rival or exceed what large labs generate internally.

The skills are already there. We just need to compile them.

---

## Appendix: SkillGym Architecture Overview

```
Public Skill Repositories
        |
        v
  [ Extraction ]
  Parse SKILL.md, evals, assertions, scripts
        |
        v
  [ Execution ]
  Run skills against evals in sandboxed environments
  Record transcripts, tool calls, timing
        |
        v
  [ Verification ]
  Grade rollouts using skill's own assertions
  Produce labeled outcomes with pass/fail per assertion
        |
        v
  [ Structuring ]
  Format into training datasets:
    - SFT: (prompt, skill, successful_trajectory)
    - DPO: (prompt, skill, winning_trajectory, losing_trajectory)
    - GRPO: (prompt, skill, trajectory_group, rewards)
        |
        v
  Training-Ready Datasets
  with per-example quality metadata
```

---

## References

1. Anthropic. Skill Creator: A skill for creating and iterating on agent skills. GitHub, 2026.
2. DeepSeek-AI. DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning. arXiv, 2025.
3. Rafailov, R. et al. Direct Preference Optimization: Your Language Model is Secretly a Reward Model. NeurIPS, 2023.
4. Chen, X. et al. Gorilla: Large Language Model Connected with Massive APIs. arXiv, 2023.
5. Gunasekar, S. et al. Self-Rewarding Language Models. arXiv, 2024.
6. Christiano, P. et al. Deep Reinforcement Learning from Human Preferences. NeurIPS, 2017.
7. Schulman, J. et al. Proximal Policy Optimization Algorithms. arXiv, 2017.
8. Li, Y. et al. SPIN: Self-Play Fine-Tuning Converts Weak Language Models to Strong Language Models. ICML, 2024.
