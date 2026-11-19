"""CuratorAgent: Ingests source material and produces a structured pedagogical outline."""

from src.config import generate_structured_output
from src.schemas.lesson import CurriculumOutline

CURATOR_PROMPT = """You are an expert pedagogical curriculum designer for interactive, bite-sized lessons.
Your job is to read the provided source document and distill it into a clean, 3 to 5 unit learning outline.

Pedagogical Rules:
1. Progressive Ordering: Unit 1 must hook the learner and establish intuitive mental models before diving into formal mechanics.
2. Bite-Sized Scope: Each unit will become a 45-75 second narrated segment. Keep the scope focused on ONE clear concept per unit.
3. High Concept Density: Avoid fluff. Focus on the core mechanics, motivations, and common pitfalls explained in the source.
4. Measurable Objectives: Define 3-5 concrete learning objectives based on Bloom's taxonomy (e.g. "Understand why...", "Trace how...", "Differentiate between...").
"""


def run_curator(source_doc: dict, provider: str = "gemini") -> CurriculumOutline:
    """Runs the Curator stage to produce a CurriculumOutline from the source document."""
    prompt = f"""{CURATOR_PROMPT}

Source Document: {source_doc['file_name']}
Word Count: {source_doc['word_count']}

=== SOURCE CONTENT START ===
{source_doc['content']}
=== SOURCE CONTENT END ===

Generate the structured CurriculumOutline according to the schema.
"""

    data = generate_structured_output(
        prompt=prompt,
        response_schema=CurriculumOutline,
        role="curator",
        provider=provider,
        temperature=0.3,
    )
    return CurriculumOutline.model_validate(data)
