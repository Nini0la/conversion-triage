from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from conversion_triage.engine import TriageResult, triage_text

router = APIRouter()
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render_highlighted_text(text: str, result: TriageResult) -> str:
    """Render HTML with inline marks for flagged spans."""
    if not text:
        return ""

    cursor = 0
    parts: list[str] = []

    for flag in sorted(result.flags, key=lambda item: (item.start, item.end)):
        start = max(0, min(flag.start, len(text)))
        end = max(start, min(flag.end, len(text)))
        if start < cursor:
            continue

        parts.append(escape(text[cursor:start]))
        severity = escape(flag.severity.value)
        category = escape(flag.category.value)
        reason = escape(flag.reason)
        snippet = escape(text[start:end])
        parts.append(
            f'<mark class="flag {severity}" title="{category}: {reason}">{snippet}</mark>'
        )
        cursor = end

    parts.append(escape(text[cursor:]))
    return "".join(parts)


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "text": "",
            "source_type": "asr",
            "context": "",
            "result": None,
            "highlighted_text": "",
        },
    )


@router.post("/triage", response_class=HTMLResponse)
def triage_page(
    request: Request,
    text: str = Form(...),
    source_type: str = Form(...),
    context: str = Form(default=""),
) -> HTMLResponse:
    result = triage_text(text=text, source_type=source_type, context=context or None)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "text": text,
            "source_type": source_type,
            "context": context,
            "result": result,
            "highlighted_text": render_highlighted_text(text, result),
        },
    )
