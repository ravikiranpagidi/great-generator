"""Semantic field inference and realistic schema-driven generation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from great_generator.core.reference_values import PRODUCT_NAMES
from great_generator.core.value_generator import RealisticValueGenerator
from great_generator.schemas.models import ColumnSpec, TableSchema

ABBREVIATIONS = {
    "cust": "customer",
    "emp": "employee",
    "addr": "address",
    "dob": "date_of_birth",
    "qty": "quantity",
    "amt": "amount",
    "num": "number",
    "no": "number",
    "zip": "postal_code",
    "zipcode": "postal_code",
    "tel": "phone",
    "cell": "mobile",
    "org": "organization",
    "dept": "department",
    "txn": "transaction",
    "tx": "transaction",
    "acct": "account",
    "prod": "product",
    "desc": "description",
}

NAME_ENTITIES = {"customer", "employee", "member", "user", "patient", "student", "person"}
ID_PREFIXES = {
    "customer_id": "CUST",
    "employee_id": "EMP",
    "member_id": "MBR",
    "user_id": "USER",
    "account_id": "ACCT",
    "transaction_id": "TXN",
    "order_id": "ORD",
    "product_id": "PROD",
    "patient_id": "PAT",
    "student_id": "STU",
    "id": "ID",
}

STATUS_VALUES = {
    "status": ["Active", "Inactive", "Pending", "Closed"],
    "account_status": ["Active", "Inactive", "Dormant", "Closed"],
    "order_status": ["Pending", "Shipped", "Delivered", "Cancelled"],
    "payment_status": ["Paid", "Pending", "Failed", "Refunded"],
    "employment_status": ["Active", "Terminated", "On Leave"],
}

DOMAIN_PRESETS: dict[str, dict[str, Any]] = {
    "banking": {
        "values": {
            "account_status": ["Active", "Dormant", "Closed", "Frozen"],
            "account_type": ["Checking", "Savings", "Credit Card", "Loan"],
            "transaction_type": ["Deposit", "Withdrawal", "Transfer", "Payment"],
            "risk_level": ["Low", "Medium", "High"],
            "status": ["Active", "Pending", "Closed", "Review"],
        },
        "id_prefixes": {"account_id": "ACCT", "transaction_id": "TXN", "customer_id": "CUST"},
        "amount_ranges": {"transaction_amount": (1.0, 5000.0), "balance": (0.0, 100000.0)},
    },
    "retail": {
        "values": {
            "order_status": ["Pending", "Shipped", "Delivered", "Cancelled", "Returned"],
            "customer_type": ["New", "Returning", "Loyalty"],
            "category": ["Electronics", "Clothing", "Home", "Beauty", "Grocery"],
            "status": ["Active", "Inactive", "Pending"],
        },
        "id_prefixes": {"order_id": "ORD", "product_id": "PROD", "customer_id": "CUST"},
    },
    "hr": {
        "values": {
            "department": ["Engineering", "Finance", "HR", "Marketing", "Operations"],
            "employment_status": ["Active", "Terminated", "On Leave"],
            "job_title": ["Data Engineer", "Analyst", "Manager", "Developer"],
            "status": ["Active", "Inactive", "On Leave"],
        },
        "id_prefixes": {"employee_id": "EMP"},
        "amount_ranges": {"salary": (30000.0, 250000.0), "income": (20000.0, 300000.0)},
    },
    "healthcare": {
        "values": {
            "department": ["Primary Care", "Cardiology", "Radiology", "Emergency"],
            "status": ["Active", "Discharged", "Pending", "Closed"],
            "risk_level": ["Low", "Medium", "High"],
        },
        "id_prefixes": {"patient_id": "PAT", "member_id": "MBR"},
    },
    "insurance": {
        "values": {
            "status": ["Active", "Expired", "Cancelled", "Pending"],
            "claim_status": ["Approved", "Denied", "Pending", "In Review", "Paid"],
            "risk_level": ["Low", "Medium", "High"],
        },
        "id_prefixes": {"customer_id": "CUST", "claim_id": "CLM", "policy_id": "POL"},
    },
    "education": {
        "values": {
            "status": ["Active", "Inactive", "Graduated", "Withdrawn"],
            "student_status": ["Enrolled", "Graduated", "Withdrawn", "On Leave"],
            "department": ["Science", "Mathematics", "Business", "Engineering", "Arts"],
        },
        "id_prefixes": {"student_id": "STU"},
    },
}

DEFAULT_VALUES = {
    "department": ["Engineering", "Finance", "HR", "Marketing", "Operations", "Risk"],
    "job_title": ["Data Engineer", "Analyst", "Manager", "Developer", "Architect"],
    "role": ["Admin", "User", "Analyst", "Manager", "Viewer"],
    "industry": ["Healthcare", "Finance", "Retail", "Technology", "Manufacturing"],
    "gender": ["Female", "Male", "Non-binary", "Prefer not to say"],
    "priority": ["Low", "Medium", "High", "Critical"],
    "risk_level": ["Low", "Medium", "High"],
    "customer_type": ["Retail", "Business", "Enterprise"],
    "member_type": ["Standard", "Premium", "Enterprise"],
    "category": ["Electronics", "Clothing", "Home", "Healthcare", "Finance"],
    "description": [
        "Standard customer record",
        "Generated business sample",
        "Synthetic test scenario",
        "Demo-ready record",
    ],
}


def normalize_column_name(column_name: str) -> str:
    """Normalize names such as ``memberName`` or ``cust-name`` to expanded snake case."""

    camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(column_name).strip())
    cleaned = re.sub(r"[\s\\-]+", "_", camel).lower()
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    raw_tokens = [token for token in cleaned.split("_") if token]
    tokens: list[str] = []
    for token in raw_tokens:
        expanded = ABBREVIATIONS.get(token, token)
        tokens.extend(part for part in expanded.split("_") if part)
    return "_".join(tokens)


def semantic_tokens(column_name: str) -> set[str]:
    """Return normalized token set for semantic matching."""

    return set(normalize_column_name(column_name).split("_"))


def infer_field_semantic_type(column_name: str, data_type: str) -> str:
    """Infer semantic field type from column name and declared data type."""

    normalized = normalize_column_name(column_name)
    tokens = set(normalized.split("_"))
    kind = dtype_kind(data_type)

    if "email" in tokens:
        return "email"
    if tokens & {"phone", "mobile"}:
        return "phone"
    if "address" in tokens or normalized.startswith("address_line"):
        return "address"
    if "city" in tokens:
        return "city"
    if "state" in tokens or "province" in tokens:
        return "state"
    if "postal" in tokens and "code" in tokens:
        return "postal_code"
    if "country" in tokens:
        return "country"
    if "company" in tokens or "organization" in tokens:
        return "company"
    if "department" in tokens:
        return "department"
    if "job" in tokens and "title" in tokens:
        return "job_title"
    if "role" in tokens:
        return "role"
    if "industry" in tokens:
        return "industry"

    if "id" in tokens or normalized.endswith("_id"):
        if "transaction" in tokens:
            return "transaction_id"
        if "order" in tokens:
            return "order_id"
        if "account" in tokens:
            return "account_id"
        if "employee" in tokens:
            return "employee_id"
        if "customer" in tokens:
            return "customer_id"
        if "member" in tokens:
            return "member_id"
        if "user" in tokens:
            return "user_id"
        if "product" in tokens:
            return "product_id"
        if normalized == "id":
            return "id"
        return "id"

    if "first" in tokens and "name" in tokens:
        return "first_name"
    if "last" in tokens and "name" in tokens:
        return "last_name"
    if "name" in tokens:
        if "company" in tokens or "organization" in tokens:
            return "company"
        if "product" in tokens:
            return "product_name"
        if "department" in tokens:
            return "department"
        if tokens & NAME_ENTITIES or "full" in tokens or normalized == "name":
            entity = next((token for token in NAME_ENTITIES if token in tokens), None)
            return f"{entity}_name" if entity else "full_name"
        return "full_name"

    if "age" in tokens:
        if "employee" in tokens:
            return "employee_age"
        if "student" in tokens:
            return "student_age"
        if "child" in tokens:
            return "child_age"
        if "senior" in tokens:
            return "senior_age"
        if "customer" in tokens:
            return "customer_age"
        return "age"

    if normalized in {"date_of_birth", "birth_date"}:
        return "date_of_birth"
    if "created" in tokens and ("date" in tokens or "at" in tokens or kind == "timestamp"):
        return "created_at" if kind == "timestamp" or "at" in tokens else "created_date"
    if "updated" in tokens and ("date" in tokens or "at" in tokens or kind == "timestamp"):
        return "updated_at" if kind == "timestamp" or "at" in tokens else "updated_date"
    if "start" in tokens and "date" in tokens:
        return "start_date"
    if "end" in tokens and "date" in tokens:
        return "end_date"
    if "transaction" in tokens and "date" in tokens:
        return "transaction_date"
    if "order" in tokens and "date" in tokens:
        return "order_date"
    if kind == "date":
        return "date"
    if kind == "timestamp":
        return "datetime"

    if "salary" in tokens:
        return "salary"
    if "income" in tokens:
        return "income"
    if "transaction" in tokens and "amount" in tokens:
        return "transaction_amount"
    if "total" in tokens and "amount" in tokens:
        return "total_amount"
    if "amount" in tokens or "payment" in tokens or "tax" in tokens:
        return "amount"
    if "price" in tokens or normalized == "unit_price":
        return "price"
    if "cost" in tokens:
        return "cost"
    if "balance" in tokens:
        return "balance"
    if "revenue" in tokens:
        return "revenue"
    if "discount" in tokens:
        return "discount"
    if "quantity" in tokens:
        return "quantity"

    if "status" in tokens:
        if "account" in tokens:
            return "account_status"
        if "order" in tokens:
            return "order_status"
        if "payment" in tokens:
            return "payment_status"
        if "employment" in tokens or "employee" in tokens:
            return "employment_status"
        return "status"
    if "type" in tokens:
        if "customer" in tokens:
            return "customer_type"
        if "member" in tokens:
            return "member_type"
        if "account" in tokens:
            return "account_type"
        if "transaction" in tokens:
            return "transaction_type"
    if "gender" in tokens:
        return "gender"
    if "category" in tokens:
        return "category"
    if "priority" in tokens:
        return "priority"
    if "risk" in tokens and "level" in tokens:
        return "risk_level"

    if "product" in tokens:
        return "product_name"
    if "sku" in tokens:
        return "sku"
    if "description" in tokens:
        return "description"

    if kind in {"int", "long"}:
        return "generic_int"
    if kind in {"float", "decimal"}:
        return "generic_float"
    if kind == "bool":
        return "boolean"
    return "generic_string"


def generate_semantic_table(
    table: TableSchema,
    rows: int,
    seed: int | None = None,
    domain: str | None = None,
    custom_rules: Mapping[str, Mapping[str, Any]] | None = None,
) -> pd.DataFrame:
    """Generate a realistic pandas DataFrame from schema semantics."""

    if rows < 0:
        raise ValueError("rows must be greater than or equal to zero.")

    rules = {str(name): dict(rule) for name, rule in (custom_rules or {}).items()}
    value_gen = RealisticValueGenerator(seed=seed).child(
        f"semantic.{table.name}.{domain or 'generic'}"
    )
    semantics = {
        column.name: _rule_type(rules.get(column.name))
        or infer_field_semantic_type(column.name, column.dtype)
        for column in table.columns
    }
    frame: dict[str, list[Any] | np.ndarray | pd.DatetimeIndex] = {}
    person_records = [value_gen.person_record() for _ in range(rows)]
    age_values = _person_age_values(semantics, rows, value_gen)
    date_context = _date_context(semantics, rows, value_gen, age_values)

    for column in table.columns:
        rule = rules.get(column.name, {})
        semantic = semantics[column.name]
        frame[column.name] = generate_semantic_values(
            column=column,
            semantic_type=semantic,
            rows=rows,
            value_gen=value_gen.child(column.name),
            domain=domain,
            rule=rule,
            person_records=person_records,
            age_values=age_values,
            date_context=date_context,
        )

    result = pd.DataFrame(frame, columns=[column.name for column in table.columns])
    _apply_cross_field_consistency(result, semantics)
    return result


def generate_semantic_values(
    column: ColumnSpec,
    semantic_type: str,
    rows: int,
    value_gen: RealisticValueGenerator,
    domain: str | None = None,
    rule: Mapping[str, Any] | None = None,
    person_records: Sequence[Any] | None = None,
    age_values: Sequence[int] | None = None,
    date_context: Mapping[str, Sequence[Any]] | None = None,
) -> list[Any] | np.ndarray | pd.DatetimeIndex:
    """Generate values for a semantic type, honoring optional user overrides."""

    rule = dict(rule or {})
    kind = dtype_kind(column.dtype)
    if "values" in rule:
        values = list(rule["values"])
        return [value_gen.random_choice(values) for _ in range(rows)]
    if semantic_type.endswith("_id") or semantic_type == "id":
        return _id_values(column, semantic_type, rows, kind, value_gen, domain, rule)
    if semantic_type in {
        "first_name",
        "last_name",
        "full_name",
        "customer_name",
        "employee_name",
        "member_name",
        "user_name",
        "patient_name",
        "student_name",
        "person_name",
    }:
        return _person_values(semantic_type, rows, value_gen, person_records)
    if semantic_type in {
        "age",
        "employee_age",
        "customer_age",
        "student_age",
        "child_age",
        "senior_age",
    }:
        min_value, max_value = _numeric_bounds(rule, _age_range(semantic_type))
        return value_gen.random_ints(rows, int(min_value), int(max_value))
    if semantic_type == "email":
        if person_records:
            return [record.email for record in person_records]
        return [value_gen.email() for _ in range(rows)]
    if semantic_type == "phone":
        return [value_gen.phone_number() for _ in range(rows)]
    if semantic_type == "address":
        return [value_gen.street_address() for _ in range(rows)]
    if semantic_type == "city":
        return [value_gen.city() for _ in range(rows)]
    if semantic_type == "state":
        return [value_gen.state() for _ in range(rows)]
    if semantic_type == "postal_code":
        return [value_gen.zip_code() for _ in range(rows)]
    if semantic_type == "country":
        return [value_gen.country() for _ in range(rows)]
    if semantic_type == "company":
        return [value_gen.company_name() for _ in range(rows)]
    if semantic_type == "product_name":
        return [value_gen.random_choice(PRODUCT_NAMES) for _ in range(rows)]
    if semantic_type == "sku":
        return [f"SKU{index:06d}" for index in range(1, rows + 1)]
    if semantic_type in DEFAULT_VALUES or _preset_values(domain, semantic_type):
        values = _preset_values(domain, semantic_type) or DEFAULT_VALUES[semantic_type]
        return [value_gen.random_choice(values) for _ in range(rows)]
    if semantic_type in STATUS_VALUES:
        values = _preset_values(domain, semantic_type) or STATUS_VALUES[semantic_type]
        return [value_gen.random_choice(values) for _ in range(rows)]
    if semantic_type in {
        "salary",
        "income",
        "amount",
        "transaction_amount",
        "price",
        "cost",
        "balance",
        "revenue",
        "discount",
        "generic_float",
    }:
        min_value, max_value = _numeric_bounds(rule, _amount_range(semantic_type, domain))
        values = [value_gen.random_amount(float(min_value), float(max_value)) for _ in range(rows)]
        return _numeric_values(values, kind)
    if semantic_type == "quantity":
        min_value, max_value = _numeric_bounds(rule, (1, 10))
        return value_gen.random_ints(rows, int(min_value), int(max_value))
    if date_context is not None and semantic_type in date_context:
        return list(date_context[semantic_type])
    if semantic_type in {"date", "created_date", "updated_date", "transaction_date", "order_date"}:
        return _date_values(rows, value_gen, rule)
    if semantic_type in {"datetime", "created_at", "updated_at"}:
        return _datetime_values(rows, value_gen, rule)
    if semantic_type == "date_of_birth":
        ages = age_values or value_gen.random_ints(rows, 18, 90)
        return _dob_values(ages, value_gen)
    if semantic_type == "boolean":
        return [value_gen.random_bool() for _ in range(rows)]
    if semantic_type == "generic_int":
        min_value, max_value = _numeric_bounds(rule, (1, 100))
        return value_gen.random_ints(rows, int(min_value), int(max_value))
    if semantic_type == "description":
        values = DEFAULT_VALUES["description"]
        return [value_gen.random_choice(values) for _ in range(rows)]
    return [
        f"{normalize_column_name(column.name) or column.name}_{index}"
        for index in range(1, rows + 1)
    ]


def validate_generated_data(
    records: Any,
    schema: TableSchema | Mapping[str, str] | str | pd.DataFrame | None = None,
    rules: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate practical quality expectations for generated schema-driven data."""

    frame = _records_to_frame(records)
    errors: list[str] = []
    warnings: list[str] = []
    if frame.empty:
        return {"passed": True, "errors": [], "warnings": ["No records to validate."]}

    rules = {str(name): dict(rule) for name, rule in (rules or {}).items()}
    schema_map = _schema_dtype_map(schema, frame)
    semantics = {
        column: _rule_type(rules.get(column))
        or infer_field_semantic_type(column, schema_map[column])
        for column in frame.columns
    }

    for column, semantic in semantics.items():
        series = frame[column]
        rule = rules.get(column, {})
        if semantic in {
            "age",
            "employee_age",
            "customer_age",
            "student_age",
            "child_age",
            "senior_age",
        }:
            min_value, max_value = _numeric_bounds(rule, _age_range(semantic))
            bad = ~pd.to_numeric(series, errors="coerce").between(min_value, max_value)
            if bool(bad.any()):
                errors.append(f"{column} has values outside {min_value}-{max_value}.")
        if semantic == "email":
            bad = ~series.astype(str).str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
            if bool(bad.any()):
                errors.append(f"{column} has invalid email values.")
        if semantic == "phone":
            bad = series.astype(str).str.replace(r"\\D", "", regex=True).str.len() < 7
            if bool(bad.any()):
                errors.append(f"{column} has invalid phone values.")
        if (
            semantic.endswith("_id") or semantic == "id" or rule.get("unique")
        ) and series.dropna().duplicated().any():
            errors.append(f"{column} has duplicate identifier values.")
        if {"min", "max"} & set(rule):
            numeric = pd.to_numeric(series, errors="coerce")
            min_value, max_value = _numeric_bounds(rule, (numeric.min(), numeric.max()))
            if not numeric.between(min_value, max_value).all():
                errors.append(f"{column} violates configured numeric range.")

    _validate_date_relationship(frame, semantics, errors)
    _validate_amount_relationship(frame, semantics, errors)
    return {"passed": not errors, "errors": errors, "warnings": warnings}


def dtype_kind(dtype: str) -> str:
    """Return compact dtype kind used by semantic generation."""

    normalized = str(dtype).lower().strip()
    if normalized.startswith("array"):
        return "array"
    if normalized.startswith("map"):
        return "map"
    if normalized.startswith("struct"):
        return "struct"
    if "bool" in normalized:
        return "bool"
    if "timestamp" in normalized or "datetime" in normalized:
        return "timestamp"
    if normalized == "date" or normalized.endswith("date"):
        return "date"
    if "decimal" in normalized or "numeric" in normalized:
        return "decimal"
    if any(token in normalized for token in ("double", "float", "real")):
        return "float"
    if "bigint" in normalized or "long" in normalized:
        return "long"
    if "int" in normalized and "interval" not in normalized:
        return "int"
    if "binary" in normalized or "bytes" in normalized:
        return "binary"
    return "string"


def _rule_type(rule: Mapping[str, Any] | None) -> str | None:
    value = (rule or {}).get("type")
    return str(value) if value else None


def _person_values(
    semantic_type: str,
    rows: int,
    value_gen: RealisticValueGenerator,
    person_records: Sequence[Any] | None,
) -> list[str]:
    if person_records is None:
        person_records = [value_gen.person_record() for _ in range(rows)]
    if semantic_type == "first_name":
        return [record.first_name for record in person_records]
    if semantic_type == "last_name":
        return [record.last_name for record in person_records]
    return [record.full_name for record in person_records]


def _id_values(
    column: ColumnSpec,
    semantic_type: str,
    rows: int,
    kind: str,
    value_gen: RealisticValueGenerator,
    domain: str | None,
    rule: Mapping[str, Any],
) -> list[str] | np.ndarray:
    if kind in {"int", "long"} and "prefix" not in rule:
        return np.arange(1, rows + 1, dtype=np.int64)
    prefix = str(
        rule.get("prefix")
        or _preset_prefix(domain, semantic_type)
        or ID_PREFIXES.get(semantic_type, "ID")
    )
    return [f"{prefix}{index:06d}" for index in range(1, rows + 1)]


def _person_age_values(
    semantics: Mapping[str, str],
    rows: int,
    value_gen: RealisticValueGenerator,
) -> list[int]:
    age_semantic = next(
        (
            semantic
            for semantic in semantics.values()
            if semantic
            in {
                "age",
                "employee_age",
                "customer_age",
                "student_age",
                "child_age",
                "senior_age",
            }
        ),
        "age",
    )
    low, high = _age_range(age_semantic)
    return value_gen.random_ints(rows, int(low), int(high))


def _date_context(
    semantics: Mapping[str, str],
    rows: int,
    value_gen: RealisticValueGenerator,
    age_values: Sequence[int],
) -> dict[str, list[Any]]:
    context: dict[str, list[Any]] = {}
    today = date(2026, 1, 1)
    created = [today - timedelta(days=value_gen.random_int(0, 730)) for _ in range(rows)]
    updated = [item + timedelta(days=value_gen.random_int(0, 120)) for item in created]
    start = [today - timedelta(days=value_gen.random_int(30, 900)) for _ in range(rows)]
    end = [item + timedelta(days=value_gen.random_int(1, 365)) for item in start]
    if "created_date" in semantics.values():
        context["created_date"] = created
    if "created_at" in semantics.values():
        context["created_at"] = [
            _as_datetime(item, value_gen.random_int(0, 23)) for item in created
        ]
    if "updated_date" in semantics.values():
        context["updated_date"] = updated
    if "updated_at" in semantics.values():
        context["updated_at"] = [
            _as_datetime(item, value_gen.random_int(0, 23)) for item in updated
        ]
    if "start_date" in semantics.values():
        context["start_date"] = start
    if "end_date" in semantics.values():
        context["end_date"] = end
    if "date_of_birth" in semantics.values():
        context["date_of_birth"] = _dob_values(age_values, value_gen)
    return context


def _as_datetime(value: date, hour: int) -> datetime:
    return datetime.combine(value, time(hour=hour, minute=0, second=0))


def _dob_values(age_values: Sequence[int], value_gen: RealisticValueGenerator) -> list[date]:
    anchor = date(2026, 1, 1)
    return [
        anchor - timedelta(days=int(age) * 365 + value_gen.random_int(0, 364)) for age in age_values
    ]


def _date_values(
    rows: int, value_gen: RealisticValueGenerator, rule: Mapping[str, Any]
) -> list[date]:
    start, end = _date_bounds(rule, date(2024, 1, 1), date(2026, 1, 1))
    return [
        start + timedelta(days=value_gen.random_int(0, max(0, (end - start).days)))
        for _ in range(rows)
    ]


def _datetime_values(
    rows: int, value_gen: RealisticValueGenerator, rule: Mapping[str, Any]
) -> list[datetime]:
    dates = _date_values(rows, value_gen, rule)
    return [_as_datetime(item, value_gen.random_int(0, 23)) for item in dates]


def _date_bounds(
    rule: Mapping[str, Any], default_start: date, default_end: date
) -> tuple[date, date]:
    start = _parse_date(rule.get("start"), default_start)
    end = _parse_date(rule.get("end"), default_end)
    if end < start:
        raise ValueError("Date override end must be greater than or equal to start.")
    return start, end


def _parse_date(value: Any, default: date) -> date:
    if value is None:
        return default
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _age_range(semantic_type: str) -> tuple[int, int]:
    return {
        "employee_age": (21, 65),
        "customer_age": (18, 85),
        "student_age": (5, 30),
        "child_age": (0, 17),
        "senior_age": (60, 95),
    }.get(semantic_type, (18, 90))


def _amount_range(semantic_type: str, domain: str | None) -> tuple[float, float]:
    preset_ranges = DOMAIN_PRESETS.get(str(domain or "").lower(), {}).get("amount_ranges", {})
    if semantic_type in preset_ranges:
        return preset_ranges[semantic_type]
    return {
        "salary": (30000.0, 250000.0),
        "income": (20000.0, 300000.0),
        "amount": (1.0, 10000.0),
        "transaction_amount": (1.0, 5000.0),
        "price": (1.0, 2000.0),
        "cost": (1.0, 50000.0),
        "balance": (0.0, 100000.0),
        "revenue": (1000.0, 1000000.0),
        "discount": (0.0, 0.35),
        "generic_float": (1.0, 1000.0),
    }.get(semantic_type, (1.0, 1000.0))


def _numeric_bounds(rule: Mapping[str, Any], defaults: tuple[Any, Any]) -> tuple[float, float]:
    min_value = float(rule.get("min", defaults[0]))
    max_value = float(rule.get("max", defaults[1]))
    if max_value < min_value:
        raise ValueError("Custom rule max must be greater than or equal to min.")
    return min_value, max_value


def _numeric_values(values: list[float], kind: str) -> list[Any] | np.ndarray:
    if kind in {"int", "long"}:
        return np.array([int(round(value)) for value in values], dtype=np.int64)
    if kind == "decimal":
        return [Decimal(str(value)) for value in values]
    return values


def _preset_values(domain: str | None, semantic_type: str) -> list[Any] | None:
    preset = DOMAIN_PRESETS.get(str(domain or "").lower(), {})
    values = preset.get("values", {})
    return values.get(semantic_type)


def _preset_prefix(domain: str | None, semantic_type: str) -> str | None:
    preset = DOMAIN_PRESETS.get(str(domain or "").lower(), {})
    prefixes = preset.get("id_prefixes", {})
    return prefixes.get(semantic_type)


def _apply_cross_field_consistency(frame: pd.DataFrame, semantics: Mapping[str, str]) -> None:
    columns_by_semantic: dict[str, list[str]] = {}
    for column, semantic in semantics.items():
        columns_by_semantic.setdefault(semantic, []).append(column)

    first = _first_column(columns_by_semantic, "first_name")
    last = _first_column(columns_by_semantic, "last_name")
    if first and last:
        for semantic in ("full_name", "customer_name", "employee_name", "member_name", "user_name"):
            for column in columns_by_semantic.get(semantic, []):
                frame[column] = frame[first].astype(str) + " " + frame[last].astype(str)
        for column in columns_by_semantic.get("email", []):
            frame[column] = [
                f"{_slug(first_name)}.{_slug(last_name)}@example.com"
                for first_name, last_name in zip(frame[first], frame[last])
            ]

    dob = _first_column(columns_by_semantic, "date_of_birth")
    age = next(
        (
            _first_column(columns_by_semantic, semantic)
            for semantic in (
                "age",
                "employee_age",
                "customer_age",
                "student_age",
                "child_age",
                "senior_age",
            )
            if _first_column(columns_by_semantic, semantic)
        ),
        None,
    )
    if dob and age:
        frame[age] = [
            max(0, int((date(2026, 1, 1) - _as_date(value)).days // 365)) for value in frame[dob]
        ]

    quantity = _first_column(columns_by_semantic, "quantity")
    price = _first_column(columns_by_semantic, "price")
    for semantic in ("total_amount", "amount"):
        for column in columns_by_semantic.get(semantic, []):
            if quantity and price and column not in {quantity, price}:
                frame[column] = np.round(
                    pd.to_numeric(frame[quantity], errors="coerce")
                    * pd.to_numeric(frame[price], errors="coerce"),
                    2,
                )


def _first_column(columns_by_semantic: Mapping[str, list[str]], semantic: str) -> str | None:
    values = columns_by_semantic.get(semantic, [])
    return values[0] if values else None


def _as_date(value: Any) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _slug(value: Any) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", str(value).strip().lower()).strip(".")
    return cleaned or "user"


def _records_to_frame(records: Any) -> pd.DataFrame:
    if isinstance(records, pd.DataFrame):
        return records.copy()
    if isinstance(records, Mapping):
        return pd.DataFrame(records)
    if isinstance(records, Sequence) and not isinstance(records, (str, bytes, bytearray)):
        return pd.DataFrame(records)
    raise TypeError("records must be a pandas DataFrame, mapping, or sequence of mappings.")


def _schema_dtype_map(
    schema: TableSchema | Mapping[str, str] | str | pd.DataFrame | None,
    frame: pd.DataFrame,
) -> dict[str, str]:
    if isinstance(schema, TableSchema):
        return {column.name: column.dtype for column in schema.columns}
    if isinstance(schema, Mapping):
        return {str(name): str(dtype) for name, dtype in schema.items()}
    if isinstance(schema, pd.DataFrame):
        return {str(column): str(dtype) for column, dtype in schema.dtypes.items()}
    return {str(column): str(dtype) for column, dtype in frame.dtypes.items()}


def _validate_date_relationship(
    frame: pd.DataFrame,
    semantics: Mapping[str, str],
    errors: list[str],
) -> None:
    by_semantic: dict[str, str] = {}
    for column, semantic in semantics.items():
        by_semantic.setdefault(semantic, column)
    for left_semantic, right_semantic in (("created_at", "updated_at"), ("start_date", "end_date")):
        left = by_semantic.get(left_semantic)
        right = by_semantic.get(right_semantic)
        if left and right:
            left_values = pd.to_datetime(frame[left], errors="coerce")
            right_values = pd.to_datetime(frame[right], errors="coerce")
            if bool((right_values < left_values).any()):
                errors.append(f"{right} must be greater than or equal to {left}.")


def _validate_amount_relationship(
    frame: pd.DataFrame,
    semantics: Mapping[str, str],
    errors: list[str],
) -> None:
    columns_by_semantic: dict[str, list[str]] = {}
    for column, semantic in semantics.items():
        columns_by_semantic.setdefault(semantic, []).append(column)
    quantity = _first_column(columns_by_semantic, "quantity")
    price = _first_column(columns_by_semantic, "price")
    total = _first_column(columns_by_semantic, "total_amount")
    if quantity and price and total:
        expected = (
            pd.to_numeric(frame[quantity], errors="coerce")
            * pd.to_numeric(frame[price], errors="coerce")
        ).round(2)
        actual = pd.to_numeric(frame[total], errors="coerce").round(2)
        if bool((expected != actual).any()):
            errors.append(f"{total} must equal {quantity} * {price}.")
