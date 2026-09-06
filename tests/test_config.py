import pytest

from ninetyninety.config import build_model, select_provider


def test_select_provider_prefers_agentrouter_then_gemini():
    assert select_provider({"AGENTROUTER_API_KEY": "a", "GOOGLE_API_KEY": "x",
                            "OPENROUTER_API_KEY": "y"}) == "agentrouter"
    assert select_provider({"GOOGLE_API_KEY": "x",
                            "OPENROUTER_API_KEY": "y"}) == "gemini"


def test_build_model_agentrouter_uses_env_model_override(monkeypatch):
    monkeypatch.setenv("AGENTROUTER_API_KEY", "dummy")
    monkeypatch.setenv("AGENTROUTER_MODEL_ID", "claude-x")
    assert build_model("agentrouter").config["model_id"] == "claude-x"


def test_select_provider_falls_back_to_openrouter():
    assert select_provider({"OPENROUTER_API_KEY": "x"}) == "openrouter"


def test_select_provider_none_when_unconfigured():
    assert select_provider({}) is None


def test_build_model_raises_with_setup_instructions(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AGENTROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="aistudio.google.com"):
        build_model()
