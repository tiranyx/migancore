"""Exports organ — PDF and slides generation."""

from typing import Any

import structlog

from .base import ToolContext, ToolExecutionError

logger = structlog.get_logger()


async def _export_pdf(args: dict, ctx: ToolContext) -> dict:
    """Export content to PDF via WeasyPrint (sandboxed)."""
    content = args.get("content", "").strip()
    title = args.get("title", "Document").strip()
    if not content:
        raise ToolExecutionError("'content' is required")

    # NOTE: WeasyPrint requires libcairo etc. Only available inside container.
    try:
        from weasyprint import HTML
        html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title></head>
        <body style='font-family: DejaVu Sans, sans-serif; padding: 2cm;'>{content}</body></html>"""
        pdf_bytes = HTML(string=html).write_pdf()
        import base64
        b64 = base64.b64encode(pdf_bytes).decode("ascii")
        logger.info("tool.export_pdf", title=title, bytes=len(pdf_bytes))
        return {"pdf_base64": b64, "title": title, "size_bytes": len(pdf_bytes)}
    except ImportError:
        raise ToolExecutionError("PDF export not available in this environment (WeasyPrint missing)")
    except Exception as exc:
        raise ToolExecutionError(f"PDF export failed: {exc}") from exc


async def _export_slides(args: dict, ctx: ToolContext) -> dict:
    """Export content to HTML slides (reveal.js compatible)."""
    slides = args.get("slides", [])
    title = args.get("title", "Presentation").strip()
    if not slides:
        raise ToolExecutionError("'slides' is required (list of markdown strings)")

    slide_html = "\n".join(
        f"<section data-markdown><textarea data-template>{s}</textarea></section>"
        for s in slides
    )
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>
    <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css'>
    </head><body><div class='reveal'><div class='slides'>{slide_html}</div></div>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.js'></script>
    <script>Reveal.initialize();</script></body></html>"""

    logger.info("tool.export_slides", title=title, count=len(slides))
    return {"html": html, "title": title, "slide_count": len(slides)}


HANDLERS: dict[str, Any] = {
    "export_pdf": _export_pdf,
    "export_slides": _export_slides,
}
