"""
Sequential merge: faster than SVD on CPU.
Step 1: Base + identity adapter -> merge -> save
Step 2: Load merged + DPO adapter -> merge -> save final
"""

import torch

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
IDENTITY_ADAPTER = "/opt/ado/models/identity_adapter_v0.4"
DPO_ADAPTER = "/opt/ado/data/models/final_adapter"
STEP1_DIR = "/opt/ado/data/models/step1_merged_identity"
FINAL_DIR = "/opt/ado/data/models/migancore_0.8_identity_fixed"

def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print("=" * 60)
    print("Sequential Merge: Identity -> DPO")
    print("=" * 60)

    # Step 1: Base + Identity
    print("\n[Step 1/2] Loading base model + identity adapter...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.bos_token_id is None:
        tokenizer.bos_token_id = tokenizer.eos_token_id

    model = PeftModel.from_pretrained(model, IDENTITY_ADAPTER, torch_dtype=torch.float16)
    print("     Merging identity adapter (r=32)...")
    model = model.merge_and_unload()
    print(f"     Saving to {STEP1_DIR}...")
    model.save_pretrained(STEP1_DIR)
    tokenizer.save_pretrained(STEP1_DIR)
    print("     Step 1 complete.")

    # Free memory
    del model
    import gc
    gc.collect()

    # Step 2: Merged Identity + DPO
    print("\n[Step 2/2] Loading merged-identity + DPO adapter...")
    model = AutoModelForCausalLM.from_pretrained(
        STEP1_DIR,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(STEP1_DIR, trust_remote_code=True)

    model = PeftModel.from_pretrained(model, DPO_ADAPTER, torch_dtype=torch.float16)
    print("     Merging DPO adapter (r=16)...")
    model = model.merge_and_unload()
    print(f"     Saving final model to {FINAL_DIR}...")
    model.save_pretrained(FINAL_DIR)
    tokenizer.save_pretrained(FINAL_DIR)
    print("     Step 2 complete.")

    print("\n" + "=" * 60)
    print("SEQUENTIAL MERGE COMPLETE!")
    print(f"Final model: {FINAL_DIR}")
    print("Next: Convert to GGUF -> Deploy to Ollama")
    print("=" * 60)

if __name__ == "__main__":
    main()
