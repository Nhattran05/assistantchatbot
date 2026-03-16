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

        provider = provider or llm_config.get("default_provider", "openai")
        model = model or llm_config.get("default_model", "gpt-4o-mini")

        match provider:
            case "openai":
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(model=model, temperature=temperature, **kwargs)
            case "anthropic":
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(model=model, temperature=temperature, **kwargs)
            case "google":
                from langchain_google_genai import ChatGoogleGenerativeAI

                return ChatGoogleGenerativeAI(model=model, temperature=temperature, **kwargs)
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
