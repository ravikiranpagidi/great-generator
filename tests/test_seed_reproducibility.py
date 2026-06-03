import pandas as pd
import pytest

from enterprise_synth import generate_domain


@pytest.mark.parametrize(
    "domain", ["ecommerce", "banking", "healthcare", "telecom", "logistics", "saas"]
)
def test_same_seed_produces_identical_data(domain):
    first = generate_domain(domain, scale="tiny", seed=123)
    second = generate_domain(domain, scale="tiny", seed=123)
    for table_name in first:
        pd.testing.assert_frame_equal(first[table_name], second[table_name])


def test_different_seed_produces_different_data():
    first = generate_domain("ecommerce", scale="tiny", seed=123)
    second = generate_domain("ecommerce", scale="tiny", seed=456)
    assert not first["orders"].equals(second["orders"])
