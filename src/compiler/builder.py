"""Compiler & Builder: Assembles audio assets, JSON spec, and HTML template into a distributable web lesson."""

import json
from pathlib import Path
from jinja2 import Template

from src.schemas.lesson import LessonSpec
from src.tools.tts_worker import generate_audio_for_segment, is_kokoro_available


def compile_lesson(spec: LessonSpec, output_root: str = "./dist", skip_tts: bool = False) -> Path:
    """Compiles the LessonSpec into a standalone interactive web application.

    1. (Optional) Generates segment audio using Kokoro TTS into dist/<lesson_id>/audio/
    2. Injects LessonSpec into the HTML5 interactive lesson template.
    3. Emits self-contained `lesson.html`.

    Returns:
        Path to compiled lesson.html
    """
    lesson_dir = Path(output_root).resolve() / spec.lesson_id
    audio_dir = lesson_dir / "audio"
    lesson_dir.mkdir(parents=True, exist_ok=True)

    # 1. Audio generation
    kokoro_ready = is_kokoro_available()
    if not skip_tts and kokoro_ready:
        audio_dir.mkdir(exist_ok=True)
        print(f"🎙️ Generating voiceover audio for {len(spec.segments)} segments with Kokoro-ONNX...")
        for seg in spec.segments:
            wav_name = f"seg-{seg.order}.wav"
            target_wav = audio_dir / wav_name
            generated_path = generate_audio_for_segment(seg.narration, str(target_wav))
            if generated_path:
                seg.audio_file = f"./audio/{wav_name}"
    else:
        print("ℹ️ Audio generation skipped or Kokoro offline. HTML player will use Web Speech Synthesizer fallback.")

    # 2. Render Template
    template_path = Path(__file__).parent / "template" / "index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    template = Template(template_content)
    rendered_html = template.render(
        lesson=spec,
        lesson_json=json.dumps(spec.model_dump(), indent=2),
    )

    # 3. Output files
    html_out = lesson_dir / "lesson.html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    # Also save spec.json for reference
    json_out = lesson_dir / "spec.json"
    with open(json_out, "w", encoding="utf-8") as f:
        f.write(spec.model_dump_json(indent=2))

    print(f"\n🎉 Lesson compiled successfully!")
    print(f"👉 Standalone Web App: file://{html_out}")
    return html_out

