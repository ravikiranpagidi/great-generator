"""Manifest helpers for generated data outputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from great_generator.planning import ColumnTags, GenerationPlan


def advisor_manifest_entry(
    plan: GenerationPlan,
    *,
    tags: ColumnTags | None = None,
    called_at: Sequence[str] | None = None,
    cache_hit: bool | None = None,
) -> dict[str, Any]:
    """Build the advisor section for a manifest."""

    entry: dict[str, Any] = {
        "name": plan.advisor,
        "model_id": plan.model_id,
        "plan_version": plan.plan_version,
        "plan_fingerprint": plan.fingerprint(),
        "called_at": list(called_at or ["schema_understanding"]),
        "human_reviewed": plan.human_reviewed,
    }
    if cache_hit is not None:
        entry["cache_hit"] = bool(cache_hit)
    if tags is not None:
        entry["columns_tagged"] = len(tags.columns)
        if "column_tagging" not in entry["called_at"]:
            entry["called_at"].append("column_tagging")
    return entry


def enrich_manifest(
    manifest: Mapping[str, Any],
    *,
    plan: GenerationPlan | None = None,
    tags: ColumnTags | None = None,
    called_at: Sequence[str] | None = None,
    cache_hit: bool | None = None,
) -> dict[str, Any]:
    """Return a manifest copy with advisor metadata when a plan is present."""

    enriched = dict(manifest)
    if plan is not None:
        enriched["advisor"] = advisor_manifest_entry(
            plan,
            tags=tags,
            called_at=called_at,
            cache_hit=cache_hit,
        )
    return enriched
