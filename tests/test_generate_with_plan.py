from great_generator import generate_from_schema, infer_generation_plan


def test_generate_from_schema_uses_plan_deterministically():
    schema = "code string, amount int"
    plan = infer_generation_plan(schema).with_edit(
        "code",
        strategy="string.pattern",
        parameters={"pattern": "ITEM{index:03d}"},
        rationale="Reviewed code pattern.",
        confidence=1.0,
    )

    left = generate_from_schema(schema, rows=5, realism="placeholder", plan=plan, seed=42)
    right = generate_from_schema(schema, rows=5, realism="placeholder", plan=plan, seed=42)

    assert left.equals(right)
    assert list(left["code"]) == ["ITEM001", "ITEM002", "ITEM003", "ITEM004", "ITEM005"]
