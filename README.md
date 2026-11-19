# ⚡ Chalk-ADK: Grounded Interactive Lessons & Video Engine

An educational content and video engine inspired by **[OlixIgnacious/chalk](https://github.com/OlixIgnacious/chalk)**, re-architected in Python with **Google Agent Development Kit (ADK)** and **Gemini**.

Chalk-ADK transforms any technical document, PDF, EPUB book, or markdown file into an **interactive, source-grounded web lesson** and **MP4 video presentation** featuring bite-sized studio narration, animated GSAP/HyperFrames scenes, interactive code sandboxes, and checkpoint comprehension quiz gates.

---

## 🌟 Key Features

* **Strict Source Grounding**: Every claim, code snippet, and quiz question cites exact verbatim excerpts from the source document.
* **4-Stage Pedagogical Pipeline**:
  * 🧠 **CuratorAgent (`gemini-3.1-flash-lite`)**: Distills raw material into a progressive 3-5 unit outline.
  * ✍️ **LessonWriterAgent (`gemini-3.8-flash`)**: Generates spoken narration scripts, checkpoint questions, and seekable **HyperFrames** HTML+GSAP timelines.
  * 🔍 **Grounding & Chalk-Learner Agent (`gemini-3.8-flash`)**: Audits factual grounding citations and performs cognitive load & pedagogical friction checks.
  * 🛑 **Human-in-the-Loop Review Gate**: Inspect and approve the lesson plan in your terminal before building audio and web assets.
* **Dual Studio TTS Narration**:
  * 🎙️ **Google AI Studio Gemini 3.8 Flash TTS**: Cloud studio voices (`Kore`, `Puck`, `Fenrir`, etc.) directly via Google GenAI SDK.
  * 💻 **Local Offline Kokoro-ONNX**: Zero-network CPU voiceover with NumPy style vector linear interpolation (`af_heart:0.7,af_bella:0.3`).
  * 🌐 **Web Speech Synthesizer fallback**: Safe offline in-browser fallback.
* **Code-to-Video Engine (HyperFrames)**:
  * Export 1080p 60fps MP4 video clips via `python -m src.cli render-video` utilizing `npx hyperframes render`.
* **Multi-Format Ingestion & Guardrails**:
  * Markdown, TXT, PDF (`--page-range X-Y`), and EPUB books (`--chapter N`).
  * 4-layer security guardrail system blocking path traversal, oversized file bombs, PDF JavaScript exploit tokens (`/JS`, `/Launch`), and prompt injection.
* **Chalk Doctor**:
  * Run `python -m src.cli doctor` for instant diagnostics across Python, virtualenv, Node.js, FFmpeg, Chrome, Kokoro weights, and API keys.
* **Companion Jupyter Notebooks**:
  * Generate interactive follow-along `.ipynb` notebooks via `--notebook`.

---

## 🚀 Quickstart

### 1. Setup Environment
```bash
# Clone or navigate to the workspace
cd /Users/olixstudios/.gemini/antigravity/scratch/chalk-adk

# Activate virtual environment
source .venv/bin/activate

# Check toolchain readiness
python -m src.cli doctor
```

### 2. Generate an Interactive Lesson
```bash
# Create lesson with Gemini 3.8 Flash TTS narration & Jupyter notebook
python -m src.cli create examples/sample_source.md --tts-provider gemini --notebook

# Or use offline Kokoro voice-blending:
python -m src.cli create examples/sample_source.md --tts-provider kokoro --voice "af_heart:0.7,af_bella:0.3"
```

### 3. Preview Your Lesson Locally
```bash
python -m src.cli preview dist/architecting-multi-agent-systems-adk/lesson.html
```
*(Runs an ephemeral local server on `http://127.0.0.1:8765` to bypass browser `file:///` security and cross-origin restrictions).*

### 4. Render Video via HyperFrames
```bash
# Render all segments to 1080p MP4:
python -m src.cli render-video dist/architecting-multi-agent-systems-adk

# Or render a specific segment:
python -m src.cli render-video dist/architecting-multi-agent-systems-adk --segment 1
```

---

## ⚙️ Multi-Model Fallback & Pacing

* **Rate Pacing**: Built-in 3.0s-4.5s request pacing guarantees zero HTTP 429 quota errors on Google AI Studio's free tier.
* **Cascade Resilience**: If a Gemini model encounters temporary high demand (503/429), it automatically cascades to `gemini-3.1-flash-lite`, and falls back to **Mistral** (`codestral-latest`) or **Groq** (`qwen/qwen3.8-27b`) when configured.

---

## 📁 Project Structure

* `src/schemas/lesson.py` – Pydantic contracts for lessons, segments, HyperFrame scenes, and audits.
* `src/agents/` – Curator, Writer, and Grounding + Chalk-Learner Verifier agents.
* `src/compiler/` – Standalone HTML/GSAP lesson player builder and HyperFrames video renderer.
* `src/tools/` – Document parser, PDF/EPUB ingest, security guardrails, diagnostic doctor, and dual TTS worker (Gemini + Kokoro).
* `src/workflow.py` – Multi-agent pipeline orchestration with terminal review gate.
* `src/cli.py` – Unified CLI for `create`, `preview`, `render-video`, and `doctor`.
* `tests/` – Unit tests for guardrails and TTS engine.
