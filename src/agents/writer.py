"""LessonWriterAgent: Drafts narrated scripts, HyperFrames animated scenes (HTML + GSAP), and interactive checkpoints."""

from src.config import generate_structured_output
from src.schemas.lesson import CurriculumOutline, LessonSpec

WRITER_PROMPT = """You are an elite educational animator and content author specializing in HyperFrames (HeyGen code-to-video).
Your goal is to turn the source document and curriculum outline into a complete, high-engagement interactive lesson specification.

Guidelines for Spoken Narration (for Kokoro TTS):
1. Spoken Word Cadence: Write natural, punchy sentences intended to be spoken aloud (~100 to 180 words per segment, roughly 45 to 75 seconds).
2. Avoid Symbol Soup: Never read raw code characters aloud verbatim (do not write "open curly brace", "equals equals", or "semicolon"). Describe the semantic intent.
3. Active Guiding Voice: Direct the learner's attention to the screen animation ("Notice line 3 as it highlights", "Watch how the Agent node connects to the Tool").

Guidelines for HyperFrames Scene Code (HTML + CSS + GSAP Timeline):
For EVERY segment, provide a `hyperframe` object:
1. `html`: Semantic, styled HTML for a 16:9 canvas (using Tailwind classes, dark slate palette, glowing indigo accents).
   - Use macOS-style window frames (`<div class="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-2xl">...</div>`).
   - For code: include realistic syntax-highlighted HTML spans with clear IDs on important lines (e.g., `id="line-1"`, `id="line-2"`).
   - For architecture/concepts: create animated CSS/SVG nodes and flow badges (e.g., `id="agent-node"`, `id="tool-node"`, `id="flow-arrow"`).
2. `css`: Any optional CSS keyframes, glow filters, or scoped utility classes.
3. `gsap_timeline`: A JavaScript code block animating the scene in sync with the narration.
   - Assume `const tl = gsap.timeline();` is already initialized.
   - Use standard GSAP 3 methods (`tl.from()`, `tl.to()`, `tl.staggerFrom()`).
   - Sequence animations smoothly using relative offset timings (`"+=0.8"`, `"+=1.5"`).
   - Example pattern:
     tl.from("#mac-window", { opacity: 0, y: 30, duration: 0.8, ease: "power2.out" })
       .from(".code-line", { opacity: 0, x: -15, stagger: 0.2, duration: 0.5 }, "+=0.5")
       .to("#line-highlight", { backgroundColor: "rgba(99,102,241,0.3)", duration: 0.4 }, "+=1.5")
       .from("#badge-callout", { scale: 0, duration: 0.6, ease: "back.out" }, "+=2.0");

Guidelines for Interactive Checkpoints:
1. Every segment concludes with ONE interactive comprehension question before the learner can proceed.
2. The question must test deep conceptual understanding or prediction, NOT trivial trivia or verbatim memorization.
3. Distractors (wrong options) must represent genuine, common developer misunderstandings.
4. Each option must contain a clear, grounded explanation of WHY it is correct or incorrect.
5. Provide a verbatim source excerpt in source_grounding backing the answer.
"""


def run_writer(
    source_doc: dict,
    outline: CurriculumOutline,
    provider: str = "gemini",
) -> LessonSpec:
    """Runs the LessonWriter stage to generate the full LessonSpec with HyperFrames scenes."""
    prompt = f"""{WRITER_PROMPT}

Source Document: {source_doc['file_name']}

=== CURRICULUM OUTLINE ===
{outline.model_dump_json(indent=2)}

=== SOURCE CONTENT START ===
{source_doc['content']}
=== SOURCE CONTENT END ===

Generate the complete LessonSpec adhering strictly to the response schema.
Ensure each segment contains:
1. Spoken narration.
2. A complete HyperFrameScene with HTML markup and a synchronized GSAP timeline.
3. An interactive checkpoint question with grounded explanations.
"""

    data = generate_structured_output(
        prompt=prompt,
        response_schema=LessonSpec,
        role="writer",
        provider=provider,
        temperature=0.3,
    )
    lesson_spec = LessonSpec.model_validate(data)
    lesson_spec.source_file = source_doc["file_path"]
    return lesson_spec
