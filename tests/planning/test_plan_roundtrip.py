from great_generator import infer_generation_plan
from great_generator.planning import GenerationPlan


def test_generation_plan_roundtrip_preserves_fields(tmp_path):
    plan = infer_generation_plan("customer_id int, customer_name string, amount double")
    path = tmp_path / "plan.json"

    plan.to_json(path)
    loaded = GenerationPlan.from_json(path)

    assert loaded.to_dict() == plan.to_dict()


def test_column_tags_roundtrip_preserves_fields(tmp_path):
    from great_generator import tag_schema
    from great_generator.planning import ColumnTags

    tags = tag_schema("customer_id int, email string")
    path = tmp_path / "tags.json"

    tags.to_json(path)
    loaded = ColumnTags.from_json(path)

    assert loaded.to_dict() == tags.to_dict()
