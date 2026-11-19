"""HyperFrames Video Renderer: Exports animated code and diagram scenes into deterministic MP4 videos."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from src.schemas.lesson import LessonSegment, LessonSpec


HYPERFRAMES_COMPOSITION_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1920, height=1080, initial-scale=1.0">
  <title>{{ segment_title }}</title>
  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- GSAP Animation Engine -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <style>
    body {
      margin: 0;
      padding: 0;
      width: 1920px;
      height: 1080px;
      background-color: #020617;
      color: #f8fafc;
      overflow: hidden;
      font-family: ui-sans-serif, system-ui, sans-serif;
    }
    {{ custom_css }}
  </style>
</head>
<body class="flex items-center justify-center p-16">
  <div class="w-full h-full flex flex-col justify-between">
    <!-- Header Banner -->
    <div class="flex items-center justify-between border-b border-slate-800 pb-6">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-2xl text-white shadow-xl shadow-indigo-600/30">
          ⚡
        </div>
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-widest text-indigo-400">CHALK-ADK LESSON</h2>
          <h1 class="text-3xl font-extrabold text-slate-100 mt-1">{{ segment_title }}</h1>
        </div>
      </div>
      <div class="px-4 py-2 rounded-lg bg-slate-900 border border-slate-800 text-sm font-mono text-slate-400">
        Segment {{ segment_order }}
      </div>
    </div>

    <!-- Main Visual Canvas (Animated via GSAP) -->
    <div id="hyperframes-canvas" class="flex-1 my-8 flex items-center justify-center">
      {{ scene_html }}
    </div>

    <!-- Subtitle / Caption Footer -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 text-xl text-slate-300 leading-relaxed text-center shadow-2xl">
      "{{ narration_text }}"
    </div>
  </div>

  <script>
    // Initialize HyperFrames GSAP timeline (paused for frame-by-frame deterministic seeking)
    const tl = gsap.timeline({ paused: true, defaults: { ease: "power2.out" } });
    
    // Register timeline with HyperFrames headless renderer
    window.__timelines = window.__timelines || {};
    window.__timelines["default"] = tl;
    window.__timelines["main"] = tl;
    window.__timeline = tl;
    
    // Injected segment animation timeline
    {{ gsap_script }}
  </script>
</body>
</html>
"""


def prepare_hyperframes_project(segment: LessonSegment, output_dir: Path) -> Path:
    """Prepares a HyperFrames project folder for a given segment with HTML and GSAP code."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine HTML & GSAP source
    import re
    if segment.hyperframe:
        scene_html = segment.hyperframe.html
        custom_css = segment.hyperframe.css or ""
        raw_script = segment.hyperframe.gsap_timeline or ""
        gsap_script = re.sub(r"\b(const|let|var)\s+tl\s*=\s*gsap\.timeline\([^)]*\);?", "", raw_script)
    else:
        # Fallback to visual block
        v = segment.visuals[0] if segment.visuals else None
        title = v.title if v else "Concept Overview"
        content = v.content if v else segment.title
        scene_html = f"""
        <div id="card" class="p-10 bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full shadow-2xl">
          <h3 class="text-2xl font-bold text-indigo-400 mb-4">{title}</h3>
          <pre class="bg-slate-950 p-6 rounded-xl font-mono text-lg text-slate-200 overflow-hidden"><code>{content}</code></pre>
        </div>
        """
        custom_css = ""
        gsap_script = 'tl.from("#card", { opacity: 0, scale: 0.9, duration: 1 });'

    rendered_html = (
        HYPERFRAMES_COMPOSITION_TEMPLATE.replace("{{ segment_title }}", segment.title)
        .replace("{{ segment_order }}", str(segment.order))
        .replace("{{ narration_text }}", segment.narration)
        .replace("{{ custom_css }}", custom_css)
        .replace("{{ scene_html }}", scene_html)
        .replace("{{ gsap_script }}", gsap_script)
    )

    index_html = output_dir / "index.html"
    with open(index_html, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    return output_dir


def render_segment_to_video(
    segment: LessonSegment,
    lesson_root: Path,
    output_mp4: Optional[Path] = None,
    fps: int = 60,
) -> Optional[Path]:
    """Renders a single segment to MP4 using npx hyperframes render."""
    project_dir = lesson_root / "hyperframes" / f"seg-{segment.order}"
    prepare_hyperframes_project(segment, project_dir)

    target_mp4 = output_mp4 or (lesson_root / "videos" / f"seg-{segment.order}.mp4")
    target_mp4.parent.mkdir(parents=True, exist_ok=True)

    print(f"🎬 [HyperFrames] Rendering Segment {segment.order} ({segment.title}) -> {target_mp4.name}...")

    cmd = [
        "npx",
        "hyperframes",
        "render",
        str(project_dir),
        "--output",
        str(target_mp4),
        "--format",
        "mp4",
        "--fps",
        str(fps),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"   ✓ Rendered: {target_mp4}")
        return target_mp4
    except FileNotFoundError:
        print("❌ Error: 'npx' command not found. Ensure Node.js is installed.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"⚠️ HyperFrames render error:\n{e.stderr or e.stdout}")
        return None


def render_all_segments(spec: LessonSpec, lesson_root: Path, fps: int = 60) -> list[Path]:
    """Renders all segments of a lesson spec into MP4 video files."""
    rendered = []
    for seg in spec.segments:
        mp4_path = render_segment_to_video(seg, lesson_root, fps=fps)
        if mp4_path and mp4_path.exists():
            rendered.append(mp4_path)
    return rendered
