"""Configuration settings, model routing, rate pacing, and resilience fallback for Chalk-ADK."""

import os
import time
import json
from dataclasses import dataclass
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

# Prevent LiteLLM from attempting network requests for cost maps on startup
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"


@dataclass
class ModelConfig:
    # Google Gemini Models (Primary)
    curator_model: str = os.getenv("CURATOR_MODEL", "gemini-3.1-flash-lite")
    writer_model: str = os.getenv("WRITER_MODEL", "gemini-3.8-flash")
    verifier_model: str = os.getenv("VERIFIER_MODEL", "gemini-3.8-flash")

    # API Keys
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    mistral_api_key: Optional[str] = os.getenv("MISTRAL_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")

    # Rate Limiting / Pacing (Seconds between API requests)
    pacing_seconds: float = float(os.getenv("REQUEST_PACING_SECONDS", "3.0"))

    # Audio & Narration (Kokoro TTS with voice blending)
    tts_provider: str = os.getenv("TTS_PROVIDER", "kokoro")
    tts_voice_id: str = os.getenv("TTS_VOICE_ID", "af_heart:0.7,af_bella:0.3")


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


def generate_structured_output(
    prompt: str,
    response_schema: Any,
    role: str = "writer",
    provider: str = "gemini",
    temperature: float = 0.3,
) -> dict:
    """Invokes LLM with structured JSON output and automatic fallback on high demand (503/429)."""
    pace_request()

    if provider == "gemini":
        from google import genai
        from google.genai import types

        primary_model = config.curator_model if role == "curator" else config.writer_model
        # Candidate cascade: primary -> gemini-3.1-flash-lite -> gemini-3.5-flash-lite
        candidates = list(dict.fromkeys([primary_model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]))

        last_error = None
        for model in candidates:
            try:
                client = genai.Client(api_key=config.gemini_api_key)
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=temperature,
                    ),
                )
                return json.loads(response.text)
            except Exception as e:
                err_msg = str(e)
                if any(x in err_msg for x in ["503", "UNAVAILABLE", "high demand", "429"]):
                    print(f"   ⚠️ Model '{model}' temporarily busy. Cascading to fallback...")
                    last_error = e
                    continue
                raise e

        # If all Gemini models are busy, try Mistral or Groq if keys are present
        if config.mistral_api_key:
            print("   ⚠️ Gemini experiencing high demand. Seamlessly routing to Mistral (Codestral)...")
            return _generate_via_litellm(prompt, response_schema, "mistral/codestral-latest", config.mistral_api_key)

        if config.groq_api_key:
            print("   ⚠️ Gemini experiencing high demand. Seamlessly routing to Groq (Qwen)...")
            return _generate_via_litellm(prompt, response_schema, "groq/qwen/qwen3.8-27b", config.groq_api_key)

        raise last_error

    elif provider == "mistral":
        model_name = "mistral/codestral-latest"
        return _generate_via_litellm(prompt, response_schema, model_name, config.mistral_api_key)

    elif provider == "groq":
        model_name = "groq/qwen/qwen3.8-27b"
        return _generate_via_litellm(prompt, response_schema, model_name, config.groq_api_key)

    raise ValueError(f"Unknown provider: {provider}")


def _generate_via_litellm(prompt: str, response_schema: Any, model: str, api_key: Optional[str]) -> dict:
    """Helper to generate structured JSON using LiteLLM."""
    import litellm
    litellm.suppress_debug_info = True

    schema_json = json.dumps(response_schema.model_json_schema())
    system_instruction = (
        f"You must strictly output valid JSON adhering to the following JSON schema:\n{schema_json}\n"
        "Do not wrap your response in markdown code fences. Output raw JSON only."
    )

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        api_key=api_key,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    # Clean possible markdown wrapping if returned
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())
