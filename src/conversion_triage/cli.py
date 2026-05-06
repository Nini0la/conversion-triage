from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from conversion_triage.engine import triage_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Triages OCR/ASR converted text for likely issues."
    )
    parser.add_argument("--source-type", choices=["asr", "ocr"], required=True)
    parser.add_argument("--context", default=None)
    parser.add_argument("--text", default=None, help="Input text. If omitted, stdin is used.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        parser.error("No input text provided. Use --text or pipe input via stdin.")

    result = triage_text(text=text, source_type=args.source_type, context=args.context)
    payload: dict[str, Any] = result.model_dump(mode="json")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
