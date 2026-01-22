import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def build_client() -> OpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    missing = [
        key
        for key in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
        if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    return OpenAI(base_url=endpoint, api_key=api_key)


def get_deployment_name() -> str:
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not deployment:
        raise RuntimeError("Missing environment variables: AZURE_OPENAI_DEPLOYMENT")
    return deployment
