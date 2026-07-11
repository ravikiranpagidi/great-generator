from great_generator import infer_generation_plan


def test_plan_edit_marks_source_and_human_reviewed():
    plan = infer_generation_plan("customer_name string, amount double")

    edited = plan.with_edit(
        "customer_name",
        strategy="semantic.full_name",
        parameters={},
        rationale="Reviewed name field.",
        confidence=1.0,
    )

    assert edited is not plan
    assert edited.human_reviewed is True
    assert edited.columns[0].source == "user_edit"
    assert edited.columns[0].strategy == "semantic.full_name"
