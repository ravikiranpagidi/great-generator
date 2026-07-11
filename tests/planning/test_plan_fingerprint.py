from great_generator.planning import schema_fingerprint


def test_schema_fingerprint_is_stable_across_runs():
    schema = "customer_id int, customer_name string, amount double"

    assert schema_fingerprint(schema) == schema_fingerprint(schema)


def test_schema_fingerprint_ignores_extra_spacing():
    left = "customer_id int, customer_name string"
    right = " customer_id   int ,  customer_name string "

    assert schema_fingerprint(left) == schema_fingerprint(right)
