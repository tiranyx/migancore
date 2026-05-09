#!/bin/bash
source /opt/conda/bin/activate migan
python3 train_sft_identity.py --dataset identity_sft_200.jsonl --output-dir ./identity_adapter --base-model Qwen/Qwen2.5-7B-Instruct --epochs 5 --lora-r 32 --merge --gguf > /root/training_run2.out 2>&1
