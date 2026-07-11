from great_generator import infer_generation_plan
from great_generator.io.manifest import enrich_manifest


def test_manifest_enrichment_is_additive():
    plan = infer_generation_plan("customer_id int")
    manifest = {"dataset": "sample"}

    enriched = enrich_manifest(manifest, plan=plan, cache_hit=True)

    assert enriched["dataset"] == "sample"
    assert enriched["advisor"]["name"] == "none"
    assert enriched["advisor"]["cache_hit"] is True
    assert enriched["advisor"]["plan_fingerprint"].startswith("sha256:")
