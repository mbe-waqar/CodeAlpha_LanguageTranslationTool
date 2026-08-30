"""Language Translation Tool — CodeAlpha Task 1."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import TranslationRequest, TranslationResponse
from app.translator import (
    ProvidersUnavailable,
    TranslationError,
    UnsupportedLanguage,
    supported_languages,
    translate,
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Language Translation Tool", version="1.0.0")


STATUS_CODES = {UnsupportedLanguage: 422, ProvidersUnavailable: 502}


@app.exception_handler(TranslationError)
def _on_translation_error(_: Request, exc: TranslationError) -> JSONResponse:
    """Bad language code -> 422 (client error); provider outage -> 502 (upstream error)."""
    return JSONResponse({"detail": str(exc)}, status_code=STATUS_CODES.get(type(exc), 500))


@app.get("/api/languages")
def languages() -> dict[str, str]:
    """All language codes the tool accepts, keyed by code."""
    return supported_languages()


@app.post("/api/translate", response_model=TranslationResponse)
def translate_text(req: TranslationRequest) -> TranslationResponse:
    result = translate(req.text.strip(), req.source, req.target)
    return TranslationResponse(**vars(result))


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
