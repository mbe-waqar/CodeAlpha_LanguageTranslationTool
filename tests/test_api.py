"""API behaviour with the network replaced by scripted providers."""

import pytest
from fastapi.testclient import TestClient

from app import providers
from app.main import app
from app.providers import ProviderError

client = TestClient(app)


def stub(monkeypatch, **registry):
    monkeypatch.setattr(providers, "PROVIDERS", registry, raising=False)
    monkeypatch.setattr("app.translator.PROVIDERS", registry)


def echo(_client, text, source, target):
    return f"[{target}] {text}", source


@pytest.fixture(autouse=True)
def default_provider(monkeypatch):
    stub(monkeypatch, google=echo)


def test_languages_endpoint_lists_codes():
    languages = client.get("/api/languages").json()
    assert languages["en"] == "English" and languages["auto"] == "Detect Language"
    assert len(languages) > 100


def test_translate_returns_translated_text():
    res = client.post("/api/translate", json={"text": "hello", "source": "en", "target": "ur"})
    assert res.status_code == 200
    assert res.json() == {"text": "[ur] hello", "source": "en", "target": "ur", "provider": "google"}


def test_repeated_translation_is_served_from_cache():
    from app.translator import translate

    payload = {"text": "hello", "source": "en", "target": "ur"}
    client.post("/api/translate", json=payload)
    client.post("/api/translate", json=payload)
    assert translate.cache_info().hits == 1


def test_falls_back_to_the_next_provider(monkeypatch):
    def broken(*_):
        raise ProviderError("upstream down")

    stub(monkeypatch, google=broken, mymemory=echo)
    assert client.post("/api/translate", json={"text": "hi"}).json()["provider"] == "mymemory"


def test_error_when_every_provider_fails(monkeypatch):
    def broken(*_):
        raise ProviderError("upstream down")

    stub(monkeypatch, google=broken)
    res = client.post("/api/translate", json={"text": "hi"})
    assert res.status_code == 502 and "upstream down" in res.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [{"text": ""}, {"text": "x" * 5001}, {"text": "hi", "target": "klingon"}, {"text": "hi", "target": "auto"}],
)
def test_invalid_requests_are_rejected(payload):
    assert client.post("/api/translate", json=payload).status_code == 422


def test_ui_is_served():
    assert "<title>Language Translation Tool" in client.get("/").text
