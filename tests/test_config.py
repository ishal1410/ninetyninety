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


def test_providers_in_order_lists_every_configured_provider():
    from ninetyninety.config import providers_in_order
    both = providers_in_order({"GOOGLE_API_KEY": "x", "OPENROUTER_API_KEY": "y"})
    assert both[0].startswith("gemini:") and both[-1] == "openrouter"
    assert len(both) >= 3  # several Gemini models, each with its own daily cap
    assert providers_in_order({"OPENROUTER_API_KEY": "y"}) == ["openrouter"]
    assert providers_in_order({}) == []


def test_build_model_gemini_accepts_a_model_suffix(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    assert build_model("gemini:gemini-3.8-flash").config["model_id"] == "gemini-3.8-flash"
