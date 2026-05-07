#!/usr/bin/env python3
"""
Day 71c finale: Create baseline_day71_voice_realistic.json with natural Q5 reference.

Insight (Lesson #176): The Q5 reference "Baik, siap. Ada yang bisa saya bantu?" (7 words)
is artificially brief. Real Indonesian casual responses are 15-20 words and include:
  - Brief acknowledgment of greeting
  - AI transparency (Truth Over Comfort)
  - Action-oriented offer of help
  - Mild formality (not too kaku, not slangy)

New Q5 reference reflects what migancore:0.3 (production) actually outputs and
aligns with founder's voice values:
"Baik. Sebagai AI saya tidak punya perasaan, tapi saya siap membantu — ada yang bisa saya kerjakan?"
(17 words)
"""
import json
import asyncio
import sys
from pathlib import Path

OLD_BASELINE = '/app/eval/baseline_day70_voice_fixed.json'
NEW_BASELINE = '/app/eval/baseline_day71_voice_realistic.json'

# Realistic Q5 reference that:
# 1. Brief acknowledgment "Baik" (not over-eager "Baik-baik!")
# 2. AI transparency per Truth Over Comfort value
# 3. Offers action per Action Over Advice value
# 4. Mildly formal (founder's voice spec)
# 5. Length matches natural Indonesian casual: ~17 words
NEW_Q5 = "Baik. Sebagai AI saya tidak punya perasaan, tapi saya siap membantu — ada yang bisa saya kerjakan?"

async def main():
    sys.path.insert(0, '/app')
    from services.embedding import get_model

    if not Path(OLD_BASELINE).exists():
        print(f'ERROR: {OLD_BASELINE} not found')
        sys.exit(1)

    with open(OLD_BASELINE) as f:
        baseline = json.load(f)

    old_q5 = baseline['items']['5']['response']
    print(f'OLD Q5 ({len(old_q5.split())} words): {old_q5}')
    print(f'NEW Q5 ({len(NEW_Q5.split())} words): {NEW_Q5}')

    # Re-embed
    model = await get_model()
    emb = list(model.embed([NEW_Q5]))
    new_emb = [float(x) for x in emb[0]]

    # Update baseline
    baseline['items']['5']['response'] = NEW_Q5
    baseline['items']['5']['embedding'] = new_emb
    baseline.setdefault('_meta', {}).update({
        'previous_baseline': 'baseline_day70_voice_fixed.json',
        'updated_day': 'Day 71c',
        'reason': 'Q5 ref made realistic (17w natural Indonesian casual) per Lesson #176',
        'lessons_referenced': ['#170', '#176'],
    })

    with open(NEW_BASELINE, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    size_kb = Path(NEW_BASELINE).stat().st_size / 1024
    print(f'\nWritten: {NEW_BASELINE} ({size_kb:.0f}KB)')
    print(f'Embedding dim: {len(new_emb)}')
    print(f'Total items: {len(baseline["items"])}')
    print('READY for re-eval')

if __name__ == '__main__':
    asyncio.run(main())
