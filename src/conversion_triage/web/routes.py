from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from conversion_triage.engine import TriageResult, fetch_youtube_text, triage_text
from conversion_triage.transcripts import TranscriptProviderError

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
            "youtube_url": "",
            "source_type": "asr",
            "context": "",
            "result": None,
            "error": "",
            "imported_from_youtube": False,
            "highlighted_text": "",
        },
    )


@router.post("/triage", response_class=HTMLResponse)
def triage_page(
    request: Request,
    text: str = Form(default=""),
    youtube_url: str = Form(default=""),
    source_type: str = Form(...),
    context: str = Form(default=""),
    action: str = Form(default="triage"),
) -> HTMLResponse:
    working_text = text.strip()
    youtube_url = youtube_url.strip()
    error = ""
    result: TriageResult | None = None
    imported_from_youtube = False

    if action == "import_youtube":
        if not youtube_url:
            error = "Provide a YouTube URL to import subtitles."
        else:
            try:
                working_text = fetch_youtube_text(url=youtube_url)
                imported_from_youtube = True
            except TranscriptProviderError as exc:
                error = str(exc)
    elif youtube_url:
        try:
            working_text = fetch_youtube_text(url=youtube_url)
            imported_from_youtube = True
        except TranscriptProviderError as exc:
            error = str(exc)

    if action == "triage" and not error and not working_text:
        error = "Provide text or a YouTube URL."

    if action == "triage" and not error:
        result = triage_text(text=working_text, source_type=source_type, context=context or None)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "text": working_text,
            "youtube_url": youtube_url,
            "source_type": source_type,
            "context": context,
            "result": result,
            "error": error,
            "imported_from_youtube": imported_from_youtube,
            "highlighted_text": render_highlighted_text(working_text, result)
            if result is not None
            else "",
        },
    )
