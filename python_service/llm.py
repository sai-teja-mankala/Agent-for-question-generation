import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _get_env_value(primary_key: str, fallback_key: str) -> str | None:
    return os.getenv(primary_key) or os.getenv(fallback_key)


def _require_env(keys: list[str]) -> None:
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")


def build_client() -> OpenAI:
    # Prefer generic OpenAI-style env vars when present to allow easy switching.
    endpoint = _get_env_value("OPENAI_BASE_URL", "AZURE_OPENAI_ENDPOINT")
    api_key = _get_env_value("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY")

    if os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_KEY"):
        _require_env(["OPENAI_BASE_URL", "OPENAI_API_KEY"])
    else:
        _require_env(["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"])

    return OpenAI(base_url=endpoint, api_key=api_key)


def get_deployment_name() -> str:
    deployment = _get_env_value("OPENAI_MODEL", "AZURE_OPENAI_DEPLOYMENT")
    if not deployment:
        raise RuntimeError(
            "Missing environment variables: OPENAI_MODEL or AZURE_OPENAI_DEPLOYMENT"
        )
    return deployment
