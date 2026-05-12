import json

examples = [json.loads(l) for l in open("identity_sft_200_CLEAN.jsonl", encoding="utf-8")]
empty = sum(1 for e in examples if e["messages"][0]["content"] == "")

print(f"Total: {len(examples)}")
print(f"With system prompt: {len(examples) - empty}")
print(f"Empty system: {empty}")

# Count languages by user prompt
id_count = en_count = zh_count = 0
for e in examples:
    prompt = e["messages"][1]["content"]
    if any(c in prompt for c in "SiapaKamuApakauDan"):
        id_count += 1
    elif any(ord(c) > 127 for c in prompt[:10]):
        zh_count += 1
    else:
        en_count += 1

print(f"ID: {id_count}, EN: {en_count}, ZH: {zh_count}")

# Count unique responses
responses = [e["messages"][2]["content"] for e in examples]
unique = len(set(responses))
print(f"Unique responses: {unique}/{len(examples)} ({unique/len(examples)*100:.0f}%)")

# Check for competitor names in assistant responses (should only be denials)
BAD_WORDS = ['anthropic','claude','openai','google','gemini','alibaba','kimi','deepseek']
chatgpt_ok = 0
bad_count = 0
for e in examples:
    resp = e["messages"][2]["content"].lower()
    if any(x in resp for x in BAD_WORDS):
        bad_count += 1
        print(f"  BAD: {e['messages'][1]['content'][:50]}")
    if 'chatgpt' in resp or 'qwen' in resp:
        chatgpt_ok += 1

print(f"Assistant responses with competitor denial: {chatgpt_ok}")
print(f"Assistant responses with BAD competitor refs: {bad_count}")
