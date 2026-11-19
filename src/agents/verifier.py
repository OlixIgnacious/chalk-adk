"""GroundingAgent: Audits the generated LessonSpec against source material for factual fidelity."""

from src.config import generate_structured_output
from src.schemas.lesson import LessonSpec, VerificationReport

VERIFIER_PROMPT = """You are a rigorous factual auditor and pedagogical reviewer (equivalent to chalk-grounding and chalk-factcheck).
Your job is to audit the generated LessonSpec against the original source document.

Audit Checklist:
1. Fact-Check: Are there any fabricated claims, invented APIs, hallucinated statistics, or inaccurate technical statements in the narration or visual code?
2. Question Quality & Correctness:
   - Is the correct option for each checkpoint indisputably supported by the source?
   - Are the distractors unmistakably incorrect according to the source?
   - Are the feedback explanations accurate and helpful?
3. Source Grounding:
   - Does every segment's source excerpt actually exist in the source text?
   - Are the citations faithful rather than taken out of context?

Evaluation Rules:
- If any claim directly contradicts the source or invents functionality not supported by it, flag it as a 'critical' or 'warning' issue.
- If everything is accurate and properly grounded, set is_grounded = True and factual_score >= 0.95.
"""


def run_verifier(
    source_doc: dict,
    lesson_spec: LessonSpec,
    provider: str = "gemini",
) -> VerificationReport:
    """Runs the GroundingAgent audit on the LessonSpec."""
    prompt = f"""{VERIFIER_PROMPT}

=== ORIGINAL SOURCE DOCUMENT ===
{source_doc['content']}

=== GENERATED LESSON SPECIFICATION ===
{lesson_spec.model_dump_json(indent=2)}

Perform a thorough audit and return the VerificationReport according to the schema.
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
