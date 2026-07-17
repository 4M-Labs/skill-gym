#!/usr/bin/env python3
"""
SFT fine-tuning of Qwen2.5-1.5B-Instruct on SkillGym marketing data.

SFT is simpler than DPO: it trains on "what good looks like" directly.
No contrastive pairs needed. Works better with small datasets (30 examples).

Uses LoRA + 4-bit quantization for RTX 4050 (6GB VRAM).
"""

import argparse
import json
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, TaskType
from trl import SFTTrainer, SFTConfig
from datasets import Dataset

# Defaults
DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
LORA_RANK = 8
LORA_ALPHA = 16
BATCH_SIZE = 1
GRAD_ACCUM = 1
LR = 2e-5


def load_data(data_file):
    with open(data_file, encoding="utf-8") as f:
        raw = json.load(f)

    # Convert to dataset format for SFTTrainer
    # SFTTrainer with "chat" format expects messages
    data = []
    for item in raw:
        data.append({
            "messages": item["messages"],
            "task_id": item.get("task_id", ""),
            "skill": item.get("skill", ""),
        })

    return Dataset.from_list(data)


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

    # LoRA config
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    # Load data
    print("Loading training data...")
    dataset = load_data(data_file)
    print(f"Loaded {len(dataset)} training examples")

    # SFT config
    training_args = SFTConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        num_train_epochs=epochs,
        learning_rate=LR,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_steps=1,
        save_strategy="epoch",
        save_total_limit=2,
        optim="paged_adamw_32bit",
        fp16=True,
        remove_unused_columns=False,
        report_to="none",
        seed=42,
        max_length=max_length,
        dataset_text_field=None,  # We use chat format
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=lora_config,
    )

    # Train
    print("Starting SFT training...")
    trainer.train(resume_from_checkpoint=resume_from)

    # Save
    print(f"Saving model to {output_dir}...")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    print("Training complete!")
    print(f"Model saved to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SFT fine-tuning of Qwen2.5-1.5B-Instruct on SkillGym marketing data"
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        required=True,
        help="Path to SFT-formatted training data JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Where to save the trained model adapter",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help=f"HuggingFace model name (default: {DEFAULT_MODEL_NAME})",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs (default: 10)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=2048,
        help="Maximum sequence length (default: 2048)",
    )
    args = parser.parse_args()

    main(args.data_file, args.output_dir, args.model_name, args.epochs, args.max_length)
