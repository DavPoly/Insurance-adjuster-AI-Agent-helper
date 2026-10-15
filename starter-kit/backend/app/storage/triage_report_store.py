from threading import Lock


class TriageReportStore:
    """In-process store for completed triage reports and their agent traces,
    keyed by claim_id. Not persisted across restarts or shared across
    processes — adequate for this single-process deployment, not a
    production-grade claim store.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._reports: dict[str, dict] = {}
        self._traces: dict[str, dict] = {}

    def save(self, claim_id: str, report: dict, trace: dict) -> None:
        with self._lock:
            self._reports[claim_id] = report
            self._traces[claim_id] = trace

    def get_report(self, claim_id: str) -> dict | None:
        return self._reports.get(claim_id)

    def get_trace(self, claim_id: str) -> dict | None:
        return self._traces.get(claim_id)


_triage_report_store = TriageReportStore()


def get_triage_report_store() -> TriageReportStore:
    return _triage_report_store
