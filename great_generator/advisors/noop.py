"""Default offline advisor."""

from __future__ import annotations

from typing import Any

from great_generator.planning import ColumnStrategy, ColumnTag, GenerationPlan, RealismReport
from great_generator.planning.plan import (
    PLAN_VERSION,
    default_strategy_for_dtype,
    make_column_tags,
    make_generation_plan,
    schema_columns,
    utc_now,
)


class NoOpAdvisor:
    """Advisor that never calls a model or reads credentials."""

    name = "none"
    model_id = "none"

    def propose_plan(self, schema: Any, hints: dict | None = None) -> GenerationPlan:
        columns = [
            ColumnStrategy(
                column=str(item["column"]),
                dtype=str(item["dtype"]),
                strategy=default_strategy_for_dtype(str(item["dtype"])),
                parameters={},
                rationale="Default dtype strategy.",
                confidence=0.0,
                source="default",
            )
            for item in schema_columns(schema)
        ]
        return make_generation_plan(
            schema,
            advisor=self.name,
            model_id=None,
            columns=columns,
            inter_column_rules=[],
            notes="No advisor was configured. The plan uses dtype defaults.",
        )

    def tag_columns(
        self,
        schema: Any,
        samples: dict[str, list] | None = None,
    ) -> Any:
        columns = [
            ColumnTag(
                column=str(item["column"]),
                pii_class=None,
                business_semantic=None,
                suggested_masking=None,
                confidence=0.0,
                source="default",
                rationale=None,
            )
            for item in schema_columns(schema)
        ]
        return make_column_tags(
            schema,
            advisor=self.name,
            model_id=None,
            columns=columns,
            notes="No advisor was configured. Column tags were not inferred.",
        )

    def review_sample(
        self,
        data: dict,
        plan: GenerationPlan,
        sample_size: int = 500,
    ) -> RealismReport:
        return RealismReport(
            report_version=PLAN_VERSION,
            advisor=self.name,
            model_id=None,
            generated_at=utc_now(),
            sample_size=sample_size,
            warnings=[],
            suggestions=[],
            notes="No advisor was configured. Realism review was not run.",
            score=None,
        )
