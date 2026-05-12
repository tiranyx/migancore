"""
Merge identity_adapter_v0.4 + DPO adapter via SVD-based weighted combination.
Handles different ranks (r=32 identity vs r=16 DPO) correctly.
No GPU training needed — pure adapter arithmetic on CPU.

Weight: identity=0.7 (dominant, for licensing), dpo=0.3 (utility preservation)
Base: Qwen/Qwen2.5-7B-Instruct (same for both adapters)
"""

import torch
import sys

# Paths
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
IDENTITY_ADAPTER = "/opt/ado/models/identity_adapter_v0.4"
DPO_ADAPTER = "/opt/ado/data/models/final_adapter"  # Most recent DPO adapter for 0.8
OUTPUT_DIR = "/opt/ado/data/models/migancore_0.8_identity_fixed"

def main():
    print("=" * 60)
    print("MiganCore Adapter SVD Merge")
    print("Identity (0.7) + DPO (0.3) = Fixed 0.8")
    print("=" * 60)

    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print("\n[1/5] Loading base model (Qwen2.5-7B-Instruct)...")
    print("     This may take 2-3 minutes on CPU...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
    )
    # Qwen2.5 fix
    if tokenizer.bos_token_id is None:
        tokenizer.bos_token_id = tokenizer.eos_token_id
    print("     Base model loaded.")

    print("\n[2/5] Loading identity adapter v0.4 (r=32)...")
    model = PeftModel.from_pretrained(
        model,
        IDENTITY_ADAPTER,
        adapter_name="identity",
        torch_dtype=torch.float16,
    )
    print("     Identity adapter loaded.")

    print("\n[3/5] Loading DPO adapter (r=16)...")
    model.load_adapter(
        DPO_ADAPTER,
        adapter_name="dpo",
        torch_dtype=torch.float16,
    )
    print("     DPO adapter loaded.")

    print("\n[4/5] Creating SVD-weighted combination: identity=0.7, dpo=0.3...")
    print("     SVD method handles different ranks (r=32 vs r=16)...")
    model.add_weighted_adapter(
        adapters=["identity", "dpo"],
        weights=[0.7, 0.3],
        adapter_name="fixed_08",
        combination_type="svd",
    )
    model.set_adapter("fixed_08")
    print("     Combined adapter 'fixed_08' created and activated.")

    print("\n[5/5] Merging and saving to disk...")
    print("     This may take 3-5 minutes...")
    merged = model.merge_and_unload()
    merged.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"     Merged model saved to: {OUTPUT_DIR}")

    print("\n" + "=" * 60)
    print("MERGE COMPLETE!")
    print(f"Output: {OUTPUT_DIR}")
    print("Next: Convert to GGUF -> Deploy to Ollama")
    print("=" * 60)

if __name__ == "__main__":
    main()
