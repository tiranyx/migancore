#!/bin/bash
source /opt/conda/bin/activate migan

echo "Merging adapter..."
python3 -c "
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer

model = AutoPeftModelForCausalLM.from_pretrained('/root/identity_adapter/final_adapter')
model = model.merge_and_unload()
model.save_pretrained('/root/identity_adapter/merged_model')
tokenizer = AutoTokenizer.from_pretrained('/root/identity_adapter/final_adapter')
tokenizer.save_pretrained('/root/identity_adapter/merged_model')
print('Merged!')
"

echo "Converting to GGUF..."
pip install -q llama-cpp-python

python3 -c "
from llama_cpp import Llama
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load merged model and convert to GGUF
# Actually llama-cpp-python doesn't have direct convert from transformers
# We need to use llama.cpp convert script or huggingface-to-gguf
print('GGUF conversion requires llama.cpp scripts. Skipping for now.')
"

echo "Compressing adapter..."
tar czf /root/identity_adapter_pkg.tar.gz -C /root/identity_adapter/final_adapter .
ls -lh /root/identity_adapter_pkg.tar.gz
