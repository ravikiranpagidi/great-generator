"""Validation and conversion for advisor JSON payloads."""

from __future__ import annotations

from typing import Any

from great_generator.advisors.exceptions import AdvisorResponseError
from great_generator.planning import (
    ColumnStrategy,
    ColumnTag,
    GenerationPlan,
    RealismReport,
    schema_fingerprint,
)
from great_generator.planning.plan import PLAN_VERSION, utc_now

try:  # pragma: no cover, covered when optional dependency is installed
    from pydantic import BaseModel, Field, ValidationError
except ImportError:  # pragma: no cover, base install keeps this optional
    BaseModel = None
    Field = None
    ValidationError = Exception


if BaseModel is not None:  # pragma: no branch

    class _StrategyModel(BaseModel):
        column: str
        dtype: str = "string"
        strategy: str
        parameters: dict[str, Any] = Field(default_factory=dict)
        rationale: str | None = None
        confidence: float = 0.0
        source: str = "advisor"

    class _PlanResponseModel(BaseModel):
        columns: list[_StrategyModel] = Field(default_factory=list)
        inter_column_rules: list[dict[str, Any]] = Field(default_factory=list)
        notes: str | None = None

    class _TagModel(BaseModel):
        column: str
        pii_class: str | None = None
        business_semantic: str | None = None
        suggested_masking: str | None = None
        confidence: float = 0.0
        source: str = "advisor"
        rationale: str | None = None

    class _TagsResponseModel(BaseModel):
        columns: list[_TagModel] = Field(default_factory=list)
        notes: str | None = None

    class _ReportResponseModel(BaseModel):
        warnings: list[str] = Field(default_factory=list)
        suggestions: list[str] = Field(default_factory=list)
        notes: str | None = None
        score: float | None = None


def plan_from_advisor_payload(
    payload: dict[str, Any],
    *,
    schema: Any,
    advisor: str,
    model_id: str,
) -> GenerationPlan:
    try:
        normalized = _validate_plan_payload(payload)
        return GenerationPlan(
            plan_version=str(payload.get("plan_version", PLAN_VERSION)),
            schema_fingerprint=str(payload.get("schema_fingerprint") or schema_fingerprint(schema)),
            advisor=advisor,
            model_id=model_id,
            generated_at=str(payload.get("generated_at") or utc_now()),
            human_reviewed=bool(payload.get("human_reviewed", False)),
            columns=[ColumnStrategy.from_dict(item) for item in normalized["columns"]],
            inter_column_rules=[dict(item) for item in normalized["inter_column_rules"]],
            notes=normalized.get("notes"),
        )
    except Exception as exc:
        raise AdvisorResponseError(
            "Advisor plan response did not match the expected schema."
        ) from exc


def tags_from_advisor_payload(
    payload: dict[str, Any],
    *,
    schema: Any,
    advisor: str,
    model_id: str,
) -> Any:
    from great_generator.planning import ColumnTags

    try:
        normalized = _validate_tags_payload(payload)
        return ColumnTags(
            tag_version=str(payload.get("tag_version", PLAN_VERSION)),
            schema_fingerprint=str(payload.get("schema_fingerprint") or schema_fingerprint(schema)),
            advisor=advisor,
            model_id=model_id,
            generated_at=str(payload.get("generated_at") or utc_now()),
            human_reviewed=bool(payload.get("human_reviewed", False)),
            columns=[ColumnTag.from_dict(item) for item in normalized["columns"]],
            notes=normalized.get("notes"),
        )
    except Exception as exc:
        raise AdvisorResponseError(
            "Advisor tag response did not match the expected schema."
        ) from exc


def report_from_advisor_payload(
    payload: dict[str, Any],
    *,
    advisor: str,
    model_id: str,
    sample_size: int,
) -> RealismReport:
    try:
        normalized = _validate_report_payload(payload)
        return RealismReport(
            report_version=str(payload.get("report_version", PLAN_VERSION)),
            advisor=advisor,
            model_id=model_id,
            generated_at=str(payload.get("generated_at") or utc_now()),
            sample_size=sample_size,
            warnings=[str(item) for item in normalized["warnings"]],
            suggestions=[str(item) for item in normalized["suggestions"]],
            notes=normalized.get("notes"),
            score=normalized.get("score"),
        )
    except Exception as exc:
        raise AdvisorResponseError(
            "Advisor review response did not match the expected schema."
        ) from exc


def _validate_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if BaseModel is not None:
        try:
            return _PlanResponseModel.model_validate(payload).model_dump()
        except ValidationError as exc:
            raise AdvisorResponseError("Advisor plan response failed validation.") from exc
    return {
        "columns": list(payload.get("columns", [])),
        "inter_column_rules": list(payload.get("inter_column_rules", [])),
        "notes": payload.get("notes"),
    }


def _validate_tags_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if BaseModel is not None:
        try:
            return _TagsResponseModel.model_validate(payload).model_dump()
        except ValidationError as exc:
            raise AdvisorResponseError("Advisor tag response failed validation.") from exc
    return {
        "columns": list(payload.get("columns", [])),
        "notes": payload.get("notes"),
    }


def _validate_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if BaseModel is not None:
        try:
            return _ReportResponseModel.model_validate(payload).model_dump()
        except ValidationError as exc:
            raise AdvisorResponseError("Advisor review response failed validation.") from exc
    return {
        "warnings": list(payload.get("warnings", [])),
        "suggestions": list(payload.get("suggestions", [])),
        "notes": payload.get("notes"),
        "score": payload.get("score"),
    }
