# Understanding Multi-Agent Systems in Google ADK

## 1. What is Google ADK?
Google's Agent Development Kit (ADK) is an open-source framework designed to construct, test, and orchestrate AI agents. While optimized for Google Gemini models through the Google GenAI SDK (`google-genai`), ADK provides first-class support for multi-provider environments via LiteLLM.

## 2. The Core Concept: Agents vs Tools
In traditional code architectures, functions perform deterministic tasks on data. In ADK:
- An **Agent** (`LlmAgent`) encapsulates goal-directed reasoning, instructions, and an LLM model backend.
- A **Tool** is a callable capability (such as a database query, file reader, or web search) exposed to an agent through structured schemas.
- Agents can also be exposed as tools to other agents, enabling hierarchical multi-agent coordination.

## 3. Workflow Orchestration Patterns
Real-world systems rarely rely on a single agent conversation loop. ADK structures agent execution into predictable topologies:
1. **Sequential Pipelines**: The output of Agent A serves directly as the input to Agent B (e.g., Ingest -> Outline -> Script).
2. **Parallel Fan-Out**: Multiple specialized evaluator agents review the same artifact simultaneously (e.g., Fact-Checker, Style Guide Reviewer, Safety Guard).
3. **Human-in-the-Loop Gates**: The workflow halts at critical state boundaries to require human sign-off before expensive or non-reversible operations (e.g., rendering video or calling external APIs).

## 4. Rate-Limiting and Free-Tier Quota Protection
When operating agents on free API tiers (such as Google AI Studio's 15 Requests Per Minute limit), developers must design lean communication topologies:
- Prefer batched structured calls using Pydantic schemas over chatty back-and-forth prompts.
- Implement explicit request pacing (e.g., 4.5 second intervals between calls) to guarantee that request bursts never trip HTTP 429 status codes.
- Leverage models with massive context windows (such as Gemini Flash) to feed entire source documents into single verification passes rather than creating dozens of micro-chunks.

