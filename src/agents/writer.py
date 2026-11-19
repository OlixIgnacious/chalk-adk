"""LessonWriterAgent: Drafts narrated scripts, visual directives, and interactive checkpoints."""

from src.config import generate_structured_output
from src.schemas.lesson import CurriculumOutline, LessonSpec

WRITER_PROMPT = """You are an elite educational content creator and interactive lesson author.
Your goal is to turn the provided source document and curriculum outline into a complete, high-engagement interactive lesson specification.

Guidelines for Spoken Narration (for Kokoro TTS):
1. Spoken Word Cadence: Write natural, punchy sentences intended to be spoken aloud (~100 to 180 words per segment, roughly 45 to 75 seconds).
2. Avoid Symbol Soup: Never read raw code characters aloud verbatim (do not write "open curly brace", "equals equals", or "semicolon"). Describe the semantic intent ("we assign the output", "we check for equality").
3. Active Guiding Voice: Direct the learner's attention to the screen ("Take a look at the diagram above", "Notice line 3 in the code block").

Guidelines for Visual Directives:
1. Every segment MUST have at least 1-2 visual blocks (e.g. syntax-highlighted code block with specific highlight_lines, a Mermaid diagram, or key summary bullets).
2. Code snippets should be self-contained, idiomatic, and minimal.
3. For architecture or flow concepts, use Mermaid diagrams (flowchart TD/LR, sequenceDiagram).

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
    """Runs the LessonWriter stage to generate the full LessonSpec."""
    prompt = f"""{WRITER_PROMPT}

Source Document: {source_doc['file_name']}

=== CURRICULUM OUTLINE ===
{outline.model_dump_json(indent=2)}

=== SOURCE CONTENT START ===
{source_doc['content']}
=== SOURCE CONTENT END ===

Generate the complete, verified LessonSpec adhering strictly to the response schema.
Ensure each segment in the outline is developed into a fully scripted LessonSegment.
"""

    data = generate_structured_output(
        prompt=prompt,
        response_schema=LessonSpec,
        role="writer",
        provider=provider,
        temperature=0.4,
    )
    lesson_spec = LessonSpec.model_validate(data)
    lesson_spec.source_file = source_doc["file_path"]
    return lesson_spec
