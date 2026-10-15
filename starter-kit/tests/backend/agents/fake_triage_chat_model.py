"""Fake chat model for exercising the triage agent's LangGraph loop and
synthesis step without calling a real LLM.
"""


class FakeTriageChatModel:
    def __init__(
        self,
        tool_loop_responses=None,
        structured_output_value=None,
        structured_output_values_by_schema=None,
    ):
        self._tool_loop_responses = list(tool_loop_responses or [])
        self._call_index = 0
        self._structured_output_value = structured_output_value
        self._structured_output_values_by_schema = structured_output_values_by_schema or {}

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        response = self._tool_loop_responses[self._call_index]
        self._call_index += 1
        return response

    def with_structured_output(self, schema):
        value = self._structured_output_values_by_schema.get(schema, self._structured_output_value)
        return _FakeStructuredOutputRunnable(value)


class _FakeStructuredOutputRunnable:
    def __init__(self, value):
        self._value = value

    def invoke(self, messages):
        return self._value
