"""Chalk-ADK CLI Entrypoint: Create, review, preview, and render HyperFrames videos."""

import argparse
import http.server
import json
import socketserver
import sys
import webbrowser
from functools import partial
from pathlib import Path

from src.workflow import run_lesson_pipeline
from src.compiler.builder import compile_lesson
from src.compiler.video_renderer import render_all_segments, render_segment_to_video
from src.schemas.lesson import LessonSpec


def serve_and_preview(file_path: Path):
    """Starts a local HTTP server and opens the browser, bypassing all file:/// origin restrictions."""
    target = file_path.resolve()
    directory = target.parent
    filename = target.name

    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))

    server = None
    port = 8765
    for p in range(8765, 8800):
        try:
            server = socketserver.TCPServer(("127.0.0.1", p), handler)
            port = p
            break
        except OSError:
            continue

    if not server:
        print(f"Opening via file URI: {target.as_uri()}")
        webbrowser.open(target.as_uri())
        return

    url = f"http://127.0.0.1:{port}/{filename}"
    print(f"\n🚀 Serving interactive lesson locally at: {url}")
    print("   ✓ Local server active (speech synthesis, GSAP, and CDN assets fully supported)")
    print("   Press Ctrl+C to stop the preview server.\n")

    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPreview server stopped.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="Chalk-ADK: Grounded interactive lessons and HyperFrames video generator"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: create
    create_parser = subparsers.add_parser("create", help="Create an interactive lesson from a source document")
    create_parser.add_argument("source", type=str, help="Path to source document (Markdown, TXT, or PDF)")
    create_parser.add_argument(
        "--output-dir",
        type=str,
        default="./dist",
        help="Directory to save compiled lesson (default: ./dist)",
    )
    create_parser.add_argument(
        "--provider",
        type=str,
        default="gemini",
        choices=["gemini", "mistral", "groq"],
        help="LLM provider (default: gemini)",
    )
    create_parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip the human review gate and automatically compile",
    )
    create_parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="Skip Kokoro TTS generation (player will use Web Speech Synthesizer fallback)",
    )
    create_parser.add_argument(
        "--page-range",
        type=str,
        default=None,
        help="Specific PDF page range to extract (e.g. '1-20' or '15-30') for large documents",
    )
    create_parser.add_argument(
        "--allow-suspicious",
        action="store_true",
        help="Bypass security warnings for PDFs containing embedded action scripts or attachments",
    )

    # Command: preview
    preview_parser = subparsers.add_parser("preview", help="Preview a compiled lesson in your default browser")
    preview_parser.add_argument("lesson_file", type=str, help="Path to lesson.html")

    # Command: render-video
    video_parser = subparsers.add_parser(
        "render-video",
        help="Compile HyperFrames scene animations into MP4 video files via npx hyperframes render",
    )
    video_parser.add_argument(
        "target",
        type=str,
        help="Path to lesson spec JSON or lesson folder (e.g. dist/architecting-multi-agent-systems-adk)",
    )
    video_parser.add_argument(
        "--segment",
        type=int,
        default=None,
        help="Specific segment number to render (default: render all segments)",
    )
    video_parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Render frame rate (default: 60)",
    )

    args = parser.parse_args()

    if args.command == "create":
        source_path = Path(args.source).resolve()
        if not source_path.exists():
            print(f"Error: Source file does not exist: {source_path}", file=sys.stderr)
            sys.exit(1)

        # 1. Run multi-agent pipeline
        spec = run_lesson_pipeline(
            source_path=str(source_path),
            output_dir=args.output_dir,
            provider=args.provider,
            auto_approve=args.auto_approve,
            page_range=args.page_range,
            allow_suspicious=args.allow_suspicious,
        )

        # 2. Compile to HTML & Audio
        html_path = compile_lesson(
            spec=spec,
            output_root=args.output_dir,
            skip_tts=args.skip_tts,
        )
        print(f"\n💡 To open and view your lesson, run:\n   python -m src.cli preview {html_path}\n")

    elif args.command == "preview":
        target = Path(args.lesson_file).resolve()
        if not target.exists():
            print(f"Error: Lesson file does not exist: {target}", file=sys.stderr)
            sys.exit(1)
        serve_and_preview(target)

    elif args.command == "render-video":
        target_path = Path(args.target).resolve()
        spec_file = None

        if target_path.is_file() and target_path.suffix == ".json":
            spec_file = target_path
            lesson_root = target_path.parent / target_path.stem
        elif target_path.is_dir():
            possible_spec = target_path / "spec.json"
            if possible_spec.exists():
                spec_file = possible_spec
            lesson_root = target_path
        else:
            json_candidate = target_path.with_suffix(".json")
            if json_candidate.exists():
                spec_file = json_candidate
                lesson_root = target_path

        if not spec_file or not spec_file.exists():
            print(f"Error: Could not locate lesson spec JSON at: {args.target}", file=sys.stderr)
            sys.exit(1)

        with open(spec_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        spec = LessonSpec.model_validate(data)

        if args.segment:
            matching = [s for s in spec.segments if s.order == args.segment]
            if not matching:
                print(f"Error: Segment {args.segment} not found in lesson spec.", file=sys.stderr)
                sys.exit(1)
            render_segment_to_video(matching[0], lesson_root=lesson_root, fps=args.fps)
        else:
            print(f"🎬 Compiling all {len(spec.segments)} segments to MP4 via HyperFrames...")
            render_all_segments(spec, lesson_root=lesson_root, fps=args.fps)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
