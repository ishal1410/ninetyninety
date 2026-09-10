import pytest

from ninetyninety.config import (
    DEFAULT_MODEL_IDS, build_model, gemini_configured, model_ids, provider_label,
)


def test_gemini_configured_needs_the_key():
    assert gemini_configured({"GOOGLE_API_KEY": "k"})
    assert not gemini_configured({"GOOGLE_API_KEY": ""})
    assert not gemini_configured({})


def test_model_ids_default_and_override():
    assert model_ids({}) == DEFAULT_MODEL_IDS.split(",")
    assert model_ids({"GEMINI_MODEL_IDS": " a , b ,"}) == ["a", "b"]
    assert model_ids({"GEMINI_MODEL_IDS": " , "}) == DEFAULT_MODEL_IDS.split(",")


def test_build_model_raises_with_setup_instructions(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        build_model()


def test_build_model_returns_a_gemini_model_for_the_first_id_by_default(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    monkeypatch.delenv("GEMINI_MODEL_IDS", raising=False)
    model = build_model()
    assert type(model).__name__ == "GeminiModel"
    assert model.config["model_id"] == "gemini-3.8-flash"
    assert provider_label(model) == "gemini:gemini-3.8-flash"


def test_build_model_takes_an_explicit_model_id(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    assert build_model("gemini-3.5-flash-lite").config["model_id"] == "gemini-3.5-flash-lite"


def test_build_model_pins_greedy_decoding_and_a_fixed_seed(monkeypatch):
    """Two runs of the same ledger must not disagree because the sampler rolled
    differently. Strands passes `params` straight into Gemini's
    GenerationConfig, so temperature 0 and a fixed seed are the whole fix."""
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    params = build_model().config["params"]
    assert params["temperature"] == 0
    assert params["top_p"] == 1
    assert isinstance(params["seed"], int)


def test_every_model_gets_its_own_params_dict(monkeypatch):
    """A shared dict would let one model's update_config change the others."""
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    first, second = build_model("a"), build_model("b")
    assert first.config["params"] is not second.config["params"]
