# conversion-triage

`conversion-triage` is a library-first Python project for reviewing OCR/ASR converted text and flagging likely conversion issues.

The triage engine is reusable on its own. The web app is a thin FastAPI wrapper around the engine.

## Requirements

- Python 3.11+
- `uv`

## Setup

```bash
uv sync --group dev
```

## Run Tests

```bash
uv run python -m pytest
```

## Run Lint

```bash
uv run ruff check .
```

## Library Usage

```python
from conversion_triage.engine import triage_text

result = triage_text(
    text="for all intensive purposes we shipped on 32/13/2026",
    source_type="asr",
    context="meeting transcript",
)

for flag in result.flags:
    print(flag.category, flag.severity, flag.reason)
```

You can also triage directly from a YouTube subtitle source:

```python
from conversion_triage.engine import triage_youtube_url

result = triage_youtube_url(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    source_type="asr",
    context="video transcript",
)
```

## CLI Usage

```bash
uv run conversion-triage --source-type asr --context "meeting transcript" \
  --text "for all intensive purposes we shipped on 32/13/2026"
```

Or with YouTube subtitles:

```bash
uv run conversion-triage --source-type asr \
  --youtube-url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Run Web App

```bash
uv run uvicorn conversion_triage.web.app:create_app --factory --reload
```

Open http://127.0.0.1:8000 and either paste text or provide a YouTube link.

## Project Layout

```text
src/conversion_triage/
├── engine/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── schemas.py
│   ├── rules.py
│   ├── chunking.py
│   ├── merge.py
│   └── llm.py
├── transcripts/
│   ├── __init__.py
│   ├── base.py
│   └── youtube.py
├── web/
│   ├── app.py
│   ├── routes.py
│   ├── templates/
│   └── static/
└── cli.py
```
