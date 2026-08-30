"""Provider parsing, exercised offline with a stubbed transport."""

import httpx
import pytest

from app.providers import ProviderError, google, mymemory


def client_returning(payload, status: int = 200) -> httpx.Client:
    handler = lambda _: httpx.Response(status, json=payload) if payload is not None else httpx.Response(status)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_google_parses_explicit_source():
    with client_returning(["Bonjour"]) as client:
        assert google(client, "Hello", "en", "fr") == ("Bonjour", "en")


def test_google_parses_detected_source():
    with client_returning([["Life is beautiful", "es"]]) as client:
        assert google(client, "La vida es bella", "auto", "en") == ("Life is beautiful", "es")


def test_google_rejects_empty_payload():
    with client_returning([]) as client, pytest.raises(ProviderError):
        google(client, "Hello", "en", "fr")


def test_google_raises_on_rate_limit():
    with client_returning(None, status=429) as client, pytest.raises(httpx.HTTPStatusError):
        google(client, "Hello", "en", "fr")


def test_mymemory_returns_translation_and_detected_language():
    payload = {"responseStatus": 200, "responseData": {"translatedText": "Hola", "detectedLanguage": "en"}}
    with client_returning(payload) as client:
        assert mymemory(client, "Hello", "auto", "es") == ("Hola", "en")


def test_mymemory_surfaces_upstream_rejection():
    payload = {"responseStatus": 403, "responseDetails": "INVALID SOURCE LANGUAGE"}
    with client_returning(payload) as client, pytest.raises(ProviderError, match="INVALID SOURCE"):
        mymemory(client, "Hello", "auto", "es")
