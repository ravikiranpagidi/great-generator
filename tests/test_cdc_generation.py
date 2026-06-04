from great_generator import generate_cdc


def test_cdc_contains_required_columns():
    cdc = generate_cdc("banking", table="customers", rows=100, seed=42)
    assert {
        "operation",
        "before",
        "after",
        "event_timestamp",
        "ingestion_timestamp",
        "sequence_number",
        "source_system",
        "late_arriving",
        "duplicate",
    }.issubset(cdc.columns)


def test_cdc_operation_mix_is_valid():
    cdc = generate_cdc("banking", table="customers", rows=100, seed=42)
    assert set(cdc["operation"]).issubset({"insert", "update", "delete"})


def test_cdc_late_arrivals_and_duplicates_are_opt_in():
    clean = generate_cdc("banking", table="customers", rows=100, seed=42)
    dirty = generate_cdc(
        "banking",
        table="customers",
        rows=100,
        late_arrival_rate=0.2,
        duplicate_rate=0.1,
        seed=42,
    )
    assert not clean["late_arriving"].any()
    assert not clean["duplicate"].any()
    assert dirty["late_arriving"].any()
    assert dirty["duplicate"].any()
    assert len(dirty) > len(clean)
