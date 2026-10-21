# Claim Triage Agent

## Architecture overview

![Architecture overview](/public/Diagram1.jpg)

## Key decisions

- **A deterministic pipeline with a fixed model-call budget** — one generative
  LLM call plus two Jev 1.14 decision calls per successful pass, replacing the
  LLM-driven ReAct loop. This cut the per-claim cost and latency, and is the
  main thing the deep dive below explores.
- **A small, local embedding model** — the corpus is already small and
  well-structured, so a lightweight local model is enough; no need for an
  API-based embedding service for this.
- **One combined embedding per claim** — the description and adjuster notes
  are embedded together rather than separately. There's some redundancy
  between the two, but both are short, and simplicity won out over a more
  deliberate retrieval design. It worked well enough in practice that the
  approach was never revisited.
- **Synthesis stays its own LLM call**, rather than folding into a decision
  node — the structured-output schema call is isolated from the deterministic
  steps, and the safety-retry path can regenerate just the assessment without
  re-running the tools.
- **In-memory storage** — claims and traces are kept in memory rather than a
  database. At this scale, state only needs to persist within a single
  session, so a database would be unnecessary overhead. Scaling this up
  would call for more durable, shared storage.

## Deep dive: from the ReAct loop to a deterministic pipeline

![ReAct loop vs deterministic pipeline](/public/Diagram2.jpg)

This recommendation is now implemented. The LangGraph ReAct loop was removed and
replaced by a fixed five-stage pipeline: one multimodal Jev 1.14 decision call for
intake and parameter extraction, three deterministic tools called directly (no
tool-binding model), one generative synthesis call, and one text-only Jev 1.14
decision call for output safety (bounded to three attempts before a `422`).
The nominal model-call budget fell from roughly 10 LLM calls to 1 LLM call + 2
Jev decision calls per successful pass, bounded at 3 LLM calls + 4 Jev calls
worst case if the safety-retry path is exhausted. Observability is kept:
`GET /agent/trace/{id}` still returns `reason`→`act`→`observe` steps, now 18 of
them (6 operations × reason/act/observe) reconstructed from the pipeline's step
records rather than a model's message history.

Measured on the 35-case development set, the median end-to-end triage latency
fell from 18.5 s to 5.4 s, and the auto-grader scores 13.57/14 with every check
passing (two UI checks skip pending browser review).

## Next steps

- Search past claims with a query built from the intake classification when
  no description is submitted; an image-only claim currently searches with an
  empty description.
- Move claim/trace storage to durable, shared storage if this grows beyond a
  single-session demo.
- Revisit combined vs. separate description/notes embeddings if the
  historical-claims corpus grows large enough for retrieval relevance to matter.
