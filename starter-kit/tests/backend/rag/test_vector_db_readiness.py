from app.rag.vector_db_readiness import wait_for_vector_db_ready

FAKE_READINESS_MAX_ATTEMPTS = 3
FAKE_READINESS_DELAY_SECONDS = 0.0


class FakeQdrantClient:
    def __init__(self, failures_before_success: int):
        self._failures_before_success = failures_before_success
        self.call_count = 0

    def get_collections(self):
        self.call_count += 1
        if self.call_count <= self._failures_before_success:
            raise ConnectionError("qdrant unreachable")
        return []


def test_wait_for_vector_db_ready_succeeds_immediately_when_already_reachable():
    client = FakeQdrantClient(failures_before_success=0)

    assert wait_for_vector_db_ready(
        client, FAKE_READINESS_MAX_ATTEMPTS, FAKE_READINESS_DELAY_SECONDS
    )
    assert client.call_count == 1


def test_wait_for_vector_db_ready_succeeds_after_transient_failures():
    client = FakeQdrantClient(failures_before_success=2)

    assert wait_for_vector_db_ready(
        client, FAKE_READINESS_MAX_ATTEMPTS, FAKE_READINESS_DELAY_SECONDS
    )
    assert client.call_count == 3


def test_wait_for_vector_db_ready_returns_false_after_exhausting_all_attempts():
    client = FakeQdrantClient(failures_before_success=FAKE_READINESS_MAX_ATTEMPTS + 1)

    assert not wait_for_vector_db_ready(
        client, FAKE_READINESS_MAX_ATTEMPTS, FAKE_READINESS_DELAY_SECONDS
    )
    assert client.call_count == FAKE_READINESS_MAX_ATTEMPTS
