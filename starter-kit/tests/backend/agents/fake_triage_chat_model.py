"""Fake chat model for exercising the triage synthesis step without a real LLM.

``FakeTriageChatModel`` answers a single ``with_structured_output`` call and
records the messages it was invoked with, so tests can assert what the synthesis
prompt was grounded in. ``CountingTriageChatModel`` extends it to count the
structured-output invocations, which the node-4 and router suites assert to pin
the bounded safety retry.
"""


class FakeTriageChatModel:
    def __init__(
        self,
        structured_output_value=None,
        structured_output_values_by_schema=None,
    ):
        self._structured_output_value = structured_output_value
        self._structured_output_values_by_schema = structured_output_values_by_schema or {}
        self.structured_output_messages: list = []

    def with_structured_output(self, schema):
        value = self._structured_output_values_by_schema.get(schema, self._structured_output_value)
        return _FakeStructuredOutputRunnable(value, self)


class _FakeStructuredOutputRunnable:
    def __init__(self, value, owner: FakeTriageChatModel):
        self._value = value
        self._owner = owner

    def invoke(self, messages):
        self._owner.structured_output_messages = messages
        return self._value

    async def ainvoke(self, messages):
        return self.invoke(messages)


class CountingTriageChatModel(FakeTriageChatModel):
    """A ``FakeTriageChatModel`` that also counts its structured-output calls.

    The router's bounded safety retry re-runs synthesis between attempts, so the
    node-4 and router suites assert how many times the LLM was invoked.
    """

    def __init__(
        self,
        structured_output_value=None,
        structured_output_values_by_schema=None,
    ) -> None:
        super().__init__(
            structured_output_value=structured_output_value,
            structured_output_values_by_schema=structured_output_values_by_schema,
        )
        self.structured_output_invoke_count = 0

    def with_structured_output(self, schema):
        return _CountingStructuredOutputRunnable(super().with_structured_output(schema), self)


class _CountingStructuredOutputRunnable:
    def __init__(self, runnable, owner: CountingTriageChatModel) -> None:
        self._runnable = runnable
        self._owner = owner

    def invoke(self, messages):
        self._owner.structured_output_invoke_count += 1
        return self._runnable.invoke(messages)

    async def ainvoke(self, messages):
        self._owner.structured_output_invoke_count += 1
        return await self._runnable.ainvoke(messages)
