# CODEX QA - Day 73: Innovation Engine Foundation

## SIGN-OFF: CONDITIONAL

## PURPOSE

Fahmi asked to strengthen MiganCore so cognitive synthesis becomes innovation:
more varied outputs, stronger coding, better ideation, better image/visual
generation, polished answers, and more reusable tools inside chat.

## COORDINATION NOTE FOR CLAUDE CODE

Codex is touching the cognitive/innovation doctrine surface only:

- `docs/INNOVATION_ENGINE_DOCTRINE.md`
- `docs/01_SOUL.md`
- `api/routers/chat.py`
- `config/agents.json`
- `README.md`
- `docs/00_INDEX.md`
- `docs/AGENT_ONBOARDING.md`
- `docs/MIGANCORE_DIRECTION_LOCK.md`
- `training/innovation_engine_sft_40.jsonl`

Codex intentionally does not edit or stage unrelated local work such as
`api/entrypoint.sh`.

## QA QUESTIONS FOR CLAUDE

1. Confirm lazy tool router still loads `generate_image`, code tools,
   `synthesize`, `run_python`, and file tools for the relevant trigger words.
2. Confirm the larger runtime prompt still fits the target context budget.
3. If Claude's Day 73 tool additions include an eval route, add Innovation
   Engine prompts to eval coverage.

## RISKS

| Severity | Area | Description | Mitigation |
|---|---|---|---|
| P2 | Prompt length | Adding doctrine can increase system prompt size. | Keep runtime block compact; monitor context budget. |
| P2 | Tool bloat | "More tools" can become noisy if router over-selects. | Lazy router should stay intent-gated. |
| P2 | Creativity drift | Innovation can become random lists. | Doctrine requires rank, prototype, test, polish, toolify. |

## VALIDATION EXPECTED

- `api/routers/chat.py` compiles.
- `config/agents.json` is valid JSON.
- `training/innovation_engine_sft_40.jsonl` has 40 valid examples.
- Production health remains healthy after rebuild.

