# Hot-Swap Guide (Day 34) — Deploy Trained Model

After Cycle 1 SimPO training (Day 32) finishes on RunPod and identity eval passes (Day 33), this guide covers the hot-swap to production.

## Prerequisites
- ✅ Training run completed: `migancore-7b-soul-v0.1` adapter saved
- ✅ Identity eval PASS (avg cosine sim ≥ 0.85 vs baseline)
- ✅ GGUF Q4_K_M file converted via `convert_gguf.py`

## Workflow (per blueprint Section 7.1)

### 1. Push GGUF to HuggingFace
```bash
# On RunPod pod (after train + convert):
huggingface-cli upload migancore/migancore-7b-soul-v0.1 \
  migancore-7b-soul-v0.1.Q4_K_M.gguf
```

### 2. Pull to Ollama on VPS
```bash
ssh root@72.62.125.6
cd /opt/ado

# Pull GGUF directly from HF Hub
docker compose exec ollama ollama pull \
  hf.co/migancore/migancore-7b-soul-v0.1
```

### 3. Verify Ollama loaded the new model
```bash
docker compose exec ollama ollama list | grep migancore
```

### 4. A/B Test Setup — `X-Model-Version` header routing

Add header-based model selection in `api/services/ollama.py` and `api/routers/chat.py`:

```python
# In chat router — read header X-Model-Version
model_version = request.headers.get("X-Model-Version", "stable")
model_name = "migancore-7b-soul-v0.1" if model_version == "v0.1" else settings.DEFAULT_MODEL

# Pass to Ollama call
async with OllamaClient() as client:
    resp = await client.chat(model=model_name, ...)
```

### 5. 24-hour A/B test plan

**Day 34 PM:**
- Deploy A/B framework
- Default 90% baseline, 10% v0.1 (random per session_id)
- Log model_version_used per message

**Day 35 AM:**
- Query metrics:
  - Avg conversation length (longer = engagement)
  - User thumb up/down ratio
  - Tool-call success rate
  - Error rate
- Decision matrix:
  - v0.1 wins ≥ 1% across all → PROMOTE (default)
  - v0.1 ties or wins 1 metric → KEEP TESTING (50/50 split, another 24h)
  - v0.1 loses any → ROLLBACK + analyze

### 6. Promote (if eval + A/B both pass)
```bash
ssh root@72.62.125.6
cd /opt/ado
echo "DEFAULT_MODEL=migancore-7b-soul-v0.1" >> .env
docker compose up -d --force-recreate api
```

### 7. Tag in DB + announce
```sql
INSERT INTO model_versions (
  base_model, version_tag, training_run_id, parent_version_id,
  gguf_uri, evaluation_scores, deployed_at
) VALUES (
  'qwen2.5-7b-instruct',
  'migancore-v0.1-soul-2026-05-04',
  -- training_run_id from MLflow
  NULL,
  'hf.co/migancore/migancore-7b-soul-v0.1',
  '{"identity_eval_avg_cosine_sim": 0.87, "ab_test_win_rate": 0.54}',
  NOW()
);
```

Update `landing.html` live stats: "Model trained on N pairs · v0.1 deployed"

## Rollback (if A/B fails)
```bash
ssh root@72.62.125.6
cd /opt/ado
sed -i 's/DEFAULT_MODEL=migancore-7b-soul-v0.1/DEFAULT_MODEL=qwen2.5:7b-instruct-q4_K_M/' .env
docker compose up -d --force-recreate api
# Document failure in WEEK4_RETRO.md
```

## Cost Audit
- Train (RunPod RTX 4090, 8hr): ~$5.50
- Eval inference (RunPod 1hr): ~$0.70
- HF Hub: free
- Ollama hot-swap: free (just disk + RAM)
- **Total per cycle: ~$6.20**

Per blueprint: $50 RunPod budget = ~8 cycles = 8 weeks of weekly fine-tuning.

## Critical Lessons (capture in WEEK4_RETRO.md after first run)
1. **Did identity eval catch any drift?** (0.85 threshold appropriate?)
2. **A/B winner: v0.1 vs baseline?** (Quantitative result)
3. **Inference speed change?** (Q4_K_M same as base, should be similar)
4. **Persona consistency in real chat?** (Manual spot-check 5-10 conversations)
5. **What dataset mix (50/30/20) actually delivered?** (Adjust for v0.2)
