from great_generator import generate_domain, generate_from_schema
from great_generator.core.reference_values import BANK_ACCOUNT_TYPES, BANK_MERCHANTS, ORDER_STATUSES


def test_realistic_ecommerce_customers_have_believable_identity_fields():
    data = generate_domain("ecommerce", scale="tiny", realism="realistic", seed=42)
    customers = data["customers"]

    assert {"first_name", "last_name", "customer_name", "email", "phone_number"}.issubset(
        customers.columns
    )
    assert customers["customer_name"].str.contains(" ").any()
    assert customers["email"].str.contains("@example.com", regex=False).all()
    assert not customers["customer_name"].str.startswith("customer_").all()


def test_placeholder_mode_preserves_simple_schema_values():
    data = generate_domain("ecommerce", scale="tiny", realism="placeholder", seed=42)
    customers = data["customers"]

    assert customers["customer_name"].iloc[0] == "customer_name_1"
    assert customers["email"].iloc[0] == "user_1@example.com"


def test_realistic_seed_reproducibility_for_identity_values():
    data1 = generate_domain("banking", scale="tiny", realism="realistic", seed=42)
    data2 = generate_domain("banking", scale="tiny", realism="realistic", seed=42)

    assert data1["customers"].equals(data2["customers"])
    assert data1["merchants"].equals(data2["merchants"])


def test_different_seed_changes_realistic_identity_values():
    data1 = generate_domain("banking", scale="tiny", realism="realistic", seed=42)
    data2 = generate_domain("banking", scale="tiny", realism="realistic", seed=43)

    assert not data1["customers"]["customer_name"].equals(data2["customers"]["customer_name"])


def test_realistic_domain_reference_values_are_used():
    data = generate_domain("banking", scale="tiny", realism="realistic", seed=42)

    assert data["merchants"]["merchant_name"].isin(BANK_MERCHANTS).any()
    assert data["accounts"]["account_type"].isin(BANK_ACCOUNT_TYPES).all()


def test_realistic_ecommerce_status_reference_values_are_used():
    data = generate_domain("ecommerce", scale="tiny", realism="realistic", seed=42)

    assert data["orders"]["order_status"].isin(ORDER_STATUSES).all()


def test_realistic_values_do_not_break_relationships():
    data = generate_domain("ecommerce", scale="tiny", realism="realistic", seed=42)

    assert data["orders"]["customer_id"].isin(data["customers"]["customer_id"]).all()
    assert data["order_items"]["order_id"].isin(data["orders"]["order_id"]).all()
    assert data["order_items"]["product_id"].isin(data["products"]["product_id"]).all()


def test_generate_from_schema_can_use_realistic_field_detection():
    frame = generate_from_schema(
        "id int, customer_name string, email string, phone_number string",
        rows=5,
        realism="realistic",
        seed=42,
    )

    assert frame["customer_name"].str.contains(" ").any()
    assert frame["email"].str.contains("@example.com", regex=False).all()
    assert not frame["customer_name"].str.startswith("customer_name_").all()
