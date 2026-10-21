# Plan: Replace the LLM ReAct loop with a deterministic Jev decision pipeline

## Goal

Change the claim-triage architecture from the current LLM-driven ReAct loop to the
deterministic pipeline recommended in `README.md` and `starter-kit/frontend/chainlit.md`
(the "Deep dive" + "Next steps"), using **TypeSafe's Jev 1.14 decision model** (via
OpenRouter) for the two structured-decision nodes and keeping a **single generative LLM
call** for synthesis.

Status: done — implemented Oct 15, 2026 (commits 1456908 … 802e861).

## Target architecture (top to bottom)

```
1. Jev 1.14 decision call  — intake + parameter extraction  (one typed call, multimodal)
     state: description + document text + policy_type, with photo(s) as inline
            image_url parts in the state array
     questions → is_property_damage, is_valid_image, no_pii_detected,
                 no_offensive_content (Noul), damage_type (Choice),
                 severity (Choice/Score), affected_areas (multi-label Noul)
     └─ if intake fails → 400 (short-circuit, bypass everything below)

2. deterministic tools  (fan-out / fan-in, no model)
     search_past_claims(query = raw description)
     estimate_repair_cost(damage_type, severity, affected_areas)   ← from node 1
     check_coverage(policy_type = form input, incident_category = node 1 damage_type)

3. synthesize_assessment  — the ONLY generative LLM call (OpenRouter)
     produces damage_description, recommendation, urgency
     deterministic fields (damage_type/severity/affected_areas/cost/similar claims)
     stitched verbatim over the LLM's free-text

4. Jev 1.14 decision call  — output safety (one typed pass/fail call, text only)
     5 Noul questions over the synthesized draft
     └─ if fails → regenerate synthesis (bounded retries) → 422 on exhaustion

5. response terminal (only via the pass path)
```

Model-call budget drops from ~10 LLM calls (worst case) to **1 LLM call + 2 Jev calls**
(Jev is ~200–300 ms, billed on input tokens only, output free — two orders of magnitude
cheaper than an LLM).

## Why Jev 1.14, via OpenRouter

`README`/`chainlit` recommended "1 LLM call + 2 structured decision calls." Jev is
TypeSafe's "System One" decision model: it answers typed questions (`noul`/`choice`/
`score`/`box`) with calibrated probabilities and generates **no text**. Jev 1.14 is
**multimodal** — it accepts text and images, which is required because two acceptance
checks are image-driven:

- `auto-grader/tests/test_guardrails.py:11-23` — 5 negative cases submitted **image-only**
  (no description), must return 400 (`IMG_036/037/038 → is_property_damage:false`,
  `IMG_039 → is_valid_image:false`, `IMG_040 → no_pii_detected:false`).
- `auto-grader/tests/test_multimodal.py:10-17` — `test_image_only` posts a photo with no
  description and expects a 200 with a full `triage_assessment`.

Routing Jev through **OpenRouter** (rather than TypeSafe's native API or a separate
provider) means the decision nodes reuse the repo's existing `OPENROUTER_API_KEY` — no new
account, no new credential, same provider as the synthesis LLM.

### Jev 1.14 facts (verified against OpenRouter docs, Oct 2026)

- Model ID: `typesafe/jev-1.14` (pinned), or `~typesafe/jev-latest` alias (tracks newest).
- Endpoint: `POST https://openrouter.ai/api/alpha/decisions` (Decisions API; plain HTTP).
  Alternative: `POST https://openrouter.ai/api/v1/systemone` (System One API,
  TypeSafe-SDK-compatible). Both authenticate with `Authorization: Bearer OPENROUTER_API_KEY`.
- Request body: `{ "model": ..., "state": <text|object|array>, "questions": { <id>: {...} } }`.
- Image format: images are passed **inline** in the `state` array as OpenAI-style parts —
  `{ "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,<...>" } }`.
  There is **no** top-level `images` field (the API rejects it with 400).
- Primitives (all single-valued):
  - `noul` — yes/no, returns 0–1 probability.
  - `choice` — pick one of N named `criteria`, returns a probability per label.
  - `score` — probability-weighted position on an ordered `criteria` rubric.
  - `box` — find one target in an image, returns `{top,bottom,left,right}` fractions
    (Jev 1.14 only; not needed here).
- Response: `answers[<id>]` with the typed value + `probabilities` + `confidence`, plus a
  `usage.cost` field.
- Multiple questions are evaluated against one `state` in a single pass.
- Context 262,144 tokens; **requests with an image run in long-context mode** (slower,
  less accurate). Image input and `box` are marked "early features" whose format/limits
  can change between releases.
- No TypeSafe account or key is required — an OpenRouter key authenticates both surfaces.

## Decisions already locked

- Full deterministic pipeline (drop the LangGraph ReAct loop).
- Architecture change only (no durable storage / prompt / embeddings work).
- Keep `GET /agent/trace/{claim_id}`; reconstruct `reason`/`act`/`observe` steps from the
  deterministic steps (relabel the OpenAPI `summary` from "ReAct execution trace" → "triage
  execution trace" as a documented deviation).
- `search_past_claims` query = the raw description (per the recommended architecture).
- Decision model = Jev 1.14 via OpenRouter Decisions API, reusing `OPENROUTER_API_KEY`.

## Open implementation choices (recommendation given; confirm during implementation)

1. **`affected_areas` (list[str])** — Jev has no list primitive. Recommended: a fixed
   room/component vocabulary, one `noul` question per candidate ("does the damage affect
   the kitchen?" etc.), thresholded ≥0.5. This matches Jev's documented multi-label-tag
   pattern, works for both image and text states, and feeds `estimate_repair_cost`'s
   distinct-area count directly.
2. **Intake booleans** — Jev returns probabilities; threshold Nouls at 0.5 to produce the
   contract's four booleans. `is_valid_image` is `null` for text-only input.
3. **API surface** — use the Decisions API (`/api/alpha/decisions`) as primary (its
   multimodal image format is explicitly documented); keep the System One API as a
   fallback. Prefer an async `httpx` client to match the async router.

## File map

### Add

- `app/llm/decision_model_client.py` — thin Jev client (`decide(state, questions) -> dict`),
  calling the OpenRouter Decisions endpoint with the existing API key.
- `app/agents/claim_decision.py` — node 1: `decide_claim(submission) -> ClaimDecisionOut`
  (builds `state` with inline images, asks the intake Nouls + damage_type/severity/
  affected_areas questions, thresholds booleans, derives `is_valid`).
- `app/agents/safety_decision.py` — node 4: `check_output_safety(assessment) -> SafetyChecksOut`
  (5 Noul questions, thresholded).
- `app/agents/deterministic_triage.py` — orchestrator: `run_deterministic_triage(...)` wires
  node 1 → tools → synthesis → node 4; builds the deterministic trace. (Supersedes `triage_agent.py`.)
- `app/agents/schemas/claim_decision_schema.py` — `ClaimDecisionOut` (4 intake bools,
  `damage_type`, `severity`, `affected_areas`).
- `app/agents/prompts/claim_decision_questions.py` — the Jev `questions` dict for node 1
  (reuses `DamageType`/`SeverityLevel` enums, `AREA_COUNTING_RULE`, `SEVERITY_CLASSIFICATION_RUBRIC`).
- `app/agents/prompts/safety_decision_questions.py` — the 5 safety Nouls.
- `app/constants/decision/decision_model_config.py` — endpoint URL, model ID
  (`typesafe/jev-1.14`), probability threshold. (One concern per file, per AGENTS.md.)

### Modify

- `app/config.py` — add `decision_model` / `decision_endpoint` settings (reuse
  `openrouter_api_key`; no new credential).
- `app/dependencies.py` — add `get_decision_model_client()` singleton.
- `app/agents/triage_synthesis.py` — `synthesize_triage_assessment` takes explicit
  `classification` + `tool_results` (not `messages`); keep verbatim stitching of
  damage_type/severity/affected_areas/cost/similar-claims.
- `app/agents/utils/triage_agent_trace.py` — build steps from deterministic records
  (reason → act/observe per tool), not `AIMessage`/`ToolMessage` history.
- `app/routers/triage.py` — swap `run_triage_agent` → `run_deterministic_triage`; safety
  retry loop now calls the Jev safety check; update route `description`/`summary`.
- `app/routers/claim_input_parsing.py` — intake validation now via `claim_decision.py`
  (Jev) instead of `intake_validator.py`.
- `starter-kit/.env.example` / `docker-compose.yml` — document `DECISION_MODEL` /
  `DECISION_ENDPOINT` (no new secret; reuses `OPENROUTER_API_KEY`).
- `starter-kit/backend/requirements.txt` — add `httpx` (pin); drop `langgraph` and
  LangChain tool-binding deps once unused (keep `langchain` for `with_structured_output`).
- `README.md`, `starter-kit/frontend/chainlit.md`, `RESULTS.md`, `AI_USAGE.md` — reflect
  the Jev decision pipeline, drop stale ReAct-loop text, fix the broken `assignment.md`
  link on `README.md:3`.
- `starter-kit/api-contract/openapi.yaml` — relabel `GET /agent/trace/{claim_id}` summary
  (documented deviation; the step schema itself is unchanged).

### Delete

- `app/agents/triage_agent.py` (superseded by `deterministic_triage.py`)
- `app/agents/triage_agent_graph.py` (LangGraph ReAct loop)
- `app/agents/intake_validator.py` (replaced by `claim_decision.py`)
- `app/agents/safety_checker.py` (replaced by `safety_decision.py`)
- `app/agents/utils/triage_agent_tools.py` (call `app/tools/*` directly)
- `app/agents/utils/claim_messages.py` (ReAct message building)
- `app/agents/prompts/triage_agent_system_prompt.py`, `intake_validator_system_prompt.py`, `safety_checker_system_prompt.py`
- `app/agents/schemas/triage_agent_state.py`
- `app/constants/agent/triage_agent_config.py` (`MAX_REACT_ITERATIONS`)

Keep: `app/constants/agent/triage_tool_names.py` (trace labels), `safety_check_retry_limits.py`,
`agent_trace_step_types.py`, `trace_metadata_keys.py`, and all `app/tools/*` deterministic functions.

## Test changes

- **Delete** `tests/backend/agents/test_triage_agent_graph.py`, `test_triage_agent_tools.py`,
  `test_intake_validator.py`, `test_safety_checker.py` (superseded).
- **Add** `test_claim_decision.py`, `test_safety_decision.py`, `test_deterministic_triage.py`
  (mock the Jev client and synthesis; assert deterministic tool calls + reconstructed trace).
- **Rewrite** `test_triage_agent.py` → covered by `test_deterministic_triage.py`.
- **Modify** `test_triage_synthesis.py` (new signature), `test_triage_agent_trace.py`
  (deterministic records), `routers/test_triage.py` (new dependency/import).
- **Unchanged** `tests/backend/tools/*`, `tests/backend/rag/*`, `test_health.py`,
  all `tests/frontend/*`.
- Test fixtures: replace `FakeTriageChatModel` ReAct-loop usage with a fake Jev client
  returning canned `answers`; keep a fake chat model for synthesis.

## Execution order (TDD, one logical commit each)

1. **Jev client + config** — add settings, constants, `decision_model_client.py`, dependency; add a client test.
2. **Node 4 (safety)** — `safety_decision.py` + test (self-contained; doesn't touch the happy path yet).
3. **Node 1 (intake + params)** — `claim_decision.py` + schema + questions + test; wire into
   `claim_input_parsing.py`.
4. **Deterministic orchestrator + trace** — `deterministic_triage.py` + rewritten trace builder + tests.
5. **Wire the router** — swap entry point + safety retry loop; update router test.
6. **Simplify synthesis** — new signature + verbatim stitching; update test.
7. **Delete the ReAct layer** — remove graph/tools/prompts/state/intake/safety + their tests;
   prune `requirements.txt`.
8. **Docs + contract** — README/chainlit/RESULTS/AI_USAGE/openapi summary.
9. **Verify** — `make test`, `make grade` (expect the 2 known UI skips), `make eval`.

## Conventions (AGENTS.md) applied to all new/changed code

- Descriptive `snake_case` names; constants in per-concern files (no generic `constants.py`).
- Type hints (mypy-clean); `ruff format` + lint.
- No magic numbers/strings in code or tests; import shared constants instead of re-typing literals.
- Every route keeps its documented statuses; a single app-level exception handler for 500s;
  use `fastapi.status.HTTP_*` everywhere.
- No bare `print`/`console.log`; structured logging for the two Jev decisions and tool steps.

## Risks / notes

- **Jev 1.14 is brand-new, and image input is an "early feature"** — its request format and
  limits can change between releases. `decision_model_client.py` isolates this; pin
  `typesafe/jev-1.14` rather than the `jev-latest` alias.
- **Vision accuracy** — Jev's visual "property damage" detection is a general model, not
  tuned to this corpus; the 5 rejection cases and image-only triage must be re-verified with
  `make grade` after wiring.
- **Image requests run in long-context mode** (slower, less accurate) — factor this into the
  latency measurement in `RESULTS.md`.
- **Removed ReAct category** — already reflected in `auto-grader/grade.py` (max auto 14);
  this plan is consistent with that decision. The reconstructed `reason/act/observe` trace
  is deterministic, not model-in-the-loop; `RESULTS.md` should note this explicitly.

## Decisions log (implementation)

- **Execution order swapped:** Phase 7 (ReAct deletion) ran before Phase 6 (synthesis
  simplification) so the signature change had no live callers to bridge.
- **`affected_areas`:** one Noul per candidate area from `AFFECTED_AREA_VOCABULARY` (30 areas
  grounded in `data/ground-truth` + knowledge-base; `dining_room` required by the auto-grader
  multimodal case).
- **Intake/safety booleans:** thresholded `>= DECISION_PROBABILITY_THRESHOLD` via shared
  `noul_answer_is_yes` (descriptive `ValueError`s naming the question id on malformed answers).
- **Decisions API only:** the System One fallback was skipped — `decision_model_client.py`
  isolates the wire format, switchable in one file.
- **Intake pass/fail + the five rejection messages** reimplemented in `claim_decision.py` (not
  imported from `intake_validator.py`) — removed the Phase-7 deletion landmine.
- **Node 1 sees the document text:** single-pass PDF extraction in `claim_input_parsing.py`,
  threaded via `ParsedClaimInput`.
- **Trace:** `build_deterministic_trace_steps` renders 18 steps (6 operations ×
  reason/act/observe); `trace_metadata_keys.py` deleted after Phase 7 left it orphaned; the
  router rewrites the synthesis/safety observe steps to the final verdict after a safety retry.
- **Synthesis:** explicit `(classification, tool_results)` per the frozen interface, PLUS an
  approved post-review deviation: `SynthesisClaimContext(claim_description, policy_type)`
  threads the raw description/policy type as grounding (manual-review prose fidelity; verbatim
  stitching unchanged — stitched fields overwrite the LLM free text).
- **Safety retry:** router-level bounded loop, cap `MAX_SAFETY_CHECK_ATTEMPTS` (3) → 422;
  `safety_checks_passed` relocated to `deterministic_triage.py`.
- **Tests:** shared `tests/backend/agents/fake_decision_model_client.py`; wire-format literals
  deliberately re-declared in fixtures (non-tautological payload assertions, rationale
  documented at the shared fake).
