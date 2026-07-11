import json
from urllib.error import URLError

import pytest

from great_generator.advisors.exceptions import AdvisorUnavailableError
from great_generator.advisors.ollama import OllamaAdvisor


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_ollama_advisor_happy_path_with_lenient_json(monkeypatch, tmp_path):
    def fake_urlopen(request, timeout):
        return _FakeResponse(
            {
                "response": (
                    "Here is JSON: "
                    '{"columns":[{"column":"email","dtype":"string","strategy":"semantic.email",'
                    '"parameters":{},"rationale":"email field","confidence":0.9,'
                    '"source":"advisor"}],"inter_column_rules":[],"notes":null}'
                )
            }
        )

    monkeypatch.setattr("great_generator.advisors.ollama.urlopen", fake_urlopen)

    advisor = OllamaAdvisor(cache_path=tmp_path)
    plan = advisor.propose_plan("email string")

    assert plan.columns[0].strategy == "semantic.email"
    assert advisor.last_cache_hit is False


def test_ollama_unreachable_raises_clear_error(monkeypatch, tmp_path):
    def fake_urlopen(request, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr("great_generator.advisors.ollama.urlopen", fake_urlopen)

    advisor = OllamaAdvisor(cache_path=tmp_path)

    with pytest.raises(AdvisorUnavailableError, match="Ollama advisor is unavailable"):
        advisor.propose_plan("email string")


def test_ollama_cache_hit_skips_http(monkeypatch, tmp_path):
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        return _FakeResponse(
            {
                "response": (
                    '{"columns":[{"column":"email","dtype":"string","strategy":"semantic.email",'
                    '"parameters":{},"rationale":"email field","confidence":0.9,'
                    '"source":"advisor"}],"inter_column_rules":[],"notes":null}'
                )
            }
        )

    monkeypatch.setattr("great_generator.advisors.ollama.urlopen", fake_urlopen)

    first = OllamaAdvisor(cache_path=tmp_path)
    second = OllamaAdvisor(cache_path=tmp_path)

    first.propose_plan("email string")
    second.propose_plan("email string")

    assert calls["count"] == 1
    assert second.last_cache_hit is True
