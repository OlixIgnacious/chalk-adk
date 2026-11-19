"""Chalk-ADK CLI Entrypoint: Create, review, and preview interactive lessons."""

import argparse
import sys
import webbrowser
from pathlib import Path

from src.workflow import run_lesson_pipeline
from src.compiler.builder import compile_lesson


def main():
    parser = argparse.ArgumentParser(
        description="Chalk-ADK: Grounded interactive lessons generator powered by Google ADK & Gemini"
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

    # Command: preview
    preview_parser = subparsers.add_parser("preview", help="Preview a compiled lesson in your default browser")
    preview_parser.add_argument("lesson_file", type=str, help="Path to lesson.html")

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
        print(f"🚀 Opening {target.name} in browser...")
        webbrowser.open(target.as_uri())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

