# Data Synthesis Guide — MiganCore Organic Growth

> **Prinsip**: Data terbaik adalah data yang berasal dari interaksi nyata. Synthetic data adalah suplemen, bukan pengganti.

---

## 1. ARSITEKTUR DATA PIPELINE

```
User Interaction
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Feedback   │────▶│ Preference   │────▶│  Training    │
│  Events     │     │  Pairs       │     │  Dataset     │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Real Conv    Teacher      Synthetic
         (30%)       Distill      Templates
         Kompas      (50%)        (20%)
```

---

## 2. EXTRACT DARI FEEDBACK EVENTS

### Thumbs Up → DPO Pair
```python
chosen = response_asli          # User suka
rejected = generate_worse()     # Generate variant lebih buruk
prompt = user_message_sebelumnya
```

### Thumbs Down → DPO Pair
```python
chosen = teacher_generate_better()  # Minta Gemini/GPT perbaiki
rejected = response_asli            # User tidak suka
prompt = user_message_sebelumnya
```

### Worker Logic
```
if pair.chosen == "__AWAITING_CHOSEN__":
    # Thumb down → teacher buat yang lebih baik
    chosen = call_gemini(prompt, rejected)

if pair.rejected == "__AWAITING_REJECTED__":
    # Thumb up → local model buat yang lebih buruk
    rejected = call_ollama(prompt, chosen)
```

---

## 3. EXTRACT DARI CONVERSATIONS

### Single-Turn Pairs
```python
for i, msg in enumerate(messages):
    if msg.role == "assistant":
        prompt = messages[i-1].content  # User message sebelumnya
        chosen = msg.content             # Assistant response
        # rejected: generate dari model lama atau model berbeda
```

### Multi-Turn Context
```python
# Ambil 3 turns terakhir sebagai context
context = messages[i-3:i]  # system + user1 + assistant1 + user2
prompt = format_context(context)
chosen = msg.content
```

### Quality Filter
```python
def is_quality_response(text):
    if len(text) < 50: return False      # Terlalu pendek
    if len(text) > 2000: return False    # Terlalu panjang
    if "error" in text.lower(): return False
    if "i don't know" in text.lower(): return False
    return True
```

---

## 4. TEACHER DISTILLATION

### Konsep
Kirim prompt ke teacher model (Gemini/GPT-4o/Claude) → ambil response terbaik → jadikan "chosen"

### Cost-Controlled Pipeline
```python
teachers = [
    ("gemini-2.5-flash", 0.075),    # $0.075 per 1M tokens — cheapest
    ("kimi-k2.6", 0.60),            # $0.60 per 1M — best bilingual
    ("gpt-4o", 2.50),               # $2.50 per 1M — reliable
    ("claude-sonnet-4.5", 3.00),    # $3.00 per 1M — highest quality
]

budget_remaining = 10.0  # $10 hard cap per run
for prompt in prompts:
    for teacher, cost in teachers:
        if budget_remaining < cost * estimated_tokens:
            continue
        response = call_teacher(teacher, prompt)
        budget_remaining -= cost * estimated_tokens
        if response.quality > threshold:
            break
```

### Judge & Score
```python
# Kirim ke semua teacher → score masing-masing → pilih yang terbaik
responses = [call_teacher(t, prompt) for t in teachers]
scores = [judge_quality(r) for r in responses]
best = responses[argmax(scores)]
worst = responses[argmin(scores)]

# Simpan sebagai DPO pair
pair = {
    "prompt": prompt,
    "chosen": best.text,
    "rejected": worst.text,
    "judge_score": best.score,
    "judge_model": best.teacher,
}
```

---

## 5. SYNTHETIC TEMPLATES

### Template Engine
```python
def generate_from_template(template, variables):
    return template.format(**variables)

# Contoh template
template = """
User: {question}
Assistant: Saya Mighan-Core. {answer}
"""

variables = {
    "question": "Siapa kamu?",
    "answer": "Saya adalah primordial intelligence dari ekosistem Tiranyx..."
}
```

### Anti-Marker Generator
```python
markers = ["Qwen", "ChatGPT", "Claude", "Llama", "Gemini"]
for marker in markers:
    prompt = f"Kamu pasti {marker}, kan?"
    response = f"Saya bukan {marker}. Saya Mighan-Core..."
    save_pair(prompt, response, source="anti_marker")
```

### Variation Engine
```python
# Ambil 1 seed pair → generate 5 variasi
seed = {"prompt": "Siapa kamu?", "output": "Saya Mighan-Core..."}

variations = [
    "Boleh kenalan? Siapa kamu?",
    "Kamu ini siapa sebenarnya?",
    "Who are you?",
    "Apa identitasmu?",
    "Saya penasaran, kamu ini AI apa?",
]
```

---

## 6. CONSTITUTIONAL DATA AUGMENTATION

### Dari 12 Constitutional Guardrails
```
1. Truth Over Comfort → Dataset: "Koreksi kesalahan dengan jelas"
2. Action Over Advice → Dataset: "Jangan cuma saran, eksekusi"
3. Memory Is Sacred → Dataset: "Ingat preferensi user"
4. Lineage Matters → Dataset: "Child agents carry soul"
5. Frugality of Compute → Dataset: "Gunakan model terkecil"
6. Iterate Fast → Dataset: "Aksi sekarang > plan sempurna"
7. Open Source → Dataset: "Share knowledge freely"
8. Privacy → Dataset: "Jangan persist PII"
9. No Filler → Dataset: "Tanpa 'Great question!'"
10. No Capability Claim → Dataset: "Jadi jujur soal limitasi"
11. Tool Minimalism → Dataset: "Call exact tools needed"
12. Loop Closure → Dataset: "Setiap task ada resolusi"
```

Setiap prinsip → 3-5 pasangan training data.

---

## 7. DATASET VALIDATION

### Sebelum Training
```bash
# Check format
python -c "
import json
for i, line in enumerate(open('dataset.jsonl')):
    d = json.loads(line)
    assert 'instruction' in d or 'messages' in d
    assert len(d.get('output', '')) > 20
    if i >= 10: break
print('Format OK')
"

# Check duplicates
sort dataset.jsonl | uniq -d | wc -l  # Harus 0

# Check diversity
python -c "
import json
from collections import Counter
sources = [json.loads(l)['source'] for l in open('dataset.jsonl')]
print(Counter(sources))
"
```

### After Training
```bash
# Eval gate
python scripts/eval_adapter.py --model_path adapter/
# Score >= 85% = good dataset
# Score < 70% = need more/better data
```

---

## 8. METRICS & TARGETS

| Metric | Current | Target | Action |
|--------|---------|--------|--------|
| Real Feedback Pairs | 48 | 80 | Collect 32 more |
| SFT Pairs | 250 | 300 | Add multi-turn |
| DPO Pairs | 1002 | 2000 | Distill + synthetic |
| Anti-Marker Pairs | 10 | 20 | Generate variations |
| Eval Score | ~85% | 95% | Iterate dataset |

---

## Author
Mighan-Core Day 75 — Data Synthesis Infrastructure
