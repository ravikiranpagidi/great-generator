"""File-backed cache for advisor calls."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from great_generator.planning.plan import canonical_json

DEFAULT_CACHE_PATH = Path(".gg_cache")


def make_cache_key(
    advisor: str,
    model_id: str,
    prompt_version: str,
    input_payload: Any,
) -> tuple[str, str]:
    input_json = canonical_json(input_payload)
    input_hash = hashlib.sha256(input_json.encode()).hexdigest()
    material = advisor + model_id + prompt_version + input_json
    cache_key = hashlib.sha256(material.encode()).hexdigest()
    return cache_key, input_hash


def get(
    key: str,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    advisor: str | None = None,
) -> dict[str, Any] | None:
    path = _entry_path(key, cache_path, advisor) if advisor else _find_entry_path(key, cache_path)
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def put(
    key: str,
    value: dict[str, Any],
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    advisor: str | None = None,
) -> None:
    target = _entry_path(key, cache_path, advisor or str(value.get("advisor", "unknown")))
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(value)
    payload.setdefault("cache_key", key)
    payload.setdefault("created_at", _utc_now())
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clear(advisor: str | None = None, cache_path: str | Path = DEFAULT_CACHE_PATH) -> None:
    root = Path(cache_path)
    if not root.exists():
        return
    if advisor is None:
        shutil.rmtree(root)
        return
    path = root / _advisor_short_name(advisor)
    if path.exists():
        shutil.rmtree(path)


def _entry_path(key: str, cache_path: str | Path, advisor: str) -> Path:
    short = _advisor_short_name(advisor)
    return Path(cache_path) / short / key[:2] / (key + ".json")


def _find_entry_path(key: str, cache_path: str | Path) -> Path | None:
    root = Path(cache_path)
    matches = list(root.glob("*/" + key[:2] + "/" + key + ".json"))
    return matches[0] if matches else None


def _advisor_short_name(advisor: str) -> str:
    prefix = advisor.split(":", 1)[0] if advisor else "unknown"
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", prefix.strip().lower())
    return cleaned or "unknown"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
