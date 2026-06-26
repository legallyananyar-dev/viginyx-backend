from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
from api.core.config import settings
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm(temperature: float = 0.0, **kwargs) -> BaseChatModel:
    """
    Factory function to get the configured LLM based on environment settings.
    """
    provider = settings.llm_provider.lower()
    
    # Provide a generous default max_tokens to prevent LengthFinishReasonError
    # when using structured outputs or returning large content.
    
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
    elif provider == "lightning-vllm":
        # Using ChatOpenAI because vLLM exposes an OpenAI-compatible API
        return ChatOpenAI(
            model="Qwen/Qwen2.5-7B-Instruct-AWQ",  # Must match the model running on the server
            temperature=temperature,
            api_key="not-needed",                  # vLLM doesn't require a key by default
            base_url="https://8000-01krc32prg8r3e6sd3v76vscg9.cloudspaces.litng.ai/v1", # Your Studio public URL + /v1
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
