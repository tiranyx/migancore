#!/usr/bin/env python3
"""Analyze the 40 new Q5 casual pairs added in Cycle 7c."""
import json
from collections import Counter

pairs = [json.loads(l) for l in open('/opt/ado/data/workspace/cycle7c_dataset.jsonl')]
c7c = [p for p in pairs if p.get('source') == 'voice_casual_q5_cycle7c']
c7_base = [p for p in pairs if p.get('source') != 'voice_casual_q5_cycle7c']

print('=== DATASET ANATOMY (548 pairs) ===')
print(f'  C7 base (formal/diverse): {len(c7_base)}')
print(f'  C7c Q5 casual greeting:   {len(c7c)}')
print()

print('=== Q5 CASUAL PAIR — PROMPT VARIANTS ===')
prompt_counts = Counter(p['prompt'] for p in c7c)
print(f'Unique prompt variants: {len(prompt_counts)}')
for prompt, count in prompt_counts.most_common():
    print(f'  {count}x  {prompt}')
print()

chosen_lens = [len(p['chosen'][-1]['content'].split()) for p in c7c]
rejected_lens = [len(p['rejected'][-1]['content'].split()) for p in c7c]
print('=== LENGTH DELTA (key signal for ORPO) ===')
print(f'  Chosen   words: min={min(chosen_lens)}, mean={sum(chosen_lens)/len(chosen_lens):.1f}, max={max(chosen_lens)}')
print(f'  Rejected words: min={min(rejected_lens)}, mean={sum(rejected_lens)/len(rejected_lens):.1f}, max={max(rejected_lens)}')
delta = sum(rejected_lens)/len(rejected_lens) - sum(chosen_lens)/len(chosen_lens)
print(f'  Mean delta: rejected is ~{delta:.0f} words MORE than chosen')
print()

print('=== SAMPLE PAIR #1 (the signal we teach the model) ===')
sample = c7c[0]
prompt = sample['prompt']
chosen = sample['chosen'][-1]['content']
rejected = sample['rejected'][-1]['content']
print(f'  Prompt:   {prompt}')
print(f'  CHOSEN:   {chosen}  ({len(chosen.split())} words)')
print(f'  REJECTED: {rejected[:100]}...  ({len(rejected.split())} words)')
