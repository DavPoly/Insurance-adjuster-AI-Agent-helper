# AI usage

- **Tools and models used:** Claude Code, with subagent-driven development. Orchestration/planning/review in this session (Sonnet); mechanical implementation tasks delegated to a fast sub-model (Haiku) following TDD plan.

- **What I delegated and what I checked myself:** Delegated most of the actual code writing to Claude Code, but did the system design and architecture thinking myself before any delegation, and put real effort into defining success criteria and code-quality requirements up front rather than prompting loosely and hoping. I read the resulting code and diffs myself, ran the tests myself instead of trusting an agent's self-report, and did my own root-cause analysis in parallel with the agent's reasoning rather than accepting its first diagnosis.

- **One suggestion I corrected or rejected, and why:** While diagnosing a frontend bug (the chat UI was visibly jittering while the triage assessment streamed in), Claude's first proposed fix, which was narrowing an upload MIME-type config, turned out to only address a secondary console warning, not the actual visible bug. I rejected it, and pushed back with a more precise description of the symptom, I also ruled out the expensive browser-automation-based debugging with playwright in favor of static analysis of the frontend bundle, which led to the real root cause (that was an expensive message-pinning layout recalculation firing on every streamed token) and the actual fix.

- **How I validated the generated code and final behavior:** Ran `make test` and `make grade` myself and read the actual pytest/grader output rather than trusting agent summaries. For the streaming-UI fix specifically, verified the config change was actually live inside the running container (`docker compose exec ui cat .chainlit/config.toml`) rather than assuming a restart had picked it up.

- **Approximate active engineering time, excluding initial installation/access checks:** ~10 hours, spread across Oct 12-13.

- **Setup/access time and interruptions, recorded separately:** Some friction getting Docker/API access fully working before active development could start, roughly 1 hour beyond a clean first-try setup.
