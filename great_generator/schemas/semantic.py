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
    "mbr": "member",
    "addr": "address",
    "dob": "date_of_birth",
    "dt": "date",
    "ts": "timestamp",
    "nm": "name",
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
    "trans": "transaction",
    "acct": "account",
    "prod": "product",
    "desc": "description",
}

NAME_ENTITIES = {"customer", "employee", "member", "user", "patient", "student", "person"}
AGE_SEMANTICS = {
    "age",
    "employee_age",
    "customer_age",
    "student_age",
    "child_age",
    "senior_age",
}
DATE_SEMANTICS = {
    "date",
    "datetime",
    "created_date",
    "created_at",
    "updated_date",
    "updated_at",
    "date_of_birth",
    "transaction_date",
    "order_date",
    "payment_date",
    "delivery_date",
    "signup_date",
    "registration_date",
    "last_login_date",
    "opened_date",
    "closed_date",
    "hire_date",
    "termination_date",
    "effective_date",
    "expiration_date",
    "due_date",
    "renewal_date",
    "scheduled_date",
    "appointment_date",
    "start_date",
    "end_date",
}
FUTURE_CAPABLE_DATE_SEMANTICS = {
    "due_date",
    "expiration_date",
    "renewal_date",
    "scheduled_date",
    "appointment_date",
}
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
    "policy_id": "POL",
    "claim_id": "CLM",
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

    return str(infer_field_semantic_info(column_name, data_type)["semantic_type"])


def infer_field_semantic_info(column_name: str, data_type: str) -> dict[str, Any]:
    """Return explainable semantic inference metadata for a field."""

    normalized = normalize_column_name(column_name)
    tokens = set(normalized.split("_"))
    kind = dtype_kind(data_type)

    if "email" in tokens:
        return _semantic_info(
            "secondary_email" if "secondary" in tokens else "email", 0.98, "email token"
        )
    if tokens & {"phone", "mobile"}:
        return _semantic_info("phone", 0.96, "phone or mobile token")
    if normalized.startswith("address_line_2") or ("address" in tokens and "2" in tokens):
        return _semantic_info("address_line_2", 0.96, "address line 2 token")
    if "address" in tokens or normalized.startswith("address_line"):
        return _semantic_info("address", 0.96, "address token")
    if "city" in tokens:
        return _semantic_info("city", 0.96, "city token")
    if "state" in tokens or "province" in tokens:
        return _semantic_info("state", 0.94, "state or province token")
    if "postal" in tokens and "code" in tokens:
        return _semantic_info("postal_code", 0.96, "postal code token")
    if "country" in tokens:
        return _semantic_info("country", 0.95, "country token")
    if "company" in tokens or "organization" in tokens:
        return _semantic_info("company", 0.92, "company or organization token")
    if "department" in tokens:
        return _semantic_info("department", 0.92, "department token")
    if "job" in tokens and "title" in tokens:
        return _semantic_info("job_title", 0.94, "job title tokens")
    if "role" in tokens:
        return _semantic_info("role", 0.86, "role token")
    if "industry" in tokens:
        return _semantic_info("industry", 0.90, "industry token")

    if "id" in tokens or normalized.endswith("_id"):
        for token, semantic in (
            ("transaction", "transaction_id"),
            ("order", "order_id"),
            ("account", "account_id"),
            ("employee", "employee_id"),
            ("customer", "customer_id"),
            ("member", "member_id"),
            ("user", "user_id"),
            ("product", "product_id"),
            ("policy", "policy_id"),
            ("claim", "claim_id"),
            ("patient", "patient_id"),
            ("student", "student_id"),
        ):
            if token in tokens:
                return _semantic_info(semantic, 0.98, f"{token} identifier")
        return _semantic_info("id", 0.88, "identifier-looking field")

    if "middle" in tokens and "name" in tokens:
        return _semantic_info("middle_name", 0.94, "middle name tokens")
    if "first" in tokens and "name" in tokens:
        return _semantic_info("first_name", 0.98, "first name tokens")
    if "last" in tokens and "name" in tokens:
        return _semantic_info("last_name", 0.98, "last name tokens")
    if "name" in tokens:
        if "company" in tokens or "organization" in tokens:
            return _semantic_info("company", 0.92, "company name tokens")
        if "product" in tokens:
            return _semantic_info("product_name", 0.94, "product name tokens")
        if "department" in tokens:
            return _semantic_info("department", 0.90, "department name tokens")
        if tokens & NAME_ENTITIES or "full" in tokens or normalized == "name":
            entity = next((token for token in NAME_ENTITIES if token in tokens), None)
            return _semantic_info(
                f"{entity}_name" if entity else "full_name",
                0.95,
                "person-name tokens",
            )
        return _semantic_info("full_name", 0.82, "name token with string type")

    if "age" in tokens:
        if "employee" in tokens:
            return _semantic_info("employee_age", 0.98, "employee age tokens")
        if "student" in tokens:
            return _semantic_info("student_age", 0.98, "student age tokens")
        if "child" in tokens:
            return _semantic_info("child_age", 0.98, "child age tokens")
        if "senior" in tokens:
            return _semantic_info("senior_age", 0.98, "senior age tokens")
        if "customer" in tokens or "member" in tokens:
            return _semantic_info("customer_age", 0.97, "customer or member age tokens")
        return _semantic_info("age", 0.96, "age token")

    if normalized in {"date_of_birth", "birth_date"}:
        return _semantic_info("date_of_birth", 0.99, "birth date tokens")
    if "created" in tokens and ("date" in tokens or "at" in tokens or "timestamp" in tokens):
        semantic = (
            "created_at" if kind == "timestamp" or {"at", "timestamp"} & tokens else "created_date"
        )
        return _semantic_info(semantic, 0.96, "created date or timestamp tokens")
    if "updated" in tokens and ("date" in tokens or "at" in tokens or "timestamp" in tokens):
        semantic = (
            "updated_at" if kind == "timestamp" or {"at", "timestamp"} & tokens else "updated_date"
        )
        return _semantic_info(semantic, 0.96, "updated date or timestamp tokens")
    for token, semantic in (
        ("transaction", "transaction_date"),
        ("order", "order_date"),
        ("payment", "payment_date"),
        ("delivery", "delivery_date"),
        ("signup", "signup_date"),
        ("registration", "registration_date"),
        ("login", "last_login_date"),
        ("opened", "opened_date"),
        ("closed", "closed_date"),
        ("hire", "hire_date"),
        ("termination", "termination_date"),
        ("effective", "effective_date"),
        ("expiration", "expiration_date"),
        ("expiry", "expiration_date"),
        ("due", "due_date"),
        ("renewal", "renewal_date"),
        ("scheduled", "scheduled_date"),
        ("appointment", "appointment_date"),
    ):
        if token in tokens and ("date" in tokens or kind in {"date", "timestamp"}):
            return _semantic_info(semantic, 0.93, f"{token} date tokens")
    if "start" in tokens and "date" in tokens:
        return _semantic_info("start_date", 0.94, "start date tokens")
    if "end" in tokens and "date" in tokens:
        return _semantic_info("end_date", 0.94, "end date tokens")
    if kind == "date":
        return _semantic_info("generic_date", 0.55, "date type without strong semantic name")
    if kind == "timestamp":
        return _semantic_info("datetime", 0.55, "timestamp type without strong semantic name")

    if "status" in tokens:
        if "account" in tokens:
            return _semantic_info("account_status", 0.96, "account status tokens")
        if "order" in tokens:
            return _semantic_info("order_status", 0.96, "order status tokens")
        if "payment" in tokens:
            return _semantic_info("payment_status", 0.96, "payment status tokens")
        if "employment" in tokens or "employee" in tokens:
            return _semantic_info("employment_status", 0.96, "employment status tokens")
        return _semantic_info("status", 0.82, "status token")
    if "type" in tokens:
        if "customer" in tokens:
            return _semantic_info("customer_type", 0.90, "customer type tokens")
        if "member" in tokens:
            return _semantic_info("member_type", 0.90, "member type tokens")
        if "account" in tokens:
            return _semantic_info("account_type", 0.90, "account type tokens")
        if "transaction" in tokens:
            return _semantic_info("transaction_type", 0.90, "transaction type tokens")

    if "salary" in tokens:
        return _semantic_info("salary", 0.96, "salary token")
    if "income" in tokens:
        return _semantic_info("income", 0.94, "income token")
    if "transaction" in tokens and "amount" in tokens:
        return _semantic_info("transaction_amount", 0.97, "transaction amount tokens")
    if "total" in tokens and "amount" in tokens:
        return _semantic_info("total_amount", 0.96, "total amount tokens")
    if normalized == "unit_price" or ("unit" in tokens and "price" in tokens):
        return _semantic_info("unit_price", 0.97, "unit price tokens")
    if "price" in tokens:
        return _semantic_info("price", 0.94, "price token")
    if "discount" in tokens:
        return _semantic_info("discount", 0.93, "discount token")
    if "tax" in tokens:
        return _semantic_info("tax", 0.93, "tax token")
    if "amount" in tokens or "payment" in tokens:
        return _semantic_info("amount", 0.88, "amount or payment token")
    if "cost" in tokens:
        return _semantic_info("cost", 0.92, "cost token")
    if "balance" in tokens:
        return _semantic_info("balance", 0.92, "balance token")
    if "revenue" in tokens:
        return _semantic_info("revenue", 0.92, "revenue token")
    if "quantity" in tokens:
        return _semantic_info("quantity", 0.96, "quantity token")
    if "risk" in tokens and "score" in tokens:
        return _semantic_info("risk_score", 0.92, "risk score tokens")

    if "gender" in tokens:
        return _semantic_info("gender", 0.94, "gender token")
    if "category" in tokens:
        return _semantic_info("category", 0.82, "category token")
    if "priority" in tokens:
        return _semantic_info("priority", 0.90, "priority token")
    if "risk" in tokens and "level" in tokens:
        return _semantic_info("risk_level", 0.92, "risk level tokens")

    if "product" in tokens:
        return _semantic_info("product_name", 0.82, "product token")
    if "sku" in tokens:
        return _semantic_info("sku", 0.95, "sku token")
    if "description" in tokens:
        return _semantic_info("description", 0.84, "description token")

    if kind in {"int", "long"}:
        return _semantic_info("generic_int", 0.30, "integer type fallback")
    if kind in {"float", "decimal"}:
        return _semantic_info("generic_float", 0.30, "numeric type fallback")
    if kind == "bool":
        return _semantic_info("boolean", 0.60, "boolean type")
    return _semantic_info("generic_string", 0.25, "string fallback")


def _semantic_info(semantic_type: str, confidence: float, reason: str) -> dict[str, Any]:
    return {
        "semantic_type": semantic_type,
        "confidence": confidence,
        "reason": reason,
    }


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
    _apply_status_aware_rules(result, semantics)
    _apply_null_rules(result, table, semantics, rules, value_gen)
    return result


def explain_generation_plan(
    table: TableSchema,
    realism: str = "realistic",
    custom_rules: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Explain how each field will be generated."""

    rules = {str(name): dict(rule) for name, rule in (custom_rules or {}).items()}
    fields: list[dict[str, Any]] = []
    recognized = 0
    for column in table.columns:
        rule = rules.get(column.name, {})
        info = infer_field_semantic_info(column.name, column.dtype)
        semantic_type = _rule_type(rule) or str(info["semantic_type"])
        confidence = 1.0 if _rule_type(rule) else float(info["confidence"])
        reason = "custom rule override" if _rule_type(rule) else str(info["reason"])
        if not semantic_type.startswith("generic_"):
            recognized += 1
        fields.append(
            {
                "column": column.name,
                "dtype": column.dtype,
                "semantic_type": semantic_type,
                "confidence": round(confidence, 2),
                "reason": reason,
                "generator": _generator_description(semantic_type),
            }
        )
    total = len(fields)
    return {
        "realism": realism,
        "table": table.name,
        "semantic_coverage": round(recognized / total, 2) if total else 1.0,
        "fields": fields,
    }


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
    if "weighted_values" in rule:
        return _weighted_values(rule["weighted_values"], rows, value_gen)
    if "values" in rule:
        values = list(rule["values"])
        return [value_gen.random_choice(values) for _ in range(rows)]
    if "pattern" in rule:
        return [str(rule["pattern"]).format(index=index) for index in range(1, rows + 1)]
    if semantic_type.endswith("_id") or semantic_type == "id":
        return _id_values(column, semantic_type, rows, kind, value_gen, domain, rule)
    if semantic_type in {
        "first_name",
        "middle_name",
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
    if semantic_type in AGE_SEMANTICS:
        min_value, max_value = _numeric_bounds(rule, _age_range(semantic_type))
        return value_gen.random_ints(rows, int(min_value), int(max_value))
    if semantic_type in {"email", "secondary_email"}:
        if person_records:
            return [record.email for record in person_records]
        return [value_gen.email() for _ in range(rows)]
    if semantic_type == "phone":
        return [value_gen.phone_number() for _ in range(rows)]
    if semantic_type == "address":
        return [value_gen.street_address() for _ in range(rows)]
    if semantic_type == "address_line_2":
        return [f"Apt {value_gen.random_int(100, 999)}" for _ in range(rows)]
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
        "unit_price",
        "cost",
        "balance",
        "revenue",
        "discount",
        "tax",
        "risk_score",
        "generic_float",
    }:
        min_value, max_value = _numeric_bounds(rule, _amount_range(semantic_type, domain))
        values = [value_gen.random_amount(float(min_value), float(max_value)) for _ in range(rows)]
        return _numeric_values(values, kind)
    if semantic_type == "quantity":
        min_value, max_value = _numeric_bounds(rule, (1, 20))
        return value_gen.random_ints(rows, int(min_value), int(max_value))
    if date_context is not None and semantic_type in date_context:
        return list(date_context[semantic_type])
    if semantic_type == "date_of_birth":
        ages = age_values or value_gen.random_ints(rows, 18, 90)
        return _dob_values(ages, value_gen)
    if semantic_type in DATE_SEMANTICS or semantic_type == "generic_date":
        return _semantic_date_values(semantic_type, rows, value_gen, rule, kind=kind)
    if semantic_type == "boolean":
        return [value_gen.random_bool() for _ in range(rows)]
    if semantic_type == "generic_int":
        min_value, max_value = _numeric_bounds(rule, (1, 100))
        return value_gen.random_ints(rows, int(min_value), int(max_value))
    if semantic_type == "description":
        values = DEFAULT_VALUES["description"]
        return [value_gen.random_choice(values) for _ in range(rows)]
    return _generic_string_values(column.name, rows)


def validate_generated_data(
    records: Any,
    schema: TableSchema | Mapping[str, str] | str | pd.DataFrame | None = None,
    rules: Mapping[str, Mapping[str, Any]] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Validate practical quality expectations for generated schema-driven data."""

    frame = _records_to_frame(records)
    errors: list[str] = []
    warnings: list[str] = []
    if frame.empty:
        return {
            "passed": True,
            "errors": [],
            "warnings": ["No records to validate."],
            "summary": {"rows_checked": 0, "columns_checked": 0, "semantic_coverage": 1.0},
        }

    rules = {str(name): dict(rule) for name, rule in (rules or {}).items()}
    schema_map = _schema_dtype_map(schema, frame)
    semantics: dict[str, str] = {}
    recognized = 0
    for column in frame.columns:
        semantic = _rule_type(rules.get(column)) or infer_field_semantic_type(
            column, schema_map[column]
        )
        semantics[column] = semantic
        if not semantic.startswith("generic_"):
            recognized += 1

    for column, semantic in semantics.items():
        series = frame[column]
        rule = rules.get(column, {})
        if semantic in AGE_SEMANTICS:
            min_value, max_value = _numeric_bounds(rule, _age_range(semantic))
            bad = ~pd.to_numeric(series, errors="coerce").between(min_value, max_value)
            if bool(bad.any()):
                errors.append(f"{column} has values outside {min_value}-{max_value}.")
        if semantic in {"email", "secondary_email"}:
            non_null = series.dropna().astype(str)
            bad = ~non_null.str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
            if bool(bad.any()):
                errors.append(f"{column} has invalid email values.")
        if semantic == "phone":
            non_null = series.dropna().astype(str)
            bad = non_null.str.replace(r"\D", "", regex=True).str.len() < 7
            if bool(bad.any()):
                errors.append(f"{column} has invalid phone values.")
        if semantic in DATE_SEMANTICS or semantic == "generic_date":
            _validate_date_column(frame, column, semantic, errors)
        if semantic in {
            "quantity",
            "salary",
            "income",
            "amount",
            "transaction_amount",
            "price",
            "unit_price",
            "cost",
            "balance",
            "discount",
            "tax",
            "risk_score",
            "generic_float",
            "generic_int",
        }:
            _validate_numeric_column(series, column, semantic, rule, errors)
        if semantic.endswith("_id") or semantic == "id" or rule.get("unique"):
            if series.isna().any():
                errors.append(f"{column} has null identifier values.")
            if series.dropna().duplicated().any():
                errors.append(f"{column} has duplicate identifier values.")
        if {"min", "max"} & set(rule):
            numeric = pd.to_numeric(series, errors="coerce")
            min_value, max_value = _numeric_bounds(rule, (numeric.min(), numeric.max()))
            if not numeric.dropna().between(min_value, max_value).all():
                errors.append(f"{column} violates configured numeric range.")
        if semantic.startswith("generic_") and strict:
            warnings.append(f"{column} used generic fallback generator.")

    _validate_age_birthdate_relationship(frame, semantics, errors)
    _validate_date_relationship(frame, semantics, errors)
    _validate_amount_relationship(frame, semantics, errors)
    _validate_status_nulls(frame, semantics, errors)
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "rows_checked": int(len(frame)),
            "columns_checked": int(len(frame.columns)),
            "semantic_coverage": (
                round(recognized / len(frame.columns), 2) if len(frame.columns) else 1.0
            ),
        },
    }


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
    if semantic_type == "middle_name":
        return [value_gen.first_name() for _ in range(rows)]
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
    today = _today()
    created = [today - timedelta(days=value_gen.random_int(1, 730)) for _ in range(rows)]
    updated = [min(today, item + timedelta(days=value_gen.random_int(0, 120))) for item in created]
    start = [today - timedelta(days=value_gen.random_int(30, 900)) for _ in range(rows)]
    end = [min(today, item + timedelta(days=value_gen.random_int(1, 365))) for item in start]
    order = [today - timedelta(days=value_gen.random_int(1, 180)) for _ in range(rows)]
    delivery = [min(today, item + timedelta(days=value_gen.random_int(1, 21))) for item in order]
    payment = [min(today, item + timedelta(days=value_gen.random_int(0, 14))) for item in order]
    opened = [today - timedelta(days=value_gen.random_int(30, 1500)) for _ in range(rows)]
    closed = [min(today, item + timedelta(days=value_gen.random_int(30, 900))) for item in opened]
    hire = [today - timedelta(days=value_gen.random_int(30, 2000)) for _ in range(rows)]
    termination = [
        min(today, item + timedelta(days=value_gen.random_int(30, 1500))) for item in hire
    ]
    effective = [today - timedelta(days=value_gen.random_int(30, 900)) for _ in range(rows)]
    expiration = [item + timedelta(days=value_gen.random_int(30, 730)) for item in effective]
    if "created_date" in semantics.values():
        context["created_date"] = created
    if "created_at" in semantics.values():
        context["created_at"] = [
            _as_safe_datetime(item, value_gen.random_int(0, 23)) for item in created
        ]
    if "updated_date" in semantics.values():
        context["updated_date"] = updated
    if "updated_at" in semantics.values():
        context["updated_at"] = [
            _as_safe_datetime(item, value_gen.random_int(0, 23)) for item in updated
        ]
    if "start_date" in semantics.values():
        context["start_date"] = start
    if "end_date" in semantics.values():
        context["end_date"] = end
    if "order_date" in semantics.values():
        context["order_date"] = order
    if "transaction_date" in semantics.values():
        context["transaction_date"] = [
            today - timedelta(days=value_gen.random_int(0, 120)) for _ in range(rows)
        ]
    if "payment_date" in semantics.values():
        context["payment_date"] = payment
    if "delivery_date" in semantics.values():
        context["delivery_date"] = delivery
    if "opened_date" in semantics.values():
        context["opened_date"] = opened
    if "closed_date" in semantics.values():
        context["closed_date"] = closed
    if "hire_date" in semantics.values():
        context["hire_date"] = hire
    if "termination_date" in semantics.values():
        context["termination_date"] = termination
    if "effective_date" in semantics.values():
        context["effective_date"] = effective
    if "expiration_date" in semantics.values():
        context["expiration_date"] = expiration
    if "signup_date" in semantics.values():
        context["signup_date"] = [
            today - timedelta(days=value_gen.random_int(1, 1000)) for _ in range(rows)
        ]
    if "registration_date" in semantics.values():
        context["registration_date"] = [
            today - timedelta(days=value_gen.random_int(1, 1000)) for _ in range(rows)
        ]
    if "last_login_date" in semantics.values():
        context["last_login_date"] = [
            today - timedelta(days=value_gen.random_int(0, 120)) for _ in range(rows)
        ]
    if "date_of_birth" in semantics.values():
        context["date_of_birth"] = _dob_values(age_values, value_gen)
    return context


def _as_datetime(value: date, hour: int) -> datetime:
    return datetime.combine(value, time(hour=hour, minute=0, second=0))


def _as_safe_datetime(value: date, hour: int) -> datetime:
    today = _today()
    if value >= today:
        return datetime.combine(today, time.min)
    return _as_datetime(value, hour)


def _dob_values(age_values: Sequence[int], value_gen: RealisticValueGenerator) -> list[date]:
    anchor = _today()
    return [
        anchor - timedelta(days=int(age) * 365 + value_gen.random_int(0, 364)) for age in age_values
    ]


def _semantic_date_values(
    semantic_type: str,
    rows: int,
    value_gen: RealisticValueGenerator,
    rule: Mapping[str, Any],
    kind: str,
) -> list[date] | list[datetime]:
    if kind == "timestamp" or semantic_type in {"datetime", "created_at", "updated_at"}:
        return _datetime_values(rows, value_gen, rule, semantic_type=semantic_type)
    return _date_values(rows, value_gen, rule, semantic_type=semantic_type)


def _date_values(
    rows: int,
    value_gen: RealisticValueGenerator,
    rule: Mapping[str, Any],
    semantic_type: str = "date",
) -> list[date]:
    today = _today()
    allow_future = bool(rule.get("allow_future", semantic_type in FUTURE_CAPABLE_DATE_SEMANTICS))
    default_end = today + timedelta(days=365) if allow_future else today
    default_start = today - timedelta(days=1095)
    if semantic_type in FUTURE_CAPABLE_DATE_SEMANTICS and allow_future:
        default_start = today
    start, end = _date_bounds(rule, default_start, default_end)
    if not allow_future:
        end = min(end, today)
    return [
        start + timedelta(days=value_gen.random_int(0, max(0, (end - start).days)))
        for _ in range(rows)
    ]


def _datetime_values(
    rows: int,
    value_gen: RealisticValueGenerator,
    rule: Mapping[str, Any],
    semantic_type: str = "datetime",
) -> list[datetime]:
    dates = _date_values(rows, value_gen, rule, semantic_type=semantic_type)
    return [_as_safe_datetime(item, value_gen.random_int(0, 23)) for item in dates]


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
        "unit_price": (1.0, 1000.0),
        "cost": (1.0, 50000.0),
        "balance": (0.0, 100000.0),
        "revenue": (1000.0, 1000000.0),
        "discount": (0.0, 0.50),
        "tax": (0.0, 0.15),
        "risk_score": (0.0, 100.0),
        "generic_float": (1.0, 1000.0),
    }.get(semantic_type, (1.0, 1000.0))


def _today() -> date:
    return date.today()


def _weighted_values(
    weighted_values: Any,
    rows: int,
    value_gen: RealisticValueGenerator,
) -> list[Any]:
    if isinstance(weighted_values, Mapping):
        values = list(weighted_values.keys())
        weights = [float(value) for value in weighted_values.values()]
    else:
        pairs = list(weighted_values)
        values = [item[0] for item in pairs]
        weights = [float(item[1]) for item in pairs]
    total = sum(weights)
    if not values or total <= 0:
        raise ValueError("weighted_values must contain at least one positive weight.")
    probabilities = [weight / total for weight in weights]
    return list(value_gen.random.choices(values, weights=probabilities, k=rows))


def _generic_string_values(column_name: str, rows: int) -> list[str]:
    normalized = normalize_column_name(column_name)
    if "code" in normalized:
        return [f"REF{index:04d}" for index in range(1, rows + 1)]
    if "category" in normalized:
        letters = ["A", "B", "C", "D"]
        return [f"Category {letters[(index - 1) % len(letters)]}" for index in range(1, rows + 1)]
    return [f"Reference {index:04d}" for index in range(1, rows + 1)]


def _generator_description(semantic_type: str) -> str:
    if semantic_type in AGE_SEMANTICS:
        low, high = _age_range(semantic_type)
        return f"integer age range {low}-{high}"
    if semantic_type.endswith("_id") or semantic_type == "id":
        return "unique identifier generator"
    if semantic_type in DATE_SEMANTICS or semantic_type == "generic_date":
        return "clean date generator with lifecycle rules"
    if semantic_type in {"email", "secondary_email"}:
        return "email generator, name-aware when possible"
    if semantic_type in {"full_name", "customer_name", "employee_name", "member_name"}:
        return "person name generator"
    if semantic_type in {"generic_int", "generic_float", "generic_string"}:
        return "safe fallback generator"
    return f"{semantic_type} generator"


def _apply_status_aware_rules(
    frame: pd.DataFrame,
    semantics: Mapping[str, str],
) -> None:
    columns_by_semantic: dict[str, list[str]] = {}
    for column, semantic in semantics.items():
        columns_by_semantic.setdefault(semantic, []).append(column)

    order_status = _first_column(columns_by_semantic, "order_status")
    order_date = _first_column(columns_by_semantic, "order_date")
    delivery_date = _first_column(columns_by_semantic, "delivery_date")
    if order_status and delivery_date:
        pending_mask = frame[order_status].astype(str).str.lower().isin({"pending", "cancelled"})
        frame.loc[pending_mask, delivery_date] = None
        if order_date:
            delivered_mask = ~pending_mask & frame[delivery_date].notna()
            frame.loc[delivered_mask, delivery_date] = [
                max(_as_date(delivery), _as_date(order))
                for delivery, order in zip(
                    frame.loc[delivered_mask, delivery_date],
                    frame.loc[delivered_mask, order_date],
                )
            ]

    payment_status = _first_column(columns_by_semantic, "payment_status")
    payment_date = _first_column(columns_by_semantic, "payment_date")
    if payment_status and payment_date:
        unpaid = {"pending", "failed", "unpaid"}
        unpaid_mask = frame[payment_status].astype(str).str.lower().isin(unpaid)
        frame.loc[unpaid_mask, payment_date] = None
        if order_date:
            paid_mask = ~unpaid_mask & frame[payment_date].notna()
            frame.loc[paid_mask, payment_date] = [
                max(_as_date(payment), _as_date(order))
                for payment, order in zip(
                    frame.loc[paid_mask, payment_date],
                    frame.loc[paid_mask, order_date],
                )
            ]

    employment_status = _first_column(columns_by_semantic, "employment_status")
    termination_date = _first_column(columns_by_semantic, "termination_date")
    hire_date = _first_column(columns_by_semantic, "hire_date")
    if employment_status and termination_date:
        terminated = frame[employment_status].astype(str).str.lower().eq("terminated")
        frame.loc[~terminated, termination_date] = None
        if hire_date:
            frame.loc[terminated, termination_date] = [
                max(_as_date(term), _as_date(hire))
                for term, hire in zip(
                    frame.loc[terminated, termination_date],
                    frame.loc[terminated, hire_date],
                )
            ]

    account_status = _first_column(columns_by_semantic, "account_status") or _first_column(
        columns_by_semantic, "status"
    )
    closed_date = _first_column(columns_by_semantic, "closed_date")
    opened_date = _first_column(columns_by_semantic, "opened_date")
    if account_status and closed_date:
        closed = frame[account_status].astype(str).str.lower().eq("closed")
        frame.loc[~closed, closed_date] = None
        if opened_date:
            frame.loc[closed, closed_date] = [
                max(_as_date(closed_value), _as_date(opened_value))
                for closed_value, opened_value in zip(
                    frame.loc[closed, closed_date],
                    frame.loc[closed, opened_date],
                )
            ]


def _apply_null_rules(
    frame: pd.DataFrame,
    table: TableSchema,
    semantics: Mapping[str, str],
    rules: Mapping[str, Mapping[str, Any]],
    value_gen: RealisticValueGenerator,
) -> None:
    primary_key = table.primary_key
    for column in table.columns:
        name = column.name
        semantic = semantics[name]
        if name == primary_key or semantic.endswith("_id") or semantic == "id":
            continue
        rule = rules.get(name, {})
        null_rate = rule.get("null_rate", _default_null_rate(semantic))
        if null_rate is None:
            continue
        rate = float(null_rate)
        if rate <= 0:
            continue
        if rate > 1:
            raise ValueError("null_rate must be between 0 and 1.")
        random_gen = value_gen.child(f"{name}.nulls").random
        mask = [random_gen.random() < rate for _ in range(len(frame))]
        frame.loc[mask, name] = None


def _default_null_rate(semantic_type: str) -> float:
    return {
        "middle_name": 0.50,
        "address_line_2": 0.70,
        "secondary_email": 0.40,
    }.get(semantic_type, 0.0)


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
        frame[age] = [max(0, int((_today() - _as_date(value)).days // 365)) for value in frame[dob]]

    quantity = _first_column(columns_by_semantic, "quantity")
    price = _first_column(columns_by_semantic, "unit_price") or _first_column(
        columns_by_semantic, "price"
    )
    discount = _first_column(columns_by_semantic, "discount")
    tax = _first_column(columns_by_semantic, "tax")
    for semantic in ("total_amount", "amount"):
        for column in columns_by_semantic.get(semantic, []):
            if quantity and price and column not in {quantity, price}:
                total = pd.to_numeric(frame[quantity], errors="coerce") * pd.to_numeric(
                    frame[price], errors="coerce"
                )
                if discount:
                    discount_values = pd.to_numeric(frame[discount], errors="coerce")
                    total = total - np.where(
                        discount_values <= 1, total * discount_values, discount_values
                    )
                if tax:
                    tax_values = pd.to_numeric(frame[tax], errors="coerce")
                    total = total + np.where(tax_values <= 1, total * tax_values, tax_values)
                frame[column] = np.round(total.clip(lower=0), 2)


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


def _validate_date_column(
    frame: pd.DataFrame,
    column: str,
    semantic: str,
    errors: list[str],
) -> None:
    values = pd.to_datetime(frame[column], errors="coerce")
    non_null = values.dropna()
    if non_null.empty:
        return
    now = pd.Timestamp.now()
    today = pd.Timestamp(_today())
    if semantic not in FUTURE_CAPABLE_DATE_SEMANTICS and bool((non_null > now).any()):
        errors.append(f"{column} contains future dates.")
    if semantic == "date_of_birth":
        if bool((non_null > now).any()):
            errors.append(f"{column} contains future birth dates.")
        ages = ((today - non_null).dt.days // 365).astype(int)
        if bool(~ages.between(0, 120).all()):
            errors.append(f"{column} implies unrealistic ages.")


def _validate_numeric_column(
    series: pd.Series,
    column: str,
    semantic: str,
    rule: Mapping[str, Any],
    errors: list[str],
) -> None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return
    default_bounds = _numeric_validation_bounds(semantic)
    if default_bounds is None:
        return
    min_value, max_value = _numeric_bounds(rule, default_bounds)
    if bool(~numeric.between(min_value, max_value).all()):
        errors.append(f"{column} has values outside {min_value}-{max_value}.")


def _numeric_validation_bounds(semantic: str) -> tuple[float, float] | None:
    if semantic in AGE_SEMANTICS:
        return _age_range(semantic)
    if semantic == "quantity":
        return (1, 20)
    if semantic in {
        "salary",
        "income",
        "amount",
        "transaction_amount",
        "price",
        "unit_price",
        "cost",
        "balance",
        "discount",
        "tax",
        "risk_score",
        "generic_float",
    }:
        return _amount_range(semantic, domain=None)
    if semantic == "generic_int":
        return (1, 100)
    return None


def _validate_age_birthdate_relationship(
    frame: pd.DataFrame,
    semantics: Mapping[str, str],
    errors: list[str],
) -> None:
    by_semantic: dict[str, str] = {}
    for column, semantic in semantics.items():
        by_semantic.setdefault(semantic, column)
    dob = by_semantic.get("date_of_birth")
    age = next(
        (by_semantic.get(semantic) for semantic in AGE_SEMANTICS if by_semantic.get(semantic)), None
    )
    if not dob or not age:
        return
    dates = pd.to_datetime(frame[dob], errors="coerce")
    ages = pd.to_numeric(frame[age], errors="coerce")
    expected = ((pd.Timestamp(_today()) - dates).dt.days // 365).astype("float")
    mismatch = (ages - expected).abs() > 1
    if bool(mismatch.fillna(False).any()):
        errors.append(f"{age} is not consistent with {dob}.")


def _validate_date_relationship(
    frame: pd.DataFrame,
    semantics: Mapping[str, str],
    errors: list[str],
) -> None:
    by_semantic: dict[str, str] = {}
    for column, semantic in semantics.items():
        by_semantic.setdefault(semantic, column)
    for left_semantic, right_semantic in (
        ("created_at", "updated_at"),
        ("created_date", "updated_date"),
        ("start_date", "end_date"),
        ("order_date", "delivery_date"),
        ("order_date", "payment_date"),
        ("opened_date", "closed_date"),
        ("hire_date", "termination_date"),
        ("effective_date", "expiration_date"),
    ):
        left = by_semantic.get(left_semantic)
        right = by_semantic.get(right_semantic)
        if left and right:
            left_values = pd.to_datetime(frame[left], errors="coerce")
            right_values = pd.to_datetime(frame[right], errors="coerce")
            mask = left_values.notna() & right_values.notna()
            if bool((right_values[mask] < left_values[mask]).any()):
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
    price = _first_column(columns_by_semantic, "unit_price") or _first_column(
        columns_by_semantic, "price"
    )
    total = _first_column(columns_by_semantic, "total_amount")
    if quantity and price and total:
        expected = pd.to_numeric(frame[quantity], errors="coerce") * pd.to_numeric(
            frame[price], errors="coerce"
        )
        discount = _first_column(columns_by_semantic, "discount")
        tax = _first_column(columns_by_semantic, "tax")
        if discount:
            discount_values = pd.to_numeric(frame[discount], errors="coerce").fillna(0)
            expected = expected - np.where(
                discount_values <= 1,
                expected * discount_values,
                discount_values,
            )
        if tax:
            tax_values = pd.to_numeric(frame[tax], errors="coerce").fillna(0)
            expected = expected + np.where(tax_values <= 1, expected * tax_values, tax_values)
        expected = pd.Series(expected).clip(lower=0).round(2)
        actual = pd.to_numeric(frame[total], errors="coerce").round(2)
        mask = expected.notna() & actual.notna()
        if bool((expected[mask] != actual[mask]).any()):
            errors.append(f"{total} must match quantity, price, discount, and tax.")


def _validate_status_nulls(
    frame: pd.DataFrame,
    semantics: Mapping[str, str],
    errors: list[str],
) -> None:
    columns_by_semantic: dict[str, list[str]] = {}
    for column, semantic in semantics.items():
        columns_by_semantic.setdefault(semantic, []).append(column)
    payment_status = _first_column(columns_by_semantic, "payment_status")
    payment_date = _first_column(columns_by_semantic, "payment_date")
    if payment_status and payment_date:
        pending = (
            frame[payment_status].astype(str).str.lower().isin({"pending", "failed", "unpaid"})
        )
        if bool(frame.loc[pending, payment_date].notna().any()):
            errors.append(f"{payment_date} should be null for unpaid payment statuses.")
    order_status = _first_column(columns_by_semantic, "order_status")
    delivery_date = _first_column(columns_by_semantic, "delivery_date")
    if order_status and delivery_date:
        blocked = frame[order_status].astype(str).str.lower().isin({"pending", "cancelled"})
        if bool(frame.loc[blocked, delivery_date].notna().any()):
            errors.append(f"{delivery_date} should be null for pending or cancelled orders.")
    employment_status = _first_column(columns_by_semantic, "employment_status")
    termination_date = _first_column(columns_by_semantic, "termination_date")
    if employment_status and termination_date:
        active = ~frame[employment_status].astype(str).str.lower().eq("terminated")
        if bool(frame.loc[active, termination_date].notna().any()):
            errors.append(f"{termination_date} should be null unless employment is terminated.")
    account_status = _first_column(columns_by_semantic, "account_status") or _first_column(
        columns_by_semantic, "status"
    )
    closed_date = _first_column(columns_by_semantic, "closed_date")
    if account_status and closed_date:
        open_status = ~frame[account_status].astype(str).str.lower().eq("closed")
        if bool(frame.loc[open_status, closed_date].notna().any()):
            errors.append(f"{closed_date} should be null unless status is closed.")
