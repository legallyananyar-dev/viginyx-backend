from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
from app.core.config import settings
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm(temperature: float = 0.0, **kwargs) -> BaseChatModel:
    """
    Factory function to get the configured LLM based on environment settings.
    """
    provider = settings.llm_provider.lower()
    
    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=settings.llm_model, 
            temperature=temperature,
            api_key=settings.google_api_key,
            **kwargs
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=settings.llm_model, 
            temperature=temperature,
            api_key=settings.chat_gpt_api_key,
            **kwargs
        )
    elif provider == "grok":
        return ChatXAI(
            model=settings.llm_model,
            temperature=temperature,
            api_key=settings.grok_api_key,
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
