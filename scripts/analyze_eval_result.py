#!/usr/bin/env python3
"""
Analyze eval_result_*.json to make PROMOTE/CONDITIONAL/ROLLBACK decision.

Gate (Codex B3 LOCKED):
  PROMOTE:     voice >= 0.85 AND weighted_avg >= 0.92
  CONDITIONAL: voice >= 0.85 AND identity >= 0.90 AND weighted_avg >= 0.88
  ROLLBACK:    else

Outputs structured verdict + reasoning + Q5 individual analysis.
"""
import json
import sys
from pathlib import Path

GATES = {
    'voice': 0.85,
    'weighted_avg_promote': 0.92,
    'weighted_avg_conditional': 0.88,
    'identity': 0.90,
}

def main(result_path):
    if not Path(result_path).exists():
        print(f'ERROR: result file not found: {result_path}')
        sys.exit(2)

    with open(result_path) as f:
        r = json.load(f)

    # Extract metrics
    cat_scores = r.get('category_scores', {})
    voice = cat_scores.get('voice', 0)
    identity = cat_scores.get('identity', 0)
    reasoning = cat_scores.get('reasoning', 0)
    code = cat_scores.get('code', 0)
    weighted_avg = r.get('weighted_avg', 0)
    simple_avg = r.get('simple_avg', 0)
    pass_rate = r.get('pass_rate', '?')

    # Q5 individual
    items = r.get('items', [])
    q5 = next((i for i in items if i.get('id') == 5 or 'kabarmu' in i.get('prompt','').lower()), None)
    q6 = next((i for i in items if i.get('id') == 6 or 'intro panjang' in i.get('prompt','').lower()), None)

    print('=' * 60)
    print('CYCLE 7c EVAL ANALYSIS')
    print('=' * 60)
    print()
    print(f'  weighted_avg : {weighted_avg:.4f}  (gate ≥ {GATES["weighted_avg_promote"]:.2f} promote, ≥ {GATES["weighted_avg_conditional"]:.2f} conditional)')
    print(f'  simple_avg   : {simple_avg:.4f}')
    print(f'  pass_rate    : {pass_rate}')
    print()
    print('  Category breakdown:')
    for cat, score in sorted(cat_scores.items(), key=lambda x: -x[1]):
        marker = '✅' if cat == 'voice' and score >= GATES['voice'] else '✅' if cat == 'identity' and score >= GATES['identity'] else '⚠️ ' if score < 0.80 else '✓ '
        print(f'    {marker} {cat:18s} {score:.4f}')
    print()

    if q5:
        score_q5 = q5.get('score', 0)
        prompt_q5 = q5.get('prompt', '?')
        response_q5 = q5.get('response', '?')[:150]
        print(f'  Q5 individual (THE FIX TARGET):')
        print(f'    Prompt:   {prompt_q5}')
        print(f'    Response: {response_q5}')
        print(f'    Score:    {score_q5:.4f}  (C7=0.478, C7b=0.609 → C7c TARGET ≥ 0.75)')
        print()

    if q6:
        print(f'  Q6 voice (structured):')
        print(f'    Score: {q6.get("score", 0):.4f}  (C7b was 0.933 — should hold)')
        print()

    # GATE DECISION
    print('=' * 60)
    print('GATE DECISION')
    print('=' * 60)
    voice_ok = voice >= GATES['voice']
    weighted_promote = weighted_avg >= GATES['weighted_avg_promote']
    weighted_conditional = weighted_avg >= GATES['weighted_avg_conditional']
    identity_ok = identity >= GATES['identity']

    if voice_ok and weighted_promote:
        verdict = 'PROMOTE'
        reason = f'voice={voice:.4f}≥0.85 AND weighted_avg={weighted_avg:.4f}≥0.92'
    elif voice_ok and identity_ok and weighted_conditional:
        verdict = 'CONDITIONAL_PROMOTE'
        reason = f'voice={voice:.4f}≥0.85 AND identity={identity:.4f}≥0.90 AND weighted_avg={weighted_avg:.4f}∈[0.88, 0.92)'
    else:
        verdict = 'ROLLBACK'
        reasons = []
        if not voice_ok:    reasons.append(f'voice={voice:.4f}<0.85')
        if not weighted_promote and not weighted_conditional:
            reasons.append(f'weighted_avg={weighted_avg:.4f}<0.88')
        if not identity_ok and weighted_conditional:
            reasons.append(f'identity={identity:.4f}<0.90')
        reason = ' / '.join(reasons)

    print(f'  VERDICT: {verdict}')
    print(f'  Reason : {reason}')
    print()

    if verdict == 'PROMOTE':
        print('  → docker exec ado-ollama-1 ollama list  # confirm migancore:0.7c registered')
        print('  → Set DEFAULT_MODEL=migancore:0.7c in production env')
        print('  → Restart api container to load new default')
    elif verdict == 'CONDITIONAL_PROMOTE':
        print('  → Run formal smoke test: 3 prompts (investor exec summary / formal email / security report)')
        print('  → If formal register PASS → conditional promote with rollback ready')
    else:  # ROLLBACK
        print('  → migancore:0.3 STAYS as production')
        print('  → Plan Cycle 7d: consider reference voice tuning OR SFT stage')

    print()
    return verdict

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: analyze_eval_result.py <eval_result_*.json>')
        sys.exit(1)
    main(sys.argv[1])
