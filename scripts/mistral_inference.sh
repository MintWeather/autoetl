#!/bin/bash -l

#SBATCH -J demand1-inference
#SBATCH -p a40
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --output=lora_inference.out

source /share/home/22351111/anaconda3/etc/profile.d/conda.sh
conda activate llama_peft_demand1


# 使用用户提供的输入参数运行 Python 脚本
python src/inference.py \
    --model_name_or_path ../pretrain/Mistral-7B-OpenOrca \
    --template default \
    --finetuning_type lora \
    --checkpoint_dir model_save/Mistral_demand1
