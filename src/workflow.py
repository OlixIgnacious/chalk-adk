"""Chalk-ADK Workflow: Orchestrates the multi-agent pipeline with human-in-the-loop review."""

import json
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
except ImportError:
    console = None

from src.tools.document_parser import load_source_document
from src.agents.curator import run_curator
from src.agents.writer import run_writer
from src.agents.verifier import run_verifier
from src.schemas.lesson import LessonSpec


def render_human_review_gate(spec: LessonSpec) -> bool:
    """Displays the generated lesson spec and awaits user approval before audio rendering."""
    print("\n" + "=" * 70)
    print("🎓 CHALK-ADK: HUMAN REVIEW GATE")
    print("=" * 70)
    print(f"Title:       {spec.title}")
    print(f"Subtitle:    {spec.subtitle}")
    print(f"Segments:    {len(spec.segments)} segments (~{spec.estimated_duration_minutes} mins)")
    print(f"Objectives:")
    for obj in spec.learning_objectives:
        print(f"  • {obj}")

    print("\n--- SEGMENTS SUMMARY ---")
    for seg in spec.segments:
        wc = len(seg.narration.split())
        est_sec = int(wc / 2.5)  # ~150 wpm for Kokoro
        print(f"\n[{seg.order}] {seg.title} (~{est_sec}s, {wc} words)")
        print(f"    Visuals: {len(seg.visuals)} block(s) ({', '.join(v.kind for v in seg.visuals)})")
        print(f"    Checkpoint: \"{seg.checkpoint.prompt}\"")
        correct_opt = next((opt for opt in seg.checkpoint.options if opt.is_correct), None)
        if correct_opt:
            print(f"    Correct Choice: [{correct_opt.id}] {correct_opt.text}")

    if spec.verification_report:
        report = spec.verification_report
        print("\n--- GROUNDING & FACTUAL AUDIT ---")
        print(f"Grounded: {report.is_grounded} | Accuracy Score: {int(report.factual_score * 100)}%")
        if report.issues:
            print(f"Factual Warnings ({len(report.issues)}):")
            for issue in report.issues:
                print(f"  [{issue.severity.upper()}] ({issue.location}): {issue.issue_description}")
        else:
            print("  ✓ Zero factual errors detected. All claims verified against source.")

        # Chalk-Learner Persona Report
        if report.learner_audit:
            la = report.learner_audit
            print("\n--- CHALK-LEARNER PERSONA AUDIT ---")
            print(
                f"Pedagogical Clarity: {int(la.friction_score * 100)}% | "
                f"Cognitive Load: {la.cognitive_load.upper()} | Target: {la.reading_level}"
            )
            print(f"Assessment: {la.pedagogical_summary}")
            if la.friction_issues:
                print("Pedagogical Friction Stumbling Blocks:")
                for fi in la.friction_issues:
                    print(f"  • [Seg {fi.segment_order}] ({fi.issue_type}): {fi.description}")
                    print(f"    Recommendation: {fi.recommendation}")
            else:
                print("  ✓ Smooth conceptual transitions. No cognitive friction points identified.")

    print("\n" + "-" * 70)
    try:
        user_input = input("Approve this lesson plan to build HTML & audio? [Y/n/edit]: ").strip().lower()
    except EOFError:
        user_input = "y"

    return user_input in ["y", "yes", ""]


def run_lesson_pipeline(
    source_path: str,
    output_dir: Optional[str] = None,
    provider: str = "gemini",
    auto_approve: bool = False,
    page_range: Optional[str] = None,
    chapter: Optional[int] = None,
    allow_suspicious: bool = False,
    generate_notebook: bool = False,
) -> LessonSpec:
    """Executes the full pipeline: Ingest -> Curate -> Write -> Verify -> Human Gate -> Notebook."""
    print(f"📖 Step 1/4: Ingesting source document '{source_path}'...")
    source_doc = load_source_document(
        source_path,
        page_range=page_range,
        chapter=chapter,
        allow_suspicious=allow_suspicious,
    )
    print(
        f"   Loaded {source_doc['word_count']} words (~{source_doc['estimated_tokens']:,} tokens, "
        f"{source_doc['line_count']} lines)."
    )
    if source_doc.get("security_warnings"):
        print(f"   🛡️ Guardrails flagged {len(source_doc['security_warnings'])} security notice(s).")

    print(f"🧠 Step 2/4: Curating curriculum outline with CuratorAgent...")
    outline = run_curator(source_doc, provider=provider)
    print(f"   Generated outline with {len(outline.units)} units: {outline.title}")

    print(f"✍️  Step 3/4: Drafting scripts, visuals & checkpoints with LessonWriterAgent...")
    spec = run_writer(source_doc, outline, provider=provider)
    print(f"   Drafted {len(spec.segments)} interactive segments.")

    print(f"🔍 Step 4/4: Auditing grounding with GroundingAgent...")
    report = run_verifier(source_doc, spec, provider=provider)
    print(f"   Verification score: {int(report.factual_score * 100)}% (Grounded: {report.is_grounded})")

    # Save intermediate spec
    out_path = Path(output_dir or "./dist")
    out_path.mkdir(parents=True, exist_ok=True)
    spec_json_path = out_path / f"{spec.lesson_id}.json"
    with open(spec_json_path, "w", encoding="utf-8") as f:
        f.write(spec.model_dump_json(indent=2))
    print(f"   Saved lesson spec to {spec_json_path}")

    # Human-in-the-loop review gate
    if not auto_approve:
        approved = render_human_review_gate(spec)
        if not approved:
            print("❌ Lesson build halted by user. You can edit the spec file and re-run.")
            return spec

    if generate_notebook:
        from src.compiler.notebook_generator import generate_companion_notebook
        nb_path = out_path / spec.lesson_id / "notebook.ipynb"
        generate_companion_notebook(spec, nb_path)

    print("✅ Lesson approved! Ready for compilation.")
    return spec

