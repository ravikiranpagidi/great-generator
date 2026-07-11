import pytest

from great_generator.advisors.noop import NoOpAdvisor
from great_generator.advisors.registry import get_advisor


def test_registry_returns_noop_for_none():
    assert isinstance(get_advisor(None), NoOpAdvisor)
    assert isinstance(get_advisor("none"), NoOpAdvisor)


def test_registry_parses_anthropic_spec(tmp_path):
    advisor = get_advisor("anthropic:claude-sonnet-4-6", cache_path=tmp_path)

    assert advisor.name == "anthropic:claude-sonnet-4-6"
    assert advisor.model_id == "claude-sonnet-4-6"


def test_registry_parses_ollama_spec(tmp_path):
    advisor = get_advisor("ollama:llama3.1:8b", cache_path=tmp_path)

    assert advisor.name == "ollama:llama3.1:8b"
    assert advisor.model_id == "llama3.1:8b"


def test_registry_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown advisor provider"):
        get_advisor("unknown:model")
