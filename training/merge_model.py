from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer

model = AutoPeftModelForCausalLM.from_pretrained("/root/identity_adapter/final_adapter")
model = model.merge_and_unload()
model.save_pretrained("/root/identity_adapter/merged_model")
tokenizer = AutoTokenizer.from_pretrained("/root/identity_adapter/final_adapter")
tokenizer.save_pretrained("/root/identity_adapter/merged_model")
print("Merged!")
