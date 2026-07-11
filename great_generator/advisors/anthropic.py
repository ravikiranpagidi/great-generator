"""Anthropic advisor implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from great_generator.advisors import cache
from great_generator.advisors._json_utils import parse_json_object
from great_generator.advisors._prompting import SYSTEM_PROMPT, render_prompt
from great_generator.advisors._validation import (
    plan_from_advisor_payload,
    report_from_advisor_payload,
    tags_from_advisor_payload,
)
from great_generator.advisors.exceptions import AdvisorResponseError, AdvisorUnavailableError
from great_generator.planning import GenerationPlan, canonical_schema
from great_generator.planning.plan import canonical_json

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"


class AnthropicAdvisor:
    """Advisor backed by the Anthropic SDK."""

    def __init__(
        self,
        model_id: str = DEFAULT_ANTHROPIC_MODEL,
        cache_path: str | Path = cache.DEFAULT_CACHE_PATH,
        refresh_cache: bool = False,
    ) -> None:
        self.model_id = model_id or DEFAULT_ANTHROPIC_MODEL
        self.name = "anthropic:" + self.model_id
        self.cache_path = Path(cache_path)
        self.refresh_cache = refresh_cache
        self.last_cache_hit = False

    def propose_plan(self, schema: Any, hints: dict | None = None) -> GenerationPlan:
        input_payload = {
            "schema": canonical_schema(schema),
            "hints": _clean_payload(hints or {}),
        }
        prompt = render_prompt(
            "propose_plan_v1.txt",
            {"schema_json": input_payload["schema"], "hints_json": input_payload["hints"]},
        )
        payload = self._cached_json_call("propose_plan_v1", input_payload, prompt, max_tokens=3000)
        return plan_from_advisor_payload(
            payload,
            schema=schema,
            advisor=self.name,
            model_id=self.model_id,
        )

    def tag_columns(
        self,
        schema: Any,
        samples: dict[str, list] | None = None,
    ) -> Any:
        input_payload = {
            "schema": canonical_schema(schema),
            "samples": _clean_payload(samples or {}),
        }
        prompt = render_prompt(
            "tag_columns_v1.txt",
            {"schema_json": input_payload["schema"], "samples_json": input_payload["samples"]},
        )
        payload = self._cached_json_call("tag_columns_v1", input_payload, prompt, max_tokens=2500)
        return tags_from_advisor_payload(
            payload,
            schema=schema,
            advisor=self.name,
            model_id=self.model_id,
        )

    def review_sample(
        self,
        data: dict,
        plan: GenerationPlan,
        sample_size: int = 500,
    ) -> Any:
        input_payload = {
            "data": _clean_payload(data),
            "plan": plan.to_dict(),
            "sample_size": int(sample_size),
        }
        prompt = render_prompt(
            "review_sample_v1.txt",
            {
                "data_json": input_payload["data"],
                "plan_json": input_payload["plan"],
                "sample_size": input_payload["sample_size"],
            },
        )
        payload = self._cached_json_call("review_sample_v1", input_payload, prompt, max_tokens=2000)
        return report_from_advisor_payload(
            payload,
            advisor=self.name,
            model_id=self.model_id,
            sample_size=sample_size,
        )

    def _cached_json_call(
        self,
        prompt_version: str,
        input_payload: dict[str, Any],
        prompt: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        key, input_hash = cache.make_cache_key(
            self.name,
            self.model_id,
            prompt_version,
            input_payload,
        )
        if not self.refresh_cache:
            entry = cache.get(key, self.cache_path, advisor=self.name)
            if entry is not None:
                self.last_cache_hit = True
                response = entry.get("response", {})
                return dict(response)
        self.last_cache_hit = False
        raw = self._call_model(prompt, max_tokens=max_tokens)
        try:
            payload = parse_json_object(raw)
        except AdvisorResponseError:
            raw = self._call_model(prompt + "\nReturn one valid JSON object only.", max_tokens)
            payload = parse_json_object(raw)
        cache.put(
            key,
            {
                "cache_key": key,
                "advisor": self.name,
                "model_id": self.model_id,
                "prompt_version": prompt_version,
                "input_hash": input_hash,
                "response": payload,
            },
            self.cache_path,
            advisor=self.name,
        )
        return payload

    def _call_model(self, prompt: str, max_tokens: int) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AdvisorUnavailableError(
                "ANTHROPIC_API_KEY is required for advisor='anthropic:<model>'."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise AdvisorUnavailableError(
                "Install the Anthropic extra with: pip install great-generator[anthropic]"
            ) from exc
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=self.model_id,
            temperature=0,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        parts: list[str] = []
        for block in getattr(message, "content", []):
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
        if not parts:
            raise AdvisorResponseError("Anthropic response did not contain text.")
        return "".join(parts)


def _clean_payload(value: Any) -> Any:
    return canonical_json(value)
