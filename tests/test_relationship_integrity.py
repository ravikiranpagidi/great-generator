from enterprise_synth import generate_domain, get_domain_schema
from enterprise_synth.utils.validation import validate_foreign_keys


def test_ecommerce_relationships_are_valid_by_default():
    data = generate_domain("ecommerce", scale="tiny", seed=42)
    violations = validate_foreign_keys(data, get_domain_schema("ecommerce"))
    assert all(count == 0 for count in violations.values()), violations


def test_banking_relationships_are_valid_by_default():
    data = generate_domain("banking", scale="tiny", seed=42)
    violations = validate_foreign_keys(data, get_domain_schema("banking"))
    assert all(count == 0 for count in violations.values()), violations
