# DPO Training Reference

Configuration, troubleshooting, and model selection for DPO fine-tuning.

## Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base model | Qwen/Qwen2.5-1.5B-Instruct | Small enough for 6GB VRAM, strong instruction following |
| Quantization | 4-bit NF4 (BitsAndBytes) | Reduces VRAM from ~3GB to ~1GB for the base model |
| LoRA rank | 8 | Low rank keeps adapter small (~35MB), sufficient for behavior learning |
| LoRA alpha | 16 | Alpha/rank = 2, standard scaling factor |
| DPO beta | 0.1 | Conservative - prevents over-optimization on small datasets |
| Epochs | 3 | Small datasets need more passes; monitor for overfitting |
| Learning rate | 5e-5 | Standard for LoRA DPO; works well with small datasets |
| Batch size | 1 | Fits in 6GB VRAM with gradient checkpointing |
| Gradient accumulation | 8 | Effective batch size = 8, stabilizes training |
| Max sequence length | 512 | Prompt: 256, response: 256;足够 for most marketing outputs |
| Optimizer | paged_adamw_32bit | Memory-efficient for quantized models |
| Gradient checkpointing | True | Trades compute for memory; essential for 6GB VRAM |

## Hardware Requirements

- **Minimum**: 6GB VRAM (RTX 4050 Laptop or equivalent)
- **Recommended**: 8GB+ VRAM for larger datasets or longer sequences
- **RAM**: 16GB+ system RAM recommended
- **Disk**: ~100MB for trained adapter + tokenizer

## Model Selection Guide

| Model | Params | VRAM (4-bit) | Quality | Notes |
|-------|--------|--------------|---------|-------|
| Qwen2.5-0.5B-Instruct | 0.5B | ~0.5GB | Lowest | Fastest training, weakest outputs |
| Qwen2.5-1.5B-Instruct | 1.5B | ~1GB | Good | Best balance for 6GB VRAM (recommended) |
| Qwen2.5-3B-Instruct | 3B | ~2GB | Better | Requires >6GB VRAM for training |
| phi-2 | 2.7B | ~2GB | Good | Alternative to Qwen, strong reasoning |
| TinyLlama-1.1B | 1.1B | ~0.8GB | Moderate | Smaller, faster, less capable |

**Recommendation**: Start with Qwen2.5-1.5B-Instruct. It has the best quality-to-VRAM ratio for skill-specific behavior learning.

## Running Training

```bash
cd skill-gym-repo/pipeline
uv run python train_dpo.py \
  --data-file dpo-data/<skill-name>/dpo_format_v2.json \
  --output-dir models/<skill-name>-dpo/ \
  --model-name Qwen/Qwen2.5-1.5B-Instruct \
  --epochs 3 \
  --max-length 512
```

## Checkpoint Resume

The training script saves checkpoints every 10 steps and keeps the last 3. If training is interrupted:

```bash
# Re-run the same command - it auto-resumes from latest checkpoint
uv run python train_dpo.py \
  --data-file dpo-data/<skill-name>/dpo_format_v2.json \
  --output-dir models/<skill-name>-dpo/
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| CUDA OOM | Not enough VRAM | Reduce `--max-length` to 256, or reduce batch size |
| Loss goes to NaN | Degenerate data or LR too high | Check DPO pairs for quality, reduce learning rate |
| Loss doesn't decrease | Chosen/rejected too similar | Need more differentiable pairs, generate more eval tasks |
| "None of the inputs have requires_grad=True" | Warning only, not an error | Training still works; LoRA params do get gradients |
| Training very slow | No GPU or large model | Check CUDA availability, use smaller model |

## Output Files

After training, the output directory contains:

```
models/<skill-name>-dpo/
├── adapter_config.json      LoRA configuration
├── adapter_model.safetensors  Trained weights (~35MB)
├── tokenizer_config.json    Tokenizer config
├── tokenizer.json           Tokenizer vocabulary
├── special_tokens_map.json  Special tokens
└── checkpoint-*/            Training checkpoints (if any)
```

## Using the Trained Model

Load the adapter on top of the base model:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
model = PeftModel.from_pretrained(base_model, "models/<skill-name>-dpo/")
tokenizer = AutoTokenizer.from_pretrained("models/<skill-name>-dpo/")
```
