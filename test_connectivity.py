"""Test script to verify API key presence and live connectivity across configured providers."""

import os
from dotenv import load_dotenv

load_dotenv()


def mask_key(key: str | None) -> str:
    if not key:
        return "[MISSING]"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def test_keys():
    print("=" * 60)
    print("🔑 CHECKING CONFIGURED API KEYS")
    print("=" * 60)
    keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    }
    for name, val in keys.items():
        status = "✅ Found" if val and not val.startswith("your_") else "⚪ Not set"
        print(f"  {name:20}: {status:10} ({mask_key(val)})")
    print()
    return keys


def test_gemini(api_key: str):
    print("Testing Google Gemini (gemini-3.5-flash-lite)...")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents="Respond with 'Gemini OK' and nothing else.",
        )
        print(f"  ✅ Gemini Response: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"  ❌ Gemini Error: {e}")
        return False


def test_litellm_provider(provider_name: str, model_name: str, api_key: str):
    print(f"Testing {provider_name} ({model_name})...")
    try:
        import litellm
        litellm.suppress_debug_info = True
        response = litellm.completion(
            model=model_name,
            messages=[{"role": "user", "content": f"Respond with '{provider_name} OK' and nothing else."}],
            api_key=api_key,
            max_tokens=20,
        )
        content = response.choices[0].message.content
        print(f"  ✅ {provider_name} Response: {content.strip()}")
        return True
    except Exception as e:
        print(f"  ❌ {provider_name} Error: {e}")
        return False


def main():
    keys = test_keys()

    if keys.get("GEMINI_API_KEY"):
        test_gemini(keys["GEMINI_API_KEY"])

    if keys.get("MISTRAL_API_KEY"):
        test_litellm_provider("Mistral", "mistral/mistral-small-latest", keys["MISTRAL_API_KEY"])

    if keys.get("GROQ_API_KEY"):
        test_litellm_provider("Groq", "groq/llama-3.3-70b-versatile", keys["GROQ_API_KEY"])

    if keys.get("OPENROUTER_API_KEY"):
        test_litellm_provider("OpenRouter", "openrouter/meta-llama/llama-3.3-70b-instruct:free", keys["OPENROUTER_API_KEY"])


if __name__ == "__main__":
    main()

