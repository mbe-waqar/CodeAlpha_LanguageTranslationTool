import pytest

from app import translator


@pytest.fixture(autouse=True)
def clear_caches():
    """Each test starts from a cold cache so results never leak between tests."""
    translator.translate.cache_clear()
    yield
    translator.translate.cache_clear()
