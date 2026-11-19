"""Jupyter Notebook Generator: Emits a companion .ipynb follow-along notebook for lessons."""

import json
from pathlib import Path
from typing import Any, Dict, List

from src.schemas.lesson import LessonSpec


def create_markdown_cell(content: str) -> Dict[str, Any]:
    """Creates a Jupyter Markdown cell structure."""
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": content.splitlines(keepends=True),
    }


def create_code_cell(code: str) -> Dict[str, Any]:
    """Creates a Jupyter Code cell structure."""
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": code.splitlines(keepends=True),
    }


def generate_companion_notebook(spec: LessonSpec, output_path: Path) -> Path:
    """Generates an interactive follow-along Jupyter notebook from a LessonSpec."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cells = []

    # 1. Title & Learning Objectives
    header_md = f"""# 📓 {spec.title}
### {spec.subtitle}
*Estimated completion time: ~{spec.estimated_duration_minutes} minutes*

---

### 🎯 Learning Objectives:
"""
    for obj in spec.learning_objectives:
        header_md += f"- [ ] {obj}\n"

    header_md += "\n> This interactive notebook accompanies the Chalk-ADK lesson. Run the cells as you listen to the narration!\n"
    cells.append(create_markdown_cell(header_md))

    # 2. Iterate through Segments
    for seg in spec.segments:
        seg_header = f"""---
## Segment {seg.order}: {seg.title}

{seg.narration}

"""
        if seg.source_citations:
            seg_header += f"> **Source Grounding:** *\"{seg.source_citations[0].excerpt}\"*\n"

        cells.append(create_markdown_cell(seg_header))

        # Check for code blocks in visuals
        code_found = False
        for v in seg.visuals:
            if v.kind == "code" and v.content:
                comment = f"# --- Segment {seg.order}: {v.title} ---\n"
                cells.append(create_code_cell(comment + v.content))
                code_found = True

        if not code_found:
            # Provide an interactive code scratchpad cell
            sample_code = f"""# Code Playground for Segment {seg.order}: {seg.title}
# Try experimenting with the concepts mentioned in this segment:

def explore_concept():
    print("Exploring {seg.title}...")

explore_concept()
"""
            cells.append(create_code_cell(sample_code))

        # Checkpoint Quiz Cell
        cp = seg.checkpoint
        quiz_md = f"""### 🧠 Checkpoint {seg.order}: Concept Check
**{cp.prompt}**

"""
        for opt in cp.options:
            quiz_md += f"- **[{opt.id}]** {opt.text}\n"

        correct_opt = next((o for o in cp.options if o.is_correct), None)
        explanation_text = correct_opt.explanation if correct_opt else "Verified by GroundingAgent."
        correct_letter = correct_opt.id if correct_opt else "Correct"

        quiz_md += f"""
<details>
<summary><b>🔍 Reveal Solution & Grounded Explanation</b></summary>

**Correct Answer:** [{correct_letter}]

{explanation_text}

*Grounding Excerpt:* `"{cp.source_grounding.excerpt}"`
</details>
"""
        cells.append(create_markdown_cell(quiz_md))

    # 3. Final Summary Cell
    summary_md = f"""---
## 🏁 Lesson Complete!
**Summary:** {spec.summary}

Great job working through this lesson! You can tweak any of the code cells above and test variations.
"""
    cells.append(create_markdown_cell(summary_md))

    notebook_data = {
        "cells": cells,
        "metadata": {
            "language_info": {"name": "python", "version": "3.12"},
            "orig_nbformat": 4,
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(notebook_data, f, indent=2)

    print(f"📓 Companion Notebook generated: {output_path.name}")
    return output_path

