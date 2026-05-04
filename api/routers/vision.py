"""
Vision router (Day 40) — direct image-describe endpoint for chat UI.

Wraps the existing analyze_image tool_executor handler so the chat frontend
can pre-process attached images BEFORE injecting their captions into the
user message. Keeps the LLM brain text-pure (modality-as-tool routing per
Anthropic Claude Skills spec Mar 2026 — aligns with ADO modular brain vision).

Endpoint:
  POST /v1/vision/describe
    body: {image_url? OR image_base64?, mime_type?, question?, lang?}
    auth: Bearer JWT (current_user)
    returns: {answer, model, lang, question}

Backend: Gemini 2.5 Flash Vision (~$0.0001/image), Claude Sonnet 4.5 fallback.
Note: do NOT add `from __future__ import annotations` here — FastAPI introspect.
"""
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from deps.auth import get_current_user
from deps.rate_limit import limiter
from models import User

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/vision", tags=["vision"])


class DescribeRequest(BaseModel):
    image_url: str | None = Field(None, description="HTTPS URL to image; either this or image_base64 required.")
    image_base64: str | None = Field(None, description="Base64-encoded image bytes; either this or image_url required.")
    mime_type: str = Field("image/jpeg", description="MIME type of image_base64 (e.g. 'image/jpeg', 'image/png').")
    question: str = Field(
        "Describe this image in detail. List notable elements and any visible text.",
        description="What to ask about the image.",
    )
    lang: str = Field("id", pattern="^(id|en)$", description="Response language: id (default) or en.")


class DescribeResponse(BaseModel):
    answer: str
    model: str
    lang: str
    question: str


@router.post("/describe", response_model=DescribeResponse)
@limiter.limit("30/minute")
async def describe_image(
    request: Request,
    body: DescribeRequest,
    current_user: User = Depends(get_current_user),
):
    """Describe / OCR / answer questions about an image via Gemini Vision.

    Frontend usage: chat.html attaches image -> POST here -> get description
    -> prepend to user message before sending to chat. AI sees text caption,
    no need to handle base64 directly in the conversation.
    """
    if not body.image_url and not body.image_base64:
        raise HTTPException(status_code=400, detail="Provide either image_url or image_base64")

    # Reuse the existing tool_executor handler so logic stays in one place.
    from services.tool_executor import _analyze_image, ToolContext, ToolExecutionError

    ctx = ToolContext(
        tenant_id=str(current_user.tenant_id),
        agent_id="vision-direct",  # not a real agent — handler ignores this for vision
    )

    try:
        result = await _analyze_image(
            {
                "image_url": body.image_url,
                "image_base64": body.image_base64,
                "mime_type": body.mime_type,
                "question": body.question,
                "lang": body.lang,
            },
            ctx,
        )
    except ToolExecutionError as exc:
        logger.warning("vision.describe_tool_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Vision backend error: {exc}")
    except Exception as exc:
        logger.error("vision.describe_unknown_error", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Vision processing failed: {exc}")

    logger.info(
        "vision.describe_ok",
        tenant_id=str(current_user.tenant_id),
        model=result.get("model"),
        lang=result.get("lang"),
        answer_len=len(result.get("answer", "")),
    )

    return DescribeResponse(
        answer=result.get("answer", ""),
        model=result.get("model", "unknown"),
        lang=result.get("lang", body.lang),
        question=result.get("question", body.question),
    )
