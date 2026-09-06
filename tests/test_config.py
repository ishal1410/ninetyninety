import pytest

from ninetyninety.config import build_model, select_provider


def test_select_provider_prefers_gemini():
    assert select_provider({"GOOGLE_API_KEY": "x",
                            "OPENROUTER_API_KEY": "y"}) == "gemini"


def test_select_provider_falls_back_to_openrouter():
    assert select_provider({"OPENROUTER_API_KEY": "x"}) == "openrouter"


def test_select_provider_none_when_unconfigured():
    assert select_provider({}) is None


def test_build_model_raises_with_setup_instructions(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="aistudio.google.com"):
        build_model()
