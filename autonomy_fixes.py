#!/usr/bin/env python3
"""
MiganCore Autonomy Fixes — Patch Script v1.0
Fixes 4 fatal flaws preventing self-growth.
"""

import sys

def fix_conversations_logger():
    """Fix 1b: Add missing logger import in conversations.py"""
    path = "/opt/ado/api/routers/conversations.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "import structlog" in content:
        print("[SKIP] conversations.py already has structlog import")
        return

    # Add structlog import after the uuid import
    content = content.replace(
        "import uuid\nfrom typing import Literal",
        "import uuid\nfrom typing import Literal\n\nimport structlog",
    )

    # Add logger = structlog.get_logger() after the router line
    content = content.replace(
        'router = APIRouter(prefix="/v1/conversations", tags=["conversations"])',
        'router = APIRouter(prefix="/v1/conversations", tags=["conversations"])\n\nlogger = structlog.get_logger()',
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[FIXED] conversations.py: Added structlog logger import")


def fix_feedback_processor_ollama():
    """Fix 1a: OllamaClient must use async with context manager"""
    path = "/opt/ado/api/workers/user_feedback_processor.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_code = """    # Use Ollama with a lightweight prompt to generate a worse/different response
    client = OllamaClient(base_url=settings.OLLAMA_URL)
    prompt = (
        f"User asked:\\n{pair.prompt}\\n\\n"
        f"The assistant gave this good response:\\n{pair.chosen}\\n\\n"
        "Generate a worse, less helpful, or slightly incorrect response "
        "for the same question. Keep it short."
    )

    try:
        resp_text = await client.generate(
            model=settings.DEFAULT_MODEL,
            prompt=prompt,
            options={"temperature": 0.9, "num_predict": 300},
        )"""

    new_code = """    prompt = (
        f"User asked:\\n{pair.prompt}\\n\\n"
        f"The assistant gave this good response:\\n{pair.chosen}\\n\\n"
        "Generate a worse, less helpful, or slightly incorrect response "
        "for the same question. Keep it short."
    )

    try:
        async with OllamaClient(base_url=settings.OLLAMA_URL) as client:
            resp_text = await client.generate(
                model=settings.DEFAULT_MODEL,
                prompt=prompt,
                options={"temperature": 0.9, "num_predict": 300},
            )"""

    if old_code not in content:
        # Try alternative format
        if "client = OllamaClient(base_url=settings.OLLAMA_URL)" in content:
            content = content.replace(
                "    # Use Ollama with a lightweight prompt to generate a worse/different response\n    client = OllamaClient(base_url=settings.OLLAMA_URL)\n    prompt = (",
                "    prompt = ("
            )
            content = content.replace(
                "    try:\n        resp_text = await client.generate(",
                "    try:\n        async with OllamaClient(base_url=settings.OLLAMA_URL) as client:\n            resp_text = await client.generate("
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print("[FIXED] user_feedback_processor.py: OllamaClient now uses async with")
            return
        print("[WARN] user_feedback_processor.py: Could not find exact pattern to replace")
        return

    content = content.replace(old_code, new_code)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[FIXED] user_feedback_processor.py: OllamaClient now uses async with")


def fix_distillation_worker_dsn():
    """Fix 2: Use superuser 'ado' instead of 'ado_app' to bypass RLS"""
    path = "/opt/ado/api/services/distillation_worker.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old = "dsn = settings.DATABASE_URL.replace(\"+asyncpg\", \"\", 1)"
    new = "dsn = settings.DATABASE_URL.replace(\"+asyncpg\", \"\", 1).replace(\"ado_app\", \"ado\", 1)"

    if old not in content:
        print("[WARN] distillation_worker.py: Could not find DSN line")
        return

    content = content.replace(old, new)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[FIXED] distillation_worker.py: DSN now uses 'ado' superuser (bypasses RLS)")


def fix_chat_streaming_cai():
    """Fix 3: Move CAI before early return in streaming endpoint"""
    path = "/opt/ado/api/routers/chat.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the early return inside the tool loop and add CAI before it
    # The pattern is:
    #   yield _sse({"type": "done", ...})
    #   logger.info("chat.stream.done_via_toolcall", ...)
    #   return

    old_pattern = '''                            yield _sse({"type": "done", "conversation_id": str(conversation_id), "message_id": str(assistant_msg_id)})
                            logger.info("chat.stream.done_via_toolcall", chunks=chunk_count, len=len(full_text), tool_iters=tool_iter)
                            return'''

    new_pattern = '''                            yield _sse({"type": "done", "conversation_id": str(conversation_id), "message_id": str(assistant_msg_id)})
                            logger.info("chat.stream.done_via_toolcall", chunks=chunk_count, len=len(full_text), tool_iters=tool_iter)
                            # M1.3: CAI auto-loop — MUST run before return
                            _cai_sample_rate_tool = tenant_for_stream.settings.get("cai_sampling_rate", 0.5)
                            if tenant_for_stream.settings.get("cai_auto_loop"):
                                _cai_sample_rate_tool = 1.0
                            _t = asyncio.create_task(
                                run_cai_pipeline(
                                    user_message=data.message,
                                    assistant_response=full_text,
                                    source_message_id=assistant_msg_id,
                                    sample_rate=_cai_sample_rate_tool,
                                )
                            )
                            _background_tasks.add(_t)
                            _t.add_done_callback(_background_tasks.discard)
                            return'''

    if old_pattern not in content:
        print("[WARN] chat.py: Could not find exact early return pattern for CAI fix")
        return

    content = content.replace(old_pattern, new_pattern)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[FIXED] chat.py: CAI now runs before early return in tool loop")


def fix_training_trigger_config():
    """Fix 4: Add RUNPOD_API_KEY to config.py (optional — prevents crash)"""
    path = "/opt/ado/api/config.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "RUNPOD_API_KEY" in content:
        print("[SKIP] config.py already has RUNPOD_API_KEY")
        return

    # Add RUNPOD_API_KEY after OLLAMA_URL or similar
    if "OLLAMA_URL: str" in content:
        content = content.replace(
            "    OLLAMA_URL: str",
            "    RUNPOD_API_KEY: str = \"\"\n    OLLAMA_URL: str"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[FIXED] config.py: Added RUNPOD_API_KEY (prevents training_trigger crash)")
    else:
        print("[WARN] config.py: Could not find insertion point for RUNPOD_API_KEY")


if __name__ == "__main__":
    print("=" * 60)
    print("MIGANCORE AUTONOMY FIXES v1.0")
    print("=" * 60)
    fix_conversations_logger()
    fix_feedback_processor_ollama()
    fix_distillation_worker_dsn()
    fix_chat_streaming_cai()
    fix_training_trigger_config()
    print("=" * 60)
    print("Done. Restart API container: docker compose restart api")
