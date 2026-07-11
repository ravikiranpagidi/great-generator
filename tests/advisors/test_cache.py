from great_generator.advisors import cache


def test_cache_put_get_roundtrip(tmp_path):
    key, input_hash = cache.make_cache_key("none", "none", "test_v1", {"b": 2, "a": 1})
    cache.put(
        key,
        {
            "advisor": "none",
            "model_id": "none",
            "prompt_version": "test_v1",
            "input_hash": input_hash,
            "response": {"ok": True},
        },
        cache_path=tmp_path,
        advisor="none",
    )

    entry = cache.get(key, cache_path=tmp_path, advisor="none")

    assert entry is not None
    assert entry["response"] == {"ok": True}


def test_cache_key_is_stable_for_sorted_payloads():
    left, _ = cache.make_cache_key("advisor", "model", "v1", {"b": 2, "a": 1})
    right, _ = cache.make_cache_key("advisor", "model", "v1", {"a": 1, "b": 2})

    assert left == right


def test_cache_clear_removes_advisor_entries(tmp_path):
    key, input_hash = cache.make_cache_key("ollama:model", "model", "v1", {"a": 1})
    cache.put(
        key,
        {
            "advisor": "ollama:model",
            "model_id": "model",
            "prompt_version": "v1",
            "input_hash": input_hash,
            "response": {"ok": True},
        },
        cache_path=tmp_path,
        advisor="ollama:model",
    )

    cache.clear("ollama:model", cache_path=tmp_path)

    assert cache.get(key, cache_path=tmp_path, advisor="ollama:model") is None
