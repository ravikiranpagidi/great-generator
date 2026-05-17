from enterprise_synth import generate_domain, get_domain_schema
from enterprise_synth.utils.validation import validate_foreign_keys


def test_null_injection_works():
    data = generate_domain("ecommerce", scale="tiny", seed=42, anomalies={"null_rate": 0.5})
    assert data["customers"].isna().any().any()


def test_duplicate_injection_works():
    clean = generate_domain("ecommerce", scale="tiny", seed=42)
    dirty = generate_domain("ecommerce", scale="tiny", seed=42, anomalies={"duplicate_rate": 0.1})
    assert len(dirty["orders"]) > len(clean["orders"])


def test_orphan_fk_injection_is_opt_in():
    clean = generate_domain("ecommerce", scale="tiny", seed=42)
    dirty = generate_domain("ecommerce", scale="tiny", seed=42, anomalies={"orphan_fk_rate": 0.2})
    clean_violations = validate_foreign_keys(clean, get_domain_schema("ecommerce"))
    dirty_violations = validate_foreign_keys(dirty, get_domain_schema("ecommerce"))
    assert all(count == 0 for count in clean_violations.values())
    assert any(count > 0 for count in dirty_violations.values())


def test_outlier_injection_works():
    clean = generate_domain("banking", scale="tiny", seed=42)
    dirty = generate_domain("banking", scale="tiny", seed=42, anomalies={"outlier_rate": 0.5})
    assert dirty["transactions"]["amount"].max() >= clean["transactions"]["amount"].max()


def test_invalid_status_code_injection_works():
    dirty = generate_domain(
        "banking", scale="tiny", seed=42, anomalies={"invalid_status_rate": 1.0}
    )
    assert "__INVALID__" in set(dirty["accounts"]["status"])
