from great_generator import generate_domain


def test_tiny_scale_profile_counts_are_exact():
    data = generate_domain("ecommerce", scale="tiny", seed=42)
    assert {name: len(frame) for name, frame in data.items()} == {
        "customers": 25,
        "products": 16,
        "orders": 60,
        "order_items": 150,
        "payments": 60,
        "shipments": 60,
        "returns": 6,
    }


def test_row_count_overrides_are_respected():
    data = generate_domain(
        "ecommerce",
        scale="tiny",
        rows={
            "customers": 10,
            "products": 8,
            "orders": 20,
            "order_items": 40,
            "payments": 20,
            "shipments": 20,
            "returns": 2,
        },
        seed=42,
    )
    assert len(data["customers"]) == 10
    assert len(data["orders"]) == 20
    assert len(data["order_items"]) == 40
