import pytest

from ninetyninety.config import bedrock_configured, build_model, provider_label


def test_bedrock_configured_needs_both_keys():
    assert bedrock_configured({"AWS_ACCESS_KEY_ID": "a", "AWS_SECRET_ACCESS_KEY": "b"})
    assert not bedrock_configured({"AWS_ACCESS_KEY_ID": "a"})
    assert not bedrock_configured({})


def test_build_model_raises_with_setup_instructions(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    with pytest.raises(RuntimeError, match="AWS_ACCESS_KEY_ID"):
        build_model()


def test_build_model_returns_a_bedrock_model_with_region_and_default_profile(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "a")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "b")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    model = build_model()
    assert type(model).__name__ == "BedrockModel"
    assert model.config["model_id"]  # SDK default Claude inference profile
    assert provider_label(model) == f"bedrock:{model.config['model_id']}"


def test_build_model_honours_bedrock_model_id_override(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "a")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "b")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
    assert build_model().config["model_id"] == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
