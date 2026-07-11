from great_generator import infer_generation_plan, review_realism, tag_schema
from great_generator.planning import ColumnTags, GenerationPlan, RealismReport


def test_noop_plan_returns_valid_default_plan():
    plan = infer_generation_plan("customer_id int, customer_name string")

    assert isinstance(plan, GenerationPlan)
    assert plan.advisor == "none"
    assert plan.model_id is None
    assert [column.source for column in plan.columns] == ["default", "default"]


def test_noop_tags_return_valid_empty_tags():
    tags = tag_schema("customer_id int, customer_name string")

    assert isinstance(tags, ColumnTags)
    assert tags.advisor == "none"
    assert all(tag.pii_class is None for tag in tags.columns)
    assert all(tag.confidence == 0.0 for tag in tags.columns)


def test_noop_review_never_raises():
    plan = infer_generation_plan("customer_id int")
    report = review_realism({"rows": [{"customer_id": 1}]}, plan)

    assert isinstance(report, RealismReport)
    assert report.warnings == []
    assert report.advisor == "none"
