import pytest

from enterprise_synth import generate_domain, get_domain_schema, list_domains


def test_list_domains_returns_expected_domains():
    assert list_domains() == [
        "automotive",
        "banking",
        "ecommerce",
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
    ]


def test_get_domain_schema_returns_metadata():
    schema = get_domain_schema("ecommerce")
    assert schema.name == "ecommerce"
    assert "orders" in schema.tables


def test_invalid_domain_raises_helpful_error():
    with pytest.raises(ValueError, match="Unknown domain"):
        get_domain_schema("unknown")


def test_invalid_engine_raises_helpful_error():
    with pytest.raises(ValueError, match="Invalid engine"):
        generate_domain("ecommerce", engine="duckdb")


def test_invalid_output_format_raises_helpful_error():
    with pytest.raises(ValueError, match="Invalid output format"):
        generate_domain("ecommerce", output_format="xml")


def test_output_path_requires_output_format(tmp_path):
    with pytest.raises(ValueError, match="output_format is required"):
        generate_domain("ecommerce", output_path=tmp_path)
