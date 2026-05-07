#!/usr/bin/env python3
"""Verify cycle7c_dataset.jsonl is in correct string format for TRL ORPO."""
import json

all_pairs = [json.loads(l) for l in open('/opt/ado/data/workspace/cycle7c_dataset.jsonl')]
print(f'Total pairs: {len(all_pairs)}')

c7c_pairs = [p for p in all_pairs if p.get('source') == 'voice_casual_q5_cycle7c']
print(f'C7c new pairs: {len(c7c_pairs)}')

sample = c7c_pairs[0]
print(f'  prompt type:   {type(sample["prompt"]).__name__}')
print(f'  chosen type:   {type(sample["chosen"]).__name__}')
print(f'  rejected type: {type(sample["rejected"]).__name__}')
print(f'  prompt:   {sample["prompt"]!r}')
print(f'  chosen:   {sample["chosen"]!r}')
print(f'  rejected: {sample["rejected"][:80]!r}...')

# Validate ALL pairs are strings
ok_count = sum(
    1 for p in all_pairs
    if isinstance(p.get('prompt'), str)
    and isinstance(p.get('chosen'), str)
    and isinstance(p.get('rejected'), str)
)
print(f'\nString format validation: {ok_count}/{len(all_pairs)} pairs OK')
if ok_count == len(all_pairs):
    print('READY FOR TRAINING')
else:
    print('FAIL - some pairs not in string format')
