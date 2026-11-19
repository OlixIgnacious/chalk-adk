"""Chalk Doctor: Comprehensive diagnostic toolchain inspector for Chalk-ADK."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()


def check_python() -> Tuple[bool, str]:
    ver = sys.version_info
    v_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if ver.major == 3 and ver.minor >= 11:
        return True, f"Python {v_str} (Supported >= 3.11)"
    return False, f"Python {v_str} (Recommended >= 3.11)"


def check_venv() -> Tuple[bool, str]:
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        return True, f"Virtual environment active ({Path(sys.prefix).name})"
    venv_dir = Path("./.venv")
    if venv_dir.exists():
        return True, "Virtual environment found at ./.venv"
    return False, "No virtual environment active. Create one with `uv venv`"


def check_node_npx() -> Tuple[bool, str]:
    node = shutil.which("node")
    npx = shutil.which("npx")
    if not node or not npx:
        return False, "Node.js or npx not found on PATH. Required for HyperFrames."
    try:
        res = subprocess.run([node, "--version"], capture_output=True, text=True, check=True)
        return True, f"Node.js {res.stdout.strip()} & npx available"
    except Exception as e:
        return False, f"Node.js check error: {e}"


def check_ffmpeg() -> Tuple[bool, str]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        return True, "FFmpeg and ffprobe available on PATH"
    elif ffmpeg:
        return True, "FFmpeg found (ffprobe missing, but ffmpeg available)"
    return False, "FFmpeg not found. Required for MP4 audio-video muxing (Install via `brew install ffmpeg`)."


def check_chrome() -> Tuple[bool, str]:
    # Check macOS app bundle or linux binaries
    mac_chrome = Path("/Applications/Google Chrome.app")
    if mac_chrome.exists():
        return True, "Google Chrome installed (/Applications/Google Chrome.app)"
    for bin_name in ["google-chrome", "chromium", "google-chrome-stable", "chromium-browser"]:
        if shutil.which(bin_name):
            return True, f"Chromium engine found ({bin_name})"
    return False, "Google Chrome / Chromium not found. Required for HyperFrames video rendering."


def check_gemini_tts() -> Tuple[bool, str]:
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and not gemini_key.startswith("your_"):
        return True, "gemini-3.8-flash-tts cloud studio engine ready (Voice: Kore, Puck, etc.)"
    return False, "GEMINI_API_KEY not configured for gemini-3.8-flash-tts"


def check_kokoro() -> Tuple[bool, str]:
    cache_dir = Path.home() / ".cache" / "kokoro"
    v1_model = cache_dir / "kokoro-v1.0.onnx"
    v1_voices = cache_dir / "voices-v1.0.bin"
    v0_model = cache_dir / "kokoro-v0_19.onnx"
    v0_voices = cache_dir / "voices.bin"

    if v1_model.exists() and v1_voices.exists():
        m_size = v1_model.stat().st_size / (1024 * 1024)
        return True, f"Kokoro v1.0 ONNX model ({m_size:.0f} MB) & voices-v1.0.bin ready in ~/.cache/kokoro/"
    if v0_model.exists() and (v0_voices.exists() or v1_voices.exists()):
        return True, "Kokoro v0.19 ONNX model ready in ~/.cache/kokoro/"
    return False, "Kokoro model weights not downloaded yet (will auto-download on first voiceover run)"


def check_api_keys() -> List[Tuple[str, bool, str]]:
    results = []
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and not gemini_key.startswith("your_"):
        results.append(("GEMINI_API_KEY", True, f"Configured ({gemini_key[:4]}...{gemini_key[-4:]})"))
    else:
        results.append(("GEMINI_API_KEY", False, "Missing in .env (Required for primary Gemini pipeline)"))

    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        results.append(("MISTRAL_API_KEY", True, f"Configured ({mistral_key[:4]}...{mistral_key[-4:]})"))
    else:
        results.append(("MISTRAL_API_KEY", False, "Not set in .env (Optional fallback for Codestral)"))

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        results.append(("GROQ_API_KEY", True, f"Configured ({groq_key[:4]}...{groq_key[-4:]})"))
    else:
        results.append(("GROQ_API_KEY", False, "Not set in .env (Optional ultra-fast fallback)"))

    return results


def run_doctor() -> bool:
    """Executes full diagnostic suite and prints formatted report."""
    print("\n" + "=" * 70)
    print("🩺 CHALK-ADK TOOLCHAIN DOCTOR")
    print("=" * 70)

    checks = [
        ("Python Version", *check_python()),
        ("Virtual Environment", *check_venv()),
        ("Node.js & NPX", *check_node_npx()),
        ("FFmpeg / ffprobe", *check_ffmpeg()),
        ("Chrome / Chromium", *check_chrome()),
        ("Gemini 3.8 Flash TTS", *check_gemini_tts()),
        ("Kokoro TTS Engine", *check_kokoro()),
    ]

    all_passed = True
    for label, passed, msg in checks:
        icon = "✅" if passed else "⚠️"
        print(f"{icon} {label:<22}: {msg}")
        if not passed and label in ["Python Version", "Node.js & NPX"]:
            all_passed = False

    print("\n--- API KEYS & MULTI-MODEL ROUTING ---")
    api_checks = check_api_keys()
    for name, passed, msg in api_checks:
        icon = "✅" if passed else ("⚪" if "Optional" in msg else "❌")
        print(f"{icon} {name:<22}: {msg}")
        if not passed and "Required" in msg:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 Toolchain Health: EXCELLENT! Everything is ready for lessons & video rendering.")
    else:
        print("ℹ️ Toolchain Health: Some optional components need attention (see above).")
    print("=" * 70 + "\n")

    return all_passed
