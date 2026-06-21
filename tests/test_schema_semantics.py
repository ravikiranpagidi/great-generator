import pandas as pd
import pytest

from great_generator import (
    explain_generation_plan,
    generate_domain,
    generate_from_schema,
    validate_generated_data,
)
from great_generator.core import value_generator
from great_generator.core.realism import normalize_realism_mode
from great_generator.schemas.semantic import (
    infer_field_semantic_info,
    infer_field_semantic_type,
    normalize_column_name,
)


def test_semantic_inference_handles_common_aliases():
    assert normalize_column_name("memberName") == "member_name"
    assert normalize_column_name("cust-name") == "customer_name"
    assert normalize_column_name("cust_nm") == "customer_name"
    assert infer_field_semantic_type("emp_name", "string") == "employee_name"
    assert infer_field_semantic_type("CustomerName", "string") == "customer_name"
    assert infer_field_semantic_type("email_id", "string") == "email"
    assert infer_field_semantic_type("city_name", "string") == "city"
    assert infer_field_semantic_type("mobile_no", "string") == "phone"
    assert infer_field_semantic_type("txn_amt", "double") == "transaction_amount"
    assert infer_field_semantic_type("created_ts", "timestamp") == "created_at"
    assert infer_field_semantic_type("transaction_amount", "double") == "transaction_amount"

    info = infer_field_semantic_info("emp_age", "int")
    assert info["semantic_type"] == "employee_age"
    assert info["confidence"] > 0.9


def test_generate_from_schema_uses_semantic_field_values_by_default():
    frame = generate_from_schema(
        {
            "customer_name": "string",
            "emp_name": "string",
            "member_name": "string",
            "age": "int",
            "address": "string",
            "email": "string",
            "phone_number": "string",
        },
        rows=20,
        seed=42,
    )

    assert frame["customer_name"].str.contains(" ").all()
    assert frame["emp_name"].str.contains(" ").all()
    assert frame["member_name"].str.contains(" ").all()
    assert not frame["address"].str.startswith("address_").any()
    assert frame["age"].between(18, 90).all()
    assert frame["email"].str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$").all()
    assert (
        frame["phone_number"].astype(str).str.replace(r"\D", "", regex=True).str.len().ge(7).all()
    )


def test_generate_from_schema_preserves_placeholder_mode_when_requested():
    frame = generate_from_schema("id int, name string", rows=3, seed=42, realistic=False)

    assert frame["id"].tolist() == [1, 2, 3]
    assert frame["name"].tolist() == ["name_1", "name_2", "name_3"]


def test_person_cross_field_consistency():
    frame = generate_from_schema(
        "first_name string, last_name string, full_name string, email string",
        rows=10,
        seed=42,
    )

    expected_full_name = frame["first_name"] + " " + frame["last_name"]
    assert frame["full_name"].equals(expected_full_name)
    for row in frame.itertuples(index=False):
        expected_email = f"{row.first_name.lower()}.{row.last_name.lower()}@example.com"
        assert row.email == expected_email


def test_age_and_date_of_birth_are_consistent():
    frame = generate_from_schema("date_of_birth date, age int", rows=10, seed=42)

    approximate_age = (
        pd.Timestamp.today().normalize() - pd.to_datetime(frame["date_of_birth"])
    ).dt.days // 365
    assert (frame["age"] == approximate_age).all()


def test_date_relationships_are_consistent():
    frame = generate_from_schema(
        (
            "created_at timestamp, updated_at timestamp, start_date date, end_date date, "
            "order_date date, delivery_date date, payment_date date, transaction_date date"
        ),
        rows=20,
        seed=42,
    )

    today = pd.Timestamp.today().normalize()
    for column in [
        "created_at",
        "updated_at",
        "start_date",
        "end_date",
        "order_date",
        "delivery_date",
        "payment_date",
        "transaction_date",
    ]:
        assert (pd.to_datetime(frame[column]) <= today).all()
    assert (pd.to_datetime(frame["updated_at"]) >= pd.to_datetime(frame["created_at"])).all()
    assert (pd.to_datetime(frame["end_date"]) >= pd.to_datetime(frame["start_date"])).all()
    assert (pd.to_datetime(frame["delivery_date"]) >= pd.to_datetime(frame["order_date"])).all()
    assert (pd.to_datetime(frame["payment_date"]) >= pd.to_datetime(frame["order_date"])).all()


def test_quantity_price_total_are_consistent():
    frame = generate_from_schema(
        "quantity int, unit_price double, discount double, tax double, total_amount double",
        rows=20,
        seed=42,
    )

    expected = frame["quantity"] * frame["unit_price"]
    expected = expected - (expected * frame["discount"])
    expected = expected + (expected * frame["tax"])
    expected = expected.round(2)
    assert frame["total_amount"].round(2).equals(expected)


def test_custom_rules_override_semantics():
    frame = generate_from_schema(
        {"customer_name": "string", "age": "int", "salary": "float", "status": "string"},
        rows=30,
        seed=42,
        custom_rules={
            "customer_name": {"type": "full_name"},
            "age": {"min": 25, "max": 55},
            "salary": {"min": 60000, "max": 160000},
            "status": {"values": ["Active", "Inactive"]},
        },
    )

    assert frame["customer_name"].str.contains(" ").all()
    assert frame["age"].between(25, 55).all()
    assert frame["salary"].between(60000, 160000).all()
    assert set(frame["status"]).issubset({"Active", "Inactive"})


def test_domain_presets_influence_values_and_prefixes():
    banking = generate_from_schema(
        {
            "account_id": "string",
            "account_status": "string",
            "transaction_type": "string",
        },
        rows=20,
        domain="banking",
        seed=42,
    )
    retail = generate_from_schema(
        {"order_status": "string", "customer_type": "string", "category": "string"},
        rows=20,
        domain="retail",
        seed=42,
    )
    hr = generate_from_schema(
        {"employee_id": "string", "department": "string", "employment_status": "string"},
        rows=20,
        domain="hr",
        seed=42,
    )

    assert banking["account_id"].str.startswith("ACCT").all()
    assert set(banking["account_status"]).issubset({"Active", "Dormant", "Closed", "Frozen"})
    assert set(banking["transaction_type"]).issubset(
        {"Deposit", "Withdrawal", "Transfer", "Payment"}
    )
    assert set(retail["order_status"]).issubset(
        {"Pending", "Shipped", "Delivered", "Cancelled", "Returned"}
    )
    assert set(retail["customer_type"]).issubset({"New", "Returning", "Loyalty"})
    assert hr["employee_id"].str.startswith("EMP").all()
    assert set(hr["employment_status"]).issubset({"Active", "Terminated", "On Leave"})


def test_validate_generated_data_returns_quality_result():
    frame = generate_from_schema(
        "customer_id string, email string, age int, quantity int, unit_price double, total_amount double",
        rows=10,
        seed=42,
    )

    result = validate_generated_data(frame)

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["summary"]["rows_checked"] == 10


def test_validate_generated_data_detects_bad_email_and_age():
    result = validate_generated_data(
        [{"email": "not-an-email", "age": 140}],
        {"email": "string", "age": "int"},
    )

    assert result["passed"] is False
    assert any("email" in error for error in result["errors"])
    assert any("age" in error for error in result["errors"])


def test_realism_typo_alias_is_supported_with_warning():
    with pytest.warns(UserWarning, match="looks like a typo"):
        assert normalize_realism_mode("realsitic") == "realistic"

    with pytest.warns(UserWarning, match="looks like a typo"):
        frame = generate_from_schema("customer_name string, age int", rows=5, realism="realsitic")

    assert frame["customer_name"].str.contains(" ").all()
    assert frame["age"].between(18, 90).all()


def test_id_safety_and_generic_numeric_ranges():
    frame = generate_from_schema(
        {
            "customer_id": "string",
            "employee_id": "string",
            "transaction_id": "string",
            "integer_metric": "int",
        },
        rows=25,
        seed=42,
    )

    assert frame["customer_id"].is_unique
    assert frame["employee_id"].is_unique
    assert frame["transaction_id"].is_unique
    assert frame["customer_id"].str.startswith("CUST").all()
    assert frame["integer_metric"].between(1, 100).all()


def test_status_aware_dates_are_null_when_status_requires_it():
    frame = generate_from_schema(
        (
            "order_status string, order_date date, delivery_date date, "
            "payment_status string, payment_date date, employment_status string, "
            "hire_date date, termination_date date, account_status string, "
            "opened_date date, closed_date date"
        ),
        rows=10,
        seed=42,
        custom_rules={
            "order_status": {"values": ["Pending"]},
            "payment_status": {"values": ["Pending"]},
            "employment_status": {"values": ["Active"]},
            "account_status": {"values": ["Active"]},
        },
    )

    assert frame["delivery_date"].isna().all()
    assert frame["payment_date"].isna().all()
    assert frame["termination_date"].isna().all()
    assert frame["closed_date"].isna().all()


def test_validation_catches_future_and_out_of_order_dates():
    result = validate_generated_data(
        [
            {
                "created_at": "2035-01-01T00:00:00",
                "updated_at": "2020-01-01T00:00:00",
            }
        ],
        {"created_at": "timestamp", "updated_at": "timestamp"},
    )

    assert result["passed"] is False
    assert any("future" in error for error in result["errors"])
    assert any("updated_at" in error for error in result["errors"])


def test_validate_and_return_report_are_opt_in():
    frame, report = generate_from_schema(
        {"customer_name": "string", "age": "int", "email": "string"},
        rows=10,
        validate=True,
        return_report=True,
        seed=42,
    )

    assert len(frame) == 10
    assert report["passed"] is True
    assert report["summary"]["semantic_coverage"] == 1.0


def test_explain_generation_plan_reports_coverage():
    plan = explain_generation_plan(
        {"customer_name": "string", "age": "int", "misc_value": "string"}
    )

    assert plan["realism"] == "realistic"
    assert plan["semantic_coverage"] < 1.0
    assert any(field["semantic_type"] == "customer_name" for field in plan["fields"])


def test_generate_domain_public_behavior_still_returns_tables():
    data = generate_domain("banking", scale="tiny")

    assert "customers" in data
    assert "accounts" in data


def test_fallback_generator_works_when_faker_is_unavailable(monkeypatch):
    monkeypatch.setattr(value_generator, "FAKER_FACTORY", None)

    frame = generate_from_schema(
        "customer_name string, address string, email string, phone string",
        rows=5,
        seed=42,
    )

    assert frame["customer_name"].str.contains(" ").all()
    assert not frame["address"].str.startswith("address_").any()
    assert frame["email"].str.match(r"^[^@\s]+@example\.com$").all()
    assert frame["phone"].astype(str).str.contains("555").all()
