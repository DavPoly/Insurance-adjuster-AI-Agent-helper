# AGENTS.md

Conventions for anyone (human or AI) working in this repo. Follow these before making changes or suggestions.

## 0. Check requirements first

Before proposing or making any change, re-check `assignment.md` and `starter-kit/api-contract` for the actual requirement. Don't guess at scope or invent requirements that aren't there.

## 1. Git

- Commit messages follow the [commit-guide](https://github.com/NurTheDev/commit-guide) convention (`type: short summary`).
- Keep commits short and focused — one logical change per commit.
- Never add AI/tool self-attribution to commit messages (no "Co-Authored-By" or similar signatures).
- AI assistants never stage or commit anything other than `.py` files — the human handles every other commit (Markdown, YAML, TOML, Dockerfile, Makefile, JSON, etc.), even when the agent authored the change. Implement and verify non-`.py` changes as usual; just leave them unstaged for the human to review and commit.

## 2. Project structure

- The project root is `starter-kit/` — that's where `Makefile` and `docker-compose.yml` live and anchor all build/run paths. Source code lives there, split `starter-kit/frontend` and `starter-kit/backend`. Don't mix concerns across the boundary.
- Tests live in a separate `starter-kit/tests` folder, mirroring the frontend/backend split internally (e.g. `starter-kit/tests/frontend/...`, `starter-kit/tests/backend/...`) — not dumped flat.
- Any deviation from `starter-kit/api-contract` must be explicitly called out (comment + commit message) with a reason — it's the source of truth for the API shape.
- `data/ground-truth` and `data/test-documents` (and other fixture data) are read-only — never modify or write into them. Outputs go elsewhere.

## 3. Naming

- Python: PEP 8 naming (`snake_case` functions/variables, `PascalCase` classes).
- Names must be descriptive, not abbreviated — `claim_amount`, not `amt`; `validate_claim_payload`, not `val_pl`.
- No magic numbers or inline literal strings — in application code AND in tests (test assertions/fixtures are not exempt). Constants go in dedicated files, split by what they represent, one concern per file. A generic filename like `constants.py` / `defaults.py` / `constants.ts` is not acceptable — name the file after its actual content (e.g. `health_check_status_labels.py`, `cost_estimate_currency.py`). Tests that assert against a production constant should import that same constant rather than re-typing its literal value; test-only fixture values (fake credentials, sample payloads, etc.) get their own descriptively-named constants file alongside the tests.
- Declarative text blocks (prompts, templates, system messages) get their own file with a descriptive name (e.g. `triage_agent_system_prompt.py`), never a generic `system_prompt.py` or inline string.

## 4. Build & environment

- Use the Make/Docker entrypoints as the only way to build/run/test (`make build`, `make test`, `make run`) — don't let frontend and backend drift into separate ad-hoc commands.
- Secrets never committed; `.env.example` stays current with whatever `.env` keys are actually read.
- Dependencies pinned (`requirements.txt`/lockfile for Python, `package-lock.json` for JS) so the grading environment matches dev.

## 5. Linting, formatting, typing

- One formatter/linter per side, pinned and run via pre-commit or CI — not manual/optional:
  - Python: `ruff` (lint + format, via `ruff format`)
  - Frontend: `prettier` + `eslint`
- Type hints required in Python (mypy-clean where feasible); TypeScript strict mode on the frontend. Descriptive naming doesn't replace static types.

## 6. Error handling & logging

- Consistent error response shape across all API endpoints — don't let each route invent its own error JSON.
- No bare `print` / `console.log` left in committed code — use a logger. Prefer structured logging, especially around agent traces/observability.
- Every HTTP route must explicitly handle every HTTP status the API contract documents for it (e.g. `claims/triage`'s 400/422, the GET endpoints' 404) — implement and test each documented error case, not just the happy path. Routes must also stay resilient to *undocumented* failures: a crash anywhere in the request path (including dependency resolution, not just the route body) must still produce a response, never nothing. A single app-level `@app.exception_handler(Exception)` catching anything unhandled and returning the shared error shape satisfies this — don't wrap every route body in its own catch-all.
- Every route must carry Swagger/OpenAPI-visible documentation (`summary`, `description`, and per-status `responses=`, including the 500 case produced by the app-level handler) so the generated docs are readable on their own — don't rely on route decorators with no metadata.
- Use FastAPI's `status.HTTP_*` constants (`from fastapi import status`) for every status code — never a raw integer like `200`/`404`/`500`, in route decorators, `responses=`, or response construction.

## 7. Documentation & AI usage traceability

- Keep `AI_USAGE.md` honest and current as you work, not filled in retroactively from memory.
- Any non-obvious AI-authored logic should be noted as you go (even briefly) so it can be accounted for in that disclosure later.
