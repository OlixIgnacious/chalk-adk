"""Configuration settings, model routing, and rate pacing for Chalk-ADK.

Optimized for Google AI Studio Free Tier and open API fallback (Mistral, Groq).
"""

import os
import time
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Prevent LiteLLM from attempting network requests for cost maps on startup
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"


@dataclass
class ModelConfig:
    # Google Gemini Models (Primary)
    curator_model: str = os.getenv("CURATOR_MODEL", "gemini-3.5-flash-lite")
    writer_model: str = os.getenv("WRITER_MODEL", "gemini-3.8-flash")
    verifier_model: str = os.getenv("VERIFIER_MODEL", "gemini-3.8-flash")

    # API Keys
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    mistral_api_key: Optional[str] = os.getenv("MISTRAL_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")

    # Rate Limiting / Pacing (Seconds between API requests)
    # 4.5 seconds per request guarantees <= 13.3 RPM, comfortably below the 15 RPM cap.
    pacing_seconds: float = float(os.getenv("REQUEST_PACING_SECONDS", "4.5"))


config = ModelConfig()

# Global timestamp tracker for rate pacing
_last_request_time: float = 0.0


def pace_request(delay: Optional[float] = None) -> None:
    """Enforces rate pacing to safeguard against hitting free-tier 15 RPM limits."""
    global _last_request_time
    wait_target = delay if delay is not None else config.pacing_seconds
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < wait_target:
        sleep_duration = wait_target - elapsed
        time.sleep(sleep_duration)
    _last_request_time = time.time()


def get_agent_model(role: str, provider: str = "gemini"):
    """Returns the model string or LiteLlm wrapper based on provider preference.

    Args:
        role: 'curator', 'writer', or 'verifier'
        provider: 'gemini', 'mistral', 'groq', or 'openrouter'
    """
    if provider == "gemini":
        if role == "curator":
            return config.curator_model
        return config.writer_model

    # Use Google ADK LiteLlm for external providers
    try:
        from google.adk.models.lite_llm import LiteLlm
    except ImportError:
        # Fallback if LiteLlm is not directly imported
        LiteLlm = None

    if provider == "mistral":
        model_name = "mistral/codestral-latest" if role == "writer" else "mistral/mistral-small-latest"
        return LiteLlm(model=model_name) if LiteLlm else model_name

    if provider == "groq":
        model_name = "groq/llama-3.3-70b-versatile"
        return LiteLlm(model=model_name) if LiteLlm else model_name

    return config.writer_model

