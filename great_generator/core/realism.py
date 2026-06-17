"""Realism modes and field-aware value enrichment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from great_generator.core.reference_values import REFERENCE_VALUES_BY_FIELD
from great_generator.core.value_generator import RealisticValueGenerator, maybe_null
from great_generator.schemas.models import ColumnSpec, DomainSchema
from great_generator.utils.random import get_rng

VALID_REALISM_MODES = {"placeholder", "realistic"}

PERSON_NAME_FIELDS = {
    "customer_name",
    "member_name",
    "patient_name",
    "person_name",
    "full_name",
    "account_holder",
    "account_holder_name",
    "policy_holder",
    "policy_holder_name",
    "employee_name",
    "user_name",
    "contact_name",
    "resident_name",
    "name",
    "agent_name",
}

COMPANY_NAME_FIELDS = {
    "agency_name",
    "carrier_name",
    "company_name",
    "employer_name",
    "organization_name",
    "reinsurer_name",
    "shipper_name",
    "supplier_name",
    "vendor_name",
}

OPTIONAL_REALISTIC_NULL_RATE = 0.03


def validate_realism(realism: str) -> None:
    if realism not in VALID_REALISM_MODES:
        raise ValueError(
            f"Invalid realism '{realism}'. Expected one of {sorted(VALID_REALISM_MODES)}."
        )


def apply_realism_pandas(
    data: Mapping[str, pd.DataFrame],
    schema: DomainSchema,
    seed: int | None,
    realism: str,
    locale: str = "en_US",
) -> dict[str, pd.DataFrame]:
    """Apply placeholder compatibility or realistic value enrichment to pandas tables."""

    validate_realism(realism)
    enriched = {table_name: frame.copy() for table_name, frame in data.items()}

    for table_name, table_schema in schema.tables.items():
        if table_name not in enriched:
            continue
        frame = enriched[table_name]
        skip = {table_schema.primary_key, *(fk.column for fk in table_schema.foreign_keys)}
        columns = [column for column in table_schema.columns if column.name not in skip]

        _ensure_missing_schema_columns(
            frame=frame,
            table_name=table_name,
            columns=columns,
            realism=realism,
            seed=seed,
            locale=locale,
        )
        if realism == "realistic":
            _apply_realistic_columns(
                frame=frame,
                table_name=table_name,
                columns=columns,
                seed=seed,
                locale=locale,
            )
        enriched[table_name] = frame

    return enriched


def generate_value_for_field(field_name: str, value_gen: RealisticValueGenerator) -> Any:
    """Generate one realistic value for a common business field name."""

    field = field_name.lower()
    if field in PERSON_NAME_FIELDS:
        return value_gen.person_name()
    if field == "first_name":
        return value_gen.first_name()
    if field == "last_name":
        return value_gen.last_name()
    if "email" in field:
        return value_gen.email()
    if "phone" in field:
        return value_gen.phone_number()
    if "address" in field:
        return value_gen.street_address()
    if field == "city":
        return value_gen.city()
    if field == "state":
        return value_gen.state()
    if "zip" in field or "postal" in field:
        return value_gen.zip_code()
    if (
        field in COMPANY_NAME_FIELDS
        or field in {"company", "employer"}
        or field.endswith("_company")
        or field.endswith("_employer")
    ):
        return value_gen.company_name()
    if field in REFERENCE_VALUES_BY_FIELD:
        return value_gen.random_choice(REFERENCE_VALUES_BY_FIELD[field])
    if "merchant" in field and "name" in field:
        return value_gen.random_choice(REFERENCE_VALUES_BY_FIELD["merchant_name"])
    if "product" in field and "name" in field:
        return value_gen.random_choice(REFERENCE_VALUES_BY_FIELD["product_name"])
    if "provider" in field and "name" in field:
        return f"Dr. {value_gen.last_name()} {value_gen.random_choice(['MD', 'DO', 'NP', 'PA'])}"
    if field.endswith("_name"):
        return value_gen.company_name()
    return None


def _ensure_missing_schema_columns(
    frame: pd.DataFrame,
    table_name: str,
    columns: Sequence[ColumnSpec],
    realism: str,
    seed: int | None,
    locale: str,
) -> None:
    rows = len(frame)
    rng = get_rng(seed, f"realism.ensure.{table_name}")
    value_gen = RealisticValueGenerator(seed=seed, locale=locale).child(f"ensure.{table_name}")
    for column in columns:
        if column.name in frame.columns:
            continue
        if realism == "realistic":
            frame[column.name] = _realistic_series(column.name, rows, value_gen.child(column.name))
        else:
            frame[column.name] = _placeholder_values(column, rows, rng)


def _apply_realistic_columns(
    frame: pd.DataFrame,
    table_name: str,
    columns: Sequence[ColumnSpec],
    seed: int | None,
    locale: str,
) -> None:
    rows = len(frame)
    column_names = {column.name for column in columns} | set(frame.columns)
    value_gen = RealisticValueGenerator(seed=seed, locale=locale).child(f"table.{table_name}")
    person_records = [value_gen.person_record() for _ in range(rows)]

    first_present = "first_name" in column_names
    last_present = "last_name" in column_names
    email_present = any("email" in column.lower() for column in column_names)
    name_columns = [column for column in column_names if column.lower() in PERSON_NAME_FIELDS]

    if first_present:
        frame["first_name"] = [record.first_name for record in person_records]
    if last_present:
        frame["last_name"] = [record.last_name for record in person_records]
    for column in name_columns:
        frame[column] = [record.full_name for record in person_records]
    if email_present:
        for column in [column for column in column_names if "email" in column.lower()]:
            frame[column] = [record.email for record in person_records]

    for column in columns:
        name = column.name
        if name in {"first_name", "last_name"} or name.lower() in PERSON_NAME_FIELDS:
            continue
        if "email" in name.lower():
            continue
        generated = _realistic_series(name, rows, value_gen.child(name))
        if generated is not None:
            if column.nullable and _is_optional_business_field(name):
                nullable_rng = value_gen.child(f"{name}.nulls").random
                generated = [
                    maybe_null(value, OPTIONAL_REALISTIC_NULL_RATE, nullable_rng)
                    for value in generated
                ]
            frame[name] = generated


def _realistic_series(
    field_name: str,
    rows: int,
    value_gen: RealisticValueGenerator,
) -> list[Any] | None:
    field = field_name.lower()

    if field in {"first_name", "last_name"} or field in PERSON_NAME_FIELDS or "email" in field:
        return [generate_value_for_field(field, value_gen) for _ in range(rows)]
    if "phone" in field:
        return [value_gen.phone_number() for _ in range(rows)]
    if "address" in field:
        return [value_gen.street_address() for _ in range(rows)]
    if field == "city":
        return [value_gen.city() for _ in range(rows)]
    if field == "state":
        return [value_gen.state() for _ in range(rows)]
    if "zip" in field or "postal" in field:
        return [value_gen.zip_code() for _ in range(rows)]
    if (
        field in COMPANY_NAME_FIELDS
        or field in {"company", "employer"}
        or field.endswith("_company")
        or field.endswith("_employer")
    ):
        return [value_gen.company_name() for _ in range(rows)]
    if "merchant" in field and "name" in field:
        return [
            value_gen.random_choice(REFERENCE_VALUES_BY_FIELD["merchant_name"]) for _ in range(rows)
        ]
    if "product" in field and "name" in field:
        return [
            value_gen.random_choice(REFERENCE_VALUES_BY_FIELD["product_name"]) for _ in range(rows)
        ]
    if "provider" in field and "name" in field:
        return [
            f"Dr. {value_gen.last_name()} {value_gen.random_choice(['MD', 'DO', 'NP', 'PA'])}"
            for _ in range(rows)
        ]
    if "facility" in field and "name" in field:
        return [f"{value_gen.city()} Medical Center" for _ in range(rows)]
    if "dealer" in field and "name" in field:
        return [f"{value_gen.company_name()} Auto Group" for _ in range(rows)]
    if "campaign" in field and "name" in field:
        return [
            f"{value_gen.random_choice(['Growth', 'Retention', 'Launch', 'Holiday'])} Campaign {index}"
            for index in range(1, rows + 1)
        ]
    if "content" in field and "name" in field:
        values = REFERENCE_VALUES_BY_FIELD.get("content_title", [])
        return [value_gen.random_choice(values) for _ in range(rows)]
    if field.endswith("_name"):
        return [value_gen.company_name() for _ in range(rows)]
    if field in REFERENCE_VALUES_BY_FIELD:
        values = REFERENCE_VALUES_BY_FIELD[field]
        return [value_gen.random_choice(values) for _ in range(rows)]
    return None


def _placeholder_values(
    column: ColumnSpec,
    rows: int,
    rng: np.random.Generator,
) -> list[Any] | np.ndarray:
    name = column.name
    dtype = column.dtype.lower()
    if "bool" in dtype:
        return rng.random(rows) < 0.5
    if "float" in dtype or "double" in dtype or "decimal" in dtype:
        return np.round(rng.normal(100, 15, rows), 2)
    if "int" in dtype or "long" in dtype:
        return rng.integers(1, 1000, rows)
    if "email" in name.lower():
        return [f"{_entity_prefix(name)}_{index}@example.com" for index in range(1, rows + 1)]
    return [f"{name}_{index}" for index in range(1, rows + 1)]


def _entity_prefix(name: str) -> str:
    for suffix in ("_email", "email"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)].strip("_") or "user"
    return "user"


def _is_optional_business_field(field_name: str) -> bool:
    field = field_name.lower()
    return any(token in field for token in ("phone", "email", "address", "secondary", "middle"))
