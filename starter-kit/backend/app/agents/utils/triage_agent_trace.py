from dataclasses import dataclass


@dataclass(frozen=True)
class DeterministicStepRecord:
    """One ordered step of a deterministic triage run, before numbering.

    The deterministic orchestrator fills these in as it walks the fixed
    pipeline, so the trace can be reconstructed without any model message
    history. ``tool_name``/``tool_input``/``tool_output`` carry the act/observe
    detail for tool steps.
    """

    step_type: str
    content: str
    recorded_at: str
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: object = None


def build_deterministic_trace_steps(records: list[DeterministicStepRecord]) -> list[dict]:
    """Builds AgentTrace-shaped steps from a deterministic run's step records."""
    steps: list[dict] = []
    for index, record in enumerate(records, start=1):
        step: dict = {
            "type": record.step_type,
            "content": record.content,
            "timestamp": record.recorded_at,
        }
        if record.tool_name is not None:
            step["tool_name"] = record.tool_name
        if record.tool_input is not None:
            step["tool_input"] = record.tool_input
        if record.tool_output is not None:
            step["tool_output"] = record.tool_output
        step["step_number"] = index
        steps.append(step)
    return steps
