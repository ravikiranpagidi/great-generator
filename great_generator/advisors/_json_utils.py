"""JSON helpers for advisor responses."""

from __future__ import annotations

import json
from typing import Any

from great_generator.advisors.exceptions import AdvisorResponseError


def parse_json_object(text: str, *, lenient: bool = False) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        if not lenient:
            raise AdvisorResponseError(
                "Advisor response was not valid JSON.",
                raw_response=text,
            ) from exc
        extracted = extract_first_json_object(text)
        if extracted is None:
            raise AdvisorResponseError(
                "Advisor response did not contain a JSON object.",
                text,
            ) from exc
        try:
            value = json.loads(extracted)
        except json.JSONDecodeError as exc:
            raise AdvisorResponseError(
                "Advisor response did not contain a valid JSON object.",
                raw_response=text,
            ) from exc
    if not isinstance(value, dict):
        raise AdvisorResponseError("Advisor response must be a JSON object.", raw_response=text)
    return value


def extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None
