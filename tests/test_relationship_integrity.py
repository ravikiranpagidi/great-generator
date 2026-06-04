from great_generator import generate_domain, get_domain_schema
from great_generator.utils.validation import validate_foreign_keys


def test_ecommerce_relationships_are_valid_by_default():
    data = generate_domain("ecommerce", scale="tiny", seed=42)
    violations = validate_foreign_keys(data, get_domain_schema("ecommerce"))
    assert all(count == 0 for count in violations.values()), violations


def test_banking_relationships_are_valid_by_default():
    data = generate_domain("banking", scale="tiny", seed=42)
    violations = validate_foreign_keys(data, get_domain_schema("banking"))
    assert all(count == 0 for count in violations.values()), violations


def test_new_domain_relationships_are_valid_by_default():
    for domain in [
        "automotive",
        "energy",
        "healthcare",
        "hospitality",
        "insurance",
        "logistics",
        "manufacturing",
        "media",
        "public_sector",
        "saas",
        "telecom",
    ]:
        data = generate_domain(domain, scale="tiny", seed=42)
        violations = validate_foreign_keys(data, get_domain_schema(domain))
        assert all(count == 0 for count in violations.values()), {domain: violations}
