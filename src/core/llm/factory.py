import os

from langchain_core.language_models import BaseChatModel


class LLMFactory:
    @staticmethod
    def create(
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> BaseChatModel:
        from src.utils import load_config

        config = load_config()
        llm_config = config.get("llm", {})

        provider = provider or llm_config.get("default_provider", "mega_llm")
        model = model or llm_config.get("default_model", "openai-gpt-oss-120b")

        match provider:
            case "mega_llm":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model="openai-gpt-oss-120b",
                    base_url="https://ai.megallm.io/v1",
                    api_key = os.getenv("MEGALLM_API_KEY"),
                    temperature= 0.2
                )
            case _:
                raise ValueError(f"LLM provider '{provider}' is not supported.")
