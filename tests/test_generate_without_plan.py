from great_generator import generate_from_schema


def test_generate_from_schema_without_plan_keeps_existing_placeholder_path():
    frame = generate_from_schema("code string", rows=3, realism="placeholder")

    assert list(frame["code"]) == ["code_1", "code_2", "code_3"]
