#!/bin/bash
source /opt/conda/bin/activate migan
nohup python3 train_sft_simple.py --dataset identity_sft_200.jsonl --output-dir ./identity_adapter --base-model Qwen/Qwen2.5-7B-Instruct --epochs 5 --lora-r 32 --merge --gguf > /root/simple_train.out 2>&1 &
echo PID: $!
