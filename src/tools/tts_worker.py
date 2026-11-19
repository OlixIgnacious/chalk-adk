"""Local TTS generator using Kokoro-ONNX v1.0 with seamless multi-voice blending.

Supports weighted style interpolation:
e.g., "af_heart:0.7,af_bella:0.3" (70% Heart + 30% Bella)
"""

import json
import os
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

DEFAULT_VOICE_ID = "af_heart:0.7,af_bella:0.3"

# Release URLs for Kokoro v1.0 (includes af_heart, af_bella, etc.)
KOKORO_V1_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_V1_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


def get_model_paths() -> tuple[Path, Path]:
    """Returns local paths for Kokoro ONNX model and voices binary."""
    cache_dir = Path.home() / ".cache" / "kokoro"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Prefer v1.0 weights
    v1_model = cache_dir / "kokoro-v1.0.onnx"
    v1_voices = cache_dir / "voices-v1.0.bin"
    if v1_model.exists() and v1_voices.exists():
        return v1_model, v1_voices

    # Fallback to v0.19 if already downloaded
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
    """Parses voice blend string into (voice_name, weight) tuples.

    Examples:
        "af_heart:0.7,af_bella:0.3" -> [("af_heart", 0.7), ("af_bella", 0.3)]
        "af_sarah"                   -> [("af_sarah", 1.0)]
        "af_heart:2+af_bella:1"     -> [("af_heart", 2.0), ("af_bella", 1.0)]
    """
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


def generate_audio_for_segment(
    narration: str,
    output_wav_path: str,
    voice_id: str = DEFAULT_VOICE_ID,
    speed: float = 1.0,
    auto_download: bool = True,
) -> Optional[str]:
    """Generates audio for a narration segment using Kokoro-ONNX and NumPy voice blending.

    Args:
        narration: Spoken text
        output_wav_path: Target .wav path
        voice_id: Name or blend formula (e.g. "af_heart:0.7,af_bella:0.3")
        speed: Speech rate multiplier (1.0 = normal)
        auto_download: Download model weights if missing

    Returns:
        Path to output WAV, or None if Kokoro is unavailable.
    """
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

        # Load Kokoro engine
        kokoro = Kokoro(str(model_path), str(voices_path))
        available_voices = kokoro.get_voices()

        blend_specs = parse_voice_blend(voice_id)

        # Compute blended style vector via linear interpolation
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
            # Fallback to first available
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
        print(f"   ✓ Generated: {out_path.name} ({duration:.1f}s, {sample_rate}Hz)")
        return str(out_path)

    except Exception as e:
        print(f"⚠️ TTS Generation failed or skipped: {e}")
        return None
