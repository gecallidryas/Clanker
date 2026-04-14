"""Capture a Gemini google_search grounding response and save the raw JSON shape.

Usage:
    python scripts/capture_gemini_grounding.py --output tests/fixtures/gemini_grounding_response.json

If GEMINI_API_KEY is not set, the script writes a safe sample payload that matches
what the parser expects. This keeps the contract refreshable without embedding
secrets in the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - optional dependency for local refreshes
    genai = None
    genai_types = None

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_QUERY = "Search for a recent Gemini grounding example and return grounded sources."
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "gemini_grounding_response.json"
SAMPLE_PAYLOAD: dict[str, Any] = {
    "candidates": [
        {
            "grounding_metadata": {
                "grounding_chunks": [
                    {
                        "web": {
                            "uri": "https://example.com/articles/gemini-grounding",
                            "title": "Example Gemini Grounding Article",
                        }
                    },
                    {
                        "web": {
                            "uri": "https://developers.googleblog.com/google-search",
                            "title": "Google Search in Gemini",
                        }
                    },
                ],
                "grounding_supports": [
                    {
                        "segment": {
                            "text": "Example Gemini Grounding Article explains how grounded results are attached to search sources."
                        },
                        "grounding_chunk_indices": [0],
                    },
                    {
                        "segment": {
                            "text": "Google Search in Gemini demonstrates the google_search tool shape and grounding metadata."
                        },
                        "grounding_chunk_indices": [1],
                    },
                ],
            }
        }
    ]
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {
            key: _jsonable(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _capture_live_payload(api_key: str, model: str, query: str) -> dict[str, Any]:
    if genai is None or genai_types is None:
        raise RuntimeError("google-genai is not installed")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=query,
        config=genai_types.GenerateContentConfig(
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
        ),
    )
    return _jsonable(response)


def _get_configured_api_key() -> str | None:
    direct_key = os.getenv("GEMINI_API_KEY")
    if direct_key:
        return direct_key

    for index in range(1, 11):
        numbered_key = os.getenv(f"GEMINI_API_KEY_{index}")
        if numbered_key:
            return numbered_key
    return None


def _is_canonical_fixture_path(path: Path) -> bool:
    return path.resolve() == DEFAULT_OUTPUT.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    args = parser.parse_args()

    api_key = _get_configured_api_key()
    if api_key:
        payload = _capture_live_payload(api_key, args.model, args.query)
        source = "live Gemini response"
    else:
        if _is_canonical_fixture_path(args.output):
            print(
                "Error: refusing to overwrite the canonical fixture with the built-in sample payload. "
                "Provide a Gemini API key or capture to a temporary output path instead.",
                file=sys.stderr,
            )
            return 1
        payload = SAMPLE_PAYLOAD
        source = "built-in sample payload"
        print(
            "Warning: no GEMINI_API_KEY detected; writing the built-in sample payload instead of a live capture.",
            file=sys.stderr,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} from {source}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
