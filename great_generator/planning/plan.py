"""Planning artifacts for deterministic schema generation."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from great_generator.schemas.models import DomainSchema, TableSchema

PLAN_VERSION = "1.0"
VALID_SOURCES = {"advisor", "user_edit", "default"}
VALID_PII_CLASSES = {
    None,
    "none",
    "direct_identifier",
    "quasi_identifier",
    "sensitive_attribute",
}


@dataclass(frozen=True)
class ColumnStrategy:
    """Generation strategy for one column."""

    column: str
    dtype: str
    strategy: str
    parameters: dict[str, Any]
    rationale: str | None
    confidence: float
    source: str

    def __post_init__(self) -> None:
        _validate_source(self.source)
        _validate_confidence(self.confidence)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ColumnStrategy:
        return cls(
            column=str(payload.get("column", "")),
            dtype=str(payload.get("dtype", "string")),
            strategy=str(payload.get("strategy", "string.pattern")),
            parameters=dict(payload.get("parameters") or {}),
            rationale=_optional_string(payload.get("rationale")),
            confidence=float(payload.get("confidence", 0.0)),
            source=str(payload.get("source", "advisor")),
        )


@dataclass(frozen=True)
class GenerationPlan:
    """Inspectable plan consumed by deterministic generation."""

    plan_version: str
    schema_fingerprint: str
    advisor: str
    model_id: str | None
    generated_at: str
    human_reviewed: bool
    columns: list[ColumnStrategy]
    inter_column_rules: list[dict[str, Any]]
    notes: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version": self.plan_version,
            "schema_fingerprint": self.schema_fingerprint,
            "advisor": self.advisor,
            "model_id": self.model_id,
            "generated_at": self.generated_at,
            "human_reviewed": self.human_reviewed,
            "columns": [column.to_dict() for column in self.columns],
            "inter_column_rules": copy.deepcopy(self.inter_column_rules),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GenerationPlan:
        return cls(
            plan_version=str(payload.get("plan_version", PLAN_VERSION)),
            schema_fingerprint=str(payload.get("schema_fingerprint", "")),
            advisor=str(payload.get("advisor", "none")),
            model_id=_optional_string(payload.get("model_id")),
            generated_at=str(payload.get("generated_at") or utc_now()),
            human_reviewed=bool(payload.get("human_reviewed", False)),
            columns=[ColumnStrategy.from_dict(item) for item in payload.get("columns", [])],
            inter_column_rules=[dict(item) for item in payload.get("inter_column_rules", [])],
            notes=_optional_string(payload.get("notes")),
        )

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(_pretty_json(self.to_dict()), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> GenerationPlan:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    def with_edit(self, column: str, **changes: Any) -> GenerationPlan:
        """Return a new plan with one column strategy changed."""

        updated: list[ColumnStrategy] = []
        found = False
        for strategy in self.columns:
            if strategy.column != column:
                updated.append(strategy)
                continue
            found = True
            allowed = set(ColumnStrategy.__dataclass_fields__) - {"column"}
            unknown = set(changes) - allowed
            if unknown:
                raise ValueError(f"Unknown column strategy fields: {sorted(unknown)}")
            updated.append(replace(strategy, **changes, source="user_edit"))
        if not found:
            raise ValueError(f"Column '{column}' was not found in the plan.")
        return replace(self, columns=updated, human_reviewed=True)

    def fingerprint(self) -> str:
        return "sha256:" + hashlib.sha256(canonical_json(self.to_dict()).encode()).hexdigest()

    def to_custom_rules(self) -> dict[str, dict[str, Any]]:
        """Convert plan strategies to existing semantic generation rules."""

        rules: dict[str, dict[str, Any]] = {}
        for column in self.columns:
            name = column.column.split(".")[-1]
            parameters = copy.deepcopy(column.parameters)
            rule_type = parameters.pop("type", None) or strategy_to_semantic_type(
                column.strategy,
                column.dtype,
                column.column,
            )
            if rule_type:
                parameters["type"] = rule_type
            rules[name] = parameters
        return rules


@dataclass(frozen=True)
class ColumnTag:
    """Advisory tags for one schema column."""

    column: str
    pii_class: str | None
    business_semantic: str | None
    suggested_masking: str | None
    confidence: float
    source: str = "advisor"
    rationale: str | None = None

    def __post_init__(self) -> None:
        _validate_source(self.source)
        _validate_confidence(self.confidence)
        if self.pii_class not in VALID_PII_CLASSES:
            raise ValueError(
                "pii_class must be one of none, direct_identifier, "
                "quasi_identifier, sensitive_attribute, or null."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ColumnTag:
        return cls(
            column=str(payload.get("column", "")),
            pii_class=_optional_string(payload.get("pii_class")),
            business_semantic=_optional_string(payload.get("business_semantic")),
            suggested_masking=_optional_string(payload.get("suggested_masking")),
            confidence=float(payload.get("confidence", 0.0)),
            source=str(payload.get("source", "advisor")),
            rationale=_optional_string(payload.get("rationale")),
        )


@dataclass(frozen=True)
class ColumnTags:
    """Inspectable column tags produced by an advisor."""

    tag_version: str
    schema_fingerprint: str
    advisor: str
    model_id: str | None
    generated_at: str
    human_reviewed: bool
    columns: list[ColumnTag]
    notes: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag_version": self.tag_version,
            "schema_fingerprint": self.schema_fingerprint,
            "advisor": self.advisor,
            "model_id": self.model_id,
            "generated_at": self.generated_at,
            "human_reviewed": self.human_reviewed,
            "columns": [column.to_dict() for column in self.columns],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ColumnTags:
        return cls(
            tag_version=str(payload.get("tag_version", PLAN_VERSION)),
            schema_fingerprint=str(payload.get("schema_fingerprint", "")),
            advisor=str(payload.get("advisor", "none")),
            model_id=_optional_string(payload.get("model_id")),
            generated_at=str(payload.get("generated_at") or utc_now()),
            human_reviewed=bool(payload.get("human_reviewed", False)),
            columns=[ColumnTag.from_dict(item) for item in payload.get("columns", [])],
            notes=_optional_string(payload.get("notes")),
        )

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(_pretty_json(self.to_dict()), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> ColumnTags:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    def with_edit(self, column: str, **changes: Any) -> ColumnTags:
        """Return new tags with one column changed."""

        updated: list[ColumnTag] = []
        found = False
        for tag in self.columns:
            if tag.column != column:
                updated.append(tag)
                continue
            found = True
            allowed = set(ColumnTag.__dataclass_fields__) - {"column"}
            unknown = set(changes) - allowed
            if unknown:
                raise ValueError(f"Unknown column tag fields: {sorted(unknown)}")
            updated.append(replace(tag, **changes, source="user_edit"))
        if not found:
            raise ValueError(f"Column '{column}' was not found in the tags.")
        return replace(self, columns=updated, human_reviewed=True)


@dataclass(frozen=True)
class RealismReport:
    """Design-time review output for a generated sample."""

    report_version: str
    advisor: str
    model_id: str | None
    generated_at: str
    sample_size: int
    warnings: list[str]
    suggestions: list[str]
    notes: str | None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RealismReport:
        return cls(
            report_version=str(payload.get("report_version", PLAN_VERSION)),
            advisor=str(payload.get("advisor", "none")),
            model_id=_optional_string(payload.get("model_id")),
            generated_at=str(payload.get("generated_at") or utc_now()),
            sample_size=int(payload.get("sample_size", 0)),
            warnings=[str(item) for item in payload.get("warnings", [])],
            suggestions=[str(item) for item in payload.get("suggestions", [])],
            notes=_optional_string(payload.get("notes")),
            score=_optional_float(payload.get("score")),
        )

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(_pretty_json(self.to_dict()), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> RealismReport:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)


def make_generation_plan(
    schema: Any,
    advisor: str,
    model_id: str | None,
    columns: list[ColumnStrategy],
    inter_column_rules: list[dict[str, Any]] | None = None,
    notes: str | None = None,
) -> GenerationPlan:
    return GenerationPlan(
        plan_version=PLAN_VERSION,
        schema_fingerprint=schema_fingerprint(schema),
        advisor=advisor,
        model_id=model_id,
        generated_at=utc_now(),
        human_reviewed=False,
        columns=columns,
        inter_column_rules=list(inter_column_rules or []),
        notes=notes,
    )


def make_column_tags(
    schema: Any,
    advisor: str,
    model_id: str | None,
    columns: list[ColumnTag],
    notes: str | None = None,
) -> ColumnTags:
    return ColumnTags(
        tag_version=PLAN_VERSION,
        schema_fingerprint=schema_fingerprint(schema),
        advisor=advisor,
        model_id=model_id,
        generated_at=utc_now(),
        human_reviewed=False,
        columns=columns,
        notes=notes,
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def schema_fingerprint(schema: Any) -> str:
    payload = canonical_schema(schema)
    digest = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    return "sha256:" + digest


def canonical_schema(schema: Any) -> dict[str, Any]:
    """Return a stable JSON-safe schema description."""

    if isinstance(schema, DomainSchema):
        return {
            "kind": "domain",
            "name": _clean_string(schema.name),
            "description": _clean_string(schema.description),
            "behaviors": sorted(_clean_string(item) for item in schema.behaviors),
            "tables": {
                name: _table_schema_payload(table)
                for name, table in sorted(schema.tables.items(), key=lambda item: item[0])
            },
        }
    if isinstance(schema, TableSchema):
        return {"kind": "table", "table": _table_schema_payload(schema)}
    try:
        from great_generator.schemas.generation import normalize_single_table_schema

        table, _source = normalize_single_table_schema(schema)
        return {"kind": "table", "table": _table_schema_payload(table)}
    except Exception:
        return {"kind": "raw", "value": _clean_string(str(schema))}


def schema_columns(schema: Any) -> list[dict[str, Any]]:
    if isinstance(schema, DomainSchema):
        rows: list[dict[str, Any]] = []
        for table_name, table in sorted(schema.tables.items(), key=lambda item: item[0]):
            for column in table.columns:
                rows.append(
                    {
                        "table": table_name,
                        "column": table_name + "." + column.name,
                        "name": column.name,
                        "dtype": column.dtype,
                        "nullable": column.nullable,
                        "description": column.description,
                    }
                )
        return rows
    if isinstance(schema, TableSchema):
        table = schema
    else:
        try:
            from great_generator.schemas.generation import normalize_single_table_schema

            table, _source = normalize_single_table_schema(schema)
        except Exception:
            return []
    return [
        {
            "table": table.name,
            "column": column.name,
            "name": column.name,
            "dtype": column.dtype,
            "nullable": column.nullable,
            "description": column.description,
        }
        for column in table.columns
    ]


def default_strategy_for_dtype(dtype: str) -> str:
    normalized = dtype.lower().strip()
    if "bool" in normalized:
        return "boolean"
    if "timestamp" in normalized or "datetime" in normalized:
        return "timestamp_range"
    if normalized == "date" or normalized.endswith("date"):
        return "date_range"
    if "decimal" in normalized or "numeric" in normalized:
        return "numeric.normal"
    if any(token in normalized for token in ("double", "float", "real")):
        return "numeric.normal"
    if "bigint" in normalized or "long" in normalized:
        return "numeric.integer"
    if "int" in normalized and "interval" not in normalized:
        return "numeric.integer"
    return "string.pattern"


def strategy_to_semantic_type(strategy: str, dtype: str, column: str) -> str:
    normalized = strategy.lower().strip()
    direct = {
        "faker.name": "full_name",
        "faker.first_name": "first_name",
        "faker.last_name": "last_name",
        "faker.email": "email",
        "faker.phone": "phone",
        "faker.address": "address",
        "faker.city": "city",
        "faker.state": "state",
        "faker.postal_code": "postal_code",
        "numeric.integer": "generic_int",
        "numeric.normal": "generic_float",
        "numeric.uniform": "generic_float",
        "date_range": "generic_date",
        "timestamp_range": "datetime",
        "categorical": "category",
        "boolean": "boolean",
        "string.pattern": "generic_string",
    }
    if normalized.startswith("semantic."):
        return normalized.split(".", 1)[1]
    if normalized in direct:
        return direct[normalized]
    try:
        from great_generator.schemas.semantic import infer_field_semantic_type

        return infer_field_semantic_type(column.split(".")[-1], dtype)
    except Exception:
        return "generic_string"


def canonical_json(value: Any) -> str:
    return json.dumps(_canonical_value(value), sort_keys=True, separators=(",", ":"), default=str)


def _pretty_json(value: Any) -> str:
    return json.dumps(_canonical_value(value), indent=2, sort_keys=True, default=str) + "\n"


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            _clean_string(str(key)): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, str):
        return _clean_string(value)
    return value


def _table_schema_payload(table: TableSchema) -> dict[str, Any]:
    return {
        "name": _clean_string(table.name),
        "primary_key": table.primary_key,
        "description": _clean_string(table.description),
        "columns": [
            {
                "name": _clean_string(column.name),
                "dtype": _clean_string(column.dtype),
                "nullable": bool(column.nullable),
                "description": _clean_string(column.description),
            }
            for column in table.columns
        ],
        "foreign_keys": [
            {
                "column": _clean_string(fk.column),
                "parent_table": _clean_string(fk.parent_table),
                "parent_column": _clean_string(fk.parent_column),
            }
            for fk in table.foreign_keys
        ],
    }


def _clean_string(value: str) -> str:
    return " ".join(value.strip().split())


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _validate_source(source: str) -> None:
    if source not in VALID_SOURCES:
        raise ValueError("source must be advisor, user_edit, or default.")


def _validate_confidence(confidence: float) -> None:
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0.")
