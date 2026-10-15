# Claim Triage Agent

## Architecture overview

![Architecture overview](/public/Diagram1.jpg)

## Key decisions

- **An LLM call for every "intelligent" step** — validation, tool reasoning,
  and synthesis all go through the model. This is expensive, and is the main
  thing worth improving — explored further in the deep dive below.
- **A small, local embedding model** — the corpus is already small and
  well-structured, so a lightweight local model is enough; no need for an
  API-based embedding service for this.
- **One combined embedding per claim** — the description and adjuster notes
  are embedded together rather than separately. There's some redundancy
  between the two, but both are short, and simplicity won out over a more
  deliberate retrieval design. It worked well enough in practice that the
  approach was never revisited.
- **Prompt engineering over architecture changes** — most of the effort went
  into prompting for the validation steps and the ReAct loop, rather than
  restructuring the pipeline itself. Those prompts could likely be tightened
  and made less verbose, which is probably necessary to scale this up.
- **In-memory storage** — claims and traces are kept in memory rather than a
  database. At this scale, state only needs to persist within a single
  session, so a database would be unnecessary overhead. Scaling this up
  would call for more durable, shared storage.

## Deep dive: is the ReAct loop earning its cost here?

![ReAct loop vs deterministic pipeline](/public/Diagram2.jpg)
