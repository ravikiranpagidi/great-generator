"""Advisor protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from great_generator.planning import ColumnTags, GenerationPlan, RealismReport

Schema = Any


@runtime_checkable
class Advisor(Protocol):
    name: str
    model_id: str

    def propose_plan(
        self,
        schema: Schema,
        hints: dict | None = None,
    ) -> GenerationPlan: ...

    def tag_columns(
        self,
        schema: Schema,
        samples: dict[str, list] | None = None,
    ) -> ColumnTags: ...

    def review_sample(
        self,
        data: dict,
        plan: GenerationPlan,
        sample_size: int = 500,
    ) -> RealismReport: ...
