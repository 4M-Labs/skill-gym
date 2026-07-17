#!/usr/bin/env python3
"""
DPO fine-tuning of Qwen2.5-1.5B-Instruct on SkillGym marketing data.
Uses LoRA + reference_free DPO for memory efficiency on RTX 4050 (6GB VRAM).
"""

import argparse
import json
import os
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, TaskType
from trl import DPOTrainer, DPOConfig
from datasets import Dataset

# Defaults
DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_PROMPT_LENGTH = 256
LORA_RANK = 4
LORA_ALPHA = 8
BATCH_SIZE = 1
GRAD_ACCUM = 1
LR = 1e-5
DPO_BETA = 0.05


def load_data(data_file):
    with open(data_file, encoding="utf-8") as f:
        raw = json.load(f)

    # Convert to dataset format for DPOTrainer
    data = {"prompt": [], "chosen": [], "rejected": []}
    for item in raw:
        prompt = item["messages"][0]["content"]
        chosen = item["messages"][1]["content"]
        rejected = item["rejected_messages"][1]["content"]
        data["prompt"].append(prompt)
        data["chosen"].append(chosen)
        data["rejected"].append(rejected)

    return Dataset.from_dict(data)


def main(data_file, output_dir, model_name, epochs, max_length):
    # Check for existing checkpoint to resume from
    resume_from = None
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoints = sorted(output_dir.glob("checkpoint-*"))
    if checkpoints:
        resume_from = str(checkpoints[-1])
        print(f"Found checkpoint: {resume_from}")
        print("Will resume training from this checkpoint.")

    print("Loading model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # LoRA config - passed to DPOTrainer, NOT applied manually
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.2,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    # Load data
    print("Loading training data...")
    dataset = load_data(data_file)
    print(f"Loaded {len(dataset)} training pairs")

    # DPO config - reference_free=True skips the reference model (saves ~50% VRAM)
    training_args = DPOConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        num_train_epochs=epochs,
        learning_rate=LR,
        lr_scheduler_type="cosine",
        warmup_ratio=0.0,
        beta=DPO_BETA,
        max_length=min(max_length, 768),
        max_prompt_length=MAX_PROMPT_LENGTH,
        logging_steps=1,
        save_strategy="epoch",
        save_total_limit=2,
        reference_free=True,
        optim="paged_adamw_32bit",
        fp16=True,
        remove_unused_columns=False,
        report_to="none",
        seed=42,
    )

    # Trainer - pass peft_config directly, not a pre-wrapped model
    # This fixes the requires_grad issue because DPOTrainer applies LoRA itself
    trainer = DPOTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=lora_config,
    )

    # Train
    print("Starting DPO training...")
    trainer.train(resume_from_checkpoint=resume_from)

    # Save
    print(f"Saving model to {output_dir}...")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    print("Training complete!")
    print(f"Model saved to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DPO fine-tuning of Qwen2.5-1.5B-Instruct on SkillGym marketing data"
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        required=True,
        help="Path to DPO-formatted training data JSON"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Where to save the trained model adapter"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help=f"HuggingFace model name (default: {DEFAULT_MODEL_NAME})"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs (default: 3)"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=768,
        help="Maximum sequence length (default: 768)"
    )
    args = parser.parse_args()

    main(args.data_file, args.output_dir, args.model_name, args.epochs, args.max_length)
