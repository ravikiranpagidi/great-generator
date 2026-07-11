"""Ollama advisor implementation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

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

DEFAULT_OLLAMA_MODEL = "llama3.1:8b"


class OllamaAdvisor:
    """Advisor backed by a local Ollama server."""

    def __init__(
        self,
        model_id: str = DEFAULT_OLLAMA_MODEL,
        cache_path: str | Path = cache.DEFAULT_CACHE_PATH,
        refresh_cache: bool = False,
        host: str | None = None,
    ) -> None:
        self.model_id = model_id or DEFAULT_OLLAMA_MODEL
        self.name = "ollama:" + self.model_id
        self.cache_path = Path(cache_path)
        self.refresh_cache = refresh_cache
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.last_cache_hit = False

    def propose_plan(self, schema: Any, hints: dict | None = None) -> GenerationPlan:
        input_payload = {"schema": canonical_schema(schema), "hints": canonical_json(hints or {})}
        prompt = render_prompt(
            "propose_plan_v1.txt",
            {"schema_json": input_payload["schema"], "hints_json": input_payload["hints"]},
        )
        payload = self._cached_json_call("propose_plan_v1", input_payload, prompt)
        return plan_from_advisor_payload(
            payload,
            schema=schema,
            advisor=self.name,
            model_id=self.model_id,
        )

    def tag_columns(self, schema: Any, samples: dict[str, list] | None = None) -> Any:
        input_payload = {
            "schema": canonical_schema(schema),
            "samples": canonical_json(samples or {}),
        }
        prompt = render_prompt(
            "tag_columns_v1.txt",
            {"schema_json": input_payload["schema"], "samples_json": input_payload["samples"]},
        )
        payload = self._cached_json_call("tag_columns_v1", input_payload, prompt)
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
            "data": canonical_json(data),
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
        payload = self._cached_json_call("review_sample_v1", input_payload, prompt)
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
                return dict(entry.get("response", {}))
        self.last_cache_hit = False
        raw = self._call_ollama(prompt)
        try:
            payload = parse_json_object(raw, lenient=True)
        except AdvisorResponseError:
            raw = self._call_ollama(prompt + "\nReturn one valid JSON object only.")
            payload = parse_json_object(raw, lenient=True)
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

    def _call_ollama(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model_id,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0},
            }
        ).encode("utf-8")
        request = Request(
            self.host + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise AdvisorUnavailableError(
                "Ollama advisor is unavailable. Check that Ollama is running and OLLAMA_HOST is correct."
            ) from exc
        return str(payload.get("response", ""))
