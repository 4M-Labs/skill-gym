@echo off
cd /d "C:\Users\michi\Desktop\Companies OS\4M Labs\skill-gym-repo\pipeline"
python evaluate_model.py --model-name "Qwen/Qwen2.5-1.5B-Instruct" --adapter-path "models/skillgym-marketing-dpo-v2" --tasks-file evals/tasks.json --output-dir evaluation
echo DONE
