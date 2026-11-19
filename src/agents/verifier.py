"""Grounding & Learner Agent: Unified factual auditor and chalk-learner persona evaluation."""

from src.config import generate_structured_output
from src.schemas.lesson import LessonSpec, VerificationReport

VERIFIER_PROMPT = """You are a dual-specialist educational auditor performing two mandatory review passes:
1. FACTUAL AUDITOR (chalk-factcheck + chalk-grounding)
2. LEARNER ADVOCATE (chalk-learner persona evaluation)

--- PASS 1: FACTUAL AUDITOR ---
- Verify that every technical statement, code construct, and diagram element is grounded in the source text.
- Check checkpoint questions: Is the designated correct answer unequivocally true per the source? Are distractors unmistakably wrong?
- Verify that every source citation excerpt is authentic and contextually accurate.

--- PASS 2: CHALK-LEARNER PERSONA ---
Simulate a motivated, intelligent learner encountering this topic for the first time. Audit for pedagogical friction:
1. Undefined Jargon: Did a segment introduce domain jargon or acronyms without first establishing an intuitive definition?
2. Abrupt Transitions: Does moving from Segment N to N+1 feel like a jarring leap with missing conceptual bridges?
3. Cognitive Overload: Is the concept density per 45-second segment balanced, or is the learner bombarded with too many new mechanisms at once?
4. Question Fairness: Does each checkpoint test genuine understanding of the segment's core takeaway, or is it trivial word-matching or an unfair trick?
5. Pacing: Is the spoken narration pacing comfortable (~130-150 words per minute)?

Fill in the `learner_audit` with `friction_score` (1.0 = smooth and clear, <0.7 = high friction), `cognitive_load`, and specific `friction_issues`.
"""


def run_verifier(
    source_doc: dict,
    lesson_spec: LessonSpec,
    provider: str = "gemini",
) -> VerificationReport:
    """Runs the unified Grounding and Chalk-Learner evaluation on the LessonSpec."""
    prompt = f"""{VERIFIER_PROMPT}

=== ORIGINAL SOURCE DOCUMENT ===
{source_doc['content']}

=== GENERATED LESSON SPECIFICATION ===
{lesson_spec.model_dump_json(indent=2)}

Perform both the factual audit and the chalk-learner persona review.
Return the complete VerificationReport adhering strictly to the schema.
"""

    data = generate_structured_output(
        prompt=prompt,
        response_schema=VerificationReport,
        role="verifier",
        provider=provider,
        temperature=0.1,
    )
    report = VerificationReport.model_validate(data)
    lesson_spec.verification_report = report
    return report
