"""TTS Generator supporting Google Gemini 3.8 Flash TTS and local Kokoro-ONNX."""

import json
import os
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

DEFAULT_KOKORO_VOICE = "af_heart:0.7,af_bella:0.3"
DEFAULT_GEMINI_VOICE = "Kore"

# Release URLs for Kokoro v1.0
KOKORO_V1_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_V1_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


def get_model_paths() -> tuple[Path, Path]:
    """Returns local paths for Kokoro ONNX model and voices binary."""
    cache_dir = Path.home() / ".cache" / "kokoro"
    cache_dir.mkdir(parents=True, exist_ok=True)

    v1_model = cache_dir / "kokoro-v1.0.onnx"
    v1_voices = cache_dir / "voices-v1.0.bin"
    if v1_model.exists() and v1_voices.exists():
        return v1_model, v1_voices

    v0_model = cache_dir / "kokoro-v0_19.onnx"
    v0_voices = cache_dir / "voices.bin"
    if v0_model.exists() and v0_voices.exists():
        return v0_model, v0_voices

    return v1_model, v1_voices


def ensure_kokoro_weights() -> bool:
    """Checks for Kokoro ONNX model and voices binary, downloading if missing."""
    model_path, voices_path = get_model_paths()

    if model_path.exists() and voices_path.exists():
        return True

    print("📥 Kokoro v1.0 weights not found locally. Downloading model (~310 MB) and voices-v1.0.bin...")
    try:
        if not voices_path.exists():
            print("   Downloading voices-v1.0.bin...")
            urllib.request.urlretrieve(KOKORO_V1_VOICES_URL, str(voices_path))

        if not model_path.exists():
            print("   Downloading kokoro-v1.0.onnx...")
            urllib.request.urlretrieve(KOKORO_V1_MODEL_URL, str(model_path))

        print("✓ Kokoro weights downloaded successfully.")
        return True
    except Exception as e:
        print(f"⚠️ Could not auto-download Kokoro weights: {e}")
        return False


def is_kokoro_available() -> bool:
    """Checks if kokoro-onnx package is installed and weights exist."""
    try:
        import kokoro_onnx
        import soundfile
        import numpy
        model_path, voices_path = get_model_paths()
        return model_path.exists() and voices_path.exists()
    except ImportError:
        return False


def parse_voice_blend(voice_id: str) -> List[Tuple[str, float]]:
    """Parses voice blend string into (voice_name, weight) tuples."""
    clean_str = voice_id.replace("+", ",").strip()
    parts = [p.strip() for p in clean_str.split(",") if p.strip()]
    result = []

    for part in parts:
        if ":" in part:
            name, weight_str = part.split(":", 1)
            try:
                weight = float(weight_str.strip())
            except ValueError:
                weight = 1.0
            result.append((name.strip(), weight))
        else:
            result.append((part.strip(), 1.0))

    return result or [("af_heart", 0.7), ("af_bella", 0.3)]


def generate_gemini_tts(
    narration: str,
    output_wav_path: str,
    voice_name: str = DEFAULT_GEMINI_VOICE,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """Generates studio voice narration using Google's gemini-3.8-flash-tts model."""
    try:
        from google import genai
        from google.genai import types

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            print("⚠️ Cannot use gemini-3.8-flash-tts: GEMINI_API_KEY is not set.")
            return None

        # Gemini audio generation currently operates under v1beta
        client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config={
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": voice_name
                    }
                }
            },
        )

        print(f"🎙️ [Gemini TTS] Synthesizing segment with gemini-3.8-flash-tts (Voice: '{voice_name}')...")
        response = client.models.generate_content(
            model="gemini-3.8-flash-tts",
            contents=narration,
            config=config,
        )

        candidate = response.candidates[0]
        part = candidate.content.parts[0]
        audio_bytes = part.inline_data.data

        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        print(f"   ✓ Generated with Gemini TTS: {out_path.name} ({len(audio_bytes) / 1024:.1f} KB)")
        return str(out_path)

    except Exception as e:
        print(f"⚠️ Gemini TTS generation error: {e}")
        return None


def generate_kokoro_tts(
    narration: str,
    output_wav_path: str,
    voice_id: str = DEFAULT_KOKORO_VOICE,
    speed: float = 1.0,
    auto_download: bool = True,
) -> Optional[str]:
    """Generates audio for a narration segment using Kokoro-ONNX and NumPy voice blending."""
    try:
        import numpy as np

        # Safe monkeypatch for NumPy 2.x allow_pickle default
        orig_load = np.load
        np.load = lambda *a, **kw: orig_load(*a, **{**kw, "allow_pickle": True})

        from kokoro_onnx import Kokoro
        import soundfile as sf

        model_path, voices_path = get_model_paths()

        if not (model_path.exists() and voices_path.exists()):
            if auto_download:
                ok = ensure_kokoro_weights()
                if not ok:
                    return None
            else:
                return None

        kokoro = Kokoro(str(model_path), str(voices_path))
        available_voices = kokoro.get_voices()
        blend_specs = parse_voice_blend(voice_id)

        style_vectors = []
        total_weight = 0.0

        for name, weight in blend_specs:
            if name in available_voices:
                style = kokoro.get_voice_style(name)
                style_vectors.append(style * weight)
                total_weight += weight
            else:
                print(f"⚠️ Voice '{name}' not found. Available voices: {available_voices[:5]}...")

        if not style_vectors:
            first = available_voices[0]
            blended_style = kokoro.get_voice_style(first)
        else:
            blended_style = sum(style_vectors) / (total_weight if total_weight > 0 else 1.0)

        print(f"🎙️ [Kokoro] Synthesizing segment with blended voice '{voice_id}'...")
        samples, sample_rate = kokoro.create(
            narration,
            voice=blended_style,
            speed=speed,
            lang="en-us",
        )

        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), samples, sample_rate)
        duration = len(samples) / sample_rate
        print(f"   ✓ Generated with Kokoro: {out_path.name} ({duration:.1f}s, {sample_rate}Hz)")
        return str(out_path)

    except Exception as e:
        print(f"⚠️ Kokoro TTS generation error: {e}")
        return None


def generate_audio_for_segment(
    narration: str,
    output_wav_path: str,
    provider: str = "gemini",
    voice_id: Optional[str] = None,
    speed: float = 1.0,
) -> Optional[str]:
    """Unified entry point for segment audio generation.

    Args:
        narration: Spoken text
        output_wav_path: Destination .wav file
        provider: 'gemini' (uses gemini-3.8-flash-tts) or 'kokoro' (local CPU engine)
        voice_id: Voice name (e.g. 'Kore', 'Puck' for Gemini; 'af_heart:0.7,af_bella:0.3' for Kokoro)
    """
    if provider == "gemini":
        voice = voice_id or DEFAULT_GEMINI_VOICE
        res = generate_gemini_tts(narration, output_wav_path, voice_name=voice)
        if res:
            return res
        print("   ⚠️ Gemini TTS fallback -> trying local Kokoro TTS...")

    # Kokoro (either primary or fallback)
    voice = voice_id if (voice_id and provider == "kokoro") else DEFAULT_KOKORO_VOICE
    return generate_kokoro_tts(narration, output_wav_path, voice_id=voice, speed=speed)
