"""Local TTS generator using Kokoro-ONNX with graceful fallback."""

import os
from pathlib import Path
from typing import Optional

KOKORO_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
KOKORO_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json"


def get_model_paths() -> tuple[Path, Path]:
    """Returns local paths for Kokoro ONNX model and voices JSON."""
    cache_dir = Path.home() / ".cache" / "kokoro"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "kokoro-v0_19.onnx", cache_dir / "voices.json"


def is_kokoro_available() -> bool:
    """Checks if kokoro-onnx package and model weights are installed."""
    try:
        import kokoro_onnx
        import soundfile
        model_path, voices_path = get_model_paths()
        return model_path.exists() and voices_path.exists()
    except ImportError:
        return False


def generate_audio_for_segment(
    narration: str,
    output_wav_path: str,
    voice: str = "af_sarah",
    speed: float = 1.0,
) -> Optional[str]:
    """Generates audio for a narration segment using Kokoro-ONNX.

    Returns the path to the generated WAV file, or None if Kokoro is unavailable.
    """
    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf

        model_path, voices_path = get_model_paths()
        if not model_path.exists() or not voices_path.exists():
            print("ℹ️  Kokoro model files not found locally.")
            print(f"   Download them to {model_path.parent} to enable local studio voice generation.")
            return None

        kokoro = Kokoro(str(model_path), str(voices_path))
        samples, sample_rate = kokoro.create(
            narration,
            voice=voice,
            speed=speed,
            lang="en-us",
        )

        out_path = Path(output_wav_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), samples, sample_rate)
        return str(out_path)

    except Exception as e:
        print(f"⚠️  TTS Generation skipped: {e}")
        return None

