#!/usr/bin/env python3
"""Audit current tool registry, skills.json, and agent system prompt."""
import json
from pathlib import Path

print('=' * 60)
print('TOOL & PROMPT AUDIT — Day 71c finale')
print('=' * 60)

# 1. skills.json (tool descriptions for LLM)
sk_path = '/opt/ado/config/skills.json'
sk = json.loads(Path(sk_path).read_text())
print(f'\n[1] {sk_path}')
print(f'    version: {sk.get("version")}')
print(f'    description: {sk.get("description","-")[:80]}')
skills = sk.get('skills', [])
print(f'    skills count: {len(skills)}')
for s in skills:
    name = s.get('name', '?')
    desc = s.get('description', s.get('summary', ''))[:60]
    print(f'      - {name}: {desc}')

# 2. agents.json (agent personality + system prompt)
ag_path = '/opt/ado/config/agents.json'
ag = json.loads(Path(ag_path).read_text())
print(f'\n[2] {ag_path}')
agents = ag.get('agents', ag if isinstance(ag, list) else [])
if isinstance(agents, list):
    print(f'    agents count: {len(agents)}')
    for a in agents:
        if isinstance(a, dict):
            name = a.get('name', a.get('id', '?'))
            sys_prompt = a.get('system_prompt', a.get('persona', ''))
            print(f'      - {name}: {len(sys_prompt)} chars system prompt')
elif isinstance(agents, dict):
    print(f'    agents (dict) keys: {list(agents.keys())[:10]}')

# 3. personalities.yaml
pers_path = '/opt/ado/config/personalities.yaml'
if Path(pers_path).exists():
    text = Path(pers_path).read_text()
    print(f'\n[3] {pers_path}')
    print(f'    size: {len(text)} chars')
    # Count personalities (top-level keys before colons)
    import re
    keys = re.findall(r'^([a-zA-Z_][a-zA-Z_0-9]*):\s*$', text, re.MULTILINE)
    print(f'    top-level personas: {len(keys)}')
    for k in keys[:15]:
        print(f'      - {k}')
