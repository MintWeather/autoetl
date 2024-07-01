#!/bin/bash -l

#SBATCH -J Demand1_Train
#SBATCH -p a40
#SBATCH -N 1
#SBATCH --gres=gpu:1

source /share/home/22351111/anaconda3/etc/profile.d/conda.sh
conda activate llama_peft_demand1

python src/train_bash.py \
    --stage sft \
    --model_name_or_path ../pretrain/Mistral-7B-OpenOrca \
    --do_train \
    --dataset demand1 \
    --template default \
    --finetuning_type lora \
    --lora_target q_proj,k_proj,v_proj,o_proj \
    --output_dir model_save/Mistral_demand1 \
    --overwrite_cache \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --lr_scheduler_type cosine \
    --logging_steps 4 \
    --save_steps 2 \
    --learning_rate 5e-5 \
    --num_train_epochs 3.0 \
    --plot_loss \
    --fp16 \
    --overwrite_output_dir