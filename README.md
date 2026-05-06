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
uv run pytest
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

## CLI Usage

```bash
uv run conversion-triage --source-type asr --context "meeting transcript" \
  --text "for all intensive purposes we shipped on 32/13/2026"
```

You can also read from stdin:

```bash
echo "This is rnore text with 1l and 0CR noise" | uv run conversion-triage --source-type ocr
```

## Run Web App

```bash
uv run uvicorn conversion_triage.web.app:create_app --factory --reload
```

Open http://127.0.0.1:8000 and paste text to review flagged spans.

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
├── web/
│   ├── app.py
│   ├── routes.py
│   ├── templates/
│   └── static/
└── cli.py
```
