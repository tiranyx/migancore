# =============================================================================
# OpenRouter — Day 73 Sprint 1.5: multi-source teacher diversity (Tabayyun)
# =============================================================================
# Free models via OpenRouter (no payment needed):
#   meta-llama/llama-3.3-70b-instruct:free   — strong open-source
#   meta-llama/llama-3.1-70b-instruct:free   — older variant
#   google/gemma-2-9b-it:free                — fast Google model
#   mistralai/mistral-7b-instruct:free       — efficient EU model
#   qwen/qwen-2.5-7b-instruct:free           — Chinese/Indonesian friendly
#
# Tabayyun principle (multi-source verify): rotate teachers per distillation
# round → broader consensus, less bias from any single perspective.

OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-70b-instruct:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]


async def call_openrouter(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    model: str = "meta-llama/llama-3.3-70b-instruct:free",
) -> TeacherResponse:
    """OpenRouter unified API — access to 50+ models including free tier."""
    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise TeacherError("OPENROUTER_API_KEY not set")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://api.migancore.com",
        "X-Title": "MiganCore Distillation",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.6,
    }

    url = "https://openrouter.ai/api/v1/chat/completions"
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code != 200:
                    raise TeacherError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise TeacherError(f"OpenRouter no choices: {data}")
                text = choices[0].get("message", {}).get("content", "")
                if not text:
                    finish = choices[0].get("finish_reason", "")
                    raise TeacherError(f"OpenRouter empty response, finish={finish}")
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)
                model_label = model.split('/')[-1].replace(':free', '')
                return TeacherResponse(
                    text=text,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    est_cost_usd=0.0,
                    teacher=f"openrouter:{model_label}",
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise TeacherError(f"OpenRouter network: {exc}")
                await asyncio.sleep(2 ** attempt)
    raise TeacherError("OpenRouter: exhausted retries")


# Convenience shortcuts per free model
async def call_llama33(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="meta-llama/llama-3.3-70b-instruct:free")


async def call_gemma2(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="google/gemma-2-9b-it:free")


async def call_qwen25(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="qwen/qwen-2.5-7b-instruct:free")


async def call_mistral7b(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="mistralai/mistral-7b-instruct:free")


TEACHER_REGISTRY.update({
    "llama33":   call_llama33,
    "gemma2":    call_gemma2,
    "qwen25":    call_qwen25,
    "mistral7b": call_mistral7b,
})


_original_is_teacher_available = is_teacher_available


def is_teacher_available(teacher: str) -> bool:  # noqa: F811
    """Extended availability check — OpenRouter teachers share one API key."""
    if teacher in ("llama33", "gemma2", "qwen25", "mistral7b"):
        api_key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "")
        return bool(api_key)
    return _original_is_teacher_available(teacher)
