# ⚡ Chalk-ADK: Grounded Interactive Lessons

An educational content engine inspired by **[OlixIgnacious/chalk](https://github.com/OlixIgnacious/chalk)**, re-architected with **Google Agent Development Kit (ADK)** and **Gemini**.

Chalk-ADK turns any technical document, chapter, or markdown file into an **interactive, source-grounded web lesson** featuring bite-sized narration, dynamic visual boards, and comprehension checkpoint gates.

---

## 🌟 Key Features

* **Strict Source Grounding**: Every claim, code snippet, and quiz question cites exact excerpts from the source document.
* **Pedagogical 3-Stage Pipeline**:
  * 🧠 **CuratorAgent (`gemini-3.5-flash-lite`)**: Distills the document into a progressive 3-5 unit outline.
  * ✍️ **LessonWriterAgent (`gemini-3.8-flash`)**: Writes spoken narration, visual directives, and checkpoint questions with grounded feedback.
  * 🔍 **GroundingAgent (`gemini-3.8-flash`)**: Audits claims and citations against the source text to prevent hallucinations.
* **Human-in-the-Loop Review Gate**: Inspect and approve the lesson plan before rendering audio and web assets.
* **Dual-Mode Narration**:
  * Studio-quality offline voiceover using **Kokoro-ONNX** (zero cloud TTS bill).
  * Automatic browser **Web Speech Synthesizer** fallback if offline weights are not installed.
* **Free-Tier Friendly**:
  * Built-in request pacing (4.5s intervals) guarantees zero HTTP 429 errors on Google AI Studio's 15 RPM free tier.
  * Native multi-provider support via **LiteLLM** for **Mistral** (`codestral`, `mistral-small`), **Groq**, and **OpenRouter**.

---

## 🚀 Quickstart

### 1. Setup Environment
```bash
# Clone or navigate to the workspace
cd /Users/olixstudios/.gemini/antigravity/scratch/chalk-adk

# Activate virtual environment
source .venv/bin/activate

# Configure your API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
```

### 2. Generate an Interactive Lesson
```bash
python -m src.cli create examples/sample_source.md
```

### 3. Preview Your Lesson
```bash
python -m src.cli preview dist/understanding-multi-agent-systems-in-google-adk/lesson.html
```

---

## ⚙️ Configuration & Alternative Models

You can switch between model providers in `.env` or via CLI flag:

```bash
# Use Mistral (Codestral / Mistral Small)
python -m src.cli create my_document.md --provider mistral

# Automatically approve without stopping at the terminal gate
python -m src.cli create my_document.md --auto-approve
```

---

## 📁 Project Structure

* `src/schemas/lesson.py` – Pydantic data contracts for lessons, segments, and checkpoints.
* `src/agents/` – Curator, Writer, and Verifier agent definitions.
* `src/compiler/` – Standalone HTML/JS/CSS interactive lesson player and asset compiler.
* `src/tools/` – Source document parser and local Kokoro-ONNX TTS worker.
* `src/workflow.py` – Multi-agent orchestration and human review gate.

