"""Translation back-ends.

Every provider has the same signature — ``(client, text, source, target)`` returning
``(translated_text, detected_source_code)`` — so the service layer can try them in order.
"""

import httpx

AUTO = "auto"
GOOGLE_URL = "https://clients5.google.com/translate_a/t"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"


class ProviderError(RuntimeError):
    """The back-end answered, but not with a usable translation."""


def _json(response: httpx.Response):
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError(f"malformed response from {response.url.host}") from exc


def google(client: httpx.Client, text: str, source: str, target: str) -> tuple[str, str]:
    """Google Translate's public endpoint (no API key required)."""
    params = {"client": "dict-chrome-ex", "sl": source, "tl": target, "q": text}
    payload = _json(client.get(GOOGLE_URL, params=params))
    if not payload:
        raise ProviderError("empty translation")
    # ["text"] when the source is explicit, [["text", "detected"]] when auto-detecting.
    head = payload[0]
    return (head[0], head[1]) if isinstance(head, list) else (head, source)


def mymemory(client: httpx.Client, text: str, source: str, target: str) -> tuple[str, str]:
    """MyMemory — key-free fallback used when Google is unreachable or rate-limited."""
    langpair = f"{'Autodetect' if source == AUTO else source}|{target}"
    payload = _json(client.get(MYMEMORY_URL, params={"q": text, "langpair": langpair}))
    if int(payload.get("responseStatus", 0)) != 200:
        raise ProviderError(payload.get("responseDetails") or "translation rejected")
    data = payload["responseData"]
    return data["translatedText"], data.get("detectedLanguage") or source


PROVIDERS = {"google": google, "mymemory": mymemory}
