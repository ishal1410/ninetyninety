"""One model provider: Amazon Bedrock, through Strands' native BedrockModel.

Credentials come from the standard AWS environment (AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY, AWS_REGION). BEDROCK_MODEL_ID optionally overrides the
SDK's default cross-region Claude inference profile.
"""
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_REGION = "us-east-1"


def bedrock_configured(env: dict) -> bool:
    return bool(env.get("AWS_ACCESS_KEY_ID") and env.get("AWS_SECRET_ACCESS_KEY"))


def build_model():
    if not bedrock_configured(os.environ):
        raise RuntimeError(
            "Amazon Bedrock is not configured. Set AWS_ACCESS_KEY_ID and "
            "AWS_SECRET_ACCESS_KEY (and AWS_REGION, default us-east-1) in .env. "
            "See .env.example.")
    from strands.models import BedrockModel
    kwargs = {"region_name": os.environ.get("AWS_REGION", DEFAULT_REGION)}
    if os.environ.get("BEDROCK_MODEL_ID"):
        kwargs["model_id"] = os.environ["BEDROCK_MODEL_ID"]
    return BedrockModel(**kwargs)


def provider_label(model) -> str:
    """What the trace shows for the provider that answered a batch."""
    model_id = getattr(model, "config", {}).get("model_id", "?")
    return f"bedrock:{model_id}"
