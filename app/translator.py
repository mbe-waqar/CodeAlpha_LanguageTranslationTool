"""Translation service: validation, provider fallback and caching."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx

from app.providers import AUTO, PROVIDERS, ProviderError

MAX_CHARS = 5000  # upstream engines reject longer payloads
TIMEOUT = 10.0
HEADERS = {"User-Agent": "CodeAlpha-TranslationTool/1.0"}
FAILURES = (httpx.HTTPError, ProviderError, KeyError, IndexError, TypeError)


class TranslationError(RuntimeError):
    """Base class for every failure this service reports."""


class UnsupportedLanguage(TranslationError):
    """The requested language code is not one we support."""


class ProvidersUnavailable(TranslationError):
    """Every back-end failed; the text could not be translated."""


@dataclass(frozen=True)
class Translation:
    text: str
    source: str  # the detected code when the request asked for auto-detection
    target: str
    provider: str


@lru_cache(maxsize=1)
def supported_languages() -> dict[str, str]:
    """Map of ``{language_code: display_name}``, loaded once from the bundled list."""
    return json.loads((Path(__file__).parent / "languages.json").read_text(encoding="utf-8"))


def validate(code: str, *, allow_auto: bool) -> str:
    """Return ``code`` if the tool supports it, else raise ``TranslationError``."""
    if code not in supported_languages() or (code == AUTO and not allow_auto):
        raise UnsupportedLanguage(f"Unsupported language code: {code!r}")
    return code


@lru_cache(maxsize=1024)
def translate(text: str, source: str = AUTO, target: str = "en") -> Translation:
    """Translate ``text``, trying each provider in turn. Repeat calls are served from cache."""
    validate(source, allow_auto=True)
    validate(target, allow_auto=False)

    errors = []
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS) as client:
        for name, provider in PROVIDERS.items():
            try:
                translated, detected = provider(client, text, source, target)
                return Translation(translated, detected, target, name)
            except FAILURES as exc:
                errors.append(f"{name}: {exc}")
    raise ProvidersUnavailable("Translation failed — " + "; ".join(errors))
